# OPS Sender - Documentação Completa

## Visão Geral

OPS Sender é uma aplicação desktop para envio automatizado de mensagens via WhatsApp Web. Desenvolvida em Python, a aplicação permite carregar uma planilha Excel contendo números de telefone e mensagens personalizadas, e envia essas mensagens de forma automatizada através da interface do WhatsApp Web.

## Estrutura do Projeto

```
modular_app/
├── utils/                  # Pacote de utilitários
│   ├── __init__.py         # Arquivo de inicialização do pacote
│   ├── phone_formatter.py  # Formatação de números de telefone
│   ├── logger.py           # Sistema de log com buffer
│   ├── progress_tracker.py # Rastreamento de progresso
│   ├── config_manager.py   # Gerenciamento de configurações
│   └── excel_reader.py     # Leitura de dados Excel
├── whatsapp_sender.py      # Lógica de envio de mensagens
├── app.py                  # Interface gráfica e controle principal
└── main.py                 # Ponto de entrada da aplicação
```

### Detalhamento dos Módulos

#### 1. Pacote `utils`

Contém classes utilitárias que podem ser reutilizadas em diferentes partes do projeto:

- **phone_formatter.py**: 
  - Classe `PhoneNumberFormatter` para normalização de números de telefone
  - Implementa cache para evitar processamento repetitivo
  - Adiciona código do país (55) e o dígito 9 para celulares brasileiros quando necessário

- **logger.py**: 
  - Classe `Logger` para registro de logs com timestamp
  - Implementa buffer limitado para economizar memória
  - Suporta callback para integração com interface gráfica

- **progress_tracker.py**: 
  - Classe `ProgressTracker` para monitoramento de progresso
  - Calcula porcentagem de conclusão
  - Suporta callback para atualização da barra de progresso na interface

- **config_manager.py**: 
  - Classe `ConfigManager` para gerenciamento de configurações
  - Salva e carrega configurações em formato JSON
  - Implementa cache para evitar leituras repetidas do arquivo

- **excel_reader.py**: 
  - Classe `ExcelReader` para leitura de planilhas Excel
  - Otimizada para ler apenas as colunas necessárias
  - Filtra linhas vazias e formata os dados para uso no aplicativo

#### 2. Módulo Principal de Envio

- **whatsapp_sender.py**: 
  - Classe `WhatsAppSender` para gerenciamento do envio de mensagens
  - Inicializa e controla o navegador via Playwright
  - Implementa lógica de envio, retry e relatório de resultados
  - Processa contatos em lotes para melhor performance
  - Suporta pausa, retomada e interrupção do processo

#### 3. Interface Gráfica

- **app.py**: 
  - Classe `App` para interface gráfica usando Tkinter
  - Implementa todas as telas e controles da aplicação
  - Gerencia o fluxo de trabalho do usuário
  - Integra-se com o WhatsAppSender através de callbacks

#### 4. Ponto de Entrada

- **main.py**: 
  - Função `main()` para inicialização da aplicação
  - Configura o encerramento adequado da aplicação
  - Ponto de entrada único para execução do programa

## Fluxo de Funcionamento

1. **Inicialização**:
   - O usuário inicia a aplicação através do arquivo `main.py`
   - A interface gráfica é carregada com as configurações salvas anteriormente

2. **Seleção de Arquivo**:
   - O usuário seleciona uma planilha Excel contendo números e mensagens
   - A aplicação valida o arquivo e exibe o número de contatos encontrados

3. **Configuração**:
   - O usuário pode ajustar configurações como:
     - Diretório do perfil do navegador
     - Tempo de espera entre mensagens
     - Número máximo de tentativas
     - Modo headless (navegador invisível)

4. **Envio de Mensagens**:
   - Ao clicar em "Iniciar Envio", o processo começa em uma thread separada
   - O navegador é inicializado e o WhatsApp Web é carregado
   - As mensagens são enviadas sequencialmente, com pausas entre elas
   - O progresso é exibido na interface gráfica

5. **Controle do Processo**:
   - O usuário pode pausar, retomar ou interromper o processo a qualquer momento
   - Logs detalhados são exibidos na interface
   - Ao final, um relatório de resultados é apresentado

6. **Finalização**:
   - O usuário pode salvar o log de atividades
   - As configurações são salvas automaticamente para uso futuro

## Dependências

### Bibliotecas Python

- **Bibliotecas Padrão**:
  - `asyncio`: Para operações assíncronas
  - `json`: Para manipulação de arquivos JSON
  - `os`: Para operações de sistema de arquivos
  - `re`: Para expressões regulares
  - `threading`: Para execução em threads separadas
  - `datetime`: Para formatação de timestamp
  - `functools`: Para decoradores como `lru_cache`
  - `urllib.parse`: Para codificação de URLs

- **Interface Gráfica**:
  - `tkinter`: Para criação da interface gráfica
  - `PIL` (Pillow): Para processamento de imagens

- **Processamento de Dados**:
  - `pandas`: Para leitura e manipulação de planilhas Excel

- **Automação Web**:
  - `playwright`: Para controle do navegador e automação web

### Requisitos de Sistema

- **Python**: Versão 3.6 ou superior
- **Sistema Operacional**: Windows, macOS ou Linux
- **Navegador**: Chromium (instalado automaticamente pelo Playwright)
- **Espaço em Disco**: Aproximadamente 200MB para a aplicação e dependências
- **Memória RAM**: Mínimo de 4GB recomendado

## Instalação

1. **Pré-requisitos**:
   ```bash
   # Instalar Python 3.6+
   # Instalar pip (gerenciador de pacotes Python)
   ```

2. **Instalação de Dependências**:
   ```bash
   pip install pandas playwright pillow
   playwright install chromium
   ```

3. **Execução**:
   ```bash
   python main.py
   ```

## Formato da Planilha Excel

A planilha deve seguir o seguinte formato:
- **Primeira linha**: Cabeçalho (ignorado pela aplicação)
- **Coluna A**: Números de telefone (com ou sem código do país)
- **Coluna B**: Mensagens personalizadas

Exemplo:
```
Telefone | Mensagem
5511999999999 | Olá, tudo bem?
11988888888 | Bom dia! Como vai?
```


