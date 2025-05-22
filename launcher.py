import os
import json
import sys
import zipfile
import shutil
import tkinter as tk
from tkinter import ttk, messagebox as mb
import requests

URL_VERSAO = "https://raw.githubusercontent.com/DiLucaYVL/OPSender/refs/heads/main/versao.json"

def get_current_version():
    try:
        with open('version.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception as e:
        print(f"[Updater] Erro ao ler versão local: {e}")
        return "0.0.0"

def verificar_atualizacao():
    try:
        versao_atual = get_current_version()
        resp = requests.get(URL_VERSAO, timeout=5)
        if resp.status_code == 200:
            dados = resp.json()
            if dados["version"] > versao_atual:
                return dados["download_url"]
    except Exception as e:
        print(f"[Updater] Erro ao verificar atualização: {e}")
    return None

def baixar_zip_com_progresso(url, status_label, progress_bar):
    from tempfile import gettempdir

    temp_dir = gettempdir()
    if not temp_dir:
        raise RuntimeError("Erro: diretório temporário inválido.")

    zip_path = os.path.join(temp_dir, "TopChatUpdate.zip")

    try:
        with requests.get(url, stream=True) as r:
            total = int(r.headers.get('Content-Length', 0))
            baixado = 0
            with open(zip_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        baixado += len(chunk)
                        porcentagem = int((baixado / total) * 100)
                        status_label.config(text=f"Baixando... ({porcentagem}%)")
                        progress_bar['value'] = porcentagem
                        status_label.update_idletasks()
                        progress_bar.update_idletasks()
    except Exception as e:
        raise RuntimeError(f"Erro durante download: {str(e)}")
    return zip_path

def extrair_com_progresso(zip_path, status_label, progress_bar):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        arquivos = zip_ref.infolist()
        total = len(arquivos)
        temp_extract_path = os.path.join(os.getenv('TEMP'), "TopChat_Atualizacao")
        if os.path.exists(temp_extract_path):
            shutil.rmtree(temp_extract_path)
        os.makedirs(temp_extract_path, exist_ok=True)
        for i, file in enumerate(arquivos, start=1):
            zip_ref.extract(file, temp_extract_path)
            porcentagem = int((i / total) * 100)
            status_label.config(text=f"Instalando... ({porcentagem}%)")
            progress_bar['value'] = porcentagem
            status_label.update_idletasks()
            progress_bar.update_idletasks()
    return temp_extract_path

def substituir_arquivos(origem, destino):
    for item in os.listdir(origem):
        s = os.path.join(origem, item)
        d = os.path.join(destino, item)
        if os.path.isdir(s):
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)

def get_base_path():
    """
    Retorna o caminho base onde estão os arquivos, seja .py ou .exe.
    """
    if getattr(sys, 'frozen', False):
        # Executando como .exe
        return os.path.dirname(sys.executable)
    else:
        # Executando como .py
        return os.path.dirname(os.path.abspath(__file__))

def iniciar_aplicacao():
    base_path = get_base_path()
    app_path = os.path.join(base_path, "app", "topchat_core.exe")
    if os.path.exists(app_path):
        os.startfile(app_path)
    else:
        mb.showerror("Erro", f"Arquivo '{app_path}' não encontrado.")

def atualizar_com_janela(url, root):
    janela = tk.Toplevel(root)
    janela.title("Atualizando TopChat")
    janela.resizable(False, False)
    janela.attributes("-topmost", True)

    # Tenta definir o ícone
    try:
        janela.iconbitmap("topchatlogo.ico")
    except Exception as e:
        print(f"[Updater] Falha ao definir ícone: {e}")

    # Centraliza a janela
    janela.update_idletasks()
    largura, altura = 350, 100
    largura_tela = janela.winfo_screenwidth()
    altura_tela = janela.winfo_screenheight()
    x = (largura_tela // 2) - (largura // 2)
    y = (altura_tela // 2) - (altura // 2)
    janela.geometry(f"{largura}x{altura}+{x}+{y}")

    status_label = tk.Label(janela, text="Preparando atualização...", anchor="w")
    status_label.pack(fill="x", padx=10, pady=5)

    progress = ttk.Progressbar(janela, mode="determinate", maximum=100)
    progress.pack(fill="x", padx=10, pady=5)

    janela.update()

    try:
        zip_path = baixar_zip_com_progresso(url, status_label, progress)
        caminho_atualizacao = extrair_com_progresso(zip_path, status_label, progress)
        substituir_arquivos(caminho_atualizacao, get_base_path())  # ← Correção aqui
        janela.destroy()
    except Exception as e:
        janela.destroy()
        mb.showerror("Erro durante atualização", str(e))

def main():
    root = tk.Tk()
    root.withdraw()

    url = verificar_atualizacao()
    if url:
        atualizar_com_janela(url, root)

    iniciar_aplicacao()

if __name__ == "__main__":
    main()
