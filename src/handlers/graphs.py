import io
import os
import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import paramiko
from paramiko.ssh_exception import SSHException, NoValidConnectionsError
from config.config import MONITORED_COMPUTERS, PATH_PRG
import traceback
from typing import Dict
import matplotlib.patheffects as path_effects
import tempfile
from .utils import get_ssh_project_path, find_computer_by_name

#########################         FUNZIONI        #########################   

# Funzione helper per inviare messaggi di errore
async def send_error_message(msg_telegram, error_message: str):
    await msg_telegram.edit_text(error_message)

# Funzione helper per generare grafici a torta

def _pie_style(fig, wedges, autotexts, title, legend_labels, legend_title):
    # Imposta il colore di sfondo della figura
    fig.set_facecolor("#f9f9f9")
    # Personalizza il testo percentuale sulle fette della torta
    for autotext in autotexts:
        autotext.set_color('white')           
        autotext.set_fontsize(13)             
        autotext.set_fontweight('bold')       
        autotext.set_path_effects([           
            path_effects.Stroke(linewidth=2, foreground='black'),
            path_effects.Normal()
        ])
    # Personalizza i bordi delle fette della torta
    for w in wedges:
        w.set_linewidth(1.5)
        w.set_edgecolor('black')
    # Imposta il titolo del grafico
    fig.suptitle(title, fontsize=17, fontweight='bold', color="#222222")
    # Aggiunge la legenda a sinistra del grafico
    fig.legend(
        wedges,
        legend_labels,
        title=legend_title,
        loc="center left",
        bbox_to_anchor=(1, 0.5),
        fontsize=13,
        title_fontsize=14,
        frameon=False
    )
    return fig

# Funzione DRY per generare grafici a torta

def generate_pie_chart(sizes, labels, colors, explode, title, legend_labels, legend_title):
    # questo if controlla se ci sono valori in sizes
    if not any(sizes):
        return None
    
    # Controllo per evitare divisioni per zero
    total = sum(sizes)
    if total == 0:
        return None

    fig, ax = plt.subplots(figsize=(10, 7))
    pie_result = ax.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        explode=explode,
        pctdistance=0.82,
        wedgeprops={'edgecolor': 'black', 'linewidth': 1.5}
    )

    # questo if controlla se ci sono valori in pie_result
    if len(pie_result) == 3:
        wedges, texts, autotexts = pie_result
    else:
        wedges, texts = pie_result # type: ignore
        autotexts = []
    fig = _pie_style(fig, wedges, autotexts, title, legend_labels, legend_title)
    return fig

async def get_meminfo(ssh) -> Dict[str, int]:
    # Esegue il comando remoto per leggere il file /proc/meminfo tramite SSH
    stdin, stdout, stderr = ssh.exec_command("cat /proc/meminfo")
    meminfo = {}
    # Scorre ogni riga dell'output
    for line in stdout:
        if ':' not in line:
            continue # Salta le righe non valide
        name, var = line.split(':', 1)
        value = var.split()[0]  # Prende solo il valore numerico
        try:
            meminfo[name.strip()] = int(value)  # Converte in intero
        except ValueError:
            continue
    return meminfo



