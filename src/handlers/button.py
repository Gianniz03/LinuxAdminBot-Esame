import asyncio
from asyncio.log import logger
from .utils import check_admin, execute_bash_command, is_host_reachable, find_computer_by_name
from .commands import get_menu_keyboard
from .monitor import *
from .graphs import *
from .sections import *
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from config.config import MONITORED_COMPUTERS

# Gestisce le callback dei bottoni inline nel bot Telegram.
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    # Verifica se l'utente è admin, altrimenti esce
    if not await check_admin(update, context):
        return

    # Controlla che la callback query sia presente e valida
    if query is None:
        return
    if not hasattr(query, "data"):
        return
    if not isinstance(query.data, str):
        return

    # Risponde alla callback query per evitare timeout lato Telegram
    try:
        await query.answer()
    except Exception as e:
        logger.warning(f"Errore nella risposta alla callback query: {e}")

    # Gestione selezione computer
    if query.data.startswith("select_computer:"):
        # Estrae il nome del computer selezionato dalla stringa della callback
        selected = query.data.split(":", 1)[1]
        computer = find_computer_by_name(MONITORED_COMPUTERS, selected)
        if not computer:
            try:
                await query.edit_message_text("❗ Computer non trovato.")
            except Exception:
                await query.answer("❗ Computer non trovato.", show_alert=True)
            return
        
        # Verifica se il computer è raggiungibile 
        is_online = await is_host_reachable(computer["ip"])
        if not is_online:
            try:
                await query.edit_message_text(f"❌ Il computer <b>{selected}</b> non è raggiungibile.", parse_mode="HTML")
            except Exception:
                await query.answer(f"❌ Il computer {selected} non è raggiungibile.", show_alert=True)
            return
        
        if not hasattr(context, "user_data"):
            context.user_data = {}
        elif context.user_data is None:
            context.user_data = {}
            
        context.user_data["selected_computer"] = selected

        try:
            await query.edit_message_text(
                f"✅ Computer selezionato: <b>{selected}</b>\nScegli un'operazione:",
                reply_markup=InlineKeyboardMarkup(get_menu_keyboard()),
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Errore nell'apertura del menu operazioni: {e}")
        return
    
    # Salva il valore della callback
    data = query.data

    # Gestione callback grafici
    if data in graphs_handlers:
        print(data)
        await handle_graph(update, context, graphs_handlers[data])
        return

    # Gestione alert
    if data in alert_map:
        action, monitor_type = alert_map[data]
        await handle_alert(update, context, action, monitor_type)
        return

    # Gestione sezioni
    if data in section_handlers:
        await section_handlers[data](update, context)
        await asyncio.sleep(1)
        return

    # Default: esegui comando bash
    await execute_bash_command(update, data, is_callback=True, context=context)
    await asyncio.sleep(1)


#########################         FUNZIONI         #########################    


#########################      MAPPA CALLBACKS      #########################


# Mappa tutte le callback a funzioni handler

# Grafici
async def handle_graph(update, context, graph_func):
    await graph_func(update, context)
    await asyncio.sleep(1)

# Alert
async def handle_alert(update, context, action, monitor_type):
    context.args = [monitor_type]
    if action == "on":
        await alert_on(update, context)
    else:
        await alert_off(update, context)
    await asyncio.sleep(1)

# Dispatcher per callback grafici
graphs_handlers = {
    "CPU_graph": send_cpu_graph,
    "RAM_graph": send_ram_graph,
    "LOG_graph": send_log_graph,
}

# Dispatcher per sezioni
section_handlers = {
    'monitor_section': show_monitor_section,
    'packages_section': show_packages_section,
    'hardware_section': show_hardware_section,
    'network_section': show_network_section,
    'utility_section': show_utility_section,
    'graphs_section': show_graphs_section,
    'alerts_section': show_alerts_section,
}

# Dispatcher per alert
alert_map = {
    "alert_on": ("on", "ram"),
    "alert_off": ("off", "ram"),
    "cpu_alert_on": ("on", "cpu"),
    "cpu_alert_off": ("off", "cpu"),
}
