"""
Gerenciador de configurações do aplicativo
"""

import json
import os
import sys


class ConfigManager:
    """Gerenciador de configurações do aplicativo"""

    # Determina o diretório de dados do aplicativo
    @classmethod
    def get_config_dir(cls):
        """
        Retorna o diretório onde o arquivo de configuração deve ser salvo.

        Returns:
            str: Caminho para o diretório de configuração
        """
        # Em produção, usa o diretório pai do executável
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(os.path.dirname(sys.executable))
        else:
            # Em desenvolvimento, usa o diretório atual
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

        # Cria um diretório de dados específico para o aplicativo
        data_dir = os.path.join(base_dir, "data")
        os.makedirs(data_dir, exist_ok=True)

        return data_dir

    @classmethod
    def get_config_path(cls):
        """
        Retorna o caminho completo para o arquivo de configuração.

        Returns:
            str: Caminho completo para o arquivo de configuração
        """
        return os.path.join(cls.get_config_dir(), "topchat_config.json")

    DEFAULT_CONFIG = {
        "last_directory": "",
        "browser_profile": "whatsapp_profile",
        "wait_time": 5,
        "max_retries": 3,
    }

    _config_cache = None  # Cache para evitar leituras repetidas do arquivo

    @classmethod
    def save(cls, config):
        """Salva as configurações em um arquivo JSON

        Args:
            config (dict): Dicionário com as configurações
        """
        try:
            # Atualiza o cache
            cls._config_cache = config.copy()

            # Garante que o diretório existe
            os.makedirs(cls.get_config_dir(), exist_ok=True)

            # Salva no arquivo
            with open(cls.get_config_path(), 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"Erro ao salvar configurações: {str(e)}")

    @classmethod
    def load(cls):
        """Carrega as configurações do arquivo JSON

        Returns:
            dict: Configurações carregadas ou padrão
        """
        # Retorna do cache se disponível
        if cls._config_cache is not None:
            return cls._config_cache.copy()

        try:
            config_path = cls.get_config_path()
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    cls._config_cache = config.copy()
                    return config
            
            # Se não existe, retorna o padrão
            cls._config_cache = cls.DEFAULT_CONFIG.copy()
            return cls._config_cache
        except Exception as e:
            print(f"Erro ao carregar configurações: {str(e)}")
            cls._config_cache = cls.DEFAULT_CONFIG.copy()
            return cls._config_cache
