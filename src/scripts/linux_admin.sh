#!/bin/bash
# Script unificato per tutte le operazioni di sistema


### MONITORAGGIO SISTEMA ###

function show_processes() {
    # Mostra i processi attivi con la lista dei parametri seguenti:
    # -eo: elenca i processi con i seguenti parametri:
    #   user: nome utente proprietario del processo
    #   pid: numero di processo
    #   %cpu: percentuale di CPU usata
    #   %mem: percentuale di memoria usata
    #   rss: Resident Set Size, la memoria residente in RAM
    #   time: tempo di esecuzione del processo
    #   comm: nome del comando eseguito
    # --sort=-%cpu: ordina la lista per utente e poi per utilizzo di CPU decrescente
    # --width=120: larghezza massima per la stampa di ogni riga
    # head -n 11: seleziona le prime 11 righe dell'elenco, ovvero i 10 processi con maggiore utilizzo di CPU
    echo "📊 PROCESSI ATTIVI (TOP 10)"
    ps -eo user,pid,%cpu,%mem,rss,time,comm --sort=-%cpu --width=120 | head -n 11 | \
    awk 'BEGIN {printf "%-8s %-6s %-5s %-5s %-8s %-10s %s\n", "USER", "PID", "%CPU", "%MEM", "RSS", "TIME", "PROCESS"} 
         NR>1 {printf "%-8s %-6s %-5s %-5s %-8s %-10s %s\n", $1, $2, $3, $4, $5/1024 "MB", $6, $7}'
}

# Recupera informazioni dettagliate sulla CPU
function get_cpu_info() {
    # Percentuale CPU usata
    cpu_usage=$(top -bn1 | grep '%Cpu(s)' | awk '{printf "%.1f", $2}')
    
    # Temperatura CPU (supporta diversi metodi di lettura)
    if [ -f /sys/class/hwmon/hwmon0/temp1_input ]; then
        cpu_temp=$(($(cat /sys/class/hwmon/hwmon*/temp*_input | head -1)/1000)) # /1000 serve per convertire in gradi Celsius 
    elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        cpu_temp=$(($(cat /sys/class/thermal/thermal_zone0/temp)/1000))
    else
        # sensors restituisce una stringa come "47.5°C" quindi ci serve cut per prendere solo i primi due caratteri (il numero) e non il simbolo di gradi
        cpu_temp=$(sensors | grep 'Package id' | awk '{print $4}' | cut -c2-3)
    fi
    
    echo -e "🖥️ CPU:"
    echo -e "• Uso: ${cpu_usage}%"
    echo -e "• Temperatura: ${cpu_temp}°C"
}

# Recupera e mostra informazioni dettagliate sull'utilizzo della RAM
function get_ram_info() {
    # Legge i valori totali, usati e liberi della RAM in MB usando il comando free
    # -m: mostra i valori in megabyte
    # awk '/Mem:/: filtra solo la riga relativa alla memoria principale
    # print $2,$3,$4: estrae i valori totali, usati e liberi
    read -r total used free <<< $(free -m | awk '/Mem:/ {print $2,$3,$4}')
    
    # Calcola le percentuali di memoria usata e libera
    perc_used=$((used*100/total))
    perc_free=$((free*100/total))
    
    echo -e "\n🧠 RAM:"
    echo -e "• Totale: ${total} MB"
    echo -e "• Usata: ${used} MB (${perc_used}%)"
    echo -e "• Libera: ${free} MB (${perc_free}%)"
}

