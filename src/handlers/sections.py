from telegram import Update
from telegram.ext import ContextTypes

async def _send_section_intro(update: Update, intro: str):
    # Invia o modifica il messaggio di introduzione della sezione.
    callback_query = getattr(update, "callback_query", None)
    if callback_query is not None:
        return await callback_query.edit_message_text(intro, parse_mode="HTML")
    elif hasattr(update, "message") and update.message is not None:
        return await update.message.reply_text(intro, parse_mode="HTML")

async def show_monitor_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
📈 <b>Monitoraggio Sistema</b>

Visualizza in tempo reale lo stato delle risorse del computer selezionato:
• Top 10 processi per uso CPU/memoria
• Carico medio del sistema (load average)
• Statistiche I/O dei dischi (iostat)
• Statistiche memoria virtuale (vmstat)
• Servizi attivi in esecuzione

<i>Scegli un'opzione dal menu per ricevere i dati aggiornati dal sistema remoto</i>
"""
    await _send_section_intro(update, intro)

async def show_packages_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
📦 <b>Gestione Pacchetti</b>

Consulta informazioni sui pacchetti installati sul sistema remoto:
• Elenco dei pacchetti installati manualmente
• Verifica aggiornamenti disponibili tramite il package manager
• Supporto per sistemi basati su apt, dnf, pacman, rpm

<i>Seleziona un'opzione per visualizzare o cercare i pacchetti</i>
"""
    await _send_section_intro(update, intro)

async def show_hardware_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
🖥️ <b>Informazioni Hardware</b>

Ottieni dettagli hardware e sistema operativo dal computer selezionato:
• Specifiche CPU (modello, core, frequenza)
• Stato e temperatura dei sensori hardware
• Elenco dispositivi di archiviazione e partizioni
• Versione kernel e distribuzione Linux

<i>Seleziona un'opzione per visualizzare le informazioni hardware o di sistema</i>
"""
    await _send_section_intro(update, intro)

async def show_network_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
🌐 <b>Rete & Sicurezza</b>

Strumenti per la diagnostica e il controllo della rete:
• Visualizza interfacce di rete e indirizzi IP
• Elenco delle connessioni attive (porte aperte)
• Visualizza traffico di rete (richiede vnstat)
• Mostra configurazione DNS
• Stato e configurazione del servizio SSH

<i>Seleziona un'opzione per ottenere informazioni di rete o sicurezza</i>
"""
    await _send_section_intro(update, intro)
    
async def show_utility_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
🧰 <b>Utilità di Sistema</b>

Strumenti rapidi per la gestione e la diagnostica:
• Visualizzazione ultimi log di sistema (journalctl)
• Visualizzazione ultimi comandi sudo eseguiti
• Uptime e carico medio del sistema

<i>Seleziona un'opzione dal menu per accedere alle utilità</i>
"""
    await _send_section_intro(update, intro)
    
async def show_graphs_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
📊 <b>Grafici di Sistema</b>

Visualizza grafici generati in tempo reale dal sistema remoto:
• Andamento utilizzo CPU nelle ultime 24 ore (richiede sysstat/sar)
• Analisi dettagliata della RAM (pie chart su categorie memoria)
• Distribuzione dei log di sistema per livello (INFO, ERROR, ecc.)

<i>Seleziona un grafico dal menu per ricevere l'immagine aggiornata</i>
"""
    await _send_section_intro(update, intro)

async def show_alerts_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = """
🚨 <b>Allerta Risorse</b>

Attiva il monitoraggio live delle risorse critiche:
• Notifiche automatiche quando la RAM supera la soglia critica
• Notifiche automatiche quando la CPU supera la soglia critica
• Visualizzazione processi responsabili in caso di allerta

<i>Attiva o disattiva gli alert dal menu sottostante</i>
"""
    await _send_section_intro(update, intro)