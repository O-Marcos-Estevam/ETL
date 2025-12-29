"""
Main Window - Janela Principal da Aplicação
============================================

Interface principal com:
- Seleção de datas (período)
- Checkboxes para ativar/desativar sistemas
- Área de logs em tempo real
- Barra de progresso
- Botões de execução e configuração
"""

import customtkinter as ctk
from datetime import datetime, date
from typing import Callable, Optional
import threading


class MainWindow(ctk.CTk):
    """
    Janela principal da aplicação ETL Pipeline Manager.
    """
    
    def __init__(self):
        super().__init__()
        
        # Configurações da janela
        self.title("ETL Pipeline Manager")
        self.geometry("800x700")
        self.minsize(700, 600)
        
        # Estado
        self.is_running = False
        self.system_vars = {}
        
        # Configura grid principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # Log expande
        
        # Cria componentes
        self._create_header()
        self._create_date_section()
        self._create_systems_section()
        self._create_log_section()
        self._create_actions_section()
        self._create_status_bar()
    
    # =========================================================================
    # CRIAÇÃO DE COMPONENTES
    # =========================================================================
    
    def _create_header(self):
        """Cria cabeçalho com título."""
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        title = ctk.CTkLabel(
            header, 
            text="🚀 ETL Pipeline Manager",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title.pack(side="left")
        
        version = ctk.CTkLabel(
            header,
            text="v1.0.0",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        version.pack(side="left", padx=10)
    
    def _create_date_section(self):
        """Cria seção de seleção de período."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        frame.grid_columnconfigure((1, 3), weight=1)
        
        # Título
        title = ctk.CTkLabel(
            frame, 
            text="📅 Período",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 5))
        
        # Data Inicial
        lbl_ini = ctk.CTkLabel(frame, text="Data Inicial:")
        lbl_ini.grid(row=1, column=0, padx=(15, 5), pady=10)
        
        today = datetime.now()
        self.entry_date_ini = ctk.CTkEntry(frame, placeholder_text="DD/MM/YYYY")
        self.entry_date_ini.insert(0, today.strftime("%d/%m/%Y"))
        self.entry_date_ini.grid(row=1, column=1, padx=5, pady=10, sticky="ew")
        
        # Data Final
        lbl_fim = ctk.CTkLabel(frame, text="Data Final:")
        lbl_fim.grid(row=1, column=2, padx=(20, 5), pady=10)
        
        self.entry_date_fim = ctk.CTkEntry(frame, placeholder_text="DD/MM/YYYY")
        self.entry_date_fim.insert(0, today.strftime("%d/%m/%Y"))
        self.entry_date_fim.grid(row=1, column=3, padx=(5, 15), pady=10, sticky="ew")
    
    def _create_systems_section(self):
        """Cria seção de seleção de sistemas."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        
        # Título
        title = ctk.CTkLabel(
            frame, 
            text="⚡ Sistemas",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=0, column=0, columnspan=4, sticky="w", padx=15, pady=(10, 5))
        
        # Lista de sistemas
        systems = [
            ("amplis", "Amplis"),
            ("maps", "MAPS"),
            ("fidc_estoque", "FIDC Estoque"),
            ("jcot", "JCOT"),
            ("britech", "Britech"),
            ("qore_pdf", "QORE PDF"),
            ("qore_excel", "QORE Excel"),
            ("qore_xml", "QORE XML"),
            ("xml_upload", "XML Upload"),
        ]
        
        # Cria checkboxes em grid 3 colunas
        for i, (key, name) in enumerate(systems):
            row = (i // 3) + 1
            col = i % 3
            
            var = ctk.BooleanVar(value=False)
            self.system_vars[key] = var
            
            cb = ctk.CTkCheckBox(
                frame, 
                text=name,
                variable=var,
                onvalue=True,
                offvalue=False
            )
            cb.grid(row=row, column=col, padx=15, pady=8, sticky="w")
        
        # Botões Select All / Deselect All
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.grid(row=10, column=0, columnspan=3, pady=(5, 10))
        
        btn_all = ctk.CTkButton(
            btn_frame, 
            text="Selecionar Todos",
            width=130,
            height=28,
            command=self._select_all_systems
        )
        btn_all.pack(side="left", padx=5)
        
        btn_none = ctk.CTkButton(
            btn_frame, 
            text="Limpar Seleção",
            width=130,
            height=28,
            fg_color="gray",
            command=self._deselect_all_systems
        )
        btn_none.pack(side="left", padx=5)
    
    def _create_log_section(self):
        """Cria área de logs."""
        frame = ctk.CTkFrame(self)
        frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(1, weight=1)
        
        # Título
        title = ctk.CTkLabel(
            frame, 
            text="📋 Log de Execução",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title.grid(row=0, column=0, sticky="w", padx=15, pady=(10, 5))
        
        # Área de texto
        self.log_text = ctk.CTkTextbox(
            frame,
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Mensagem inicial
        self._log("Sistema pronto. Selecione os sistemas e clique em EXECUTAR.")
    
    def _create_actions_section(self):
        """Cria botões de ação."""
        frame = ctk.CTkFrame(self, fg_color="transparent")
        frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        frame.grid_columnconfigure((0, 1, 2), weight=1)
        
        # Botão Executar
        self.btn_execute = ctk.CTkButton(
            frame,
            text="🚀 EXECUTAR",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#28a745",
            hover_color="#218838",
            command=self._on_execute
        )
        self.btn_execute.grid(row=0, column=0, padx=10, sticky="ew")
        
        # Botão Parar
        self.btn_stop = ctk.CTkButton(
            frame,
            text="⏹️ PARAR",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45,
            fg_color="#dc3545",
            hover_color="#c82333",
            state="disabled",
            command=self._on_stop
        )
        self.btn_stop.grid(row=0, column=1, padx=10, sticky="ew")
        
        # Botão Configurações
        self.btn_config = ctk.CTkButton(
            frame,
            text="⚙️ Configurações",
            font=ctk.CTkFont(size=14),
            height=45,
            fg_color="gray",
            command=self._on_config
        )
        self.btn_config.grid(row=0, column=2, padx=10, sticky="ew")
    
    def _create_status_bar(self):
        """Cria barra de status inferior."""
        frame = ctk.CTkFrame(self, height=35, corner_radius=0)
        frame.grid(row=5, column=0, sticky="ew")
        frame.grid_columnconfigure(1, weight=1)
        
        # Status
        self.lbl_status = ctk.CTkLabel(
            frame, 
            text="Status: ⏸️ Aguardando",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_status.grid(row=0, column=0, padx=15, pady=5)
        
        # Barra de progresso
        self.progress = ctk.CTkProgressBar(frame, width=300)
        self.progress.grid(row=0, column=1, padx=10, pady=5, sticky="e")
        self.progress.set(0)
        
        # Porcentagem
        self.lbl_percent = ctk.CTkLabel(
            frame,
            text="0%",
            font=ctk.CTkFont(size=12)
        )
        self.lbl_percent.grid(row=0, column=2, padx=(5, 15), pady=5)
    
    # =========================================================================
    # MÉTODOS AUXILIARES
    # =========================================================================
    
    def _log(self, message: str):
        """Adiciona mensagem ao log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")  # Auto-scroll
    
    def _select_all_systems(self):
        """Seleciona todos os sistemas."""
        for var in self.system_vars.values():
            var.set(True)
    
    def _deselect_all_systems(self):
        """Desmarca todos os sistemas."""
        for var in self.system_vars.values():
            var.set(False)
    
    def _update_status(self, text: str):
        """Atualiza texto de status."""
        self.lbl_status.configure(text=f"Status: {text}")
    
    def _update_progress(self, value: float):
        """Atualiza barra de progresso (0.0 a 1.0)."""
        self.progress.set(value)
        self.lbl_percent.configure(text=f"{int(value * 100)}%")
    
    def _get_selected_systems(self) -> list:
        """Retorna lista de sistemas selecionados."""
        return [key for key, var in self.system_vars.items() if var.get()]
    
    # =========================================================================
    # EVENT HANDLERS
    # =========================================================================
    
    def _on_execute(self):
        """Handler do botão Executar."""
        selected = self._get_selected_systems()
        
        if not selected:
            self._log("⚠️ Nenhum sistema selecionado!")
            return
        
        self._log(f"🚀 Iniciando execução: {', '.join(selected)}")
        self._update_status("▶️ Executando...")
        
        # Atualiza UI
        self.btn_execute.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.is_running = True
        
        # TODO: Iniciar execução em thread separada
        # Por enquanto, simula progresso
        self._simulate_execution(selected)
    
    def _on_stop(self):
        """Handler do botão Parar."""
        self._log("⏹️ Execução interrompida pelo usuário.")
        self._update_status("⏹️ Parado")
        self.is_running = False
        
        self.btn_execute.configure(state="normal")
        self.btn_stop.configure(state="disabled")
    
    def _on_config(self):
        """Handler do botão Configurações."""
        self._log("⚙️ Abrindo configurações...")
        # TODO: Abrir diálogo de configurações
    
    def _simulate_execution(self, systems: list):
        """Simula execução para demonstração."""
        def run():
            import time
            total = len(systems)
            for i, sys in enumerate(systems):
                if not self.is_running:
                    break
                    
                self.after(0, lambda s=sys: self._log(f"➡️ Executando {s}..."))
                time.sleep(1)  # Simula trabalho
                
                progress = (i + 1) / total
                self.after(0, lambda p=progress: self._update_progress(p))
                self.after(0, lambda s=sys: self._log(f"✅ {s} concluído!"))
            
            self.after(0, self._execution_finished)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
    
    def _execution_finished(self):
        """Chamado quando a execução termina."""
        self._log("🎉 Execução finalizada!")
        self._update_status("✅ Concluído")
        
        self.btn_execute.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.is_running = False


# Para testes
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = MainWindow()
    app.mainloop()
