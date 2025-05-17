import asyncio
import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
import pandas as pd
from urllib.parse import quote
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
import threading
import re
import os
import json
from datetime import datetime
from PIL import Image, ImageTk



class WhatsAppSender:
    """Classe responsável pelo gerenciamento do envio de mensagens via WhatsApp Web"""

    def __init__(self, log_callback=None, progress_callback=None):
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.running = False
        self.paused = False
        self.browser = None
        self.page = None
        self.total_messages = 0
        self.sent_messages = 0
        self.failed_messages = []
        self.retry_count = {}
        self.max_retries = 3

    def log(self, message):
        """Registra mensagens no log"""
        if self.log_callback:
            self.log_callback(message)
        else:
            print(message)

    def update_progress(self, value=None, max_value=None):
        """Atualiza a barra de progresso"""
        if self.progress_callback:
            self.progress_callback(value, max_value)

    def normalize_phone(self, phone):
        """Normaliza o número de telefone para o formato internacional"""
        # Remove caracteres não numéricos
        phone = re.sub(r'\D', '', str(phone))

        # Verifica se já tem código do país
        if not phone.startswith('55') and len(phone) <= 11:
            phone = '55' + phone

        # Adiciona 9 se for celular brasileiro sem o 9
        if len(phone) == 12 and phone.startswith('55'):
            # Insere o 9 após o DDD (posição 4)
            phone = phone[:4] + '9' + phone[4:]

        return phone

    async def initialize_browser(self, user_data_dir="whatsapp_profile", headless=False):
        """Inicializa o navegador uma única vez para todas as mensagens"""
        self.log("\U0001F680 Inicializando navegador...")

        # Garante que o diretório existe
        os.makedirs(user_data_dir, exist_ok=True)
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "./ms-playwright"
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=headless
        )

        self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()

        # Verifica se o WhatsApp Web está logado
        await self.page.goto("https://web.whatsapp.com/")
        self.log("\U0001F50D Verificando status do login no WhatsApp...")

        # Aguarda indefinidamente até que o WhatsApp esteja carregado (conversas visíveis)
        await self.page.wait_for_selector('div[role="grid"]', timeout=0)
        self.log("✅ WhatsApp Web carregado e pronto para envio!")

        return True

    async def send_message(self, phone, message):
        """Envia uma mensagem para um número específico"""
        if not message.strip():
            self.log(f"⚠️ Mensagem vazia para {phone}, pulando...")
            return False

        try:
            # Normaliza o número de telefone
            normalized_phone = self.normalize_phone(phone)

            # Codifica a mensagem para URL
            encoded_message = quote(message.replace('\n', '%0A'))

            # Constrói a URL do WhatsApp
            url = f"https://web.whatsapp.com/send/?phone={normalized_phone}&text={encoded_message}&type=phone_number&app_absent=0"

            self.log(f"🔗 Acessando conversa com {normalized_phone}...")
            await self.page.goto(url)

            # Espera até que a página carregue e o campo de mensagem esteja disponível
            try:
                await self.page.wait_for_selector('div[contenteditable="true"]', timeout=30000)

                # Pequena pausa para garantir que a página está completamente carregada
                await self.page.wait_for_timeout(1500)

                # Verifica se há mensagem de erro de número inválido
                invalid_number = await self.page.query_selector('div[data-animate-modal-body="true"]')
                if invalid_number:
                    self.log(f"❌ Número inválido: {normalized_phone}")
                    return False

                # Envia a mensagem
                await self.page.keyboard.press("Enter")
                self.log(f"📤 Mensagem enviada para {normalized_phone}, aguardando confirmação...")

                # Espera pela confirmação de envio
                await self.page.wait_for_selector('div.message-out', timeout=15000)
                await self.page.wait_for_selector('span[data-icon="msg-check"], span[data-icon="msg-dblcheck"]',
                                                  timeout=10000)

                self.log(f"✅ Mensagem confirmada para {normalized_phone}")
                return True

            except PlaywrightTimeoutError as e:
                self.log(f"⚠️ Timeout ao enviar mensagem para {normalized_phone}: {str(e)}")
                return False

        except Exception as e:
            self.log(f"❌ Erro ao enviar mensagem para {normalized_phone}: {str(e)}")
            return False

    async def process_contacts(self, contacts):
        """Processa a lista de contatos e envia mensagens"""
        self.running = True
        self.paused = False
        self.total_messages = len(contacts)
        self.sent_messages = 0
        self.failed_messages = []
        self.retry_count = {}

        # Inicializa a barra de progresso
        self.update_progress(0, self.total_messages)

        try:
            # Inicializa o navegador uma única vez
            await self.initialize_browser()

            for i, (phone, message) in enumerate(contacts):
                # Verifica se o processo foi interrompido
                if not self.running:
                    self.log("🛑 Processo interrompido pelo usuário.")
                    break

                # Verifica se está pausado
                while self.paused and self.running:
                    await asyncio.sleep(1)

                # Atualiza o progresso
                self.update_progress(i, self.total_messages)

                # Tenta enviar a mensagem
                success = await self.send_message(phone, message)

                if success:
                    self.sent_messages += 1
                else:
                    # Adiciona à lista de falhas
                    self.failed_messages.append((phone, message))

                # Pausa entre mensagens para evitar bloqueio
                if i < len(contacts) - 1:  # Não espera após a última mensagem
                    self.log(f"⏳ Aguardando antes da próxima mensagem...")
                    await self.page.wait_for_timeout(5000)  # 5 segundos entre mensagens

            # Tenta reenviar mensagens que falharam (até max_retries vezes)
            if self.failed_messages and self.running:
                self.log(f"🔄 Tentando reenviar {len(self.failed_messages)} mensagens que falharam...")

                retry_messages = self.failed_messages.copy()
                self.failed_messages = []

                for phone, message in retry_messages:
                    # Verifica se o processo foi interrompido
                    if not self.running:
                        self.log("🛑 Processo de retry interrompido pelo usuário.")
                        break

                    # Verifica se está pausado
                    while self.paused and self.running:
                        await asyncio.sleep(1)

                    # Verifica o número de tentativas
                    self.retry_count[phone] = self.retry_count.get(phone, 0) + 1

                    if self.retry_count[phone] <= self.max_retries:
                        self.log(f"🔄 Tentativa {self.retry_count[phone]} para {phone}...")
                        success = await self.send_message(phone, message)

                        if success:
                            self.sent_messages += 1
                        else:
                            self.failed_messages.append((phone, message))

                        # Pausa entre mensagens
                        await self.page.wait_for_timeout(5000)
                    else:
                        self.log(f"❌ Número máximo de tentativas excedido para {phone}")
                        self.failed_messages.append((phone, message))

        except Exception as e:
            self.log(f"❌ Erro durante o processamento: {str(e)}")
        finally:
            # Atualiza o progresso final
            self.update_progress(self.total_messages, self.total_messages)

            # Fecha o navegador
            if self.browser:
                await self.browser.close()

            self.running = False

            # Relatório final
            self.log("\n📊 RELATÓRIO FINAL:")
            self.log(f"✅ Mensagens enviadas com sucesso: {self.sent_messages}/{self.total_messages}")
            self.log(f"❌ Mensagens com falha: {len(self.failed_messages)}/{self.total_messages}")

            if self.failed_messages:
                self.log("\n⚠️ Números com falha no envio:")
                for phone, _ in self.failed_messages:
                    self.log(f"  - {phone}")

            self.log("\n🏁 Processo finalizado.")

    def pause(self):
        """Pausa o envio de mensagens"""
        self.paused = True
        self.log("⏸️ Processo pausado. Clique em Retomar para continuar.")

    def resume(self):
        """Retoma o envio de mensagens"""
        self.paused = False
        self.log("▶️ Processo retomado.")

    def stop(self):
        """Interrompe o envio de mensagens"""
        self.running = False
        self.log("🛑 Interrompendo o processo... Aguarde.")


