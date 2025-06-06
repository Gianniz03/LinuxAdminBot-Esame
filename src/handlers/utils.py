import asyncio
from asyncio.log import logger
from datetime import datetime
import paramiko.ssh_exception 
from paramiko.ssh_exception import NoValidConnectionsError
from telegram import Update
from telegram.ext import ContextTypes
from config.config import GIOVANNI, ANTONINO, MONITORED_COMPUTERS, MAX_TELEGRAM_MESSAGE_LENGTH, PATH_PRG
from pathlib import Path
import html
# Importa typing la gestione dei tipi di dati in python
from typing import Dict, Any, List, Optional


LIST_OF_ADMINS = [GIOVANNI, ANTONINO]  

# Ottiene il percorso del progetto in modo dinamico sostituendo l'utente locale con l'utente SSH
# 
# Parametri:
#   ssh_user (str): Nome dell'utente SSH a cui mappare il percorso
#   local_path (Path): Percorso locale del progetto (oggetto Path)
#
# Ritorna:
#   str: Percorso del progetto mappato per l'utente SSH, o il percorso originale se non è possibile mapparlo
def get_ssh_project_path(ssh_user: str, local_path: Path) -> str:
    # Divide il percorso in componenti
    parts = local_path.parts
    
    # Cerca l'indice della cartella 'home' nel percorso
    try:
        home_idx = parts.index('home')
        # Ricostruisce il percorso sostituendo l'utente locale dopo 'home' con ssh_user
        # Esempio: /home/local_user/project -> /home/ssh_user/project
        new_parts = parts[:home_idx+1] + (ssh_user,) + parts[home_idx+2:]
        
        # L'asterisco (*) converte la tupla in argomenti separati:
        # Esempio: Path(*['home', 'ssh_user', 'project']) diventa Path('home', 'ssh_user', 'project')
        # Equivalente a scrivere manualmente: Path('home', 'ssh_user', 'project')
        return str(Path(*new_parts))
    except ValueError:
        # Se 'home' non è presente nel percorso, ritorna il percorso originale
        # (caso in cui il progetto non è nella home directory)
        return str(local_path)

def truncate_message(text, max_length=MAX_TELEGRAM_MESSAGE_LENGTH, html_tag_len=11):
    # Calcola lo spazio massimo disponibile per il contenuto, lasciando spazio per il tag HTML e il messaggio di troncamento
    max_content = max_length - html_tag_len - 15 
    # Se il testo supera la lunghezza massima consentita, lo tronca e aggiunge un avviso
    if len(text) > max_content:
        return text[:max_content] + "\n...[Messaggio troncato per Telegram]..."
    # Altrimenti restituisce il testo originale
    return text

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Middleware che verifica se l'utente è autorizzato 
    user = update.effective_user
    
    # Prepara i dati per il log
    nickname = ""
    if user and user.username:
        nickname = f"@{user.username}"
    else:
        nickname = "Nessun nickname"

    full_name = ""
    if user:
        first_name = user.first_name or ""
        last_name = user.last_name or ""
        # Strip elimina gli spazi inutili
        full_name = f"{first_name} {last_name}".strip()
    else:
        full_name = "Utente sconosciuto"
        
    log_data = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user.id if user else "unknown",
        "username": user.username if user and user.username else "no-username",
        "nickname": nickname,
        "full_name": full_name,
        "action": "access-authorized",
        "command": update.message.text if update.message else "callback-query"
    }
    
    if user is None or user.id not in LIST_OF_ADMINS:
        log_data["action"] = "access-denied"
        # Messaggio all'utente
        if update.message:
            await update.message.reply_text(
                f"🚫 Accesso negato - il tuo ID: {user.id if user else 'unknown'} - Nickname: {nickname} non appartiene agli Admin!"
            )
        elif update.callback_query:
            try:
                await update.callback_query.answer(
                    f"🚫 Accesso negato - ID: {user.id if user else 'unknown'} - Nickname: {nickname} non autorizzato", 
                    show_alert=True
                )
                await update.callback_query.edit_message_reply_markup(reply_markup=None)
            except Exception as e:
                logger.warning(f"Errore nella risposta accesso negato: {e}")
        
        # Scrittura su file di log dettagliato
        try:
            with open(PATH_PRG / 'logs/accessi_non_autorizzati.log', 'a', encoding='utf-8') as log_file:
                log_file.write(f"{log_data}\n")
        except Exception as e:
            logger.warning(f"Errore scrittura log accessi non autorizzati: {e}")
        
        # Log sulla console
        logger.warning(
            f"Accesso negato - "
            f"UserID: {log_data['user_id']}, "
            f"Nickname: {log_data['nickname']}, "
            f"Nome: {log_data['full_name']}, "
            f"Azione: {log_data['action']}, "
            f"Comando: {log_data['command']}"
        )
        
        return False
    
    # Log accesso autorizzato su file separato
    try:
        # Logga accessi admin autorizzati in un file dedicato.
        log_path = PATH_PRG / 'logs/accessi_autorizzati.log'
        with open(log_path, 'a', encoding='utf-8') as log_file:
            log_file.write(f"{log_data}\n")
    except Exception as e:
        logger.warning(f"Errore scrittura log accessi autorizzati: {e}")
    # Log accesso autorizzato sulla console
    logger.info(f"Accesso autorizzato per UserID: {user.id if user else 'unknown'}, Nickname: @{user.username if user and user.username else 'no-username'}")
    return True


