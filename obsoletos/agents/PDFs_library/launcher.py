import tkinter as tk
from tkinter import scrolledtext
import subprocess
import threading
import time
import os
import webbrowser

PORT = 8100
processes = []

# ==============================
# CONFIG (ESCOLHA 1 MODELO)
# ==============================
MODEL = "llama3.1:8b-instruct-q4_0"
# opções seguras:
# "phi3:mini"
# "llama3.1:8b-instruct-q4_0"

# ==============================
# UTIL
# ==============================
def log(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)

def run_cmd(cmd, background=False):
    if background:
        p = subprocess.Popen(cmd, shell=True)
        processes.append(p)
        return p
    else:
        return subprocess.run(cmd, shell=True)

# ==============================
# LIMPEZA
# ==============================
def clean_env():
    log("[INFO] Limpando ambiente...")
    os.system("taskkill /F /IM ollama.exe >nul 2>&1")
    os.system("taskkill /F /IM streamlit.exe >nul 2>&1")
    os.system("taskkill /F /IM python.exe >nul 2>&1")
    time.sleep(2)

# ==============================
# OLLAMA
# ==============================
def start_ollama():
    log("[INFO] Iniciando Ollama...")
    run_cmd("ollama serve", background=True)
    time.sleep(3)

def preload_model():
    log(f"[INFO] Preloading {MODEL} (warmup)...")

    # roda síncrono pra evitar concorrência de memória
    subprocess.run(f'ollama run {MODEL} "ok"', shell=True)

    log("[OK] Modelo pronto")

# ==============================
# PORTA
# ==============================
def free_port():
    log(f"[INFO] Liberando porta {PORT}...")
    killed = set()

    try:
        output = subprocess.check_output(
            f"netstat -ano | findstr :{PORT}", shell=True
        ).decode()

        for line in output.splitlines():
            pid = line.strip().split()[-1]

            if pid not in killed:
                log(f"[ALERTA] Matando PID {pid}")
                run_cmd(f"taskkill /PID {pid} /F")
                killed.add(pid)

    except:
        log("[OK] Porta livre")

# ==============================
# STREAMLIT
# ==============================
def start_streamlit():
    log("[INFO] Iniciando Streamlit...")

    p = subprocess.Popen(
        f"streamlit run app/ui/app.py --server.port {PORT}",
        shell=True
    )
    processes.append(p)

    time.sleep(4)

    # abre browser de forma confiável
    webbrowser.open(f"http://localhost:{PORT}")

    log("[OK] Interface aberta no navegador")

# ==============================
# PIPELINE
# ==============================
def start_all():
    threading.Thread(target=_start_all).start()

def _start_all():
    clean_env()
    start_ollama()
    preload_model()
    free_port()
    start_streamlit()

    log("✅ SciVault rodando com 1 modelo!")

# ==============================
# STOP
# ==============================
def stop_all():
    log("[INFO] Encerrando processos...")

    for p in processes:
        try:
            p.terminate()
        except:
            pass

    os.system("taskkill /IM ollama.exe /F >nul 2>&1")
    os.system("taskkill /IM streamlit.exe /F >nul 2>&1")

    log("[OK] Tudo encerrado")

# ==============================
# UI
# ==============================
root = tk.Tk()
root.title("🚀 SciVault Launcher")
root.geometry("700x500")

frame = tk.Frame(root)
frame.pack(pady=10)

btn_start = tk.Button(frame, text="▶ Iniciar SciVault", command=start_all, width=20, bg="green", fg="white")
btn_start.grid(row=0, column=0, padx=10)

btn_stop = tk.Button(frame, text="⛔ Parar Tudo", command=stop_all, width=20, bg="red", fg="white")
btn_stop.grid(row=0, column=1, padx=10)

log_box = scrolledtext.ScrolledText(root, width=85, height=25)
log_box.pack(pady=10)

root.mainloop()