async def send_ram_graph(update, context):
    # Genera e invia i grafici della memoria tramite SSH
    msg_telegram = await (update.message or update.callback_query.message).reply_text(
        "⏳ Analisi dettagliata della memoria in corso..."
    )
    
    # Recupera il computer selezionato dall'utente
    selected = context.user_data.get("selected_computer")
    if not selected:
        await send_error_message(msg_telegram, "❗ Devi prima selezionare un computer.")
        return

    # Cerca il computer selezionato nella lista dei computer monitorati
    computer = find_computer_by_name(MONITORED_COMPUTERS, selected)
            
    if not computer:
        await send_error_message(msg_telegram, "❗ Computer non trovato.")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(computer["ip"], username=computer["user"], timeout=5)
        # Recupera le informazioni di memoria tramite SSH
        meminfo = await get_meminfo(ssh)

        # Genera tutti i grafici a torta della memoria
        graphs = {}
        pie_generators = [
            (generate_simple_memory_pie, "📊 Panoramica Memoria"),
            (generate_free_vs_available_memory_pie, "📊 Libera vs Disponibile"),
            (generate_apps_processes_pie, "📊 Memoria App e Processi"),
            (generate_active_memory_pie, "📊 Memoria Attivamente Usata"),
            (generate_cache_memory_pie, "📊 Cache del Filesystem"),
            (generate_kernel_memory_pie, "📊 Memoria del Kernel"),
        ]
        for gen, caption in pie_generators:
            fig = await gen(meminfo)
            if fig:
                graphs[caption] = (fig, caption)

        # Gestione della memoria di swap separatamente
        swap_graph = await generate_swap_memory_pie(meminfo)
        if swap_graph:
            graphs["📊 Memoria di Swap"] = (swap_graph, "📊 Memoria di Swap")
        else:
            await (update.message or update.callback_query.message).reply_text(
                f"❗ La memoria di swap non è impostata su questo sistema ({selected})."
            )

        # Invia tutti i grafici
        await msg_telegram.delete()
        for caption, (fig, _) in graphs.items():
            buf = io.BytesIO()
            fig.savefig(buf, format='png', bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            await (update.message or update.callback_query.message).reply_photo(
                buf,
                caption=f"{caption} su {selected}"
            )

    except Exception as e:
        # Gestione degli errori: invia il traceback all'utente
        tb = traceback.format_exc()
        await send_error_message(msg_telegram, f"❌ Errore: {str(e)}\n\n<pre>{tb}</pre>")
    finally:
        ssh.close()


#########################         GRAFICI CPU         #########################   


# Funzione per inviare il grafico CPU
async def send_cpu_graph(update, context):
    # Invia un messaggio di attesa all'utente
    msg_telegram = await (update.message or update.callback_query.message).reply_text("⏳ Connessione SSH e generazione del grafico CPU...")

    # Recupera il computer selezionato dall'utente
    selected = context.user_data.get("selected_computer")
    if not selected:
        await send_error_message(msg_telegram, "❗ Devi prima selezionare un computer.")
        return

    # Cerca il computer selezionato nella lista dei computer monitorati
    computer = find_computer_by_name(MONITORED_COMPUTERS, selected)
       
    if not computer:
        await send_error_message(msg_telegram, "❗ Computer non trovato.")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(computer["ip"], username=computer["user"], timeout=5)
        # Costruisce il percorso remoto degli script e log
        remote_path = get_ssh_project_path(computer["user"], PATH_PRG)
        script_path = f"{remote_path}/scripts/cpu_usage.sh"
        # Esegue lo script remoto per aggiornare il log CPU
        stdin, stdout, stderr = ssh.exec_command(f"bash {script_path}")
        stdout.channel.recv_exit_status()

        # Scarica il file di log CPU via SFTP in un file temporaneo locale
        sftp = ssh.open_sftp()
        remote_log_path = f"{remote_path}/logs/cpu_usage.log"
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            local_log_path = tmp_file.name
            sftp.get(remote_log_path, local_log_path)
        sftp.close()

        # Legge i dati dal file temporaneo e li prepara per il grafico
        timestamps, cpu_percents = [], []
        try:
            with open(local_log_path) as f:
                next(f) # Salta l'intestazione
                for line in f:
                    if "Media:" in line or not line.strip():
                        continue
                    try:
                        ts, cpu = line.strip().split(",")
                        timestamps.append(datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S"))
                        cpu_percents.append(float(cpu))
                    except ValueError:
                        continue
        except Exception as e:
            await send_error_message(msg_telegram, f"❌ Errore lettura file temporaneo CPU: {e}")
            return

        # Se non ci sono dati validi, avvisa l'utente
        if not timestamps:
            await send_error_message(
                msg_telegram,
                "❗ *Nessun dato CPU valido trovato*\n\n"
                "🔧*Possibili cause:*\n"
                r"1\. Il servizio di monitoraggio non è attivo.\n\n"
                "*Ricorda di attivare il servizio sysstat* con:\n"
                "• `sudo systemctl start sysstat`\n\n"
                "*Abilità all'avvio del sistema:*\n"
                "• `sudo systemctl enable sysstat`"
            )
            return
        
        # Crea il grafico dell'utilizzo CPU
        plt.figure(figsize=(13, 6))
        plt.plot(
            timestamps,
            cpu_percents,
            label="CPU %",
            color="#007acc",
            linewidth=2,
            marker="o",
            markersize=4,
            markerfacecolor="#ff6600"
        )
        plt.xlabel("Tempo", fontsize=12)
        plt.ylabel("Utilizzo CPU (%)", fontsize=12)
        plt.title(f"Utilizzo CPU nelle ultime 24 ore su {selected}", fontsize=14)
        plt.ylim(0, 100)
        plt.grid(True, linestyle="--", alpha=0.5)
        plt.legend(loc="upper right", fontsize=11)
        plt.tight_layout()
        plt.gca().set_facecolor("#f9f9f9")
        plt.gcf().autofmt_xdate()
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        img_path = f"/tmp/{selected}_cpu_usage_24h.png"
        plt.savefig(img_path)
        plt.close()

        # Invia il grafico all'utente
        try:
            with open(img_path, "rb") as img:
                await msg_telegram.delete()
                await (update.message or update.callback_query.message).reply_photo(img, caption=f"Grafico utilizzo CPU 24h per {selected}")
        except Exception as e:
            await send_error_message(msg_telegram, f"❌ Errore invio immagine CPU: {e}")
        # Elimina i file temporanei
        try:
            os.remove(local_log_path)
            os.remove(img_path)
        except Exception:
            pass
    # Gestione degli errori di connessione e SSH
    except NoValidConnectionsError:
        await send_error_message(msg_telegram, "❌ Impossibile connettersi al server. Verifica l'indirizzo IP e la disponibilità del server.")
    except SSHException as e:
        await send_error_message(msg_telegram, f"❌ Errore SSH: {e}")
    # Gestione degli errori generali
    except Exception as e:
        await send_error_message(msg_telegram, f"❌ Errore durante la connessione SSH o generazione del grafico: {e}")
    finally:
        ssh.close()


#########################         GRAFICI LOG         #########################   

async def send_log_graph(update, context):
    # Genera e invia il grafico a torta dei log syslog tramite SSH
    # Invia un messaggio di attesa all'utente
    msg_telegram = await (update.message or update.callback_query.message).reply_text("⏳ Connessione SSH e generazione del grafico syslog...")

    # Recupera il computer selezionato dall'utente
    selected = context.user_data.get("selected_computer")
    if not selected:
        await send_error_message(msg_telegram, "❗ Devi prima selezionare un computer.")
        return

    # Cerca il computer selezionato nella lista dei computer monitorati
    computer = find_computer_by_name(MONITORED_COMPUTERS, selected)
       
    if not computer:
        await send_error_message(msg_telegram, "❗ Computer non trovato.")
        return

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(computer["ip"], username=computer["user"], timeout=5)
        
        # Costruisce il percorso remoto degli script e log
        remote_path = get_ssh_project_path(computer["user"], PATH_PRG)
        script_path = f"{remote_path}/scripts/log.sh"
        # Esegui lo script remoto che genera syslog.log
        stdin, stdout, stderr = ssh.exec_command(f"bash {script_path}")
        stdout.channel.recv_exit_status()  # Attendi che il comando finisca

        # Scarica il file syslog.log via SFTP in un file temporaneo locale
        sftp = ssh.open_sftp()
        remote_log_path = f"{remote_path}/logs/syslog.log"
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            local_log_path = tmp_file.name
            sftp.get(remote_log_path, local_log_path)
        sftp.close()

        # Leggi solo le righe 2-7 del file log locale e genera il grafico a torta
        log_types = {}
        total_logs = 0
        try:
            with open(local_log_path, "r") as f:
                lines = f.readlines()[1:7]
                for line in lines:
                    line = line.strip()
                    if line.startswith("Totale log:"):
                        total_logs = int(line.split(":", 1)[1].strip())
                    elif ":" in line:
                        tipo, count = line.split(":", 1)
                        log_types[tipo.strip()] = int(count.strip())
        except Exception as e:
            await send_error_message(msg_telegram, f"❌ Errore lettura file temporaneo log: {e}")
            return

        # Se non ci sono dati validi, avvisa l'utente
        if not log_types:
            await send_error_message(msg_telegram, "❗ Nessun log rilevante trovato nelle ultime 24 ore.")
            return


        # Prepara dati per il grafico
        labels = list(log_types.keys())
        sizes = list(log_types.values())
        colors = ['#4CAF50', '#F44336', '#FF9800', '#2196F3', '#9C27B0'][:len(labels)]
        # Trova l'indice della fetta più grande
        max_size = max(sizes) if sizes else 0
        max_idx = sizes.index(max_size)
        explode = [0] * len(labels)
        explode[max_idx] = 0.08 # type: ignore
        
        # Prepara le etichette della legenda
        legend_labels = []
        for label, size in zip(labels, sizes):
            legend_labels.append(f"{label}\n({size} log)")
        title = f"Distribuzione dei Log\nTotale: {total_logs} log"
        legend_title = "Tipologia Log"

        # Genera il grafico a torta
        fig = generate_pie_chart(sizes, labels, colors, explode, title, legend_labels, legend_title)
        if not fig:
            await send_error_message(msg_telegram, "❗ Nessun dato valido per il grafico syslog.")
            return

        # Invia il grafico all'utente
        try:
            buf = io.BytesIO()
            fig.savefig(buf, format="png", bbox_inches='tight', facecolor=fig.get_facecolor())
            plt.close(fig)
            buf.seek(0)
            await msg_telegram.delete()
            await (update.message or update.callback_query.message).reply_photo(buf, caption=f"Grafico syslog 24h per {selected}")
        except Exception as e:
            await send_error_message(msg_telegram, f"❌ Errore invio immagine log: {e}")
        # Elimina il file temporaneo locale
        try:
            os.remove(local_log_path)
        except Exception:
            pass
    # Gestione degli errori di connessione e SSH
    except NoValidConnectionsError:
        await send_error_message(msg_telegram, "❌ Impossibile connettersi al server. Verifica l'indirizzo IP e la disponibilità del server.")
    except SSHException as e:
        await send_error_message(msg_telegram, f"❌ Errore SSH: {e}")
    # Gestione degli errori generali
    except Exception as e:
        await send_error_message(msg_telegram, f"❌ Errore durante la connessione SSH o generazione del grafico: {e}")
    finally:
        ssh.close()



#########################         GRAFICI MEMORIA         #########################   


async def generate_simple_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico semplice della memoria libera vs utilizzata
    total = meminfo.get('MemTotal', 0) / 1024  # Memoria totale in MB
    free = meminfo.get('MemAvailable', 0) / 1024 # Memoria disponibile in MB
    used = total - free # Memoria utilizzata

    sizes = [used, free]
    labels = ['Memoria Utilizzata', 'Memoria Libera']
    colors = ['#ff6b6b', '#4cd137']
    explode = [0.08, 0]
    total_gb = total / 1024 # Conversione in GB
    if total_gb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Panoramica Memoria\nTotale: {total_gb:.2f} GB',
        legend_labels, "Stato"
    )


async def generate_main_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico a torta delle categorie principali della memoria
    # Calcola la memoria usata da app/processi, cache, kernel e libera
    apps_mem = (meminfo.get('AnonPages', 0) + 
                meminfo.get('Mapped', 0) + 
                meminfo.get('Shmem', 0)) / 1024
    cache_mem = (meminfo.get('Cached', 0) + 
                 meminfo.get('Buffers', 0)) / 1024
    kernel_mem = (meminfo.get('Slab', 0) + 
                 meminfo.get('KernelStack', 0) + 
                 meminfo.get('PageTables', 0)) / 1024
    free_mem = meminfo.get('MemFree', 0) / 1024

    sizes = [apps_mem, cache_mem, kernel_mem, free_mem]
    labels = ['App e Processi', 'Cache Filesystem', 'Kernel', 'Memoria Libera']
    colors = ['#ff6f61', '#6baed6', '#74c476', '#fd8d3c']
    explode = [0.08, 0, 0, 0]
    total_gb = meminfo.get('MemTotal', 0) / (1024 * 1024)
    if total_gb == 0:
        return None

    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Utilizzo della Memoria\nTotale: {total_gb:.2f} GB',
        legend_labels, "Categorie"
    )

