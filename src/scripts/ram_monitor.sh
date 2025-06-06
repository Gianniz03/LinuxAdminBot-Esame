#!/bin/bash

THRESHOLD=95
CHECK_INTERVAL=30
MAX_PROCESSES=10

while true; do
    echo "Monitoraggio RAM attivo (soglia: ${THRESHOLD}%)"

    # Calcola la percentuale di RAM usata:
    # free: mostra info memoria
    # awk: calcola % RAM usata come (totale - disponibile)/totale * 100
    RAM_PERCENT=$(free | awk '/Mem:/ {printf("%.0f"), ($2-$7)/$2 * 100}')

    # Se superata la soglia, mostra processi più affamati di RAM
    if [[ $RAM_PERCENT -gt $THRESHOLD ]]; then
        echo -e "RAM al ${RAM_PERCENT}% (soglia: ${THRESHOLD}%) [$(date +'%H:%M:%S')]"

        # Mostra tabella processi con intestazione formattata
        printf "\n%-8s %-10s %-6s %-8s %s\n" "PID" "USER" "%MEM" "SIZE(MB)" "COMMAND"
        
        # Estrae processi ordinati per uso RAM:
        # ps -eo: lista processi con colonne specifiche
        # --sort=-%mem: ordina per %RAM decrescente
        # head: limita ai primi MAX_PROCESSES
        # awk: converte RSS in MB e formatta output
        ps --no-headers -eo pid,user,%mem,rss,comm --sort=-%mem | head -n $MAX_PROCESSES | awk '{
                size_mb = $4/1024;
                printf "%-8s %-10s %-6s %-8.1f %s\n", $1, $2, $3, size_mb, $5
            }'

        echo -e ""
        echo "===END_MONITOR_BLOCK==="
    fi

    # Attesa tra un check e l'altro
    sleep $CHECK_INTERVAL
done
