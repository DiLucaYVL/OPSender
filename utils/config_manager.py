"""
Gerenciador de configurações do aplicativo
"""

import json
import os


class ConfigManager:
    """Gerenciador de configurações do aplicativo"""

    CONFIG_FILE = "whatsapp_sender_config.json"
    DEFAULT_CONFIG = {
        "last_directory": "",
        "browser_profile": "whatsapp_profile",
        "wait_time": 5,
        "max_retries": 3,
        "headless": False
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
            
            # Salva no arquivo
            with open(cls.CONFIG_FILE, 'w', encoding='utf-8') as f:
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
            if os.path.exists(cls.CONFIG_FILE):
                with open(cls.CONFIG_FILE, 'r', encoding='utf-8') as f:
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