async def generate_active_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico della memoria attivamente usata (Active) e inattiva (Inactive)
    # Recupera i valori delle varie categorie di memoria attiva/inattiva
    active_anon = meminfo.get('Active(anon)', 0) / 1024
    active_file = meminfo.get('Active(file)', 0) / 1024
    inactive_anon = meminfo.get('Inactive(anon)', 0) / 1024
    inactive_file = meminfo.get('Inactive(file)', 0) / 1024

    sizes = [active_anon, active_file, inactive_anon, inactive_file]
    labels = ['Active Anon', 'Active File', 'Inactive Anon', 'Inactive File']
    colors = ['#ff6f61', '#6baed6', '#b2df8a', '#fdbf6f']
    explode = [0, 0, 0, 0]
    total_gb = sum(sizes) / 1024
    if total_gb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Memoria Attiva/Inattiva\nTotale: {total_gb:.2f} GB',
        legend_labels, "Categorie"
    )

async def generate_cache_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico della cache del filesystem
    cached = meminfo.get('Cached', 0) / 1024
    buffers = meminfo.get('Buffers', 0) / 1024

    sizes = [cached, buffers]
    labels = ['Cache Disco', 'Buffer I/O']
    colors = ['#66b3ff', '#99ff99']
    explode = [0.08, 0]
    total_gb = sum(sizes) / 1024
    if total_gb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Cache del Filesystem\nTotale: {total_gb:.2f} GB',
        legend_labels, "Categorie"
    )

