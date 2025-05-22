"""
Gerenciador de envio de mensagens via WhatsApp Web
"""

import asyncio
import os
from urllib.parse import quote

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from utils.phone_formatter import PhoneNumberFormatter
from utils.logger import Logger
from utils.progress_tracker import ProgressTracker

from plyer import notification


class WhatsAppSender:
    """Gerenciador de envio de mensagens via WhatsApp Web"""

    def __init__(self, logger=None, progress_tracker=None):
        """Inicializa o gerenciador de envio de mensagens

        Args:
            logger (Logger, optional): Instância de Logger para registro de logs
            progress_tracker (ProgressTracker, optional): Instância de ProgressTracker
        """
        # Componentes auxiliares
        self.logger = logger or Logger()
        self.progress = progress_tracker or ProgressTracker()

        # Estado do processo
        self.running = False
        self.paused = False

        # Estatísticas
        self.total_messages = 0
        self.sent_messages = 0
        self.failed_messages = []
        self.retry_count = {}

        # Configurações
        self.max_retries = 3
        self.wait_time = 5  # segundos
        self.headless = False
        self.user_data_dir = "whatsapp_profile"

        # Recursos do navegador
        self.browser = None
        self.page = None
        self.playwright = None

        # Task principal para controle de cancelamento
        self.main_task = None

    async def initialize_browser(self):
        """Inicializa o navegador para a sessão do WhatsApp Web

        Configura e inicia o navegador Chromium via Playwright,
        otimizando configurações para reduzir uso de recursos.

        Returns:
            bool: True se inicializado com sucesso
        """
        self.logger.log("\U0001F680 Inicializando navegador...")

        # Garante que o diretório existe
        os.makedirs(self.user_data_dir, exist_ok=True)

        # Define o caminho para os binários do Playwright
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "./ms-playwright"

        playwright = None
        browser = None

        try:
            # Inicia o Playwright e o navegador
            playwright = await async_playwright().start()
            self.playwright = playwright

            # Configurações otimizadas para o navegador
            browser_args = []
            if self.headless:
                browser_args.extend([
                    '--disable-gpu',
                    '--disable-dev-shm-usage',
                    '--disable-setuid-sandbox',
                    '--no-sandbox',
                ])

            browser = await playwright.chromium.launch_persistent_context(
                user_data_dir=self.user_data_dir,
                headless=self.headless,
                args=browser_args
            )
            self.browser = browser

            # Obtém a página ou cria uma nova
            self.page = browser.pages[0] if browser.pages else await browser.new_page()

            # Otimiza o carregamento da página no modo headless
            if self.headless:
                # Bloqueia recursos não essenciais para melhorar performance
                await self.page.route('**/*.{png,jpg,jpeg,gif,svg,css,woff,woff2,ttf,otf}',
                                    lambda route: route.abort())

            # Acessa o WhatsApp Web e aguarda o carregamento
            await self.page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded")
            self.logger.log("\U0001F50D Verificando status do login no WhatsApp...")

            # Aguarda até que o WhatsApp esteja carregado (conversas visíveis)
            await self.page.wait_for_selector('div[role="grid"]', timeout=0)
            self.logger.log("✅ WhatsApp Web carregado e pronto para envio!")

            return True

        except Exception as e:
            self.logger.log(f"❌ Erro ao inicializar o navegador: {str(e)}")

            # Em caso de erro, libera os recursos já alocados
            if browser and browser != self.browser:
                try:
                    await browser.close()
                except Exception:
                    pass

            if playwright and playwright != self.playwright:
                try:
                    await playwright.stop()
                except Exception:
                    pass

            # Propaga a exceção para tratamento adequado
            raise

    async def send_message(self, phone, message):
        """Envia uma mensagem para um número específico

        Acessa a conversa do WhatsApp com o número especificado,
        envia a mensagem e aguarda confirmação de envio.

        Args:
            phone (str): Número de telefone do destinatário
            message (str): Texto da mensagem a ser enviada

        Returns:
            bool: True se a mensagem foi enviada com sucesso
        """
        if not message.strip():
            self.logger.log(f"⚠️ Mensagem vazia para {phone}, pulando...")
            return False

        if not self.running or not self.browser or not self.page:
            return False

        try:
            # Normaliza o número de telefone
            normalized_phone = PhoneNumberFormatter.normalize(phone)

            # Codifica a mensagem para URL
            encoded_message = quote(message)

            # Constrói a URL do WhatsApp
            url = f"https://web.whatsapp.com/send/?phone={normalized_phone}&text={encoded_message}&type=phone_number&app_absent=0"

            self.logger.log(f"🔗 Acessando conversa com {normalized_phone}...")

            # Otimiza o carregamento da página
            await self.page.goto(url, wait_until="domcontentloaded")

            # Espera até que a página carregue e o campo de mensagem esteja disponível
            try:
                # Verifica novamente se o processo foi interrompido
                if not self.running:
                    return False

                # Usa uma estratégia de espera mais eficiente
                await self.page.wait_for_selector('div[contenteditable="true"]',
                                                state="visible",
                                                timeout=30000)

                # Pequena pausa para garantir que a página está completamente carregada
                await asyncio.sleep(1.5)  # Mais eficiente que wait_for_timeout

                # Verifica se há mensagem de erro de número inválido
                invalid_number = await self.page.query_selector('div[data-animate-modal-body="true"]')
                if invalid_number:
                    self.logger.log(f"❌ Número inválido: {normalized_phone}")
                    return False

                # Verifica novamente se o processo foi interrompido
                if not self.running:
                    return False

                # Envia a mensagem
                await self.page.keyboard.press("Enter")
                self.logger.log(f"📤 Mensagem enviada para {normalized_phone}, aguardando confirmação...")

                # Espera pela confirmação de envio de forma mais eficiente
                await self.page.wait_for_selector('div.message-out',
                                                state="visible",
                                                timeout=15000)
                await self.page.wait_for_selector('span[data-icon="msg-check"], span[data-icon="msg-dblcheck"]',
                                                state="visible",
                                                timeout=10000)

                self.logger.log(f"✅ Mensagem confirmada para {normalized_phone}")
                return True

            except PlaywrightTimeoutError as e:
                self.logger.log(f"⚠️ Timeout ao enviar mensagem para {normalized_phone}: {str(e)}")
                return False

        except Exception as e:
            self.logger.log(f"❌ Erro ao enviar mensagem para {normalized_phone}: {str(e)}")
            return False

    async def process_contacts(self, contacts):
        """Processa a lista de contatos e envia mensagens

        Inicializa o navegador, processa os contatos em lotes e
        tenta reenviar mensagens que falharam.

        Args:
            contacts (list): Lista de tuplas (telefone, mensagem)
        """
        # Inicializa o estado do processo
        self.running = True
        self.paused = False
        self.total_messages = len(contacts)
        self.sent_messages = 0
        self.failed_messages = []
        self.retry_count = {}

        # Inicializa a barra de progresso
        self.progress.update(0, self.total_messages)

        try:
            # Cria uma task principal para poder cancelar facilmente
            self.main_task = asyncio.create_task(self._process_contacts_internal(contacts))
            await self.main_task

        except asyncio.CancelledError:
            self.logger.log("🛑 Processo cancelado.")
        except Exception as e:
            self.logger.log(f"❌ Erro durante o processamento: {str(e)}")
        finally:
            # Finaliza o processo, garantindo liberação de recursos
            await self._finalize_process()

    async def _process_contacts_internal(self, contacts):
        """Implementação interna do processamento de contatos

        Método separado para facilitar o cancelamento da task.

        Args:
            contacts (list): Lista de tuplas (telefone, mensagem)
        """
        browser_initialized = False

        try:
            # Inicializa o navegador uma única vez
            browser_initialized = await self.initialize_browser()

            # Processa cada contato em lotes para melhor performance
            batch_size = min(10, self.total_messages)  # Tamanho do lote adaptativo

            for i in range(0, self.total_messages, batch_size):
                # Verifica se o processo foi interrompido
                if not self.running:
                    break

                # Cria um lote de contatos
                batch = contacts[i:i+batch_size]

                # Processa o lote
                for j, (phone, message) in enumerate(batch):
                    current_index = i + j

                    # Verifica se o processo foi interrompido
                    if not self.running:
                        self.logger.log("🛑 Processo interrompido pelo usuário.")
                        break

                    # Verifica se está pausado
                    while self.paused and self.running:
                        await asyncio.sleep(0.5)  # Reduz o intervalo de verificação

                    # Atualiza o progresso
                    self.progress.update(current_index)

                    # Tenta enviar a mensagem
                    success = await self.send_message(phone, message)

                    if success:
                        self.sent_messages += 1
                    else:
                        # Adiciona à lista de falhas
                        self.failed_messages.append((phone, message))

                    # Pausa entre mensagens para evitar bloqueio (inclusive após a última)
                    if self.running:  # Só aguarda se ainda estiver rodando
                        self.logger.log(f"⏳ Aguardando {self.wait_time} segundos antes de continuar...")
                        await asyncio.sleep(self.wait_time)

                # Verifica novamente se o processo foi interrompido após o lote
                if not self.running:
                    break

            # Tenta reenviar mensagens que falharam (até max_retries vezes)
            if self.running and browser_initialized:
                await self._retry_failed_messages()

        except Exception as e:
            self.logger.log(f"❌ Erro durante o processamento: {str(e)}")
            raise
        finally:
            # Garante que o navegador seja fechado mesmo em caso de erro
            if not self.running and browser_initialized:
                try:
                    await self._close_browser_resources()
                except Exception as e:
                    self.logger.log(f"⚠️ Erro ao fechar recursos do navegador: {str(e)}")

    async def _close_browser_resources(self):
        """Fecha os recursos do navegador de forma segura"""
        try:
            if self.browser:
                await self.browser.close()
                self.browser = None

            if self.playwright:
                await self.playwright.stop()
                self.playwright = None

            self.page = None
        except Exception as e:
            self.logger.log(f"⚠️ Erro ao fechar recursos do navegador: {str(e)}")
            # Reseta as referências mesmo em caso de erro
            self.browser = None
            self.playwright = None
            self.page = None

    async def _retry_failed_messages(self):
        """Tenta reenviar mensagens que falharam

        Processa as mensagens com falha em lotes, respeitando
        o número máximo de tentativas configurado.
        """
        if not self.failed_messages or not self.running:
            return

        self.logger.log(f"🔄 Tentando reenviar {len(self.failed_messages)} mensagens que falharam...")

        retry_messages = self.failed_messages.copy()
        self.failed_messages = []

        # Processa as mensagens com falha em lotes para melhor performance
        batch_size = min(5, len(retry_messages))  # Tamanho do lote menor para retry

        try:
            for i in range(0, len(retry_messages), batch_size):
                # Verifica se o processo foi interrompido
                if not self.running:
                    self.logger.log("🛑 Processo de retry interrompido pelo usuário.")
                    break

                # Cria um lote de mensagens com falha
                batch = retry_messages[i:i+batch_size]

                for phone, message in batch:
                    # Verifica se o processo foi interrompido
                    if not self.running:
                        self.logger.log("🛑 Processo de retry interrompido pelo usuário.")
                        break

                    # Verifica se está pausado
                    while self.paused and self.running:
                        await asyncio.sleep(0.5)

                    # Verifica o número de tentativas
                    self.retry_count[phone] = self.retry_count.get(phone, 0) + 1

                    if self.retry_count[phone] <= self.max_retries:
                        self.logger.log(f"🔄 Tentativa {self.retry_count[phone]} para {phone}...")
                        success = await self.send_message(phone, message)

                        if success:
                            self.sent_messages += 1
                        else:
                            self.failed_messages.append((phone, message))

                        # Pausa entre mensagens
                        if self.running:  # Só aguarda se ainda estiver rodando
                            await asyncio.sleep(self.wait_time)
                    else:
                        self.logger.log(f"❌ Número máximo de tentativas excedido para {phone}")
                        self.failed_messages.append((phone, message))

                # Verifica novamente se o processo foi interrompido após o lote
                if not self.running:
                    break
        except Exception as e:
            self.logger.log(f"❌ Erro durante o reenvio de mensagens: {str(e)}")
            # Não propaga a exceção para não interromper o processo principal

    async def _finalize_process(self):
        """Finaliza o processo de envio

        Atualiza o progresso final, fecha o navegador de forma limpa
        e gera um relatório final com estatísticas.
        """
        # Atualiza o progresso final
        self.progress.update(self.total_messages)

        # Fecha o navegador de forma limpa
        try:
            await self._close_browser_resources()
        except Exception as e:
            self.logger.log(f"⚠️ Erro ao fechar recursos do navegador: {str(e)}")
        finally:
            # Garante que o estado seja atualizado mesmo em caso de erro
            self.running = False

        # Relatório final
        self.logger.log("\n📊 RELATÓRIO FINAL:")
        self.logger.log(f"✅ Mensagens enviadas com sucesso: {self.sent_messages}/{self.total_messages}")
        self.logger.log(f"❌ Mensagens com falha: {len(self.failed_messages)}/{self.total_messages}")

        if self.failed_messages:
            self.logger.log("\n⚠️ Números com falha no envio:")
            for index, (phone, message, _) in enumerate(self.failed_messages):
                self.logger.log(f"  - Linha {index+2}: {phone} → '{message}'")

        self.logger.log("\n🏁 Processo finalizado.")

        #Notificação
        if self.sent_messages > 0 or self.failed_messages:
            mensagem = f"{self.sent_messages} enviadas com sucesso, {len(self.failed_messages)} com falha."
            notification.notify(
                title="TopChat – Envio Finalizado",
                message=mensagem,
                app_name="TopChat",
                timeout=5
            )

        self.logger.log("\n🏁 Processo finalizado.")


    async def stop(self):
        """Interrompe o envio e encerra imediatamente o navegador"""
        if not self.running:
            return

        self.logger.log("🛑 Interrompendo o processo... Fechando navegador...")
        self.running = False

        # Cancela a task principal se existir
        if self.main_task and not self.main_task.done():
            self.main_task.cancel()
            try:
                # Aguarda pelo cancelamento com timeout maior
                await asyncio.wait_for(self.main_task, timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        # Força o fechamento do navegador imediatamente
        try:
            await self._close_browser_resources()
        except Exception as e:
            self.logger.log(f"⚠️ Erro ao fechar o navegador: {str(e)}")
        finally:
            # Garante que o processo seja considerado finalizado
            self.browser = None
            self.page = None
            self.playwright = None

            self.logger.log("✅ Navegador fechado e processo interrompido com sucesso.")
