#!/bin/bash
# Uso: ./add_monitored_computer.sh utente ip

# Controlla che vengano passati esattamente 2 argomenti
if [ $# -ne 2 ]; then
  echo "Uso: $0 nomeutente iputente"
  exit 1
fi

# Carica la variabile KEY_PATH dal file di configurazione
source "$(dirname "$0")/../config/ssh_key.env"

ssh-copy-id -i "$KEY_PATH" "$1@$2"
echo "Chiave pubblica copiata su $1@$2"