async def generate_kernel_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico della memoria del kernel
    slab = meminfo.get('Slab', 0) / 1024
    kernel_stack = meminfo.get('KernelStack', 0) / 1024
    page_tables = meminfo.get('PageTables', 0) / 1024

    sizes = [slab, kernel_stack, page_tables]
    labels = ['Slab', 'Kernel Stack', 'Page Tables']
    colors = ['#ff9999', '#ffcc99', '#99ff99']
    explode = [0.08, 0, 0]
    total_mb = sum(sizes)
    if total_mb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size:.2f} MB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Memoria del Kernel\nTotale: {total_mb:.2f} MB',
        legend_labels, "Categorie"
    )

async def generate_apps_processes_pie(meminfo: Dict[str, int]):
    # Genera il grafico della memoria usata da app e processi
    anon = meminfo.get('AnonPages', 0) / 1024
    mapped = meminfo.get('Mapped', 0) / 1024
    shmem = meminfo.get('Shmem', 0) / 1024

    sizes = [anon, mapped, shmem]
    labels = ['Memoria Dinamica', 'File Mappati', 'Memoria Condivisa']
    colors = ['#ff6f61', '#6baed6', '#74c476']
    explode = [0.08, 0, 0]
    total_gb = sum(sizes) / 1024
    if total_gb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Memoria App e Processi\nTotale: {total_gb:.2f} GB',
        legend_labels, "Categorie"
    )

