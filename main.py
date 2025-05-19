"""
Arquivo principal para inicialização do aplicativo OPS Sender
"""

import tkinter as tk
from app import App


def main():
    """Função principal do aplicativo
    
    Inicializa a interface gráfica e configura o encerramento
    adequado da aplicação.
    """
    root = tk.Tk()
    app = App(root)

    # Configura o ícone da aplicação (opcional)
    try:
        root.iconbitmap("topfamalogo.ico")
    except:
        pass

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