# Mostra statistiche di rete con informazioni su download/upload
function get_network_info() {
    # Verifica se vnstat è installato per ottenere metriche più accurate
    # command -v verifica la presenza del comando nel sistema
    if command -v vnstat &> /dev/null; then
        echo -e "\n🌐 RETE:"
        # vnstat -tr 2: mostra traffico in tempo reale con:
        #   -t: traffico
        #   -r: aggiornamento ogni 2 secondi
        # grep -A 2 'rx': filtra righe relative a download (rx) e le 2 righe successive
        # awk: formatta l'output convertendo i valori:
        #   $2/1024*8: converte da KB/s a Mb/s (1KB = 8Kb)
        vnstat -tr 2 | grep -A 2 'rx' | awk '
            /rx/ {printf "• Download: %.2f Mb/s\n", $2/1024*8}
            /tx/ {printf "• Upload: %.2f Mb/s\n", $2/1024*8}'
    else
        # Messaggio alternativo se vnstat non è installato
        echo -e "\n🌐 RETE:"
        echo "Installare vnstat per i dati di rete"
    fi
}

# Mostra informazioni sull'utilizzo del disco
function get_disk_info() {
    # Ottiene informazioni sul disco principale usando df:
    # -h: mostra i valori in formato leggibile (KB, MB, GB)
    # /: specifica la partizione root
    # awk 'NR==2': prende solo la seconda riga dell'output (quella con i dati)
    # print $2,$3,$4,$5: estrae spazio totale, usato, libero e percentuale
    disk_info=$(df -h / | awk 'NR==2 {print $2,$3,$4,$5}')
    
    # Assegna i valori alle variabili
    read -r total used free perc <<< "$disk_info"
    
    # Stampa le informazioni formattate con emoji
    echo -e "\n💾 DISCO PRINCIPALE:"
    echo -e "• Totale: ${total}"
    echo -e "• Usato: ${used} (${perc})"
    echo -e "• Libero: ${free}"
}

# Funzione principale per mostrare tutte le risorse
function show_resources() {
    echo -e "📊 MONITOR RISORSE SISTEMA"
    echo "----------------------------------------"
    
    get_cpu_info
    get_ram_info
    get_network_info
    get_disk_info
    
    echo -e "\nℹ️ Aggiornato: $(date +'%H:%M:%S')"
}

# Mostra il carico medio del sistema
function show_loadavg() {
    echo "📊 CARICO MEDIO DEL SISTEMA"
    echo "---------------------------"
    cat /proc/loadavg | awk '{printf "• 1 minuto: %s\n• 5 minuti: %s\n• 15 minuti: %s\n", $1, $2, $3}'
}

# Mostra statistiche avanzate sull'I/O dei dischi
function show_iostat() {
    echo "📊 STATISTICHE I/O DISCHI"
    echo "--------------------------"
    
    # Verifica se iostat è installato
    if command -v iostat &>/dev/null; then
        # iostat -x 1 1: mostra statistiche estese con:
        #   -x: statistiche estese
        #   1 1: intervallo di 1 secondo, eseguito 1 volta
        # awk: formatta l'output in colonne allineate
        #   NR==1: intestazione con nomi delle colonne
        #   NR==3: riga di separazione
        #   NR>6: dati effettivi per ogni disco
        iostat -x 1 1 | awk '
            NR==1 {print "Disco", $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12; next}
            NR==3 {print; next}
            NR>6 {
                printf "%-10s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s %8s\n",
                    $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            }
        '
    else
        echo "iostat non è installato. Usa 'sudo apt install sysstat' per installarlo."
    fi
}

# Mostra statistiche avanzate sulla memoria virtuale
function show_vmstat() {
    echo "📊 STATISTICHE MEMORIA VIRTUALE"
    echo "-------------------------------"
    
    # Verifica se vmstat è installato
    if command -v vmstat &>/dev/null; then
        # vmstat 1 5: mostra statistiche con:
        #   1: intervallo di aggiornamento in secondi
        #   5: numero di report da generare
        # Include info su: processi, memoria, swap, I/O, CPU
        vmstat 1 5
    else
        echo "vmstat non è installato. Usa 'sudo apt install procps' per installarlo."
    fi
}

