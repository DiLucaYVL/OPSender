"""
Gerenciador de progresso com suporte a callbacks
"""


class ProgressTracker:
    """Gerenciador de progresso com suporte a callbacks"""
    
    def __init__(self, callback=None):
        """Inicializa o rastreador de progresso
        
        Args:
            callback (callable, optional): Função de callback para atualizar progresso
        """
        self.callback = callback
        self.current = 0
        self.total = 0
    
    def update(self, current=None, total=None):
        """Atualiza o progresso
        
        Atualiza os valores de progresso atual e total, e notifica
        o callback se configurado.
        
        Args:
            current (int, optional): Valor atual do progresso
            total (int, optional): Valor máximo do progresso
        """
        if current is not None:
            self.current = current
        if total is not None:
            self.total = total
            
        if self.callback:
            self.callback(self.current, self.total)
    
    @property
    def percentage(self):
        """Calcula a porcentagem de progresso
        
        Returns:
            float: Porcentagem de progresso (0-100)
        """
        if self.total <= 0:
            return 0
        return (self.current / self.total) * 100