async def generate_free_vs_available_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico che mostra la differenza tra memoria libera e disponibile
    total = meminfo.get('MemTotal', 0) / 1024  # MB
    free = meminfo.get('MemFree', 0) / 1024
    available = meminfo.get('MemAvailable', 0) / 1024
    used = total - available
    reclaimable = available - free  # Memoria recuperabile (cache, buffer, etc.)

    sizes = [used, free, reclaimable]
    labels = ['Memoria In Uso', 'Memoria Libera', 'Memoria Recuperabile']
    colors = ['#ff6b6b', '#4cd137', '#45aaf2']
    explode = [0.08, 0, 0]
    total_gb = total / 1024
    if total_gb == 0:
        return None
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')
    
    # Genera il grafico a torta
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Analisi Dettagliata Memoria\nTotale: {total_gb:.2f} GB',
        legend_labels, "Stato"
    )


# GRAFICO SWAP: 
async def generate_swap_memory_pie(meminfo: Dict[str, int]):
    # Genera il grafico della memoria di swap
    swap_total = meminfo.get('SwapTotal', 0) / 1024  # MB
    swap_free = meminfo.get('SwapFree', 0) / 1024

    # Gestione di valori non validi
    if swap_total <= 0:
        return None  # Indica che la swap non è impostata

    swap_used = max(swap_total - swap_free, 0)
    total = swap_used + swap_free
    if total == 0:
        return None

    sizes = [swap_used, swap_free]
    labels = ['Swap Usata', 'Swap Libera']
    colors = ['#ff6b6b', '#4cd137']
    explode = [0.08, 0]
    total_gb = swap_total / 1024 if swap_total else 0
    
    # Prepara le etichette della legenda con i valori in GB
    legend_labels = []
    for label, size in zip(labels, sizes):
        legend_labels.append(f'{label}\n({size/1024:.2f} GB)')

    # Genera il grafico a torta della swap
    return generate_pie_chart(
        sizes, labels, colors, explode,
        f'Memoria di Swap\nTotale: {total_gb:.2f} GB',
        legend_labels, "Stato"
    )