# Mostra la lista dei servizi attivi con systemctl
function show_services() {
    echo "📊 SERVIZI ATTIVI"
    echo "-----------------"
    
    # Verifica se systemctl è disponibile (sistemi con systemd)
    if command -v systemctl &>/dev/null; then
        # Conteggio totale servizi attivi:
        # list-units --type=service --state=running: lista solo servizi attivi
        # --no-pager --no-legend: output pulito senza paginazione
        # wc -l: conta il numero di righe
        total=$(systemctl list-units --type=service --state=running --no-pager --no-legend | wc -l)
        echo "Totale servizi attivi: $total"
        echo ""
        
        # Lista compatta dei primi 20 servizi:
        # head -n 20: limita a 20 servizi
        # awk: formatta l'output con punti elenco
        echo "PRIMI 20 SERVIZI:"
        systemctl list-units --type=service --state=running --no-pager --no-legend | head -n 20 | awk '{print "• " $1}'
        
        # Se ci sono più di 20 servizi, mostra avviso
        if [ $total -gt 20 ]; then
            echo ""
            echo "... e altri $(($total-20)) servizi"
        fi
    else
        echo "systemctl non è disponibile. Controlla i servizi manualmente."
    fi
}

### HARDWARE - SO ###

# Mostra informazioni hardware e sistema operativo
function hardware_info() {
    echo "🖥️ INFORMAZIONI HARDWARE"
    
    # Informazioni sulla CPU:
    # lscpu: mostra dettagli CPU
    # grep -E: filtra solo modello, core e frequenza
    echo -e "\n🔹 CPU:"
    lscpu | grep -E 'Model name|Core|MHz'
    
    # Temperatura componenti:
    # sensors: mostra temperature (se installato lm-sensors)
    # 2>/dev/null: silenzia eventuali errori
    echo -e "\n🌡️ TEMPERATURE:"
    sensors 2>/dev/null || echo "Sensori non disponibili"
    
    # Dispositivi di archiviazione:
    # lsblk: lista dispositivi a blocchi
    # -o: specifica colonne da mostrare
    echo -e "\n💾 DISPOSITIVI:"
    lsblk -o NAME,SIZE,TYPE,MOUNTPOINT
}

# Mostra informazioni sul kernel e sistema operativo
function get_system_info() {
    echo "🐧 KERNEL E SISTEMA OPERATIVO"
    echo "----------------------------------"
    
    # Informazioni base del kernel con uname -a:
    # Mostra kernel version, nome host, architettura, etc.
    uname -a
    
    # Informazioni aggiuntive sulla distribuzione:
    # Prima prova a leggere da /etc/os-release (sistemi moderni)
    if [ -f /etc/os-release ]; then
        echo -e "\n📦 DISTRIBUZIONE:"
        # Estrae solo il PRETTY_NAME dal file
        grep PRETTY_NAME /etc/os-release | cut -d '"' -f2
    elif command -v lsb_release &>/dev/null; then
        # Alternativa per sistemi con lsb_release
        echo -e "\n📦 DISTRIBUZIONE:"
        lsb_release -d | cut -f2-
    fi
}

### SEZIONE GESTIONE PACCHETTI ###

# Controlla gli aggiornamenti disponibili
function check_updates() {
    echo "🔄 AGGIORNAMENTI DISPONIBILI"
    
    # Gestione aggiornamenti per sistemi basati su Debian/Ubuntu (apt)
    if command -v apt &>/dev/null; then
        # Conta pacchetti aggiornabili (escludendo riga di intestazione)
        updates=$(apt list --upgradable 2>/dev/null | wc -l)
        
        # Se <=1 (solo riga di intestazione) nessun aggiornamento
        if [ "$updates" -le 1 ]; then
            echo "Nessun aggiornamento disponibile"
        else
            # Mostra lista completa pacchetti aggiornabili
            apt list --upgradable
        fi
    
    # Gestione aggiornamenti per sistemi basati su Fedora/RHEL (dnf)
    elif command -v dnf &>/dev/null; then
        # --quiet: output minimale
        dnf check-update --quiet || echo "Nessun aggiornamento disponibile"
    
    # Messaggio per sistemi non supportati
    else
        echo "Sistema non supportato"
    fi
}

