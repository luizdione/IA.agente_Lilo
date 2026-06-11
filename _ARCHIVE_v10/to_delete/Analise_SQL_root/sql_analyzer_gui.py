

"""
Interface Gráfica para Sistema de Análise Estatística de Dados SQL
===================================================================
Interface moderna usando CustomTkinter para análise estatística automatizada.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import pandas as pd
import threading
from typing import Optional
import sys
import os
from pathlib import Path
from datetime import datetime
import shutil
import subprocess
import tempfile
import textwrap

# Importar o módulo de análise
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from sql_statistical_analyzer import DatabaseConnection, BiologicalDataAnalyzer


class SQLStatisticalAnalyzerGUI:
    """
    Interface gráfica principal para análise estatística de dados SQL.
    Segue o padrão do exemplo_uso.py com funcionalidades completas.
    """

    def __init__(self):
        """Inicializa a interface gráfica"""
        # Configuração do tema
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Janela principal
        self.root = ctk.CTk()
        self.root.title("LILO - IA para análise de dados em SQL e estatística")
        try:
            sw = int(self.root.winfo_screenwidth())
            sh = int(self.root.winfo_screenheight())
            # 16:9 widescreen
            h = min(int(sh * 0.88), 900)
            w = min(int(h * 16 / 9), int(sw * 0.92))
            self.root.geometry(f"{w}x{h}")
            self.root.minsize(int(w * 0.85), int(h * 0.85))
            self.window_width = w
            self.window_height = h
        except Exception:
            self.root.geometry("1100x900")
            self.window_width = 1100
            self.window_height = 900

        # Estilos unificados
        self.btn_fg = "#1f7a1f"
        self.btn_hover = "#166116"
        self.btn_border = "#2aa02a"
        # Fontes (reduzidas para evitar cortes em combobox/entry)
        self.font_select_label = ctk.CTkFont(size=14)
        self.font_select_value = ctk.CTkFont(size=13)

        self.left_width_ratio = 0.50
        self._accent_preset = "green"

        # Variáveis de estado
        self.db_connection = DatabaseConnection()
        self.current_data: Optional[pd.DataFrame] = None
        self.analyzer: Optional[BiologicalDataAnalyzer] = None
        self.current_figures = []

        # Pasta padrão para salvar gráficos
        self.graficos_dir = Path(__file__).parent / "graficos"
        try:
            self.graficos_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        self.rscript_path = shutil.which("Rscript")

        # Configurações padrão de conexão
        self.default_connections = {
            'Servidor 1 (Hostinger)': {
                'host': 'auth-db887.hstgr.io',
                'database': 'u112348440_ifrj_crj_lgm',
                'user': 'u112348440_Desenvolvedor',
                'password': 'DarwinMendel2025@@##',
                'port': 3306
            },
            'Servidor 2 (Local/Remoto)': {
                'host': '127.0.0.1',
                'database': 'u112348440_cx120',
                'user': 'u112348440_Darwin',
                'password': 'DarwinMendel2025@@##',
                'port': 3306
            }
        }

        self._create_widgets()
        self._layout_widgets()

    def _apply_layout_preset(self, preset: str):
        try:
            if preset == "compact":
                self.left_width_ratio = 0.30
            elif preset == "wide":
                self.left_width_ratio = 0.40
            elif preset == "half":
                self.left_width_ratio = 0.50
            else:
                self.left_width_ratio = 0.35

            w = int(getattr(self, "window_width", 1100) * self.left_width_ratio)
            try:
                self.left_column.configure(width=w)
            except Exception:
                pass

            # Force layout refresh
            try:
                self.root.update_idletasks()
            except Exception:
                pass
        except Exception:
            pass

    def _apply_theme(self, appearance: str, preset: str):
        """Aplica tema: appearance = Dark/Light/System; preset = green/windows11/luna/ios."""
        try:
            ctk.set_appearance_mode(appearance)
        except Exception:
            pass

        self._accent_preset = preset

        # Presets visuais (aproximações — CustomTkinter não usa CSS)
        if preset == "windows11":
            try:
                ctk.set_appearance_mode("Light")
            except Exception:
                pass
            self.btn_fg = "#0078D4"
            self.btn_hover = "#106EBE"
            self.btn_border = "#2B88D8"
        elif preset == "luna":
            # Windows XP Luna (aproximação): azul vivo + highlight
            try:
                ctk.set_appearance_mode("Light")
            except Exception:
                pass
            self.btn_fg = "#2A6BD4"
            self.btn_hover = "#1F5CB8"
            self.btn_border = "#6AA7FF"
        elif preset == "ios":
            # iOS (aproximação): acento azul iOS em modo claro
            try:
                ctk.set_appearance_mode("Light")
            except Exception:
                pass
            self.btn_fg = "#0A84FF"
            self.btn_hover = "#006EDB"
            self.btn_border = "#66B6FF"
        else:
            # green default
            self.btn_fg = "#1f7a1f"
            self.btn_hover = "#166116"
            self.btn_border = "#2aa02a"

        self._apply_button_style()

    def _apply_button_style(self):
        """Atualiza cores dos principais botões já criados."""
        btn_names = [
            "theme_dark_btn",
            "theme_light_btn",
            "theme_system_btn",
            "preset_win11_btn",
            "preset_luna_btn",
            "preset_ios_btn",
            "layout_compact_btn",
            "layout_narrow_btn",
            "layout_wide_btn",
            "connect_btn",
            "science_help_btn",
            "refresh_tables_btn",
            "csv_import_browse_btn",
            "csv_import_load_btn",
            "file_browse_btn",
            "file_load_btn",
            "load_data_btn",
            "preview_test_btn",
            "plot_info_btn",
            "inspect_btn",
            "recommend_btn",
            "execute_btn",
            "visualize_btn",
            "report_btn",
            "sqlite_browse_btn",
            "sqlite_open_btn",
        ]
        for n in btn_names:
            try:
                b = getattr(self, n)
            except Exception:
                continue
            try:
                b.configure(fg_color=self.btn_fg, hover_color=self.btn_hover)
            except Exception:
                pass
        try:
            self.plot_info_btn.configure(border_color=self.btn_border)
        except Exception:
            pass

    def _create_widgets(self):
        """Cria todos os widgets da interface"""

        # ==================== FRAME PRINCIPAL COM 2 COLUNAS ====================
        self.main_container = ctk.CTkFrame(self.root)

        # Barra de status inferior
        self.status_bar = ctk.CTkFrame(self.root, fg_color="transparent", height=26)
        self.status_left = ctk.CTkFrame(self.status_bar, fg_color="transparent")
        self.status_right = ctk.CTkFrame(self.status_bar, fg_color="transparent")

        # Botões de tema (ícones)
        self.theme_dark_btn = ctk.CTkButton(
            self.status_left,
            text="☾",
            width=32,
            height=22,
            command=lambda: self._apply_theme("Dark", "green"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.theme_light_btn = ctk.CTkButton(
            self.status_left,
            text="☀",
            width=32,
            height=22,
            command=lambda: self._apply_theme("Light", "green"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.theme_system_btn = ctk.CTkButton(
            self.status_left,
            text="⛭",
            width=32,
            height=22,
            command=lambda: self._apply_theme("System", "green"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Presets de estilo
        self.preset_win11_btn = ctk.CTkButton(
            self.status_left,
            text="Win11",
            width=54,
            height=22,
            command=lambda: self._apply_theme("Light", "windows11"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.preset_luna_btn = ctk.CTkButton(
            self.status_left,
            text="Luna",
            width=54,
            height=22,
            command=lambda: self._apply_theme("Light", "luna"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.preset_ios_btn = ctk.CTkButton(
            self.status_left,
            text="iOS",
            width=48,
            height=22,
            command=lambda: self._apply_theme("Light", "ios"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Presets de layout
        self.layout_compact_btn = ctk.CTkButton(
            self.status_right,
            text="50%",
            width=48,
            height=22,
            command=lambda: self._apply_layout_preset("half"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.layout_narrow_btn = ctk.CTkButton(
            self.status_right,
            text="35%",
            width=48,
            height=22,
            command=lambda: self._apply_layout_preset("normal"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.layout_wide_btn = ctk.CTkButton(
            self.status_right,
            text="40%",
            width=48,
            height=22,
            command=lambda: self._apply_layout_preset("wide"),
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Coluna ESQUERDA (50%) - Controles com rolagem
        self.left_column = ctk.CTkScrollableFrame(
            self.main_container,
            width=int(self.window_width * 0.35),
            label_text="CONTROLES E CONFIGURAÇÕES"
        )

        # Coluna DIREITA (50%) - Resultados
        self.right_column = ctk.CTkFrame(self.main_container, width=680)

        # ==================== PAINEL DE TABELAS (Coluna Esquerda - NOVO) ====================
        self.tables_browser_frame = ctk.CTkFrame(self.left_column)
        self.tables_browser_label = ctk.CTkLabel(
            self.tables_browser_frame,
            text="📚 TABELAS DO BANCO",
            font=ctk.CTkFont(size=14, weight="bold")
        )

        # Lista de tabelas (ScrollableFrame)
        self.tables_list_frame = ctk.CTkScrollableFrame(
            self.tables_browser_frame,
            height=200,
            width=620,
            label_text="Clique em uma tabela para carregar"
        )

        self.tables_buttons = []  # Lista para armazenar botões de tabelas

        # Mensagem inicial
        self.tables_info_label = ctk.CTkLabel(
            self.tables_browser_frame,
            text="ℹ️ Conecte ao banco para ver as tabelas",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )

        # ==================== AJUDA CIENTÍFICA (Coluna Esquerda) ====================
        self.science_help_frame = ctk.CTkFrame(self.left_column)
        self.science_help_label = ctk.CTkLabel(
            self.science_help_frame,
            text="🧠 AJUDA CIENTÍFICA (Objetivo da análise)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.science_help_text = ctk.CTkTextbox(self.science_help_frame, height=90, width=620)
        self.science_help_text.insert(
            "1.0",
            "Descreva: (1) objetivo, (2) variáveis, (3) grupos/diagnóstico, (4) o que deseja comparar/medir.\n"
            "Ex.: Quero comparar Temperatura/Umidade entre Diagnóstico (positivo/negativo) e ver correlação entre clima e prevalência."
        )
        self.science_help_btn = ctk.CTkButton(
            self.science_help_frame,
            text="✨ Sugerir Gráfico & Estatística",
            command=self._suggest_from_science_help,
            height=32,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # ==================== PAINEL DE CONEXÃO (Coluna Esquerda) ====================
        self.connection_frame = ctk.CTkFrame(self.left_column)
        self.connection_label = ctk.CTkLabel(
            self.connection_frame,
            text="🔌 CONEXÃO COM BANCO DE DADOS",
            font=ctk.CTkFont(size=14, weight="bold")
        )

        # Tipo de conexão
        self.connection_type_var = ctk.StringVar(value="MySQL Remoto")
        self.connection_type_frame = ctk.CTkFrame(self.connection_frame)

        self.radio_mysql = ctk.CTkRadioButton(
            self.connection_type_frame,
            text="MySQL Remoto",
            variable=self.connection_type_var,
            value="MySQL Remoto",
            command=self._on_connection_type_change
        )

        self.radio_local = ctk.CTkRadioButton(
            self.connection_type_frame,
            text="MySQL Local",
            variable=self.connection_type_var,
            value="MySQL Local",
            command=self._on_connection_type_change
        )

        self.radio_sqlite = ctk.CTkRadioButton(
            self.connection_type_frame,
            text="SQLite (Arquivo)",
            variable=self.connection_type_var,
            value="SQLite",
            command=self._on_connection_type_change
        )

        # Seleção de servidor padrão
        self.server_preset_label = ctk.CTkLabel(self.connection_frame, text="Servidor Padrão:", font=self.font_select_label)
        self.server_preset_combo = ctk.CTkComboBox(
            self.connection_frame,
            values=list(self.default_connections.keys()),
            command=self._load_preset_connection,
            font=self.font_select_value
        )

        # Campos de conexão MySQL
        self.mysql_frame = ctk.CTkFrame(self.connection_frame)

        self.host_label = ctk.CTkLabel(self.mysql_frame, text="Host:", font=self.font_select_label)
        self.host_entry = ctk.CTkEntry(self.mysql_frame, width=300, font=self.font_select_value)

        self.port_label = ctk.CTkLabel(self.mysql_frame, text="Porta:", font=self.font_select_label)
        self.port_entry = ctk.CTkEntry(self.mysql_frame, width=100, font=self.font_select_value)
        self.port_entry.insert(0, "3306")

        self.database_label = ctk.CTkLabel(self.mysql_frame, text="Banco:", font=self.font_select_label)
        self.database_entry = ctk.CTkEntry(self.mysql_frame, width=300, font=self.font_select_value)

        self.user_label = ctk.CTkLabel(self.mysql_frame, text="Usuário:", font=self.font_select_label)
        self.user_entry = ctk.CTkEntry(self.mysql_frame, width=300, font=self.font_select_value)

        self.password_label = ctk.CTkLabel(self.mysql_frame, text="Senha:", font=self.font_select_label)
        self.password_entry = ctk.CTkEntry(self.mysql_frame, width=300, show="*", font=self.font_select_value)

        # Campo para SQLite
        self.sqlite_frame = ctk.CTkFrame(self.connection_frame)
        self.sqlite_label = ctk.CTkLabel(self.sqlite_frame, text="Arquivo SQLite:", font=self.font_select_label)
        self.sqlite_entry = ctk.CTkEntry(self.sqlite_frame, width=400, font=self.font_select_value)
        self.sqlite_browse_btn = ctk.CTkButton(
            self.sqlite_frame,
            text="Procurar",
            width=100,
            command=self._browse_sqlite_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        self.sqlite_open_btn = ctk.CTkButton(
            self.sqlite_frame,
            text="Abrir/Importar",
            width=140,
            command=self._open_sqlite_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Botão conectar
        self.connect_btn = ctk.CTkButton(
            self.connection_frame,
            text="🔗 CONECTAR",
            command=self._connect_database,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )

        self.connection_status = ctk.CTkLabel(
            self.connection_frame,
            text="⚪ Desconectado",
            font=ctk.CTkFont(size=12)
        )

        # ==================== IMPORTAR CSV/EXCEL (Logo abaixo da conexão) ====================
        self.csv_import_frame = ctk.CTkFrame(self.left_column)
        self.csv_import_label = ctk.CTkLabel(
            self.csv_import_frame,
            text="📁 IMPORTAR CSV/EXCEL",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.csv_import_row = ctk.CTkFrame(self.csv_import_frame, fg_color="transparent")
        self.csv_import_entry = ctk.CTkEntry(self.csv_import_row, width=320, font=self.font_select_value)
        self.csv_import_browse_btn = ctk.CTkButton(
            self.csv_import_row,
            text="Procurar",
            width=90,
            command=self._browse_data_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.csv_import_load_btn = ctk.CTkButton(
            self.csv_import_row,
            text="Abrir/Importar",
            width=130,
            command=self._load_data_from_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # ==================== PAINEL DE DADOS (Coluna Esquerda) ====================
        self.data_frame = ctk.CTkFrame(self.left_column)
        self.data_label = ctk.CTkLabel(
            self.data_frame,
            text="📊 SELEÇÃO DE DADOS",
            font=ctk.CTkFont(size=14, weight="bold")
        )

        # Seleção de tabela
        self.table_label = ctk.CTkLabel(self.data_frame, text="Tabela:", font=self.font_select_label)
        self.table_combo = ctk.CTkComboBox(self.data_frame, width=360, state="disabled", font=self.font_select_value)
        self.refresh_tables_btn = ctk.CTkButton(
            self.data_frame,
            text="🔄",
            width=40,
            command=self._refresh_tables,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Query SQL customizada
        self.query_label = ctk.CTkLabel(self.data_frame, text="Query SQL (opcional):", font=self.font_select_label)
        self.query_text = ctk.CTkTextbox(self.data_frame, height=80, width=550, font=self.font_select_value)
        self.query_text.insert("1.0", "SELECT * FROM tabela LIMIT 1000")

        # Fonte de dados alternativa: CSV/Excel
        self.data_source_var = ctk.StringVar(value="SQL")
        self.data_source_label = ctk.CTkLabel(self.data_frame, text="Fonte de Dados:", font=self.font_select_label)
        self.data_source_combo = ctk.CTkComboBox(
            self.data_frame,
            width=160,
            values=["SQL", "Arquivo (CSV/Excel)"],
            command=lambda _: self._on_data_source_change(),
            font=self.font_select_value
        )
        self.data_source_combo.set("SQL")

        # Área antiga de importação dentro de "Seleção de Dados" (mantida por compatibilidade, mas não exibida)
        self.file_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        self.file_label = ctk.CTkLabel(self.file_frame, text="Importar CSV/Excel:", font=self.font_select_label)
        self.file_entry = ctk.CTkEntry(self.file_frame, width=360, font=self.font_select_value)
        self.file_browse_btn = ctk.CTkButton(
            self.file_frame,
            text="Procurar",
            width=90,
            command=self._browse_data_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )
        self.file_load_btn = ctk.CTkButton(
            self.file_frame,
            text="Abrir/Importar",
            width=130,
            command=self._load_data_from_file,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Botão carregar dados
        self.load_data_btn = ctk.CTkButton(
            self.data_frame,
            text=" CARREGAR DADOS",
            command=self._load_data,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )

        # Preview dos dados
        self.preview_label = ctk.CTkLabel(self.data_frame, text="Preview dos Dados:")
        self.preview_text = scrolledtext.ScrolledText(
            self.data_frame,
            height=8,
            width=65,
            bg="#2b2b2b",
            fg="white",
            font=("Consolas", 8)
        )

        # ==================== PREVIEW (Coluna Direita - Topo) ====================
        self.preview_right_frame = ctk.CTkFrame(self.right_column)
        self.preview_right_label = ctk.CTkLabel(
            self.preview_right_frame,
            text=" PREVIEW DOS DADOS",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        # Preview em formato de planilha (Treeview + scrollbars)
        self.preview_table_frame = ctk.CTkFrame(self.preview_right_frame)
        self.preview_table = ttk.Treeview(self.preview_table_frame, show="headings")
        self.preview_table_vsb = ttk.Scrollbar(self.preview_table_frame, orient="vertical", command=self.preview_table.yview)
        self.preview_table_hsb = ttk.Scrollbar(self.preview_table_frame, orient="horizontal", command=self.preview_table.xview)
        self.preview_table.configure(yscrollcommand=self.preview_table_vsb.set, xscrollcommand=self.preview_table_hsb.set)

        # ==================== PAINEL DE ANÁLISE (Coluna Esquerda) ====================
        self.analysis_frame = ctk.CTkFrame(self.left_column)
        self.analysis_label = ctk.CTkLabel(
            self.analysis_frame,
            text="🧬 CONFIGURAR ANÁLISE ESTATÍSTICA",
            font=ctk.CTkFont(size=14, weight="bold")
        )

        # ===== PASSO 1: Seleção de Variáveis =====
        self.step1_label = ctk.CTkLabel(
            self.analysis_frame,
            text="📌 PASSO 1: Escolha as Variáveis",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("black", "white")
        )

        self.vars_count_label = ctk.CTkLabel(
            self.analysis_frame,
            text="❓ Quantas variáveis você quer analisar? (2 a 5)",
            font=self.font_select_label
        )
        self.vars_count_combo = ctk.CTkComboBox(
            self.analysis_frame,
            width=120,
            values=["2", "3", "4", "5"],
            command=lambda _: self._on_vars_count_change(),
            font=self.font_select_value
        )
        self.vars_count_combo.set("")

        self.vars_select_frame = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        self.vars_select_rows = []
        self.vars_select_combos = []
        for i in range(5):
            row = ctk.CTkFrame(self.vars_select_frame, fg_color="transparent")
            lbl = ctk.CTkLabel(row, text=f"Variável {i+1}:", width=120, anchor="w", font=self.font_select_label)
            cb = ctk.CTkComboBox(
                row,
                width=420,
                state="disabled",
                command=lambda _: self._update_test_preview(),
                font=self.font_select_value
            )
            lbl.pack(side="left", padx=(0, 6))
            cb.pack(side="left", fill="x", expand=True)
            self.vars_select_rows.append(row)
            self.vars_select_combos.append(cb)

        self.numeric_var_label = ctk.CTkLabel(
            self.analysis_frame,
            text="❓ Qual variável você quer analisar? (numérica)",
            font=self.font_select_label
        )
        self.numeric_var_combo = ctk.CTkComboBox(
            self.analysis_frame,
            width=500,
            state="disabled",
            font=self.font_select_value
        )

        self.group_var_label = ctk.CTkLabel(
            self.analysis_frame,
            text="❓ Quer comparar entre grupos? (opcional)",
            font=self.font_select_label
        )
        self.group_var_combo = ctk.CTkComboBox(
            self.analysis_frame,
            width=500,
            state="disabled",
            command=lambda _: self._update_test_preview(),
            font=self.font_select_value
        )
        self.group_var_combo.set("Nenhum")

        # ===== PASSO 2: Tipo de Análise (AUTO-PREVIEW) =====
        self.step2_label = ctk.CTkLabel(
            self.analysis_frame,
            text="📌 PASSO 2: Recomendação de Teste",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("black", "white")
        )

        self.test_preview_frame = ctk.CTkFrame(self.analysis_frame, fg_color="#2b2b2b")
        self.test_preview_label = ctk.CTkLabel(
            self.test_preview_frame,
            text="ℹ️ Selecione as variáveis acima para ver sugestão de teste",
            font=ctk.CTkFont(size=9),
            text_color="gray",
            wraplength=480
        )

        self.preview_test_btn = ctk.CTkButton(
            self.analysis_frame,
            text="🔄 Atualizar Recomendação",
            command=self._update_test_preview,
            height=30,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover
        )

        # Vincular atualização ao mudar combo numérico também
        self.numeric_var_combo.configure(command=lambda _: self._update_test_preview())

        # ===== PASSO 3: Configuração de Gráfico =====
        self.step3_label = ctk.CTkLabel(
            self.analysis_frame,
            text="📌 PASSO 3: Escolha o Tipo de Gráfico",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("black", "white")
        )

        self.plot_type_label = ctk.CTkLabel(
            self.analysis_frame,
            text="❓ Como você quer visualizar os dados?",
            font=self.font_select_label
        )

        # Lista de tipos de gráfico com descrições
        self.plot_options = {
            "Automático (Recomendado)": "Sistema escolhe o melhor gráfico",
            "Boxplot": "Mostra distribuição e outliers",
            "Prevalência por Faixa": "Mostra proporção por faixas (bins) de uma variável",
            "Scatter com Regressão": "Mostra relação entre duas variáveis + ajuste linear",
            "Diagrama de Venn": "Interseções entre conjuntos/categorias",
            "Matriz de Correlação (Spearman)": "Correlação não-paramétrica entre variáveis numéricas",
            "Matriz Categórica (V de Cramér)": "Associação entre variáveis categóricas",
            "Violino": "Mostra densidade da distribuição",
            "Barras com Erro": "Mostra médias com erro padrão",
            "Histograma": "Mostra frequência dos valores",
            "Dispersão": "Mostra relação entre duas variáveis",
            "Linha de Tendência": "Mostra padrão temporal"
        }

        # Resumos científicos (usados no botão '?')
        self.plot_science_info = {
            "Boxplot": (
                "Boxplot (ex.: Temperatura / Precipitação / Umidade)\n"
                "├─ Adequado: Compara distribuições entre grupos\n"
                "├─ Construção: IQR, mediana, whiskers, outliers\n"
                "├─ Dados: coletas, dados_climaticos, diagnosticos (dependendo do dataset)\n"
                "├─ Testes: Shapiro-Wilk (normalidade), Mann-Whitney U (2 grupos), Kruskal-Wallis (3+ grupos)\n"
                "└─ Interpretação: Medianas/IQR diferentes sugerem influência do fator/grupo"
            ),
            "Prevalência por Faixa": (
                "Prevalência por Faixa\n"
                "├─ Adequado: Medir proporção de um desfecho (ex.: positivo/negativo) por faixas (bins)\n"
                "├─ Construção: bins (quantis ou intervalos fixos) + proporção por bin\n"
                "├─ Dados: variável contínua (clima) + variável categórica (diagnóstico/grupo)\n"
                "├─ Testes: Qui-quadrado (tabela bin x desfecho), tendência (quando aplicável)\n"
                "└─ Interpretação: aumento/redução da prevalência por faixa sugere associação"
            ),
            "Scatter com Regressão": (
                "Scatter com Regressão\n"
                "├─ Adequado: Relação entre duas variáveis numéricas\n"
                "├─ Construção: dispersão + linha de regressão (OLS)\n"
                "├─ Dados: 2 colunas numéricas (ex.: temperatura vs umidade)\n"
                "├─ Testes: Spearman/Pearson (correlação), regressão linear (coeficientes/p-valor)\n"
                "└─ Interpretação: inclinação ≠ 0 sugere associação; cuidado com outliers"
            ),
            "Diagrama de Venn": (
                "Diagrama de Venn\n"
                "├─ Adequado: Interseção entre 2 ou 3 conjuntos (categorias/condições)\n"
                "├─ Construção: conjuntos definidos por regra (ex.: colunas booleanas/flag)\n"
                "├─ Dados: 2-3 colunas indicando presença/ausência\n"
                "├─ Testes: Qui-quadrado/Fisher (dependendo do desenho)\n"
                "└─ Interpretação: sobreposição indica coocorrência"
            ),
            "Matriz de Correlação (Spearman)": (
                "Matriz de Correlação (Spearman)\n"
                "├─ Adequado: Associações monotônicas; robusto a não-normalidade\n"
                "├─ Construção: matriz ρ (rho) + heatmap\n"
                "├─ Dados: múltiplas variáveis numéricas\n"
                "├─ Testes: Spearman (ρ, p-valor); ajuste por múltiplas comparações (opcional)\n"
                "└─ Interpretação: |ρ| maior => associação mais forte (não implica causalidade)"
            ),
            "Matriz Categórica (V de Cramér)": (
                "Matriz Categórica (V de Cramér)\n"
                "├─ Adequado: Associação entre variáveis categóricas\n"
                "├─ Construção: V baseado em Qui-quadrado e tamanho da tabela\n"
                "├─ Dados: múltiplas colunas categóricas\n"
                "├─ Testes: Qui-quadrado; V de Cramér como medida de efeito\n"
                "└─ Interpretação: V≈0 fraco; V maior indica associação (escala depende do problema)"
            ),
        }

        self.plot_type_combo = ctk.CTkComboBox(
            self.analysis_frame,
            values=list(self.plot_options.keys()),
            width=500,
            command=self._on_plot_type_change,
            font=self.font_select_value
        )
        self.plot_type_combo.set("Automático (Recomendado)")

        self.plot_info_btn = ctk.CTkButton(
            self.analysis_frame,
            text="?",
            width=30,
            height=28,
            command=self._show_plot_science_info,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            border_width=2,
            border_color=self.btn_border,
            corner_radius=8
        )

        # Descrição do gráfico escolhido
        self.plot_description_label = ctk.CTkLabel(
            self.analysis_frame,
            text=" " + self.plot_options["Automático (Recomendado)"],
            font=ctk.CTkFont(size=9),
            text_color="#95E1D3"
        )

        # ===== PREVIEW DE CONFIGURAÇÃO =====
        self.config_summary_frame = ctk.CTkFrame(self.analysis_frame, fg_color="#1a1a1a")
        self.config_summary_label = ctk.CTkLabel(
            self.config_summary_frame,
            text=" RESUMO DA CONFIGURAÇÃO:",
            font=ctk.CTkFont(size=10, weight="bold")
        )
        self.config_summary_text = ctk.CTkLabel(
            self.config_summary_frame,
            text="Configure as opções acima",
            font=ctk.CTkFont(size=9),
            text_color="gray",
            wraplength=480,
            justify="left"
        )

        # Botões de ação (2 linhas para não estourar largura)
        self.actions_row1 = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        self.actions_row2 = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")

        self.inspect_btn = ctk.CTkButton(
            self.actions_row1,
            text=" INSPECIONAR DADOS",
            command=self._inspect_data,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            width=200,
            height=35
        )

        self.recommend_btn = ctk.CTkButton(
            self.actions_row1,
            text=" RECOMENDAR TESTE",
            command=self._recommend_test,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            width=200,
            height=35
        )

        self.execute_btn = ctk.CTkButton(
            self.actions_row1,
            text=" EXECUTAR ANÁLISE COMPLETA",
            command=self._execute_full_analysis,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            width=240,
            height=35
        )

        self.visualize_btn = ctk.CTkButton(
            self.actions_row2,
            text=" GERAR VISUALIZAÇÕES",
            command=self._generate_visualizations,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            width=240,
            height=35
        )

        self.report_btn = ctk.CTkButton(
            self.actions_row2,
            text=" RELATÓRIO COMPLETO",
            command=self._generate_report,
            fg_color=self.btn_fg,
            hover_color=self.btn_hover,
            width=240,
            height=35
        )

        # ==================== PAINEL DE RESULTADOS (Coluna Direita) ====================
        self.results_frame = ctk.CTkFrame(self.right_column)
        self.results_label = ctk.CTkLabel(
            self.results_frame,
            text=" RESULTADOS",
            font=ctk.CTkFont(size=16, weight="bold")
        )

        # Abas para diferentes tipos de resultado
        self.results_notebook = ttk.Notebook(self.results_frame)

        # Aba de texto
        self.text_results_frame = ttk.Frame(self.results_notebook)
        self.results_text = scrolledtext.ScrolledText(
            self.text_results_frame,
            height=35,
            width=75,
            bg="#2b2b2b",
            fg="white",
            font=("Consolas", 9)
        )
        self.results_text.pack(fill='both', expand=True, padx=5, pady=5)

        # Aba de gráficos com rolagem
        self.plot_results_frame = ttk.Frame(self.results_notebook)

        # Canvas com scrollbar para gráficos
        self.plot_canvas = tk.Canvas(self.plot_results_frame, bg="#2b2b2b")
        self.plot_scrollbar = ttk.Scrollbar(self.plot_results_frame, orient="vertical", command=self.plot_canvas.yview)
        self.plot_canvas_frame = tk.Frame(self.plot_canvas, bg="#2b2b2b")

        self.plot_canvas_frame.bind(
            "<Configure>",
            lambda e: self.plot_canvas.configure(scrollregion=self.plot_canvas.bbox("all"))
        )

        self.plot_canvas.create_window((0, 0), window=self.plot_canvas_frame, anchor="nw")
        self.plot_canvas.configure(yscrollcommand=self.plot_scrollbar.set)

        self.plot_canvas.pack(side="left", fill="both", expand=True)
        self.plot_scrollbar.pack(side="right", fill="y")

        self.results_notebook.add(self.text_results_frame, text="Resultados Textuais")
        self.results_notebook.add(self.plot_results_frame, text="Visualizações")

    def _layout_widgets(self):
        """Organiza os widgets na interface - Layout 2 colunas (50% cada)"""

        # Barra de status sempre no rodapé
        self.status_bar.pack(side='bottom', fill='x', padx=6, pady=(0, 2))
        self.status_left.pack(side='left', padx=4)
        self.status_right.pack(side='right', padx=4)

        self.theme_dark_btn.pack(side='left', padx=(0, 4))
        self.theme_light_btn.pack(side='left', padx=4)
        self.theme_system_btn.pack(side='left', padx=4)

        self.preset_win11_btn.pack(side='left', padx=(10, 4))
        self.preset_luna_btn.pack(side='left', padx=4)
        self.preset_ios_btn.pack(side='left', padx=4)

        self.layout_wide_btn.pack(side='right', padx=(4, 0))
        self.layout_compact_btn.pack(side='right', padx=4)
        self.layout_narrow_btn.pack(side='right', padx=4)

        self.main_container.pack(fill='both', expand=True, padx=5, pady=5)

        # ==================== LAYOUT 2 COLUNAS ====================
        # Coluna ESQUERDA (~50%)
        try:
            self.left_column.configure(width=int(self.window_width * self.left_width_ratio))
        except Exception:
            pass
        # CTkScrollableFrame pode "sumir" conteúdo quando pack_propagate(False) + fill='y'.
        # Mantemos largura fixa via configure(width=...) e deixamos o pack medir corretamente.
        self.left_column.pack(side='left', fill='both', expand=True, padx=(0, 2))

        # Coluna DIREITA (~50%)
        self.right_column.pack(side='right', fill='both', expand=True, padx=(2, 0))

        # ==================== COLUNA ESQUERDA - CONTROLES ====================

        # PAINEL DE CONEXÃO (agora no topo)
        self.connection_frame.pack(fill='x', padx=5, pady=5)
        self.connection_label.pack(pady=5)

        self.connection_type_frame.pack(pady=5)
        self.radio_mysql.pack(side='left', padx=5)
        self.radio_local.pack(side='left', padx=5)
        self.radio_sqlite.pack(side='left', padx=5)

        self.server_preset_label.pack(pady=2)
        self.server_preset_combo.pack(pady=5)

        # MySQL frame
        self.mysql_frame.pack(pady=5)
        row = 0
        self.host_label.grid(row=row, column=0, padx=5, pady=2, sticky='w')
        self.host_entry.grid(row=row, column=1, padx=5, pady=2)
        self.port_label.grid(row=row, column=2, padx=5, pady=2, sticky='w')
        self.port_entry.grid(row=row, column=3, padx=5, pady=2)

        row += 1
        self.database_label.grid(row=row, column=0, padx=5, pady=2, sticky='w')
        self.database_entry.grid(row=row, column=1, padx=5, pady=2)

        row += 1
        self.user_label.grid(row=row, column=0, padx=5, pady=2, sticky='w')
        self.user_entry.grid(row=row, column=1, padx=5, pady=2)

        row += 1
        self.password_label.grid(row=row, column=0, padx=5, pady=2, sticky='w')
        self.password_entry.grid(row=row, column=1, padx=5, pady=2)

        self.connect_btn.pack(pady=10)
        self.connection_status.pack(pady=2)

        # IMPORTAR CSV/EXCEL (logo abaixo da conexão)
        self.csv_import_frame.pack(fill='x', padx=5, pady=5)
        self.csv_import_label.pack(pady=5)
        self.csv_import_row.pack(fill='x', padx=10, pady=(0, 8))
        self.csv_import_entry.pack(in_=self.csv_import_row, side='left', padx=5, fill='x', expand=True)
        self.csv_import_browse_btn.pack(in_=self.csv_import_row, side='left', padx=5)
        self.csv_import_load_btn.pack(in_=self.csv_import_row, side='left', padx=5)

        # AJUDA CIENTÍFICA (logo abaixo da conexão)
        self.science_help_frame.pack(fill='x', padx=5, pady=5)
        self.science_help_label.pack(pady=(8, 4))
        self.science_help_text.pack(fill='x', padx=10, pady=(0, 6))
        self.science_help_btn.pack(pady=(0, 10))

        # PAINEL DE TABELAS (agora abaixo)
        self.tables_browser_frame.pack(fill='x', padx=5, pady=5)
        self.tables_browser_label.pack(pady=5)
        self.tables_list_frame.pack(fill='x', padx=10, pady=5)
        self.tables_info_label.pack(pady=2)

        # PAINEL DE DADOS
        self.data_frame.pack(fill='both', padx=5, pady=10)
        self.data_label.pack(pady=5)

        table_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        table_frame.pack(pady=5)
        self.table_label.pack(in_=table_frame, side='left', padx=5)
        self.table_combo.pack(in_=table_frame, side='left', padx=5)
        self.refresh_tables_btn.pack(in_=table_frame, side='left', padx=5)

        source_frame = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        source_frame.pack(pady=5)
        self.data_source_label.pack(in_=source_frame, side='left', padx=5)
        self.data_source_combo.pack(in_=source_frame, side='left', padx=5)

        # Aplica visibilidade inicial dos controles de fonte de dados
        self._on_data_source_change()

        self.query_label.pack(pady=2)
        self.query_text.pack(pady=5, padx=10)

        self.load_data_btn.pack(pady=10)

        # Preview agora fica na coluna direita (topo)
        # (mantemos os widgets antigos criados na coluna esquerda por compatibilidade,
        # mas não exibimos aqui no layout)

        # PAINEL DE ANÁLISE (NOVO LAYOUT INTERATIVO)
        self.analysis_frame.pack(fill='both', padx=5, pady=10)
        self.analysis_label.pack(pady=5)

        # PASSO 1: Variáveis
        self.step1_label.pack(pady=(10, 5))

        self.vars_count_label.pack(pady=2, padx=10, anchor='w')
        self.vars_count_combo.pack(pady=2, padx=10, anchor='w')
        self.vars_select_frame.pack(fill='x', padx=10, pady=(2, 6))

        self.numeric_var_label.pack(pady=2, padx=10, anchor='w')
        self.numeric_var_combo.pack(pady=2, padx=10)
        self.group_var_label.pack(pady=2, padx=10, anchor='w')
        self.group_var_combo.pack(pady=2, padx=10)

        # PASSO 2: Recomendação de Teste
        self.step2_label.pack(pady=(15, 5))
        self.test_preview_frame.pack(fill='x', padx=10, pady=5)
        self.test_preview_label.pack(pady=10, padx=10)
        self.preview_test_btn.pack(pady=5)

        # PASSO 3: Tipo de Gráfico
        self.step3_label.pack(pady=(15, 5))
        self.plot_type_label.pack(pady=2, padx=10, anchor='w')

        plot_select_row = ctk.CTkFrame(self.analysis_frame, fg_color="transparent")
        plot_select_row.pack(pady=2, padx=10, fill='x')
        self.plot_type_combo.pack(in_=plot_select_row, side='left', fill='x', expand=True)
        self.plot_info_btn.pack(in_=plot_select_row, side='left', padx=(8, 0))
        self.plot_description_label.pack(pady=2, padx=10)

        # BOTÕES DE AÇÃO (logo após o Passo 3)
        self.actions_row1.pack(pady=(10, 5), padx=10, fill='x')
        # Centralizar com grid: colunas 0 e 4 são espaçadores (weight=1)
        self.actions_row1.grid_columnconfigure(0, weight=1)
        self.actions_row1.grid_columnconfigure(1, weight=0)
        self.actions_row1.grid_columnconfigure(2, weight=0)
        self.actions_row1.grid_columnconfigure(3, weight=0)
        self.actions_row1.grid_columnconfigure(4, weight=1)
        self.inspect_btn.grid(row=0, column=1, padx=4, pady=2)
        self.recommend_btn.grid(row=0, column=2, padx=4, pady=2)
        self.execute_btn.grid(row=0, column=3, padx=4, pady=2)

        self.actions_row2.pack(pady=(0, 10), padx=10, fill='x')
        # Centralizar com grid: colunas 0 e 3 são espaçadores (weight=1)
        self.actions_row2.grid_columnconfigure(0, weight=1)
        self.actions_row2.grid_columnconfigure(1, weight=0)
        self.actions_row2.grid_columnconfigure(2, weight=0)
        self.actions_row2.grid_columnconfigure(3, weight=1)
        self.visualize_btn.grid(row=0, column=1, padx=4, pady=2)
        self.report_btn.grid(row=0, column=2, padx=4, pady=2)

        # RESUMO DA CONFIGURAÇÃO
        self.config_summary_frame.pack(fill='x', padx=10, pady=10)
        self.config_summary_label.pack(pady=5)
        self.config_summary_text.pack(pady=5, padx=10)

        # ==================== COLUNA DIREITA - PREVIEW (Topo) + RESULTADOS (Base) ====================
        self.right_column.grid_rowconfigure(0, weight=1)
        self.right_column.grid_rowconfigure(1, weight=1)
        self.right_column.grid_columnconfigure(0, weight=1)

        self.preview_right_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=(5, 2))
        self.preview_right_label.pack(pady=5)
        self.preview_table_frame.pack(fill='both', expand=True, padx=5, pady=(0, 5))
        self.preview_table.grid(row=0, column=0, sticky="nsew")
        self.preview_table_vsb.grid(row=0, column=1, sticky="ns")
        self.preview_table_hsb.grid(row=1, column=0, sticky="ew")
        self.preview_table_frame.grid_rowconfigure(0, weight=1)
        self.preview_table_frame.grid_columnconfigure(0, weight=1)

        self.results_frame.grid(row=1, column=0, sticky='nsew', padx=5, pady=(2, 5))
        self.results_label.pack(pady=5)
        self.results_notebook.pack(fill='both', expand=True, padx=5, pady=5)

    def _on_plot_type_change(self, choice=None):
        """Atualiza interface quando tipo de gráfico muda."""
        try:
            selected = choice or self.plot_type_combo.get()
        except Exception:
            selected = choice

        try:
            desc = self.plot_options.get(selected, "")
            if desc:
                self.plot_description_label.configure(text=" " + desc)
            else:
                self.plot_description_label.configure(text="")
        except Exception:
            pass

        self._update_config_summary()

    def _show_plot_science_info(self):
        """Exibe resumo científico do gráfico selecionado."""
        try:
            selected = self.plot_type_combo.get()
        except Exception:
            selected = ""

        info = self.plot_science_info.get(selected)
        if not info:
            # fallback para opções antigas
            desc = self.plot_options.get(selected, "")
            info = f"{selected}\n\n{desc}\n\n(Sem resumo científico cadastrado para esta opção.)"

        if self.rscript_path:
            info += "\n\nR: Rscript detectado (integração disponível)."
        else:
            info += "\n\nR: Rscript não detectado (usando estatística em Python)."

        messagebox.showinfo("Resumo Científico", info)

    def _safe_save_figure(self, fig, stem: str, fmt: str = "png") -> Optional[Path]:
        try:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            clean = "".join([c if c.isalnum() or c in "-_" else "_" for c in stem])
            out = self.graficos_dir / f"{clean}_{ts}.{fmt}"
            fig.savefig(out, dpi=200, bbox_inches="tight", format=fmt)
            return out
        except Exception:
            return None

    def _export_figure(self, fig, stem: str, fmt: str):
        p = self._safe_save_figure(fig, stem=stem, fmt=fmt)
        if p:
            messagebox.showinfo("Exportar", f"Gráfico exportado com sucesso:\n{p}")
        else:
            messagebox.showerror("Exportar", "Falha ao exportar o gráfico")

    def _run_r(self, script_text: str) -> Optional[str]:
        if not self.rscript_path:
            return None
        try:
            with tempfile.TemporaryDirectory() as td:
                p = Path(td)
                script_path = p / "analysis.R"
                script_path.write_text(script_text, encoding="utf-8")
                proc = subprocess.run(
                    [self.rscript_path, str(script_path)],
                    capture_output=True,
                    text=True,
                    check=False
                )
                out = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
                return out.strip()
        except Exception:
            return None

    def _stats_for_current_plot(self, plot_type: str, vars_sel, group_col=None) -> str:
        """Gera texto de stats (Python) relacionado ao tipo de plot."""
        lines = []
        try:
            if self.current_data is None:
                return "Sem dados carregados."

            df = self.current_data

            if plot_type == "Matriz de Correlação (Spearman)":
                numeric_vars = [v for v in vars_sel if v in df.columns and pd.api.types.is_numeric_dtype(df[v])]
                if len(numeric_vars) < 2:
                    return "Selecione pelo menos 2 variáveis numéricas para Spearman."
                corr = df[numeric_vars].corr(method="spearman")
                lines.append(" Spearman (ρ) - Matriz")
                lines.append(corr.round(4).to_string())
            elif plot_type == "Matriz Categórica (V de Cramér)":
                from scipy.stats import chi2_contingency

                cat_vars = [v for v in vars_sel if v in df.columns and not pd.api.types.is_numeric_dtype(df[v])]
                if len(cat_vars) < 2:
                    return "Selecione pelo menos 2 variáveis categóricas para V de Cramér."

                def cramers_v(x, y):
                    conf = pd.crosstab(x, y)
                    if conf.shape[0] < 2 or conf.shape[1] < 2:
                        return 0.0
                    chi2 = chi2_contingency(conf)[0]
                    n = conf.to_numpy().sum()
                    r, k = conf.shape
                    return float((chi2 / (n * (min(k - 1, r - 1)))) ** 0.5) if n > 0 and min(k - 1, r - 1) > 0 else 0.0

                lines.append(" V de Cramér - Associações")
                for i in range(len(cat_vars)):
                    for j in range(i + 1, len(cat_vars)):
                        v = cramers_v(df[cat_vars[i]], df[cat_vars[j]])
                        lines.append(f"- {cat_vars[i]} vs {cat_vars[j]}: V={v:.4f}")
            elif plot_type in ("Boxplot", "Prevalência por Faixa"):
                from scipy.stats import shapiro, mannwhitneyu, kruskal

                numeric_vars = [v for v in vars_sel if v in df.columns and pd.api.types.is_numeric_dtype(df[v])]
                if not numeric_vars:
                    return "Selecione ao menos 1 variável numérica."

                if group_col and group_col in df.columns:
                    groups = df[group_col].dropna().unique().tolist()
                    if len(groups) >= 2:
                        g0, g1 = groups[0], groups[1]
                        for nv in numeric_vars[:3]:
                            s0 = df.loc[df[group_col] == g0, nv].dropna()
                            s1 = df.loc[df[group_col] == g1, nv].dropna()
                            if len(s0) >= 3 and len(s1) >= 3:
                                try:
                                    p0 = shapiro(s0)[1]
                                    p1 = shapiro(s1)[1]
                                    lines.append(f" Shapiro-Wilk ({nv}) - {g0}: p={p0:.4f}; {g1}: p={p1:.4f}")
                                except Exception:
                                    pass
                                try:
                                    p_mw = mannwhitneyu(s0, s1, alternative="two-sided")[1]
                                    lines.append(f" Mann-Whitney U ({nv}) - p={p_mw:.4f}")
                                except Exception:
                                    pass
                    elif len(groups) > 2:
                        for nv in numeric_vars[:3]:
                            samples = [df.loc[df[group_col] == g, nv].dropna() for g in groups]
                            try:
                                p_kw = kruskal(*samples)[1]
                                lines.append(f" Kruskal-Wallis ({nv}) - p={p_kw:.4f}")
                            except Exception:
                                pass
                else:
                    nv = numeric_vars[0]
                    s = df[nv].dropna()
                    if len(s) >= 3:
                        try:
                            p = shapiro(s)[1]
                            lines.append(f" Shapiro-Wilk ({nv}) - p={p:.4f}")
                        except Exception:
                            pass
            elif plot_type == "Scatter com Regressão":
                from scipy.stats import spearmanr

                numeric_vars = [v for v in vars_sel if v in df.columns and pd.api.types.is_numeric_dtype(df[v])]
                if len(numeric_vars) < 2:
                    return "Selecione 2 variáveis numéricas para scatter+regressão."
                x, y = numeric_vars[0], numeric_vars[1]
                dd = df[[x, y]].dropna()
                if len(dd) < 3:
                    return "Dados insuficientes para correlação/regressão."
                rho, p = spearmanr(dd[x], dd[y])
                lines.append(f" Spearman ({x} vs {y}) - ρ={rho:.4f}, p={p:.4f}")

            if not lines:
                return "Sem estatísticas específicas configuradas para esta visualização."
            return "\n".join(lines)
        except Exception as e:
            return f"Erro ao calcular estatísticas: {e}"

    def _create_figures_for_plot_type(self, plot_type: str, vars_sel, group_col=None):
        """Cria figuras matplotlib para o tipo de plot selecionado."""
        if self.current_data is None:
            return []

        df = self.current_data
        figures = []

        def _new_fig(title: str, figsize=(10, 5)):
            fig = plt.Figure(figsize=figsize)
            ax = fig.add_subplot(111)
            ax.set_title(title)
            return fig, ax

        # Normaliza group
        if group_col == "Nenhum":
            group_col = None
        if group_col and group_col not in df.columns:
            group_col = None

        numeric_vars = [v for v in vars_sel if v in df.columns and pd.api.types.is_numeric_dtype(df[v])]
        cat_vars = [v for v in vars_sel if v in df.columns and not pd.api.types.is_numeric_dtype(df[v])]

        if plot_type in ("Automático (Recomendado)", ""):
            # Fallback: usa create_visualizations tradicional
            numeric_col = self.numeric_var_combo.get() if hasattr(self, "numeric_var_combo") else (numeric_vars[0] if numeric_vars else None)
            if not numeric_col:
                return []
            figures = self.analyzer.create_visualizations(numeric_col, group_col)
            return [(figures[i], f"Auto_{i+1}") for i in range(len(figures))]

        if plot_type == "Boxplot":
            if not numeric_vars:
                return []

            if group_col:
                m = df[[group_col] + numeric_vars].copy()
                m = m.melt(id_vars=[group_col], var_name="Variável", value_name="Valor")
                fig, ax = _new_fig("Boxplot por Grupo")
                sns.boxplot(data=m, x=group_col, y="Valor", hue="Variável", ax=ax)
                ax.tick_params(axis='x', rotation=45)
                figures.append((fig, "Boxplot"))
            else:
                fig, ax = _new_fig("Boxplot")
                sns.boxplot(data=df[numeric_vars], ax=ax)
                ax.tick_params(axis='x', rotation=45)
                figures.append((fig, "Boxplot"))

        elif plot_type == "Prevalência por Faixa":
            # Usa manualmente: vars_sel[0]=contínua para bins; vars_sel[1]=categórica (desfecho)
            if len(vars_sel) < 2:
                return []
            x = vars_sel[0]
            outcome = vars_sel[1]
            if x not in df.columns or outcome not in df.columns:
                return []

            d = df[[x, outcome]].dropna().copy()
            # bins por quantis (5 faixas)
            try:
                d["Faixa"] = pd.qcut(d[x], q=5, duplicates="drop")
            except Exception:
                d["Faixa"] = pd.cut(d[x], bins=5)

            tab = pd.crosstab(d["Faixa"], d[outcome], normalize='index')
            fig, ax = _new_fig(f"Prevalência por Faixa ({x} vs {outcome})", figsize=(11, 5))
            tab.plot(kind='bar', stacked=True, ax=ax)
            ax.set_ylabel("Proporção")
            ax.tick_params(axis='x', rotation=45)
            figures.append((fig, "Prevalencia_por_Faixa"))

        elif plot_type == "Scatter com Regressão":
            if len(numeric_vars) < 2:
                return []
            x, y = numeric_vars[0], numeric_vars[1]
            d = df[[x, y] + ([group_col] if group_col else [])].dropna().copy()
            fig, ax = _new_fig(f"Scatter com Regressão ({x} vs {y})", figsize=(9, 6))
            if group_col:
                sns.scatterplot(data=d, x=x, y=y, hue=group_col, ax=ax)
            else:
                sns.scatterplot(data=d, x=x, y=y, ax=ax)
            sns.regplot(data=d, x=x, y=y, scatter=False, ax=ax, color="red")
            figures.append((fig, "Scatter_Regressao"))

        elif plot_type == "Diagrama de Venn":
            # Usa lib 'venn' se disponível. Necessita 2 ou 3 variáveis categóricas/flags.
            try:
                from venn import venn
            except Exception:
                return []

            cols = vars_sel[:3]
            cols = [c for c in cols if c in df.columns]
            if len(cols) < 2:
                return []

            # Interpretação: define conjunto como valores não-nulos/verdadeiros
            sets = {}
            for c in cols:
                s = set(df.index[df[c].notna()])
                if pd.api.types.is_bool_dtype(df[c]):
                    s = set(df.index[df[c] == True])
                sets[c] = s

            fig = plt.Figure(figsize=(7, 6))
            ax = fig.add_subplot(111)
            ax.set_title("Diagrama de Venn")
            venn(sets, ax=ax)
            figures.append((fig, "Venn"))

        elif plot_type == "Matriz de Correlação (Spearman)":
            if len(numeric_vars) < 2:
                return []
            corr = df[numeric_vars].corr(method="spearman")
            fig, ax = _new_fig("Matriz de Correlação (Spearman)", figsize=(10, 8))
            sns.heatmap(corr, annot=False, cmap="coolwarm", center=0, ax=ax)
            figures.append((fig, "Matriz_Spearman"))

        elif plot_type == "Matriz Categórica (V de Cramér)":
            from scipy.stats import chi2_contingency

            if len(cat_vars) < 2:
                return []

            def cramers_v(x, y):
                conf = pd.crosstab(x, y)
                if conf.shape[0] < 2 or conf.shape[1] < 2:
                    return 0.0
                chi2 = chi2_contingency(conf)[0]
                n = conf.to_numpy().sum()
                r, k = conf.shape
                return float((chi2 / (n * (min(k - 1, r - 1)))) ** 0.5) if n > 0 and min(k - 1, r - 1) > 0 else 0.0

            mat = pd.DataFrame(index=cat_vars, columns=cat_vars, dtype=float)
            for i in cat_vars:
                for j in cat_vars:
                    mat.loc[i, j] = 1.0 if i == j else cramers_v(df[i], df[j])

            fig, ax = _new_fig("Matriz Categórica (V de Cramér)", figsize=(10, 8))
            sns.heatmap(mat, annot=False, cmap="viridis", vmin=0, vmax=1, ax=ax)
            figures.append((fig, "Matriz_CramersV"))

        else:
            # fallback: mantém visualizações existentes
            numeric_col = self.numeric_var_combo.get() if hasattr(self, "numeric_var_combo") else (numeric_vars[0] if numeric_vars else None)
            if numeric_col:
                figs = self.analyzer.create_visualizations(numeric_col, group_col)
                return [(figs[i], f"Auto_{i+1}") for i in range(len(figs))]

        return figures

    def _add_plot_card(self, fig, title: str, plot_type: str, vars_sel, group_col=None):
        """Adiciona um card com botões (Info/Stats/Export) + canvas para uma figura."""
        card = ctk.CTkFrame(self.plot_canvas_frame)
        card.pack(fill='both', expand=True, padx=8, pady=8)

        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill='x', padx=8, pady=(8, 4))

        lbl = ctk.CTkLabel(header, text=f" {title}", anchor="w")
        lbl.pack(side='left', fill='x', expand=True)

        btn_info = ctk.CTkButton(
            header,
            text=" Info",
            width=80,
            command=lambda: messagebox.showinfo("Info", self.plot_science_info.get(plot_type, plot_type))
        )
        btn_info.pack(side='left', padx=3)

        btn_stats = ctk.CTkButton(
            header,
            text=" Stats",
            width=80,
            command=lambda: messagebox.showinfo("Stats", self._stats_for_current_plot(plot_type, vars_sel, group_col))
        )
        btn_stats.pack(side='left', padx=3)

        btn_png = ctk.CTkButton(header, text="PNG", width=60, command=lambda: self._export_figure(fig, title, "png"))
        btn_png.pack(side='left', padx=3)

        btn_jpg = ctk.CTkButton(header, text="JPG", width=60, command=lambda: self._export_figure(fig, title, "jpg"))
        btn_jpg.pack(side='left', padx=3)

        btn_tif = ctk.CTkButton(header, text="TIF", width=60, command=lambda: self._export_figure(fig, title, "tif"))
        btn_tif.pack(side='left', padx=3)

        # Canvas
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True, padx=8, pady=(0, 8))

    def _on_vars_count_change(self):
        try:
            n = int(self.vars_count_combo.get())
        except Exception:
            n = 0

        # Mostra apenas após o usuário escolher N (2-5)
        if n not in (2, 3, 4, 5):
            for row in getattr(self, "vars_select_rows", []):
                try:
                    row.pack_forget()
                except Exception:
                    pass
            for cb in self.vars_select_combos:
                try:
                    cb.set("")
                    cb.configure(state="disabled")
                except Exception:
                    pass
            self._update_test_preview()
            return

        for i, cb in enumerate(self.vars_select_combos):
            if i < n:
                try:
                    self.vars_select_rows[i].pack(fill="x", pady=2)
                except Exception:
                    pass
                cb.configure(state="normal")
            else:
                try:
                    self.vars_select_rows[i].pack_forget()
                except Exception:
                    pass
                cb.set("")
                cb.configure(state="disabled")

        self._update_test_preview()

    def _get_selected_vars(self):
        try:
            n = int(self.vars_count_combo.get())
        except Exception:
            n = 0

        if n not in (2, 3, 4, 5):
            return []

        vars_sel = []
        for i in range(n):
            try:
                v = (self.vars_select_combos[i].get() or "").strip()
            except Exception:
                v = ""
            if v and v not in vars_sel:
                vars_sel.append(v)
        return vars_sel

    def _suggest_tests_multi(self, vars_sel, group_col=None):
        """Heurística simples para sugerir testes quando há múltiplas variáveis."""
        suggestions = []
        if not self.current_data is None and vars_sel:
            numeric_vars = [v for v in vars_sel if v in self.current_data.columns and pd.api.types.is_numeric_dtype(self.current_data[v])]
            cat_vars = [v for v in vars_sel if v in self.current_data.columns and not pd.api.types.is_numeric_dtype(self.current_data[v])]

            if group_col and group_col in self.current_data.columns:
                try:
                    n_groups = int(self.current_data[group_col].nunique(dropna=True))
                except Exception:
                    n_groups = 0

                if numeric_vars:
                    if n_groups <= 2:
                        suggestions.append("Teste t / Mann-Whitney (para cada variável numérica)")
                    elif n_groups > 2:
                        suggestions.append("ANOVA / Kruskal-Wallis (para cada variável numérica)")
                        if len(numeric_vars) >= 2:
                            suggestions.append("MANOVA (múltiplas variáveis dependentes)")
                if cat_vars:
                    suggestions.append("Qui-quadrado / Fisher (variáveis categóricas)")
            else:
                if len(numeric_vars) >= 2:
                    suggestions.append("Correlação (Pearson/Spearman) entre variáveis")
                    suggestions.append("Regressão linear múltipla (se houver variável alvo)")
                if cat_vars and numeric_vars:
                    suggestions.append("ANOVA/Regressão com fatores categóricos")

        return suggestions

    def _render_preview_table(self, df):
        """Renderiza um DataFrame em formato de planilha na área de Preview."""
        try:
            if df is None:
                return

            # Limpa colunas atuais
            for col in self.preview_table["columns"]:
                pass
            self.preview_table.delete(*self.preview_table.get_children())

            cols = list(df.columns)
            self.preview_table["columns"] = cols

            # Cabeçalhos + largura inicial
            for c in cols:
                self.preview_table.heading(c, text=str(c))
                self.preview_table.column(c, width=140, anchor="w", stretch=True)

            # Inserir linhas (limitado para performance)
            max_rows = min(len(df), 200)
            for i in range(max_rows):
                row = df.iloc[i].tolist()
                self.preview_table.insert("", "end", values=["" if v is None else str(v) for v in row])

        except Exception:
            # Não deixa a UI quebrar se o render falhar
            pass

    def _update_config_summary(self):
        """Atualiza o resumo de configuração (texto corrido)."""
        try:
            plot = self.plot_type_combo.get() if hasattr(self, "plot_type_combo") else "-"
        except Exception:
            plot = "-"

        vars_sel = self._get_selected_vars()
        group = None
        try:
            group = self.group_var_combo.get()
            if group == "Nenhum":
                group = None
        except Exception:
            group = None

        tests = self._suggest_tests_multi(vars_sel, group)

        analysis_name = "Análise Estatística Multivariada" if len(vars_sel) >= 3 else "Análise Estatística"
        axes_desc = ""
        if plot and plot != "Automático (Recomendado)":
            axes_desc = f"O gráfico selecionado é '{plot}', onde os eixos representam as variáveis escolhidas conforme o tipo de visualização."
        else:
            axes_desc = "O sistema escolherá automaticamente a melhor visualização para as variáveis selecionadas."

        vars_desc = "nenhuma" if not vars_sel else ", ".join([f"'{v}'" for v in vars_sel])
        group_desc = f"A variável de grupo é '{group}' para comparação entre categorias." if group else "Nenhuma variável de grupo foi definida."

        if tests:
            tests_desc = "Testes sugeridos: " + "; ".join(tests) + "."
        else:
            tests_desc = "Testes sugeridos: (selecione variáveis e/ou grupo para recomendações)."

        text = (
            f"{analysis_name}. Você selecionou as variáveis {vars_desc}. {group_desc} "
            f"{axes_desc} {tests_desc}"
        )

        try:
            self.config_summary_text.configure(text=text, text_color="white")
        except Exception:
            pass

    def _on_connection_type_change(self):
        """Atualiza interface quando tipo de conexão muda"""
        conn_type = self.connection_type_var.get()

        if conn_type == "SQLite":
            self.mysql_frame.pack_forget()
            self.sqlite_frame.pack(pady=5)
            self.sqlite_label.pack(side='left', padx=5)
            self.sqlite_entry.pack(side='left', padx=5)
            self.sqlite_browse_btn.pack(side='left', padx=5)
            self.sqlite_open_btn.pack(side='left', padx=5)
            self.server_preset_combo.configure(state="disabled")
        else:
            self.sqlite_frame.pack_forget()
            self.mysql_frame.pack(pady=5)
            self.server_preset_combo.configure(state="normal")

    def _open_sqlite_file(self):
        """Seleciona um arquivo SQLite e conecta automaticamente."""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo SQLite",
            filetypes=[("SQLite Database", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")]
        )
        if not filename:
            return

        try:
            self.connection_type_var.set("SQLite")
        except Exception:
            pass

        try:
            self._on_connection_type_change()
        except Exception:
            pass

        self.sqlite_entry.delete(0, 'end')
        self.sqlite_entry.insert(0, filename)
        self._connect_database()

    def _load_preset_connection(self, choice):
        """Carrega configurações de conexão pré-definidas"""
        if choice in self.default_connections:
            config = self.default_connections[choice]
            self.host_entry.delete(0, 'end')
            self.host_entry.insert(0, config['host'])
            self.port_entry.delete(0, 'end')
            self.port_entry.insert(0, str(config['port']))
            self.database_entry.delete(0, 'end')
            self.database_entry.insert(0, config['database'])
            self.user_entry.delete(0, 'end')
            self.user_entry.insert(0, config['user'])
            self.password_entry.delete(0, 'end')
            self.password_entry.insert(0, config.get('password', ''))

    def _browse_sqlite_file(self):
        """Abre diálogo para selecionar arquivo SQLite"""
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo SQLite",
            filetypes=[("SQLite Database", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")]
        )
        if filename:
            self.sqlite_entry.delete(0, 'end')
            self.sqlite_entry.insert(0, filename)

    def _connect_database(self):
        """Conecta ao banco de dados"""
        def connect_thread():
            conn_type = self.connection_type_var.get()
            success = False

            try:
                if conn_type == "SQLite":
                    db_path = self.sqlite_entry.get()
                    if not db_path:
                        messagebox.showerror("Erro", "Selecione um arquivo SQLite")
                        return
                    success = self.db_connection.connect_sqlite(db_path)

                else:
                    host = self.host_entry.get()
                    database = self.database_entry.get()
                    user = self.user_entry.get()
                    password = self.password_entry.get()
                    port = int(self.port_entry.get())

                    if not all([host, database, user]):
                        messagebox.showerror("Erro", "Preencha todos os campos obrigatórios")
                        return

                    success = self.db_connection.connect_mysql(host, database, user, password, port)

                if success:
                    self.connection_status.configure(text="🟢 Conectado", text_color="green")
                    self.table_combo.configure(state="normal")
                    self._refresh_tables()
                    messagebox.showinfo("Sucesso", "Conectado ao banco de dados!")
                else:
                    self.connection_status.configure(text="🔴 Erro na conexão", text_color="red")
                    messagebox.showerror("Erro", "Falha ao conectar ao banco de dados")

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao conectar: {str(e)}")
                self.connection_status.configure(text="🔴 Erro na conexão", text_color="red")

        threading.Thread(target=connect_thread, daemon=True).start()

    def _refresh_tables(self):
        """Atualiza lista de tabelas e popula o navegador visual"""
        tables = self.db_connection.get_tables()

        # Atualizar combo box (mantém compatibilidade)
        if tables:
            self.table_combo.configure(values=tables)
            if len(tables) > 0:
                self.table_combo.set(tables[0])

        # NOVO: Popular lista visual de tabelas
        self._populate_tables_browser(tables)

    def _populate_tables_browser(self, tables):
        """Popula o navegador visual de tabelas"""
        # Limpar botões existentes
        for btn in self.tables_buttons:
            btn.destroy()
        self.tables_buttons.clear()

        if not tables:
            self.tables_info_label.configure(
                text="⚠️ Nenhuma tabela encontrada no banco",
                text_color="orange"
            )
            return

        # Atualizar info
        self.tables_info_label.configure(
            text=f"✅ {len(tables)} tabela(s) disponível(is) - Clique para carregar",
            text_color="green"
        )

        # Criar botão para cada tabela
        for i, table_name in enumerate(tables):
            # Obter info da tabela
            try:
                columns = self.db_connection.get_table_columns(table_name)
                num_cols = len(columns)
                tooltip = f"{num_cols} colunas: {', '.join(columns[:3])}{'...' if len(columns) > 3 else ''}"
            except:
                tooltip = "Clique para carregar"

            # Frame para cada tabela
            table_btn_frame = ctk.CTkFrame(self.tables_list_frame)
            table_btn_frame.pack(fill='x', padx=5, pady=2)

            # Botão principal da tabela
            table_btn = ctk.CTkButton(
                table_btn_frame,
                text=f"📋 {table_name}",
                command=lambda t=table_name: self._load_table_quick(t),
                width=450,
                height=35,
                anchor="w",
                fg_color="#1f538d",
                hover_color="#14375e"
            )
            table_btn.pack(side='left', padx=2)

            # Botão de info
            info_btn = ctk.CTkButton(
                table_btn_frame,
                text="ℹ️",
                command=lambda t=table_name: self._show_table_info(t),
                width=40,
                height=35,
                fg_color="#2b2b2b",
                hover_color="#404040"
            )
            info_btn.pack(side='left', padx=2)

            # Tooltip
            try:
                # Criar label de tooltip (simplificado)
                pass
            except:
                pass

            self.tables_buttons.append(table_btn_frame)

    def _load_table_quick(self, table_name):
        """Carrega tabela rapidamente ao clicar"""
        # Atualizar query automaticamente
        try:
            query = self.db_connection.build_select_all_query(table_name, limit=1000)
        except Exception:
            query = f"SELECT * FROM {table_name} LIMIT 1000"
        self.query_text.delete("1.0", "end")
        self.query_text.insert("1.0", query)

        # Atualizar combo
        self.table_combo.set(table_name)

        # Carregar dados
        self._load_data()

    def _show_table_info(self, table_name):
        """Mostra informações detalhadas da tabela"""
        try:
            columns = self.db_connection.get_table_columns(table_name)

            # Executar query para pegar amostra e tipos
            sample_query = f"SELECT * FROM {table_name} LIMIT 5"
            sample_data = self.db_connection.execute_query(sample_query)

            info_text = f"TABELA: {table_name}\n"
            info_text += "=" * 60 + "\n\n"
            info_text += f"Número de colunas: {len(columns)}\n\n"
            info_text += "COLUNAS:\n"
            info_text += "-" * 60 + "\n"

            if sample_data is not None:
                for col in columns:
                    dtype = str(sample_data[col].dtype) if col in sample_data.columns else "N/A"
                    info_text += f"  • {col} ({dtype})\n"

                info_text += "\n" + "-" * 60 + "\n"
                info_text += f"\nPRIMEIRAS {len(sample_data)} LINHAS:\n"
                info_text += "-" * 60 + "\n"
                info_text += sample_data.to_string()
            else:
                for col in columns:
                    info_text += f"  • {col}\n"

            # Mostrar em janela
            info_window = ctk.CTkToplevel(self.root)
            info_window.title(f"Informações - {table_name}")
            info_window.geometry("700x600")

            text_widget = scrolledtext.ScrolledText(
                info_window,
                width=80,
                height=30,
                bg="#2b2b2b",
                fg="white",
                font=("Consolas", 9)
            )
            text_widget.pack(fill='both', expand=True, padx=10, pady=10)
            text_widget.insert("1.0", info_text)
            text_widget.configure(state="disabled")

            # Botão para carregar
            load_btn = ctk.CTkButton(
                info_window,
                text=f"📥 Carregar Tabela '{table_name}'",
                command=lambda: [self._load_table_quick(table_name), info_window.destroy()],
                height=40,
                fg_color="green",
                hover_color="darkgreen"
            )
            load_btn.pack(pady=10)

        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao obter informações: {str(e)}")

    def _load_data(self):
        """Carrega dados do banco"""
        def load_thread():
            try:
                query = self.query_text.get("1.0", "end-1c").strip()

                if not query:
                    table = self.table_combo.get()
                    if not table:
                        messagebox.showerror("Erro", "Selecione uma tabela ou digite uma query")
                        return
                    try:
                        query = self.db_connection.build_select_all_query(table, limit=1000)
                    except Exception:
                        query = f"SELECT * FROM {table} LIMIT 1000"

                self.current_data = self.db_connection.execute_query(query)

                if self.current_data is not None and not self.current_data.empty:
                    self.analyzer = BiologicalDataAnalyzer(self.current_data)

                    # Atualizar preview
                    preview = f"Dados carregados: {len(self.current_data)} linhas, {len(self.current_data.columns)} colunas\n\n"
                    preview += self.current_data.head(10).to_string()

                    self.preview_text.delete('1.0', 'end')
                    self.preview_text.insert('1.0', preview)

                    # Preview principal (coluna direita)
                    try:
                        self._render_preview_table(self.current_data)
                    except Exception:
                        pass

                    # Atualizar combos de variáveis
                    numeric_cols = self.current_data.select_dtypes(include=['number']).columns.tolist()
                    all_cols = self.current_data.columns.tolist()

                    self.numeric_var_combo.configure(values=numeric_cols, state="normal")
                    if numeric_cols:
                        self.numeric_var_combo.set(numeric_cols[0])

                    # Popular combos multi-variáveis com todas as colunas
                    try:
                        for idx, cb in enumerate(self.vars_select_combos):
                            cb.configure(values=all_cols)
                            if idx < 2 and all_cols:
                                cb.set(all_cols[min(idx, len(all_cols)-1)])
                    except Exception:
                        pass

                    group_cols = ["Nenhum"] + all_cols
                    self.group_var_combo.configure(values=group_cols, state="normal")
                    self.group_var_combo.set("Nenhum")
                    self._update_test_preview()

                    messagebox.showinfo("Sucesso", f"Dados carregados: {len(self.current_data)} registros")
                else:
                    msg = "Nenhum dado retornado pela query."
                    if query:
                        msg += f"\n\nQuery executada:\n{query}"
                    try:
                        if getattr(self.db_connection, "last_error", None):
                            msg += f"\n\nDetalhe do erro:\n{self.db_connection.last_error}"
                    except Exception:
                        pass

                    # Diagnóstico adicional: tenta COUNT(*) quando a query é o SELECT padrão
                    try:
                        if not self.query_text.get("1.0", "end-1c").strip():
                            table = self.table_combo.get()
                        else:
                            table = self.table_combo.get()
                        if table:
                            cnt_q = self.db_connection.build_count_query(table)
                            cnt = self.db_connection.execute_scalar(cnt_q)
                            if cnt is not None:
                                msg += f"\n\nCOUNT(*) em {table}: {cnt}"
                    except Exception:
                        pass
                    msg += "\n\nDicas:\n- Verifique se a tabela tem registros\n- Se o nome da tabela tiver espaço/hífen/palavra reservada, o LILO agora tenta fazer quoting automaticamente\n- Teste no banco: SELECT COUNT(*) FROM <tabela>"
                    messagebox.showerror("Erro", msg)

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar dados: {str(e)}")

        threading.Thread(target=load_thread, daemon=True).start()

    def _update_test_preview(self):
        """Mostra a recomendação de teste simplificada no painel lateral"""
        if self.analyzer is None:
            self.test_preview_label.configure(text="ℹ️ Carregue os dados primeiro para ver sugestões", text_color="gray")
            return

        vars_sel = self._get_selected_vars()
        group_col = self.group_var_combo.get()
        if group_col == "Nenhum":
            group_col = None

        if len(vars_sel) < 2:
            self.test_preview_label.configure(text="⚠️ Selecione pelo menos 2 variáveis", text_color="#FF6B6B")
            self._update_config_summary()
            return

        try:
            suggestions = self._suggest_tests_multi(vars_sel, group_col)
            if suggestions:
                preview_text = "✅ Sugestões de Testes/Análises:\n" + "\n".join([f"- {s}" for s in suggestions])
            else:
                preview_text = "ℹ️ Selecione variáveis e/ou grupo para ver sugestões"
            self.test_preview_label.configure(text=preview_text, text_color="#95E1D3")
        except Exception as e:
            self.test_preview_label.configure(text=f"❌ Erro ao recomendar: {str(e)}", text_color="#FF6B6B")

        self._update_config_summary()

    def _inspect_data(self):
        """Executa inspeção de dados"""
        if self.analyzer is None:
            messagebox.showwarning("Aviso", "Carregue os dados primeiro")
            return

        structure = self.analyzer.inspect_data_structure()

        result = "=" * 80 + "\n"
        result += "INSPEÇÃO DE DADOS\n"
        result += "=" * 80 + "\n\n"
        result += f"Total de observações: {structure['n_rows']}\n"
        result += f"Total de colunas: {structure['n_columns']}\n\n"
        result += f"Colunas numéricas ({len(structure['numeric_columns'])}):\n"
        for col in structure['numeric_columns']:
            result += f"  • {col}\n"
        result += f"\nColunas categóricas ({len(structure['categorical_columns'])}):\n"
        for col in structure['categorical_columns']:
            result += f"  • {col}\n"

        result += "\n" + "=" * 80 + "\n"

        self.results_text.delete('1.0', 'end')
        self.results_text.insert('1.0', result)
        self.results_notebook.select(0)

    def _recommend_test(self):
        """Recomenda teste estatístico"""
        if self.analyzer is None:
            messagebox.showwarning("Aviso", "Carregue os dados primeiro")
            return

        numeric_col = self.numeric_var_combo.get()
        group_col = self.group_var_combo.get()
        if group_col == "Nenhum":
            group_col = None

        recommendation = self.analyzer.recommend_test(numeric_col, group_col)

        result = "=" * 80 + "\n"
        result += "RECOMENDAÇÃO DE TESTE ESTATÍSTICO\n"
        result += "=" * 80 + "\n\n"
        result += f"Variável analisada: {numeric_col}\n"
        if group_col:
            result += f"Variável de grupo: {group_col}\n"
        result += f"\nTeste recomendado: {recommendation['test_name']}\n"
        result += f"Tipo: {recommendation['test_type']}\n"
        result += "\nRaciocínio:\n"
        for reason in recommendation['reasoning']:
            result += f"  • {reason}\n"

        if 'post_hoc' in recommendation:
            result += f"\nTeste post-hoc recomendado: {recommendation['post_hoc']}\n"

        result += "\n" + "=" * 80 + "\n"

        self.results_text.delete('1.0', 'end')
        self.results_text.insert('1.0', result)
        self.results_notebook.select(0)

    def _execute_full_analysis(self):
        """Executa análise estatística completa"""
        if self.analyzer is None:
            messagebox.showwarning("Aviso", "Carregue os dados primeiro")
            return

        numeric_col = self.numeric_var_combo.get()
        group_col = self.group_var_combo.get()
        if group_col == "Nenhum":
            group_col = None

        # Executar teste
        test_result = self.analyzer.execute_test(numeric_col, group_col)

        result = "=" * 80 + "\n"
        result += "RESULTADOS DA ANÁLISE ESTATÍSTICA\n"
        result += "=" * 80 + "\n\n"
        result += f"Teste: {test_result['test_name']}\n"
        if test_result['statistic'] is not None:
            result += f"Estatística do teste: {test_result['statistic']:.4f}\n"
        if test_result['p_value'] is not None:
            result += f"P-valor: {test_result['p_value']:.6f}\n"
            result += f"Significância (α=0.05): {'SIM' if test_result['significant'] else 'NÃO'}\n"
        result += f"\nInterpretação: {test_result['interpretation']}\n"

        if 'post_hoc' in test_result['details']:
            result += "\n" + "=" * 80 + "\n"
            result += "ANÁLISE POST-HOC\n"
            result += "=" * 80 + "\n"
            result += test_result['details']['post_hoc']

        result += "\n" + "=" * 80 + "\n"

        self.results_text.delete('1.0', 'end')
        self.results_text.insert('1.0', result)
        self.results_notebook.select(0)

    def _generate_visualizations(self):
        """Gera visualizações"""
        if self.analyzer is None:
            messagebox.showwarning("Aviso", "Carregue os dados primeiro")
            return

        vars_sel = self._get_selected_vars() if hasattr(self, "_get_selected_vars") else []
        group_col = self.group_var_combo.get() if hasattr(self, "group_var_combo") else None
        if group_col == "Nenhum":
            group_col = None

        plot_type = None
        try:
            plot_type = self.plot_type_combo.get()
        except Exception:
            plot_type = "Automático (Recomendado)"

        # Limpar canvas anterior
        for widget in self.plot_canvas_frame.winfo_children():
            widget.destroy()

        # Gerar figuras por tipo
        try:
            figs = self._create_figures_for_plot_type(plot_type, vars_sel, group_col)
        except Exception:
            figs = []

        if not figs:
            messagebox.showwarning("Aviso", "Não foi possível gerar visualizações com as variáveis/plot selecionados")
            return

        # Exibir figuras (com card e botões) + salvar automaticamente
        for item in figs:
            if isinstance(item, tuple) and len(item) == 2:
                fig, title = item
            else:
                fig, title = item, "Figura"

            # Salva automaticamente em PNG
            try:
                self._safe_save_figure(fig, stem=title, fmt="png")
            except Exception:
                pass

            self._add_plot_card(fig, title=title, plot_type=plot_type, vars_sel=vars_sel, group_col=group_col)

        self.results_notebook.select(1)
        messagebox.showinfo("Sucesso", "Visualizações geradas!")

    def _on_data_source_change(self):
        """Alterna visibilidade dos controles de SQL vs arquivo."""
        try:
            src = self.data_source_combo.get()
        except Exception:
            src = "SQL"

        is_file = src == "Arquivo (CSV/Excel)"

        # A área de importação CSV/Excel deve permanecer sempre visível (pedido do usuário).
        # Aqui apenas ajustamos o estado dos controles de SQL.

        try:
            self.table_combo.configure(state="disabled" if is_file else "normal")
        except Exception:
            pass

        try:
            self.query_text.configure(state="disabled" if is_file else "normal")
        except Exception:
            pass

    def _browse_data_file(self):
        filename = filedialog.askopenfilename(
            title="Selecionar arquivo de dados",
            filetypes=[
                ("CSV", "*.csv"),
                ("Excel", "*.xlsx *.xls"),
                ("All files", "*.*"),
            ]
        )
        if filename:
            target = None
            try:
                target = self.csv_import_entry
            except Exception:
                target = None
            if target is None:
                target = self.file_entry

            try:
                target.delete(0, 'end')
                target.insert(0, filename)
            except Exception:
                pass
            try:
                self.data_source_combo.set("Arquivo (CSV/Excel)")
            except Exception:
                pass
            self._on_data_source_change()

    def _load_data_from_file(self):
        """Carrega dados de CSV/Excel e habilita o mesmo fluxo de análise."""
        path = ""
        try:
            path = (self.csv_import_entry.get() or "").strip()
        except Exception:
            path = ""
        if not path:
            path = self.file_entry.get().strip() if hasattr(self, "file_entry") else ""
        if not path:
            messagebox.showerror("Erro", "Selecione um arquivo CSV/Excel")
            return

        def load_thread():
            try:
                p = Path(path)
                if p.suffix.lower() == ".csv":
                    df = pd.read_csv(path, sep=None, engine="python")
                elif p.suffix.lower() in (".xlsx", ".xls"):
                    df = pd.read_excel(path)
                else:
                    messagebox.showerror("Erro", "Formato não suportado. Use CSV ou Excel (.xls/.xlsx)")
                    return

                self.current_data = df
                self.analyzer = BiologicalDataAnalyzer(self.current_data)

                # Preview (planilha)
                try:
                    self._render_preview_table(self.current_data)
                except Exception:
                    pass

                # Popular combos
                all_cols = self.current_data.columns.tolist()
                numeric_cols = self.current_data.select_dtypes(include=['number']).columns.tolist()

                self.numeric_var_combo.configure(values=numeric_cols, state="normal")
                if numeric_cols:
                    self.numeric_var_combo.set(numeric_cols[0])

                try:
                    for idx, cb in enumerate(self.vars_select_combos):
                        cb.configure(values=all_cols)
                        if idx < 2 and all_cols:
                            cb.set(all_cols[min(idx, len(all_cols)-1)])
                except Exception:
                    pass

                group_cols = ["Nenhum"] + all_cols
                self.group_var_combo.configure(values=group_cols, state="normal")
                self.group_var_combo.set("Nenhum")
                self._update_test_preview()

                messagebox.showinfo("Sucesso", f"Arquivo carregado: {len(self.current_data)} linhas, {len(self.current_data.columns)} colunas")
            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao carregar arquivo: {e}")

        threading.Thread(target=load_thread, daemon=True).start()

    def _suggest_from_science_help(self):
        """Sugestões heurísticas (prontas para plugar IA depois)."""
        try:
            txt = self.science_help_text.get("1.0", "end-1c").lower().strip()
        except Exception:
            txt = ""

        if not txt:
            messagebox.showwarning("Ajuda Científica", "Escreva seu objetivo/variáveis antes de pedir sugestão")
            return

        # Heurística simples de seleção de gráfico
        plot = None
        if "cram" in txt or "categ" in txt or "v de cramer" in txt or "cramer" in txt:
            plot = "Matriz Categórica (V de Cramér)"
        elif "spearman" in txt or "correl" in txt or "matriz" in txt:
            plot = "Matriz de Correlação (Spearman)"
        elif "venn" in txt or "intersec" in txt:
            plot = "Diagrama de Venn"
        elif "preval" in txt or "faixa" in txt or "bins" in txt:
            plot = "Prevalência por Faixa"
        elif "regress" in txt or "scatter" in txt or "dispers" in txt:
            plot = "Scatter com Regressão"
        elif "box" in txt or "boxplot" in txt or "mediana" in txt:
            plot = "Boxplot"
        else:
            plot = "Automático (Recomendado)"

        try:
            self.plot_type_combo.set(plot)
            self._on_plot_type_change(plot)
        except Exception:
            pass

        messagebox.showinfo("Sugestão", f"Sugestão inicial de gráfico: {plot}\n\nAjuste manualmente as variáveis (2-5) e clique em 'Gerar Visualizações'.")

    def _generate_report(self):
        """Gera relatório completo"""
        if self.analyzer is None:
            messagebox.showwarning("Aviso", "Carregue os dados primeiro")
            return

        numeric_col = self.numeric_var_combo.get()
        group_col = self.group_var_combo.get()
        if group_col == "Nenhum":
            group_col = None

        report = self.analyzer.generate_full_report(numeric_col, group_col)

        self.results_text.delete('1.0', 'end')
        self.results_text.insert('1.0', report)
        self.results_notebook.select(0)

        # Opção para salvar relatório
        save = messagebox.askyesno("Salvar Relatório", "Deseja salvar o relatório em arquivo?")
        if save:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                messagebox.showinfo("Sucesso", f"Relatório salvo em: {filename}")

    def run(self):
        """Inicia a aplicação"""
        self.root.mainloop()


def main():
    """Função principal"""
    app = SQLStatisticalAnalyzerGUI()
    app.run()


if __name__ == "__main__":
    main()
