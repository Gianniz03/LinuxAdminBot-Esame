#!/bin/bash

# Ottiene il percorso assoluto dello script in esecuzione:
# 1. "$0" contiene il nome dello script
# 2. "readlink -f" risolve i link simbolici e dà il percorso assoluto
# 3. "dirname" estrae solo la directory (senza il nome del file)
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# File di log dove verranno salvati i dati di utilizzo CPU
LOGFILE="${SCRIPT_DIR}/../logs/cpu_usage.log"



# Data corrente nel formato YYYY-MM-DD
TODAY=$(date +%Y-%m-%d)

# Imposta la localizzazione numerica in inglese per garantire
# che i numeri decimali usino il punto (.) invece della virgola (,)
export LC_NUMERIC=C

# Intestazione CSV per il file di log
echo "timestamp,cpu_percent" > "$LOGFILE"

# Analizza l'output del comando 'sar' per ottenere l'utilizzo CPU
# -u: mostra statistiche CPU
# -s 00:00:00: inizia dalla mezzanotte
sar -u -s 00:00:00 | grep " all " | while read -r line; do
    # Estrae l'ora dal report (primo campo)
    ORA=$(echo "$line" | awk '{print $1}')
    # Estrae la percentuale di CPU idle (ottavo campo)
    # Sostituisce eventuali virgole con punti per il formato decimale
    IDLE=$(echo "$line" | awk '{print $8}' | tr ',' '.')
    
    # Calcola la percentuale di utilizzo CPU:
    # 100% - percentuale idle = percentuale utilizzata
    # Formattato con 2 decimali
    CPU=$(awk "BEGIN {printf \"%.2f\", 100 - $IDLE}")
    
    # Scrive nel file di log la data, ora e percentuale CPU utilizzata
    echo "$TODAY $ORA,$CPU" >> "$LOGFILE"
done

# Calcola e registra la media dell'utilizzo CPU giornaliero
# -F,: usa la virgola come separatore di campo
# NR>1: salta la prima riga (intestazione)
# !/Media:/: esclude eventuali righe già contenenti medie
AVG=$(awk -F, 'NR>1 && !/Media:/ {sum+=$2; count++} END {if(count>0) printf "%.2f", sum/count}' "$LOGFILE")
echo "$TODAY Media:,$AVG" >> "$LOGFILE"