# Mostra la lista dei pacchetti installati dall'utente
function list_user_packages() {
    local filter="${1:-}"
    local max_lines=50  # Limite visualizzazione
    
    echo "📦 PACCHETTI INSTALLATI DALL'UTENTE"
    echo "----------------------------------"
    
    # Rileva il package manager
    if command -v apt &>/dev/null; then
        # Debian/Ubuntu (apt)
        comm -23 \
            <(apt-mark showmanual | sort) \
            <(gzip -dc /var/log/installer/initial-status.gz | sed -n 's/^Package: //p' | sort) \
            | grep -i "$filter" | head -n "$max_lines"
        
    elif command -v pacman &>/dev/null; then
        # Arch Linux (pacman)
        pacman -Qqe | grep -v "$(pacman -Qqg base)" | grep -i "$filter" | head -n "$max_lines"
        
    elif command -v rpm &>/dev/null; then
        # RHEL/Fedora (rpm)
        rpm -qa --qf '%{NAME}\n' | grep -i "$filter" | head -n "$max_lines"
        
    else
        echo "ERRORE: Package manager non supportato"
        return 1
    fi
    
    echo -e "\nℹ️ Mostrati massimo $max_lines pacchetti."
}

### NETWORK ###

# Mostra informazioni di rete
function network_info() {
    echo "🌐 INFORMAZIONI DI RETE"
    
    # Mostra le interfacce di rete con indirizzi IP:
    # ip -brief address: formato compatto con info essenziali
    echo -e "\n🔹 INTERFACCE:"
    ip -brief address
    
    # Mostra le connessioni di rete attive:
    # netstat -tuln: mostra connessioni TCP/UDP in ascolto (-l)
    # head -n 15: limita l'output alle prime 15 righe
    echo -e "\n📶 CONNESSIONI:"
    netstat -tuln | head -n 15
    
    # Mostra l'IP pubblico del sistema:
    # curl -s ifconfig.me: chiamata al servizio esterno in modalità silenziosa
    echo -e "\n🌍 IP PUBBLICO:"
    curl -s ifconfig.me
}

# Mostra le configurazioni DNS
function show_dns() {
    echo "🌐 DNS"
    echo "------------------"

    # Mostra i nameserver configurati nel file resolv.conf
    echo "🔸 DNS Locale (resolv.conf):"
    
    # Verifica l'esistenza del file resolv.conf
    if [ -f /etc/resolv.conf ]; then
        # Estrae e formatta gli indirizzi dei nameserver:
        # grep: trova le righe con 'nameserver'
        # awk: formatta l'output con punti elenco
        grep "nameserver" /etc/resolv.conf | awk '{print "• " $2}'
    else
        # Messaggio alternativo se il file non esiste
        echo "Impossibile trovare /etc/resolv.conf"
    fi
}

### UTILITA ###

# Mostra i log di sistema
function show_logs() {
    echo "📜 ULTIMI LOG DI SISTEMA"
    
    # journalctl -n 20: mostra gli ultimi 20 log
    # --no-pager: output diretto senza paginazione
    # 2>/dev/null: silenzia eventuali errori
    # ||: mostra messaggio alternativo se il comando fallisce
    journalctl -n 20 --no-pager 2>/dev/null || echo "Impossibile visualizzare i log"
}

# Mostra il tempo di avvio e il carico medio
function show_uptime() {
    echo "⏱️ UPTIME DEL SISTEMA"
    
    # uptime -p: mostra il tempo di avvio in formato leggibile
    uptime -p
    
    # Mostra il carico medio
    echo -e "\n🕰️ CARICO MEDIO:"
    cat /proc/loadavg
}