async def execute_bash_command(update: Update, command: str, is_callback: bool = False, context=None):
    # Recupera il computer selezionato dall'user_data del context
    selected = None
    if context is not None:
        if hasattr(context, "user_data"):
            selected = context.user_data.get("selected_computer")

    if selected is None:
        msg = "❗ Devi prima selezionare un computer."
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        elif update.message:
            await update.message.reply_text(msg)
        return False

    # Cerca il computer selezionato nella lista dei computer monitorati
    computer = find_computer_by_name(MONITORED_COMPUTERS, selected)

    # Controlla se il computer è stato trovato nella lista MONITORED_COMPUTERS
    if computer is None:
        msg = "❗ Computer non trovato."

        # Invia il messaggio in modo diverso a seconda del tipo di richiesta:
        # - Se è una callback (es. da tastiera inline)
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(msg)
        # - Se è un messaggio normale
        elif update.message:
            await update.message.reply_text(msg)
            
        # Interrompe l'esecuzione della funzione
        return False

    try:
        # Configurazione connessione SSH
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(computer["ip"], username=computer["user"], timeout=5)
        
        # Esegue lo script remoto passando il comando come parametro
        remote_path = get_ssh_project_path(computer["user"], PATH_PRG)
        script_path = f"{remote_path}/scripts/linux_admin.sh"
        stdin, stdout, stderr = ssh.exec_command(f"bash {script_path} {command}")
        
        # Elaborazione output con gestione errori e formattazione per Telegram
        output = stdout.read().decode() + stderr.read().decode()
        
        # Escape HTML special characters before wrapping in <pre> tags
        escaped_output = html.escape(output)
        escaped_output = truncate_message(escaped_output)
        escaped_output = f"<pre>{escaped_output}</pre>"
        
        ssh.close()
        
        # Invio risposta differenziato tra callback e messaggi diretti
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(escaped_output, parse_mode="HTML")
        elif update.message:
            await update.message.reply_text(escaped_output, parse_mode="HTML")
    
    # Gestione errori specifici di connessione SSH
    except (NoValidConnectionsError, TimeoutError, OSError) as e:
        error_msg = "❌ Il computer non è raggiungibile."
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(error_msg, parse_mode="HTML")
        elif update.message:
            await update.message.reply_text(error_msg, parse_mode="HTML")
        return False
    
    # Catch-all per altri errori imprevisti (mostra dettagli errore)
    except Exception as e:
        error_msg = str(e)
        if is_callback and update.callback_query:
            await update.callback_query.edit_message_text(f"❌ Errore:\n<pre>{html.escape(error_msg)}</pre>", parse_mode="HTML")
        elif update.message:
            await update.message.reply_text(f"❌ Errore:\n<pre>{html.escape(error_msg)}</pre>", parse_mode="HTML")
        return False
    
    return True

async def is_host_reachable(ip):
    # Restituisce True se il PC risponde al ping, False altrimenti.
    try:
        # Esegue il comando ping in modo asincrono (1 pacchetto, timeout 1 secondo)
        proc = await asyncio.create_subprocess_exec(
            "ping", "-c", "1", "-W", "1", ip,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.communicate()
        # Restituisce True se il codice di ritorno è 0 (host raggiungibile)
        return proc.returncode == 0
    except Exception as e:
        # Logga eventuali errori e restituisce False
        logger.warning(f"Ping fallito per {ip}: {e}")
        return False
    
# La funzione ricerca il computer scelto nella lista di computer monitorati [Lista di dizionari] e restituisce il primo dizionario trovato con il nome corrispondente.
def find_computer_by_name(computers: List[Dict[str, Any]], target_name: str) -> Optional[Dict[str, Any]]:
    for computer in computers:
        if computer["name"] == target_name:
            return computer
    return None