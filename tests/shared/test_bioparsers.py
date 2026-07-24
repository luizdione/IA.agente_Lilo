"""
Testes de shared/bioparsers.py (V20.1). Travam os bugs achados na auditoria
adversarial: descarte da melhor pose no Vina 1.2.x, Cq com virgula (pt-BR),
ALT simbolico de gVCF contado como indel, e a deteccao de summary.txt do FastQC.
Deterministicos, sem LLM.
"""
from shared.bioparsers import (parse_vina, parse_qpcr, parse_fastqc,
                               parse_vcf_summary, detect, parse_bio_log)
from pathlib import Path


# ── VINA ─────────────────────────────────────────────────────────────────────
VINA_12 = """AutoDock Vina v1.2.5
mode |   affinity | dist from best mode
     | (kcal/mol) | rmsd l.b.| rmsd u.b.
-----+------------+----------+----------
   1       -9.428          0          0
   2       -9.335      1.997      2.792
   3       -8.192      2.034      2.868
"""

VINA_112 = """-----+------------+----------+----------
   1       -9.400      0.000      0.000
   2       -8.900      2.104      3.542
"""


def test_vina_12x_preserva_melhor_pose():
    # rmsd '0' inteiro no modo 1 (Vina 1.2.x) NAO pode descartar a melhor pose.
    out = parse_vina(VINA_12)
    assert "3 pose" in out
    assert "Melhor: modo 1" in out
    assert "-9.43" in out
    assert "AVISO" not in out


def test_vina_112_formato_fixo_nao_regride():
    out = parse_vina(VINA_112)
    assert "Melhor: modo 1" in out and "-9.40" in out


def test_vina_lacuna_avisa():
    # numeracao comecando em 2 => alguma linha nao reconhecida => aviso explicito
    out = parse_vina("-----+---\n   2   -8.9   1.0   2.0\n   3   -8.1   1.5   2.9\n")
    assert "AVISO" in out


# ── qPCR ─────────────────────────────────────────────────────────────────────
QPCR_PTBR = """Well;Fluor;Target;Content;Sample;Cq
A01;SYBR;GAPDH;Unkn;Ctrl;19,85
A02;SYBR;GAPDH;Unkn;Ctrl;19,92
A03;SYBR;GAPDH;Unkn;Trat;24,53
A04;SYBR;GAPDH;Unkn;Trat;Undetermined
"""


def test_qpcr_virgula_decimal_ptbr():
    out = parse_qpcr(QPCR_PTBR)
    assert "nenhum valor" not in out
    assert "Ctrl / GAPDH" in out and "Trat / GAPDH" in out
    # Undetermined descartado, nao confundido com "nao amplificou"
    assert "1 celula" in out


def test_qpcr_agrupa_por_sample_nao_well():
    out = parse_qpcr(QPCR_PTBR)
    # se agrupasse por Well (A01/A02) apareceriam 4 grupos; por Sample sao 2
    assert "2 grupo" in out


# ── FastQC ───────────────────────────────────────────────────────────────────
FASTQC_DATA = ("##FastQC\t0.11.9\n>>Basic Statistics\tpass\n#Measure\tValue\n"
               ">>END_MODULE\n>>Per base sequence quality\twarn\n>>END_MODULE\n")
FASTQC_SUMMARY = ("PASS\tBasic Statistics\tsample.fastq\n"
                  "FAIL\tPer base sequence quality\tsample.fastq\n")


def test_fastqc_data_txt():
    out = parse_fastqc(FASTQC_DATA)
    assert "1 PASS" in out and "1 WARN" in out


def test_fastqc_summary_txt_detectado():
    assert detect(Path("summary.txt"), FASTQC_SUMMARY) == "fastqc"
    out = parse_fastqc(FASTQC_SUMMARY)
    assert "1 PASS" in out and "1 FAIL" in out


# ── VCF ──────────────────────────────────────────────────────────────────────
VCF_GVCF = """##fileformat=VCFv4.2
#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO
chr1\t100\t.\tA\tG\t50\tPASS\t.
chr1\t200\t.\tC\tT\t.\t.\t.
chr1\t300\t.\tA\t<NON_REF>\t.\t.\t.
chr1\t400\t.\tG\t<DEL>\t.\t.\t.
chr1\t500\t.\tAT\tA\t.\t.\t.
"""


def test_vcf_gvcf_nao_conta_alt_simbolico_como_indel():
    out = parse_vcf_summary(VCF_GVCF)
    # A>G, C>T (SNP), <DEL> (SV), AT>A (indel). <NON_REF> ignorado.
    assert "4 variantes" in out
    assert "2 SNPs" in out
    assert "1 indels" in out
    assert "1 SV" in out
    assert "Ti=2" in out
    assert "nao-variante" in out


# ── auto-detect via parse_bio_log ────────────────────────────────────────────
def test_parse_bio_log_autodetect(tmp_path):
    fv = tmp_path / "dock.log"; fv.write_text(VINA_12, encoding="utf-8")
    assert "Melhor: modo 1" in parse_bio_log(str(fv))
    fc = tmp_path / "run.vcf"; fc.write_text(VCF_GVCF, encoding="utf-8")
    assert "variantes" in parse_bio_log(str(fc))


def test_parse_bio_log_arquivo_inexistente():
    assert "nao encontrado" in parse_bio_log("/nao/existe/x.log").lower()
