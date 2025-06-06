# Importa il modulo logging per la gestione dei log
import logging
# Importa la libreria per la gestione delle applicazioni Telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from config.config import BOT_TOKEN
from handlers.button import button_handler
from handlers.commands import menu, start

# Configura il logging per mostrare informazioni utili durante l'esecuzione
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

def main():
    # Inizializza l'applicazione Telegram con il token del bot
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN non è impostato. Fornisci un token valido in config/config.py.")
    
    # Crea l'applicazione Telegram con il token fornito
    app = Application.builder().token(BOT_TOKEN).build()
    # Configurazione dei comandi del bot
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    # Aggiunge il gestore per le callback dei pulsanti inline
    app.add_handler(CallbackQueryHandler(button_handler, pattern=".*")) # type: ignore
    # Avvia il polling per ricevere gli aggiornamenti da Telegram
    app.run_polling()

if __name__ == "__main__":
    main()