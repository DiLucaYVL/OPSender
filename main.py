"""
Arquivo principal para inicialização do aplicativo TopChat
"""

import os
import sys
import tkinter as tk
from app import App


def main():
    """Função principal do aplicativo

    Inicializa a interface gráfica e configura o encerramento
    adequado da aplicação.
    """
    # Adiciona o diretório atual ao PATH para garantir que as importações funcionem
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

    root = tk.Tk()
    app = App(root)

    # Configura o ícone da aplicação
    try:
        icon_path = os.path.join(base_dir, "topchatlogo.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception as e:
        print(f"Erro ao carregar ícone: {str(e)}")

    # Configura o encerramento da aplicação
    def on_closing():
        if hasattr(app, 'sender') and app.sender.running:
            if tk.messagebox.askyesno("Confirmar Saída", "O processo de envio está em andamento. Deseja realmente sair?"):
                app.sender.stop()
                root.destroy()
        else:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)

    # Inicia o loop principal
    root.mainloop()


if __name__ == "__main__":
    main()
