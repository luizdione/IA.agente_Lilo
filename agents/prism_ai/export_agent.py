"""
Prism AI — Prism Export Agent
==============================
Gera arquivos .pzfx (formato XML do GraphPad Prism).
Estrutura dados, grupos e metadados em formato compatível.
"""

import numpy as np
import pandas as pd
from pathlib import Path
from typing import Optional
from dataclasses import dataclass
import xml.etree.ElementTree as ET
from xml.dom import minidom

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from shared.logger import get_logger

log = get_logger("PrismExport")


@dataclass
class ExportResult:
    """Resultado da exportação."""
    pzfx_path: str
    csv_path: Optional[str]
    success: bool
    warnings: list[str]


class ExportAgent:
    """Exporta dados e resultados para formato GraphPad Prism (.pzfx)."""

    # Namespace XML do GraphPad Prism
    PZFX_NS = "http://graphpad.com/prism/Prism.htm"

    def run(self, ingested_data, classification, stats_result,
            output_dir: str, config: dict = None) -> ExportResult:
        """
        Exporta dados para .pzfx e opcionalmente .csv.

        Args:
            ingested_data: IngestedData
            classification: ExperimentClassification
            stats_result: StatsResult
            output_dir: diretório de saída
            config: dict com filename, export_csv, etc.

        Returns:
            ExportResult com caminhos e status.
        """
        config = config or {}
        out = Path(output_dir)
        out.mkdir(parents=True, exist_ok=True)
        warnings = []

        filename = config.get("filename", "prism_analysis")
        export_csv = config.get("export_csv", True)

        d = ingested_data
        exp_type = classification.experiment_type.value

        # 1. Gerar .pzfx
        pzfx_path = str(out / f"{filename}.pzfx")
        try:
            self._generate_pzfx(d, classification, stats_result, pzfx_path)
            log.info(f"  .pzfx exportado: {pzfx_path}")
        except Exception as e:
            warnings.append(f"Erro ao gerar .pzfx: {e}")
            log.error(f"  Erro .pzfx: {e}")
            pzfx_path = ""

        # 2. Gerar .csv (opcional)
        csv_path = None
        if export_csv:
            csv_path = str(out / f"{filename}_data.csv")
            try:
                d.df.to_csv(csv_path, index=False)
                log.info(f"  CSV exportado: {csv_path}")
            except Exception as e:
                warnings.append(f"Erro ao gerar CSV: {e}")
                csv_path = None

        return ExportResult(
            pzfx_path=pzfx_path,
            csv_path=csv_path,
            success=bool(pzfx_path),
            warnings=warnings,
        )

    # ── Geração PZFX ────────────────────────────────────────────────────

    def _generate_pzfx(self, data, classification, stats, output_path: str):
        """Gera arquivo .pzfx (XML) compatível com GraphPad Prism."""
        root = ET.Element("GraphPadPrismFile")
        root.set("PrismXMLVersion", "5.00")
        root.set("xmlns", self.PZFX_NS)

        # Created info
        created = ET.SubElement(root, "Created")
        ET.SubElement(created, "OriginalVersion").text = "LILO Prism AI Copilot"
        ET.SubElement(created, "CreatedByProgram").text = "LILO"
        ET.SubElement(created, "CreatedByVersion").text = "1.0"

        # Info table
        info = ET.SubElement(root, "InfoSequence")
        self._add_info(info, "Title", "LILO Prism AI Analysis")
        self._add_info(info, "Notes",
                       f"Experiment: {classification.experiment_type.value}\n"
                       f"Test: {stats.test_full_name}\n"
                       f"p-value: {stats.p_value:.6f}")

        # Data table
        table_seq = ET.SubElement(root, "TableSequence")
        table = ET.SubElement(table_seq, "Table")
        table.set("ID", "Table0")

        title = ET.SubElement(table, "Title")
        title.text = "Data"

        # Determinar tipo de tabela Prism
        table_type = self._get_prism_table_type(classification)

        # Colunas e dados
        df = data.df
        gc = data.group_column
        vc = data.value_columns[0]

        groups = df[gc].unique().tolist()

        # Formato: cada grupo como uma coluna
        y_columns = ET.SubElement(table, "YColumn")
        y_columns.set("Width", "143")
        y_columns.set("Decimals", "4")

        for i, grp in enumerate(groups):
            col = ET.SubElement(y_columns if i == 0 else table, "YColumn" if i > 0 else "SubColumn")
            if i > 0:
                col.set("Width", "143")
                col.set("Decimals", "4")
                sub = ET.SubElement(col, "SubColumn")
            else:
                sub = col

            # Título do grupo
            title_elem = ET.SubElement(sub if i == 0 else col, "Title")
            title_elem.text = str(grp)

            # Dados
            vals = df.loc[df[gc] == grp, vc].dropna().values
            for v in vals:
                d_elem = ET.SubElement(sub if i == 0 else col, "d")
                d_elem.text = f"{v:.6f}"

        # Escrever XML formatado
        xml_str = ET.tostring(root, encoding="unicode")
        pretty = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # Remover declaração XML duplicada
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]

        with open(output_path, "w", encoding="utf-8") as f:
            f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
            f.write("\n".join(lines))

    def _add_info(self, parent, key, value):
        ref = ET.SubElement(parent, "Ref")
        ref.set("ID", key)
        ref.text = str(value)

    def _get_prism_table_type(self, classification) -> str:
        """Mapeia tipo de experimento para tipo de tabela Prism."""
        mapping = {
            "two_group_comparison": "Column",
            "multi_group_comparison": "Column",
            "paired_comparison": "Column",
            "one_sample": "Column",
            "correlation": "XY",
            "time_series": "XY",
            "repeated_measures": "GroupedColumn",
            "dose_response": "XY",
        }
        return mapping.get(classification.experiment_type.value, "Column")