# Mostra i log di sudo
function show_sudo_log() {
    echo "🔐 ULTIMI COMANDI ESEGUITI CON SUDO"
    echo "-----------------------------------"
    
    # Supporta diversi sistemi di logging:
    
    # 1. Per sistemi Ubuntu/Debian (auth.log)
    if [ -f /var/log/auth.log ]; then
        # Cerca righe con 'sudo:' e mostra le ultime 20
        grep -a 'sudo:' /var/log/auth.log | tail -n 20
    
    # 2. Per sistemi RHEL/CentOS (secure)
    elif [ -f /var/log/secure ]; then
        # Cerca righe con 'sudo:' e mostra le ultime 20
        grep -a 'sudo:' /var/log/secure | tail -n 20
    
    # 3. Per sistemi con systemd-journald
    else
        if command -v journalctl &>/dev/null; then
            echo "(Trovato systemd-journald)"
            # journalctl con filtro per comandi sudo
            # --no-pager: output diretto
            # -n 20: ultimi 20 log
            # --output=cat: formato semplice
            journalctl _COMM=sudo --no-pager -n 20 --output=cat | grep -a 'COMMAND='
        fi
    fi
}

# Controlla lo stato completo del servizio SSH
function check_ssh_status() {
    echo "🔒 MONITORAGGIO SSH"
    echo "-------------------"

    # Verifica se il servizio SSH è attivo:
    # Controlla entrambi i nomi comuni del servizio (sshd e ssh)
    if systemctl is-active --quiet sshd 2>/dev/null; then
        echo "• Servizio SSH: ATTIVO (sshd)"
    elif systemctl is-active --quiet ssh 2>/dev/null; then
        echo "• Servizio SSH: ATTIVO (ssh)"
    else
        echo "• Servizio SSH: NON ATTIVO"
    fi

    # Mostra la porta SSH configurata:
    # Legge da sshd_config, default a 22 se non specificato
    SSH_PORT=$(grep -E "^Port " /etc/ssh/sshd_config 2>/dev/null | awk '{print $2}' | head -n1)
    if [ -z "$SSH_PORT" ]; then
        SSH_PORT=22
    fi
    echo "• Porta SSH configurata: $SSH_PORT"

    # Verifica se la porta è effettivamente in ascolto:
    # ss -tln: mostra porte TCP in ascolto
    if ss -tln 2>/dev/null | grep -q ":$SSH_PORT "; then
        echo "• Porta $SSH_PORT in ascolto"
    else
        echo "• Porta $SSH_PORT NON in ascolto"
    fi

    # Mostra gli ultimi accessi SSH riusciti:
    # last -n 5 -a: ultimi 5 accessi con info host
    echo "• Ultimi 5 accessi SSH riusciti:"
    last -n 5 -a
}

### DISPATCHER PRINCIPALE ###

# Gestisce i diversi comandi e funzionalità
case "$1" in
    processes)
        show_processes
        ;;
    loadavg)
        show_loadavg
        ;;
    iostat)
        show_iostat
        ;;
    vmstat)
        show_vmstat
        ;;
    services)
        show_services
        ;;
    resources)
        show_resources
        ;;
    updates)
        check_updates
        ;;
    dns)
        show_dns
        ;;
    hardware)
        hardware_info
        ;;
    network)
        network_info
        ;;
    packages)
        list_user_packages
        ;;
    logs)
        show_logs
        ;;
    uptime)
        show_uptime
        ;;
    info_kernel_os)
        get_system_info
        ;;
    sudolog)
        show_sudo_log
        ;;
    ssh)
        check_ssh_status
        ;;
    *)
        echo "Comando non valido. Opzioni disponibili:"
        echo "processes | resources | updates | dns | hardware | network | packages | logs | uptime | system | loadavg | iostat | vmstat | services | sudolog | check_ssh_status"
        exit 1
        ;;
esac