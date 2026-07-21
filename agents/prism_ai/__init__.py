"""
agents/prism_ai — Prism AI Copilot: Análise Científica Automatizada
====================================================================
Módulo multi-agente para detecção de experimento, estatística,
visualização, escrita científica e exportação .pzfx.

Sub-agentes:
  1. IngestionAgent     — leitura e padronização de dados
  2. ClassificationAgent — classificação do tipo de experimento
  3. StatsAgent         — seleção e execução de testes estatísticos
  4. VisualizationAgent — gráficos padrão publicação
  5. WritingAgent       — geração de texto "Resultados"
  6. ExportAgent        — exportação .pzfx (GraphPad Prism)
"""

from .main import PrismAgent

__all__ = ["PrismAgent"]
