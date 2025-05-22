"""
Leitor de dados de planilhas Excel
"""

import os
import pandas as pd


class ExcelReader:
    """Leitor de dados de planilhas Excel"""

    @staticmethod
    def read_contacts(file_path):
        """Lê os contatos da planilha Excel a partir da linha 2
        
        Lê uma planilha Excel contendo números de telefone e mensagens,
        ignorando a primeira linha (cabeçalho) e linhas com números vazios.
        
        Args:
            file_path (str): Caminho do arquivo Excel
            
        Returns:
            list: Lista de tuplas (telefone, mensagem)
            
        Raises:
            FileNotFoundError: Se o arquivo não existir
            Exception: Se houver erro na leitura
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        # Lê a planilha ignorando a primeira linha (linha de título)
        # Usa otimização para ler apenas as colunas necessárias
        df = pd.read_excel(
            file_path, 
            header=None, 
            skiprows=1, 
            usecols=[0, 1],  # Lê apenas as duas primeiras colunas
            dtype={0: str, 1: str}
        )

        # Filtra linhas vazias de forma eficiente
        df = df.dropna(subset=[0])  # Remove linhas com número vazio
        
        # Processa os dados de forma otimizada
        contatos = []
        for _, row in df.iterrows():
            numero = str(row[0]).strip()
            mensagem = str(row[1]).strip() if pd.notna(row[1]) else ""
            contatos.append((numero, mensagem))

        return contatos
