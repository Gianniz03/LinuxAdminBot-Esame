#!/bin/bash

THRESHOLD=95
CHECK_INTERVAL=30
MAX_PROCESSES=10

while true; do
    echo "Monitoraggio CPU attivo (soglia: ${THRESHOLD}%)"
    
    # Calcola la percentuale di CPU usata (media su tutti i core):
    # top -bn2: esegue top in modalità batch per 2 iterazioni
    # grep: filtra la riga con le statistiche CPU
    # tail: prende l'ultima lettura (più stabile)
    # awk: calcola %CPU usata come 100 - %idle
    CPU_PERCENT=$(top -bn2 | grep "Cpu(s)" | tail -n 1 | awk '{print 100 - $8}' | awk '{printf("%.0f", $1)}')

    # Se superata la soglia, mostra processi più affamati di CPU
    if [[ $CPU_PERCENT -gt $THRESHOLD ]]; then
        echo -e "CPU al ${CPU_PERCENT}% (soglia: ${THRESHOLD}%) [$(date +'%H:%M:%S')]"

        # Mostra tabella processi con intestazione formattata
        printf "\n%-8s %-10s %-6s %s\n" "PID" "USER" "%CPU" "COMMAND"
        
        # Estrae processi ordinati per uso CPU:
        # ps -eo: lista processi con colonne specifiche
        # --sort=-%cpu: ordina per %CPU decrescente
        # head: limita ai primi MAX_PROCESSES
        # awk: formatta l'output
        ps --no-headers -eo pid,user,%cpu,comm --sort=-%cpu | head -n $MAX_PROCESSES | awk '{
            printf "%-8s %-10s %-6s %s\n", $1, $2, $3, $4
        }'

        echo -e ""
        echo "===END_MONITOR_BLOCK==="
    fi

    # Attesa tra un check e l'altro
    sleep $CHECK_INTERVAL
done