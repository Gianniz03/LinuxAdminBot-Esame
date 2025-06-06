import json
from os import getenv
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# GESTIONE PATH DEL PROGETTO
PATH_PRG = Path(__file__).resolve().parent.parent

# GESTIONE DELLA CONFIGURAZIONE ENV
BOT_TOKEN = getenv("BOT_TOKEN")

# Converte gli ID in interi
GIOVANNI_ENV = getenv("GIOVANNI")
ANTONINO_ENV = getenv("ANTONINO")

if GIOVANNI_ENV is None:
    raise ValueError("La variabile d'ambiente 'GIOVANNI' non è impostata")
if ANTONINO_ENV is None:
    raise ValueError("La variabile d'ambiente 'ANTONINO' non è impostata")

GIOVANNI = int(GIOVANNI_ENV)
ANTONINO = int(ANTONINO_ENV)

# GESTIONE COMPUTER MONITORATI
with open(PATH_PRG / 'config/monitored_computers.json', 'r', encoding='utf-8') as f:
    MONITORED_COMPUTERS = json.load(f)

MAX_TELEGRAM_MESSAGE_LENGTH = int(getenv("MAX_TELEGRAM_MESSAGE_LENGTH", "4096"))
