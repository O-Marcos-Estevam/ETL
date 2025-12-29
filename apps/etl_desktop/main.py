"""
ETL Pipeline Manager - Entry Point
===================================

Aplicação desktop para gerenciar e executar o pipeline ETL.
Usa CustomTkinter para interface moderna com tema escuro.

Uso:
    python main.py
"""

import sys
import os

# Adiciona o diretório pai ao path para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import customtkinter as ctk
from ui.main_window import MainWindow


def main():
    """Inicializa e executa a aplicação."""
    # Configurações do CustomTkinter
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    
    # Cria e executa a janela principal
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
