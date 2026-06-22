"""
brain/classifier.py — Classificação semântica automática em temas do laboratório.
Usa os próprios embeddings (sem regras manuais). Ajuste LAB_THEMES conforme a realidade.
"""
from __future__ import annotations

LAB_THEMES = {
    "nelore_gwas_eqtl": "GWAS eQTL Nelore Bos indicus genômica SNP QTL",
    "reproducao_bovina": "reprodução bovina IATF PAG progesterona eCG sincronização",
    "diagnostico_molecular": "PCR diagnóstico Trichomonas Brucella Campylobacter primers",
    "doencas_negligenciadas": "Chagas Leishmaniose Trypanosoma cruzaína docking",
    "naftoquinonas": "naftoquinona 2-SCN-NQ ADMET docking tripanosomatídeo",
    "qpcr_metodologia": "qPCR eficiência curva padrão primer design Ct",
    "estresse_termico": "estresse térmico endométrio oócito bovino temperatura",
    "metagenomica": "metagenômica microbiota rúmen 16S celulase zebu",
}


class ThemeClassifier:
    def __init__(self, embedder):
        self.embedder = embedder
        self.theme_embeddings = {
            name: embedder.embed_query(desc) for name, desc in LAB_THEMES.items()
        }

    def classify(self, abstract: str, top_n: int = 2) -> list[str]:
        if not abstract:
            return ["outros"]
        q = self.embedder.embed_query(abstract)
        scores = {t: cosine(q, e) for t, e in self.theme_embeddings.items()}
        return sorted(scores, key=scores.get, reverse=True)[:top_n]


def cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
