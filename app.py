"""
Interface gráfica principal do aplicativo
"""

import asyncio
import os
import threading
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk
import tkinter as tk
from PIL import Image, ImageTk

from utils.config_manager import ConfigManager
from utils.excel_reader import ExcelReader
from utils.logger import Logger
from utils.progress_tracker import ProgressTracker
from whatsapp_sender import WhatsAppSender


class App:
    """Interface gráfica principal do aplicativo"""

    def __init__(self, master):
        """Inicializa a interface gráfica
        
        Args:
            master: Janela principal do Tkinter
        """
        self.master = master
        self.config = ConfigManager.load()

        # Configuração da janela principal
        master.title("OPS Sender")
        master.geometry("700x600")
        master.minsize(600, 500)

        # Variáveis de controle
        self.arquivo_excel = None
        
        # Inicializa componentes
        self._create_widgets()
        
        # Inicializa o sender com callbacks para log e progresso
        self.sender = WhatsAppSender(
            logger=Logger(self.log_msg),
            progress_tracker=ProgressTracker(self.update_progress)
        )

    def _create_widgets(self):
        """Cria os widgets da interface"""
        self._create_logo_section()
        main_frame = self._create_main_frame()
        self._create_file_section(main_frame)
        self._create_config_section(main_frame)
        self._create_control_section(main_frame)
        self._create_progress_section(main_frame)
        self._create_log_section(main_frame)
        
        # Mensagem inicial
        self.log_msg("🚀 Aplicativo iniciado. Selecione uma planilha Excel para começar.")

    def _create_logo_section(self):
        """Cria a seção do logo"""
        logo_container = tk.Frame(self.master)
        logo_container.pack(fill=tk.X)

        try:
            logo_image = Image.open("topfama_logo.png")
            logo_image = logo_image.resize((250, 90), Image.LANCZOS)
            self.logo_topfama_img = ImageTk.PhotoImage(logo_image)

            logo_label = ttk.Label(logo_container, image=self.logo_topfama_img)
            logo_label.pack(anchor="center")
        except Exception as e:
            print(f"Erro ao carregar imagens de logo: {e}")

    def _create_main_frame(self):
        """Cria o frame principal
        
        Returns:
            ttk.Frame: Frame principal
        """
        main_frame = ttk.Frame(self.master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        return main_frame

    def _create_file_section(self, parent):
        """Cria a seção de seleção de arquivo
        
        Args:
            parent: Widget pai
        """
        file_frame = ttk.LabelFrame(parent, text="Seleção de Arquivo", padding="5")
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

    def _create_config_section(self, parent):
        """Cria a seção de configurações
        
        Args:
            parent: Widget pai
        """
        config_frame = ttk.LabelFrame(parent, text="Configurações", padding="5")
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

    def _create_control_section(self, parent):
        """Cria a seção de controles
        
        Args:
            parent: Widget pai
        """
        control_frame = ttk.Frame(parent)
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

    def _create_progress_section(self, parent):
        """Cria a seção de progresso
        
        Args:
            parent: Widget pai
        """
        progress_frame = ttk.Frame(parent)
        progress_frame.pack(fill=tk.X, pady=5)

        self.progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X)

        self.progress_label = ttk.Label(progress_frame, text="0/0 mensagens processadas")
        self.progress_label.pack(anchor=tk.E, pady=2)

    def _create_log_section(self, parent):
        """Cria a seção de log
        
        Args:
            parent: Widget pai
        """
        log_frame = ttk.LabelFrame(parent, text="Log de Atividades", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.log = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD)
        self.log.pack(fill=tk.BOTH, expand=True)

        # Botão para salvar log
        save_log_button = ttk.Button(log_frame, text="Salvar Log", command=self.salvar_log)
        save_log_button.pack(anchor=tk.E, pady=5)

    def selecionar_arquivo(self):
        """Seleciona o arquivo Excel com os contatos
        
        Abre um diálogo para seleção de arquivo Excel e
        verifica se o formato está correto.
        """
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
            ConfigManager.save(self.config)

            self.log_msg(f"✅ Planilha selecionada: {arquivo}")

            # Tenta ler a planilha para verificar se está no formato correto
            try:
                contatos = ExcelReader.read_contacts(arquivo)
                self.log_msg(f"📋 {len(contatos)} contatos encontrados na planilha.")
            except Exception as e:
                messagebox.showerror("Erro", str(e))
                self.log_msg(f"❌ Erro ao ler a planilha: {str(e)}")

    def iniciar_envio(self):
        """Inicia o processo de envio de mensagens
        
        Configura o sender com as configurações atuais e
        inicia o processo em uma thread separada.
        """
        if not self.arquivo_excel:
            messagebox.showerror("Erro", "Selecione uma planilha Excel primeiro.")
            return

        # Atualiza as configurações
        self._update_config()

        # Configura o sender com as novas configurações
        self.sender.max_retries = self.config["max_retries"]
        self.sender.wait_time = self.config["wait_time"]
        self.sender.headless = self.config["headless"]
        self.sender.user_data_dir = self.config["browser_profile"]

        # Atualiza os botões
        self._update_buttons_state(sending=True)

        # Limpa o log
        self.log.delete(1.0, tk.END)
        self.log_msg("🚀 Iniciando processo de envio...")

        # Inicia o processo em uma thread separada
        threading.Thread(target=self.executar_envios, daemon=True).start()

    def _update_config(self):
        """Atualiza as configurações com os valores da interface"""
        self.config["browser_profile"] = self.profile_var.get()
        self.config["wait_time"] = self.wait_var.get()
        self.config["max_retries"] = self.retry_var.get()
        self.config["headless"] = self.headless_var.get()
        ConfigManager.save(self.config)

    def _update_buttons_state(self, sending=False, paused=False):
        """Atualiza o estado dos botões de controle
        
        Args:
            sending (bool): Se está enviando mensagens
            paused (bool): Se o envio está pausado
        """
        if sending:
            self.start_button.config(state=tk.DISABLED)
            self.pause_button.config(state=tk.NORMAL)
            self.resume_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        elif paused:
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.NORMAL)
        else:
            self.start_button.config(state=tk.NORMAL)
            self.pause_button.config(state=tk.DISABLED)
            self.resume_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.DISABLED)

    def executar_envios(self):
        """Executa o processo de envio em uma thread separada
        
        Lê os contatos da planilha e inicia o processo de envio
        de mensagens de forma assíncrona.
        """
        try:
            # Lê os contatos da planilha
            contatos = ExcelReader.read_contacts(self.arquivo_excel)

            if not contatos:
                self.log_msg("⚠️ Nenhum contato válido encontrado na planilha.")
                self._update_buttons_state()
                return

            # Executa o envio de mensagens
            asyncio.run(self.sender.process_contacts(contatos))

        except Exception as e:
            self.log_msg(f"❌ Erro durante o processo: {str(e)}")
            messagebox.showerror("Erro", str(e))
        finally:
            self._update_buttons_state()

    def pausar_envio(self):
        """Pausa o processo de envio"""
        self.sender.pause()
        self._update_buttons_state(sending=True, paused=True)

    def retomar_envio(self):
        """Retoma o processo de envio"""
        self.sender.resume()
        self._update_buttons_state(sending=True)

    def interromper_envio(self):
        """Interrompe o processo de envio
        
        Solicita confirmação do usuário antes de interromper.
        """
        if messagebox.askyesno("Confirmar", "Tem certeza que deseja interromper o envio?"):
            self.sender.stop()
            self._update_buttons_state()

    def log_msg(self, msg):
        """Adiciona uma mensagem ao log
        
        Args:
            msg (str): Mensagem a ser adicionada
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.log.see(tk.END)

    def update_progress(self, value, max_value):
        """Atualiza a barra de progresso
        
        Args:
            value (int): Valor atual do progresso
            max_value (int): Valor máximo do progresso
        """
        if max_value > 0:
            self.progress["value"] = (value / max_value) * 100
            self.progress_label.config(text=f"{value}/{max_value} mensagens processadas")
        else:
            self.progress["value"] = 0
            self.progress_label.config(text="0/0 mensagens processadas")

    def salvar_log(self):
        """Salva o conteúdo do log em um arquivo de texto
        
        Abre um diálogo para seleção do local de salvamento
        e salva o conteúdo atual do log.
        """
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
