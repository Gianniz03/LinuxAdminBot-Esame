from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.config import PATH_PRG, MONITORED_COMPUTERS
from .utils import check_admin, is_host_reachable


#########################      START      #########################

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Ottieni la parte relativa dopo /home/<utente>/
    prg_parts = PATH_PRG.parts
    try:
        home_idx = prg_parts.index("home")
        relative_path = "/".join(prg_parts[home_idx+2:])  # salta anche il nome utente
    except ValueError:
        relative_path = str(PATH_PRG)

    intro = (
        "👋 <b>Benvenuto in LinuxAdminBot!</b>\n\n"
        "Questo bot ti permette di:\n"
        "• Monitorare in tempo reale CPU, RAM, dischi e rete dei tuoi server Linux\n"
        "• Visualizzare grafici e statistiche di sistema\n"
        "• Gestire pacchetti, servizi, hardware e configurazioni di rete\n"
        "• Eseguire comandi amministrativi in modo sicuro via SSH\n"
        "• Ricevere alert automatici su risorse critiche\n"
        "• Consultare log di sistema e informazioni dettagliate sull’hardware\n\n"
        "<b>Comandi principali:</b>\n"
        "• /menu — Mostra il menu principale\n"
        "• /start — Mostra questa presentazione\n"
        "• Usa i bottoni per navigare tra le sezioni e le funzioni avanzate\n\n"
        "⚠️ <b>Avvertenza</b>:\n"
        "Se si riscontrano problemi relativi a file o cartella non trovata, "
        f"si prega di clonare il progetto nella propria home in:\n<code>~/{relative_path}</code>"
    )
    if update.message is not None:
        await update.message.reply_text(intro, parse_mode="HTML")


#########################      MENU      #########################

def get_menu_keyboard():
    # Crea una tastiera inline con i pulsanti per le varie sezioni del menu
    return [
        [InlineKeyboardButton("📈 Monitoraggio", callback_data="monitor_section")],
        [
            InlineKeyboardButton("⚙️ Top 10 Processi", callback_data="processes"),
            InlineKeyboardButton("📊 Risorse", callback_data="resources")
        ],
        [
            InlineKeyboardButton("📶 Carico Medio Sistema", callback_data="loadavg"),
            InlineKeyboardButton("💾 Statistiche I/O", callback_data="iostat")
        ],
        [
            InlineKeyboardButton("🧠 Statistiche Memoria Virtule", callback_data="vmstat"),
            InlineKeyboardButton("🛠️ Servizi Attivi", callback_data="services")
        ],
        [InlineKeyboardButton("🖥️ Hardware - OS", callback_data="hardware_section")],
        [
            InlineKeyboardButton("🖥️ Hardware Info", callback_data="hardware"),
            InlineKeyboardButton("🐧 Versione Kernel - OS", callback_data="info_kernel_os")
        ],
        [InlineKeyboardButton("📦 Pacchetti", callback_data="packages_section")],
        [
            InlineKeyboardButton("📦 Lista Pacchetti", callback_data="packages"),
            InlineKeyboardButton("🔄 Aggiornamenti", callback_data="updates")
        ],
        [InlineKeyboardButton("🌐 Rete", callback_data="network_section")],
        [
            InlineKeyboardButton("📡 Network Info", callback_data="network"),
            InlineKeyboardButton("🌍 DNS", callback_data="dns"),
            InlineKeyboardButton("🔐 SSH", callback_data="ssh")
        ],
        [InlineKeyboardButton("🧰 Utilità", callback_data="utility_section")],
        [
            InlineKeyboardButton("📜 Log", callback_data="logs"),
            InlineKeyboardButton("📜 Log Sudo", callback_data="sudolog"),
            InlineKeyboardButton("⏱️ Uptime", callback_data="uptime")
        ],
        [InlineKeyboardButton("📊 Grafici", callback_data="graphs_section")],
        [
            InlineKeyboardButton("🧾 Grafico CPU", callback_data="CPU_graph"),
            InlineKeyboardButton("🧾 Grafico RAM", callback_data="RAM_graph"),
            InlineKeyboardButton("🧾 Grafico LOG", callback_data="LOG_graph")
        ],
        [InlineKeyboardButton("🔔 Alert", callback_data="alerts_section")],
        [
            InlineKeyboardButton("🟢 RAM Monitor ON", callback_data="alert_on"),
            InlineKeyboardButton("🔴 RAM Monitor OFF", callback_data="alert_off"),
            InlineKeyboardButton("🟢 CPU Monitor ON", callback_data="cpu_alert_on"),
            InlineKeyboardButton("🔴 CPU Monitor OFF", callback_data="cpu_alert_off")
        ]
    ]

async def get_computer_keyboard():
    # Inizializza una lista vuota per la keyboard
    keyboard = []

    # Crea una lista di task asincroni per verificare lo stato dei computer
    tasks = []
    for computer in MONITORED_COMPUTERS:
        # Per ogni computer monitorato, crea un task per verificare se è raggiungibile
        task = is_host_reachable(computer["ip"])
        tasks.append(task)
    
    # Esegue tutti i task in parallelo e raccoglie i risultati
    statuses = []
    for task in tasks:
        # Attende il completamento di ogni task e salva lo stato
        status = await task
        statuses.append(status)

    # Crea i pulsanti per la keyboard in base allo stato dei computer
    for computer, online in zip(MONITORED_COMPUTERS, statuses):
        # Sceglie l'emoji verde se online, rosso se offline
        status_emoji = "🟢" if online else "🔴"
        keyboard.append([
            # Crea un pulsante inline con:
            # - emoji dello stato
            # - nome del computer
            # - indirizzo IP
            # - callback data con il nome del computer
            InlineKeyboardButton(
                f"{status_emoji} {computer['name']} ({computer['ip']})",
                callback_data=f"select_computer:{computer['name']}"
            )
        ])
    return keyboard

async def menu(update, context):
    if not await check_admin(update, context):
        return
    keyboard = await get_computer_keyboard()
    await update.message.reply_text(
        "💻 Seleziona il computer da monitorare:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )

