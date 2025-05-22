"""
Gerenciador de logs com suporte a callbacks e formatação de timestamp
"""

from datetime import datetime


class Logger:
    """Gerenciador de logs com suporte a callbacks e formatação de timestamp"""
    
    def __init__(self, callback=None):
        """Inicializa o logger
        
        Args:
            callback (callable, optional): Função de callback para receber logs
        """
        self.callback = callback
        self._buffer = []
        self._buffer_size = 100  # Limita o tamanho do buffer para economizar memória
    
    def log(self, message):
        """Registra uma mensagem no log
        
        Adiciona timestamp à mensagem, armazena no buffer interno e
        encaminha para o callback se configurado.
        
        Args:
            message (str): Mensagem a ser registrada
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        # Adiciona ao buffer interno com limite de tamanho
        self._buffer.append(formatted_message)
        if len(self._buffer) > self._buffer_size:
            self._buffer.pop(0)  # Remove o item mais antigo
            
        if self.callback:
            self.callback(message)
        else:
            print(formatted_message)
    
    def get_buffer(self):
        """Retorna o buffer de mensagens
        
        Returns:
            list: Lista de mensagens no buffer
        """
        return self._buffer.copy()
