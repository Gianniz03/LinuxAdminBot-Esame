import asyncio
from asyncio.log import logger
from telegram import Update
from telegram.ext import ContextTypes
import paramiko
from config.config import MONITORED_COMPUTERS, PATH_PRG
from .utils import get_ssh_project_path, find_computer_by_name

# Mappa dei tipi di monitoraggio e script associati
MONITOR_TYPES = {
    "ram": str(PATH_PRG / "scripts/ram_monitor.sh"),
    "cpu": str(PATH_PRG / "scripts/cpu_monitor.sh"),
    # Qui si possono aggiungere altri tipi di monitoraggio
}

# Inizializza dizionari per tracciare i processi di monitoraggio
MONITOR_PROCESSES = {}
for monitor_type in MONITOR_TYPES:
    MONITOR_PROCESSES[monitor_type] = {}  # {user_id: {computer_name: channel}}

# Inizializza dizionari per tracciare gli ultimi messaggi inviati
MONITOR_LAST_MSG = {}
for monitor_type in MONITOR_TYPES:
    MONITOR_LAST_MSG[monitor_type] = {}  # {user_id: {computer_name: last_message_id}}

def get_reply_function(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Restituisce la funzione di risposta più adatta per l'update, oppure None se non disponibile.
    
    # Gestisce il caso in cui l'update sia una callback query (pulsante premuto)
    if hasattr(update, "callback_query") and update.callback_query:
        # Se possibile, preferisce modificare il messaggio esistente (edit_message_text)
        if hasattr(update.callback_query, "edit_message_text"):
            return update.callback_query.edit_message_text
            
        # Altrimenti, come fallback, invia un nuovo messaggio nella chat
        if hasattr(update, "effective_chat") and update.effective_chat:
            chat_id = update.effective_chat.id
            
            # Definisce una funzione interna per inviare un nuovo messaggio
            def send_message(text, parse_mode=None, disable_notification=False):
                return context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    disable_notification=disable_notification
                )
                
            return send_message
            
    return None

async def monitor_control(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str):
    # Gestisce l'attivazione/disattivazione del monitoraggio
    
    # Determina il tipo di monitoraggio
    if context.args and len(context.args) > 0:
        # Converte in minuscolo per uniformare l'input (case-insensitive)
        monitor_type = context.args[0].lower()
    else:
        # Prende il primo tipo disponibile come default
        # iter(MONITOR_TYPES) crea un iteratore dal dizionario (solo le chiavi)
        # next() restituisce il prossimo elemento, in questo caso il primo
        monitor_type = next(iter(MONITOR_TYPES))
    
    # Verifica che il tipo sia valido
    script_path = MONITOR_TYPES.get(monitor_type)
    if script_path is None:
        return
    
    # Gestisce le azioni
    if action == "on":
        await monitor_on(update, context, monitor_type, script_path)
    elif action == "off":
        await monitor_off(update, context, monitor_type)

async def monitor_on(update: Update, context: ContextTypes.DEFAULT_TYPE, monitor_type: str, script_path: str):
    # Attiva il monitoraggio (RAM/CPU) per il computer selezionato
    # Recupera dati utente e computer
    selected = context.user_data.get("selected_computer") if context.user_data else None
    user_id = update.effective_user.id if update.effective_user else None
    
    # Gestione errori base: se non è stato selezionato un computer, avvisa l'utente
    reply = get_reply_function(update, context)
    if not selected:
        if reply:
            await reply("❗ Devi prima selezionare un computer.")
        return

    # Verifica se monitoraggio già attivo
    user_monitors = MONITOR_PROCESSES[monitor_type].setdefault(user_id, {})
    if selected in user_monitors:
        if reply:
            await reply(f"⚠️ Monitoraggio {monitor_type.upper()} già attivo per {selected}!")
        return


    # Cerca il computer selezionato nella lista dei computer monitorati
    computer = find_computer_by_name(MONITORED_COMPUTERS, selected)
            
    if not computer:
        if reply:
            await reply("❗ Computer non trovato.")
        return

    # Connessione SSH e avvio monitoraggio
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # Connessione SSH al computer selezionato
        ssh.connect(computer["ip"], username=computer["user"], timeout=5)
        transport = ssh.get_transport()
        
        # Se il trasporto SSH non è disponibile, avvisa l'utente
        if not transport:
            if reply:
                await reply(f"❌ Errore avvio monitoraggio {monitor_type.upper()}: trasporto SSH non disponibile.")
            return
            
        # Apre una nuova sessione SSH e avvia lo script di monitoraggio remoto
        channel = transport.open_session()
        ssh_user = computer["user"]
        remote_path = get_ssh_project_path(ssh_user, PATH_PRG)
        remote_script_path = f"{remote_path}/scripts/{monitor_type}_monitor.sh"
        channel.exec_command(f"bash {remote_script_path}")

        # Salva il canale SSH per poterlo chiudere successivamente
        user_monitors[selected] = channel
        if reply:
            await reply(f"✅ Monitoraggio {monitor_type.upper()} attivato per {selected}!")
        # Avvia la lettura asincrona dell'output del monitoraggio
        asyncio.create_task(read_monitor_output_ssh(update, context, channel, selected, monitor_type, user_id))
    except Exception as e:
        if reply:
            await reply(f"❌ Errore avvio monitoraggio {monitor_type.upper()}: {e}")

