"""
Utilitário para formatação de números de telefone
"""

import re
from functools import lru_cache


class PhoneNumberFormatter:
    """Utilitário para formatação de números de telefone no padrão internacional"""
    
    @staticmethod
    @lru_cache(maxsize=128)  # Cache para evitar processamento repetido de números
    def normalize(phone):
        """Normaliza o número de telefone para o formato internacional
        
        Converte qualquer formato de número para o padrão internacional,
        adicionando código do país (55 para Brasil) e o 9 para celulares
        brasileiros quando necessário.
        
        Args:
            phone (str): Número de telefone em qualquer formato
            
        Returns:
            str: Número formatado no padrão internacional
        """
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
