#!/bin/bash

# Imposta la data/ora di inizio per l'estrazione dei log
# (ultime 24 ore rispetto al momento dell'esecuzione)
since=$(date --date='24 hours ago' '+%Y-%m-%d %H:%M:%S')


# Ottiene il percorso assoluto dello script in esecuzione:
# 1. "$0" contiene il nome dello script
# 2. "readlink -f" risolve i link simbolici e dà il percorso assoluto
# 3. "dirname" estrae solo la directory (senza il nome del file)
SCRIPT_DIR=$(dirname "$(readlink -f "$0")")
# File di log dove verranno salvati i dati di utilizzo CPU
LOGFILE="${SCRIPT_DIR}/../logs/syslog.log"




# Livelli di log da analizzare nel riepilogo
# I livelli sono quelli standard di syslog/journald
levels="INFO ERROR WARNING DEBUG CRITICAL"

# Estrae tutti i log di sistema delle ultime 24 ore
# utilizzando journalctl e li salva in un file temporaneo
journalctl --since "$since" > "$LOGFILE.tmp"

# Calcola il numero totale di log estratti
total=$(wc -l < "$LOGFILE.tmp")

# Crea il file di output con un riepilogo iniziale
echo "===== RIEPILOGO LOG ULTIME 24 ORE =====" > "$LOGFILE"
echo "Totale log: $total" >> "$LOGFILE"

# Per ogni livello di log, conta le occorrenze e le aggiunge al riepilogo
for level in $levels; do
    # Conta le righe che contengono esattamente il livello di log
    count=$(grep -c "\b$level\b" "$LOGFILE.tmp")
    echo "$level: $count" >> "$LOGFILE"
done

# Aggiunge una linea di separazione al riepilogo
echo "=======================================" >> "$LOGFILE"
echo "" >> "$LOGFILE"

# Aggiunge tutti i log estratti dopo il riepilogo
cat "$LOGFILE.tmp" >> "$LOGFILE"

# Elimina il file temporaneo
rm "$LOGFILE.tmp"