async def monitor_off(update: Update, context: ContextTypes.DEFAULT_TYPE, monitor_type: str):
    # Disattiva il monitoraggio (RAM/CPU) per il computer selezionato
    
    # Recupera il computer selezionato dall'utente, se presente
    selected = None
    if context.user_data:
        selected = context.user_data.get("selected_computer")

    # Recupera l'id utente Telegram, se presente
    user_id = None
    if update.effective_user:
        user_id = update.effective_user.id    
    
    # Ottiene la funzione di risposta più adatta (edit o send message)
    reply = get_reply_function(update, context)
    
    # Se non è stato selezionato un computer, avvisa l'utente
    if not selected:
        if reply:
            await reply("❗ Devi prima selezionare un computer.")
        return

    # Recupera il dizionario dei monitoraggi attivi per il tipo richiesto
    user_monitors_dict = MONITOR_PROCESSES.get(monitor_type)
    if user_monitors_dict:
        user_monitors = user_monitors_dict.get(user_id, {})
    else:
        user_monitors = {}
    # Recupera il canale SSH associato al monitoraggio
    channel = user_monitors.get(selected)
    if not channel:
        # Se il monitoraggio non è attivo, avvisa l'utente
        if reply:
            await reply(f"⚠️ Monitoraggio {monitor_type.upper()} non attivo per {selected}!")
        return

    # Chiude il canale SSH e rimuove il monitoraggio dalla lista
    channel.close()
    user_monitors.pop(selected, None)
    if reply:
        await reply(f"✅ Monitoraggio {monitor_type.upper()} disattivato per {selected}!")

async def read_monitor_output_ssh(update, context, channel, selected, monitor_type, user_id):
    # Legge l'output dello script monitor via SSH e invia in HTML tabellare
    output_block = []

    # Recupera l'id della chat dove inviare i messaggi
    chat_id = None
    if hasattr(update, "effective_chat") and update.effective_chat:
        chat_id = update.effective_chat.id
    try:
        # Continua a leggere finché il canale SSH non segnala la fine
        while not channel.exit_status_ready():
            if channel.recv_ready():
                # Riceve e decodifica l'output dal canale SSH
                line = channel.recv(4096).decode()
                for decoded_line in line.splitlines():
                    output_block.append(decoded_line)
                    # Quando trova il marker di fine blocco, invia il messaggio
                    if "===END_MONITOR_BLOCK===" in decoded_line:
                        html_msg = (
                            f"<b>🔔 [{selected}] Monitoraggio {monitor_type.upper()}</b>\n"
                            f"<pre>{'\n'.join(output_block)}</pre>"
                        )
                        # Elimina il vecchio messaggio se esiste
                        user_last_msgs = MONITOR_LAST_MSG[monitor_type].get(user_id, {})
                        last_msg_id = user_last_msgs.get(selected)
                        if chat_id and last_msg_id:
                            try:
                                await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
                            except Exception:
                                pass  # Il messaggio potrebbe essere già stato eliminato
                        # Invia il nuovo messaggio con i dati aggiornati
                        if chat_id:
                            sent = await context.bot.send_message(chat_id=chat_id, text=html_msg, parse_mode="HTML")
                            MONITOR_LAST_MSG[monitor_type].setdefault(user_id, {})[selected] = sent.message_id
                        output_block = []
            await asyncio.sleep(0.5)
        # Alla fine, se ci sono ancora dati non inviati, invia l'ultimo messaggio
        if output_block and chat_id:
            html_msg = (
                f"<b>🔔 [{selected}] Monitoraggio {monitor_type.upper()}</b>\n"
                f"<pre>{'\n'.join(output_block)}</pre>"
            )
            user_last_msgs = MONITOR_LAST_MSG[monitor_type].get(user_id, {})
            last_msg_id = user_last_msgs.get(selected)
            if last_msg_id:
                try:
                    await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
                except Exception:
                    pass
            sent = await context.bot.send_message(chat_id=chat_id, text=html_msg, parse_mode="HTML")
            MONITOR_LAST_MSG[monitor_type].setdefault(user_id, {})[selected] = sent.message_id
    except Exception as e:
        # Logga eventuali errori nella lettura dell'output SSH
        logger.warning(f"Errore lettura output {monitor_type.upper()} monitor SSH: {e}")
    finally:
        # Rimuove il canale SSH dalla lista dei monitoraggi attivi
        if MONITOR_PROCESSES[monitor_type].get(user_id, None):
            MONITOR_PROCESSES[monitor_type][user_id].pop(selected, None)
        # Elimina il messaggio residuo alla fine del monitoraggio
        user_last_msgs = MONITOR_LAST_MSG[monitor_type].get(user_id, {})
        last_msg_id = user_last_msgs.pop(selected, None)
        if chat_id and last_msg_id:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=last_msg_id)
            except Exception:
                pass

# --- Handler unici e semplici ---

async def alert_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_control(update, context, "on")

async def alert_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await monitor_control(update, context, "off")