class ExcelReader:
    """Classe responsável pela leitura e validação de dados da planilha"""

    @staticmethod
    def read_contacts(file_path):
        """Lê os contatos da planilha Excel a partir da linha 2"""
        try:
            # Verifica se o arquivo existe
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

            # Lê a planilha ignorando a primeira linha (linha de título)
            df = pd.read_excel(file_path, header=None, skiprows=1, dtype={0: str, 1: str})

            contatos = []
            for _, row in df.iterrows():
                numero = str(row[0]).strip() if pd.notna(row[0]) else ""
                mensagem = str(row[1]).strip() if pd.notna(row[1]) else ""

                # Ignora linhas em branco
                if numero == "":
                    continue

                contatos.append((numero, mensagem))

            return contatos

        except Exception as e:
            raise Exception(f"Erro ao ler a planilha: {str(e)}")



class ConfigManager:
    """Classe para gerenciar configurações do aplicativo"""

    CONFIG_FILE = "whatsapp_sender_config.json"

    @staticmethod
    def save_config(config):
        """Salva as configurações em um arquivo JSON"""
        try:
            with open(ConfigManager.CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações: {str(e)}")

    @staticmethod
    def load_config():
        """Carrega as configurações do arquivo JSON"""
        default_config = {
            "last_directory": "",
            "browser_profile": "whatsapp_profile",
            "wait_time": 5,
            "max_retries": 3,
            "headless": False
        }

        try:
            if os.path.exists(ConfigManager.CONFIG_FILE):
                with open(ConfigManager.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default_config
        except Exception as e:
            print(f"Erro ao carregar configurações: {str(e)}")
            return default_config


class App:
    """Classe principal da aplicação"""

    def __init__(self, master):
        self.master = master
        self.config = ConfigManager.load_config()

        # Configuração da janela principal
        master.title("OPS Sender")
        master.geometry("700x600")
        master.minsize(600, 500)

        # Variáveis de controle
        self.arquivo_excel = None
        self.sender = WhatsAppSender(
            log_callback=self.log_msg,
            progress_callback=self.update_progress
        )

        # Criação da interface
        self.create_widgets()

    def create_widgets(self):
        """Cria os widgets da interface"""

        logo_container = tk.Frame(self.master)
        logo_container.pack(fill=tk.X)

        try:
            logo_image = Image.open("topfama_logo.png")
            logo_image = logo_image.resize((250, 90), Image.LANCZOS)
            self.logo_topfama_img = ImageTk.PhotoImage(logo_image)

            logo_label = ttk.Label(logo_container, image=self.logo_topfama_img)
            logo_label.pack(anchor="center")  # ← centraliza horizontalmente


        except Exception as e:
            print(f"Erro ao carregar imagens de logo: {e}")

        # Frame principal com padding
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Seção de seleção de arquivo
        file_frame = ttk.LabelFrame(main_frame, text="Seleção de Arquivo", padding="5")
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Label(file_frame, text="Selecione a planilha Excel com os contatos:").pack(anchor=tk.W, pady=2)

        file_select_frame = ttk.Frame(file_frame)
        file_select_frame.pack(fill=tk.X, pady=2)

        self.path_entry = ttk.Entry(file_select_frame)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        self.select_button = ttk.Button(
            file_select_frame,
            text="Selecionar Planilha",
            command=self.selecionar_arquivo
        )
        self.select_button.pack(side=tk.RIGHT)

        # Seção de configurações
        config_frame = ttk.LabelFrame(main_frame, text="Configurações", padding="5")
        config_frame.pack(fill=tk.X, pady=5)

        # Configuração de perfil do navegador
        profile_frame = ttk.Frame(config_frame)
        profile_frame.pack(fill=tk.X, pady=2)

        ttk.Label(profile_frame, text="Diretório do perfil:").pack(side=tk.LEFT, padx=(0, 5))

        self.profile_var = tk.StringVar(value=self.config.get("browser_profile", "whatsapp_profile"))
        profile_entry = ttk.Entry(profile_frame, textvariable=self.profile_var)
        profile_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Configuração de tempo de espera
        wait_frame = ttk.Frame(config_frame)
        wait_frame.pack(fill=tk.X, pady=2)

        ttk.Label(wait_frame, text="Tempo de espera entre mensagens (segundos):").pack(side=tk.LEFT, padx=(0, 5))

        self.wait_var = tk.IntVar(value=self.config.get("wait_time", 5))
        wait_spinbox = ttk.Spinbox(wait_frame, from_=1, to=30, textvariable=self.wait_var, width=5)
        wait_spinbox.pack(side=tk.LEFT)

        # Configuração de tentativas
        retry_frame = ttk.Frame(config_frame)
        retry_frame.pack(fill=tk.X, pady=2)

        ttk.Label(retry_frame, text="Número máximo de tentativas:").pack(side=tk.LEFT, padx=(0, 5))

        self.retry_var = tk.IntVar(value=self.config.get("max_retries", 3))
        retry_spinbox = ttk.Spinbox(retry_frame, from_=1, to=10, textvariable=self.retry_var, width=5)
        retry_spinbox.pack(side=tk.LEFT)

        # Opção de modo headless
        self.headless_var = tk.BooleanVar(value=self.config.get("headless", False))
        headless_check = ttk.Checkbutton(
            config_frame,
            text="Executar navegador em modo invisível (headless)",
            variable=self.headless_var
        )
        headless_check.pack(anchor=tk.W, pady=2)

        # Seção de controles
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=10)

        # Botões de controle
        self.start_button = ttk.Button(
            control_frame,
            text="Iniciar Envio",
            command=self.iniciar_envio,
            state=tk.DISABLED
        )
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.pause_button = ttk.Button(
            control_frame,
            text="Pausar",
            command=self.pausar_envio,
            state=tk.DISABLED
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = ttk.Button(
            control_frame,
            text="Retomar",
            command=self.retomar_envio,
            state=tk.DISABLED
        )
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(
            control_frame,
            text="Interromper",
            command=self.interromper_envio,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)

        # Barra de progresso
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="0/0 mensagens enviadas")
        self.progress_label.pack(anchor=tk.E, pady=2)

        # Área de log
        log_frame = ttk.LabelFrame(main_frame, text="Log de Atividades", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)

        # Botão para salvar log
        save_log_button = ttk.Button(log_frame, text="Salvar Log", command=self.salvar_log)
        save_log_button.pack(anchor=tk.E, pady=5)

        # Mensagem inicial
        self.log_msg("🚀 Aplicativo iniciado. Selecione uma planilha Excel para começar.")

    def selecionar_arquivo(self):
        """Seleciona o arquivo Excel com os contatos"""
        # Diretório inicial baseado na última seleção
        initial_dir = self.config.get("last_directory", "")
        if not os.path.exists(initial_dir):
            initial_dir = os.path.expanduser("~")

        arquivo = filedialog.askopenfilename(
            filetypes=[("Excel Files", "*.xlsx")],
            initialdir=initial_dir
        )

        if arquivo:
            self.arquivo_excel = arquivo
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, arquivo)
            self.start_button.config(state=tk.NORMAL)

            # Salva o diretório para uso futuro
            self.config["last_directory"] = os.path.dirname(arquivo)
            ConfigManager.save_config(self.config)

            self.log_msg(f"✅ Planilha selecionada: {arquivo}")

            # Tenta ler a planilha para verificar se está no formato correto
            try:
                contatos = ExcelReader.read_contacts(arquivo)
                self.log_msg(f"📋 {len(contatos)} contatos encontrados na planilha.")
            except Exception as e:
                messagebox.showerror("Erro", str(e))
                self.log_msg(f"❌ Erro ao ler a planilha: {str(e)}")

    def iniciar_envio(self):
        """Inicia o processo de envio de mensagens"""
        if not self.arquivo_excel:
            messagebox.showerror("Erro", "Selecione uma planilha Excel primeiro.")
            return

        # Atualiza as configurações
        self.config["browser_profile"] = self.profile_var.get()
        self.config["wait_time"] = self.wait_var.get()
        self.config["max_retries"] = self.retry_var.get()
        self.config["headless"] = self.headless_var.get()
        ConfigManager.save_config(self.config)

        # Configura o sender com as novas configurações
        self.sender.max_retries = self.config["max_retries"]

        # Atualiza os botões
        self.start_button.config(state=tk.DISABLED)
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)

        # Limpa o log
        self.log.delete(1.0, tk.END)
        self.log_msg("🚀 Iniciando processo de envio...")

        # Inicia o processo em uma thread separada
        threading.Thread(target=self.executar_envios).start()

    def executar_envios(self):
        """Executa o processo de envio em uma thread separada"""
        try:
            # Lê os contatos da planilha
            contatos = ExcelReader.read_contacts(self.arquivo_excel)

            if not contatos:
                self.log_msg("⚠️ Nenhum contato válido encontrado na planilha.")
                self.reset_ui()
                return

            # Executa o envio de mensagens
            asyncio.run(self.sender.process_contacts(contatos))

        except Exception as e:
            self.log_msg(f"❌ Erro durante o processo: {str(e)}")
            messagebox.showerror("Erro", str(e))
        finally:
            self.reset_ui()

    def pausar_envio(self):
        """Pausa o processo de envio"""
        self.sender.pause()
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.NORMAL)

    def retomar_envio(self):
        """Retoma o processo de envio"""
        self.sender.resume()
        self.pause_button.config(state=tk.NORMAL)
        self.resume_button.config(state=tk.DISABLED)

    def interromper_envio(self):
        """Interrompe o processo de envio"""
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja interromper o envio?"):
            self.sender.stop()
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def reset_ui(self):
        """Reseta a interface após o término do processo"""
        self.start_button.config(state=tk.NORMAL)
        self.pause_button.config(state=tk.DISABLED)
        self.resume_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.DISABLED)

    def log_msg(self, msg):
        """Adiciona uma mensagem ao log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log.see(tk.END)

    def update_progress(self, value, max_value):
        """Atualiza a barra de progresso"""
        if max_value > 0:
            self.progress["value"] = (value / max_value) * 100
            self.progress_label.config(text=f"{value}/{max_value} mensagens processadas")
        else:
            self.progress["value"] = 0
            self.progress_label.config(text="0/0 mensagens processadas")

    def salvar_log(self):
        """Salva o conteúdo do log em um arquivo de texto"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"log_whatsapp_{timestamp}.txt"

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            initialfile=filename,
            filetypes=[("Arquivos de Texto", "*.txt"), ("Todos os Arquivos", "*.*")]
        )

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.log.get(1.0, tk.END))
                messagebox.showinfo("Sucesso", f"Log salvo com sucesso em:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao salvar o log: {str(e)}")


# Função principal
def main():
    root = tk.Tk()
    app = App(root)

    # Configura o ícone da aplicação (opcional)
    try:
        root.iconbitmap("topfamalogo.ico")
    except:
        pass

    # Configura o encerramento da aplicação
    def on_closing():
        if hasattr(app, 'sender') and app.sender.running:
            if messagebox.askyesno("Confirmar Saída", "O processo de envio está em andamento. Deseja realmente sair?"):
                app.sender.stop()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Inicia o loop principal
    root.mainloop()


if __name__ == "__main__":
    main()
