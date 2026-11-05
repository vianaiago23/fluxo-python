"""Geração do relatório financeiro em PDF (fpdf2)."""

from collections import defaultdict

from fpdf import FPDF
from fpdf.fonts import FontFace

from constantes import MESES, formatar_reais, hoje

VERDE = (0, 82, 39)
VERMELHO = (178, 58, 31)
TINTA = (15, 36, 26)
CINZA = (90, 105, 97)
PRATA = (174, 184, 178)
PRATA_CLARO = (232, 237, 234)
BRANCO = (255, 255, 255)


class Relatorio(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("helvetica", size=8)
        self.set_text_color(*CINZA)
        self.cell(0, 5, "Fluxo - controle financeiro", align="L")
        self.set_y(-14)
        self.cell(0, 5, f"Pagina {self.page_no()} de {{nb}}", align="R")


def _desenhar_marca(pdf, x, y, lado):
    """Redesenha o ícone do app: quadrado verde, gráfico de área branco e base prata."""
    pdf.set_fill_color(*VERDE)
    pdf.rect(x, y, lado, lado, style="F")

    escala = lado / 96.0
    pontos = [(22, 66), (38, 44), (52, 54), (74, 24), (74, 66)]
    pdf.set_fill_color(*BRANCO)
    pdf.polygon([(x + px * escala, y + py * escala) for px, py in pontos], style="F")

    pdf.set_fill_color(*PRATA)
    pdf.rect(x + 20 * escala, y + 70 * escala, 56 * escala, 4 * escala, style="F")


def _cabecalho(pdf, nome_negocio, largura):
    _desenhar_marca(pdf, 14, 9, 14)

    pdf.set_xy(32, 11)
    pdf.set_font("helvetica", "B", 18)
    pdf.set_text_color(*TINTA)
    pdf.cell(pdf.get_string_width("Flu"), 7, "Flu")
    pdf.set_text_color(*VERDE)
    pdf.cell(pdf.get_string_width("xo"), 7, "xo")

    pdf.set_xy(32, 19)
    pdf.set_font("helvetica", size=9)
    pdf.set_text_color(*CINZA)
    pdf.cell(100, 5, f"Relatorio financeiro - {nome_negocio}")
    pdf.set_xy(largura - 74, 19)
    pdf.cell(60, 5, f"Gerado em {hoje().strftime('%d/%m/%Y')}", align="R")

    pdf.set_draw_color(*VERDE)
    pdf.set_line_width(0.6)
    pdf.line(14, 30, largura - 14, 30)


def _caixas_resumo(pdf, largura, entradas, saidas, saldo):
    caixas = [
        ("TOTAL DE ENTRADAS", formatar_reais(entradas), VERDE),
        ("TOTAL DE SAIDAS", formatar_reais(saidas), VERMELHO),
        ("SALDO GERAL", formatar_reais(saldo), VERDE if saldo >= 0 else VERMELHO),
    ]
    largura_caixa = (largura - 28 - 10) / 3
    for posicao, (rotulo, valor, cor) in enumerate(caixas):
        x = 14 + posicao * (largura_caixa + 5)
        pdf.set_fill_color(*PRATA_CLARO)
        pdf.rect(x, 40, largura_caixa, 22, style="F")

        pdf.set_xy(x + 5, 44)
        pdf.set_font("helvetica", size=7)
        pdf.set_text_color(*CINZA)
        pdf.cell(largura_caixa - 10, 4, rotulo)

        pdf.set_xy(x + 5, 50)
        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(*cor)
        pdf.cell(largura_caixa - 10, 7, valor)


def gerar_pdf(nome_negocio, lancamentos):
    """Monta o relatório completo e devolve os bytes do PDF."""
    pdf = Relatorio(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    largura = pdf.w

    entradas = sum(l["valor"] for l in lancamentos if l["tipo"] == "entrada")
    saidas = sum(l["valor"] for l in lancamentos if l["tipo"] == "despesa")

    _cabecalho(pdf, nome_negocio, largura)
    _caixas_resumo(pdf, largura, entradas, saidas, entradas - saidas)

    # agrupa por mês, na ordem cronológica
    por_mes = defaultdict(list)
    for movimento in lancamentos:
        por_mes[movimento["data"][:7]].append(movimento)

    pdf.set_y(72)
    for chave in sorted(por_mes):
        do_mes = por_mes[chave]
        ano, mes = int(chave[:4]), int(chave[5:7])
        entra = sum(l["valor"] for l in do_mes if l["tipo"] == "entrada")
        sai = sum(l["valor"] for l in do_mes if l["tipo"] == "despesa")

        if pdf.get_y() > 240:
            pdf.add_page()

        pdf.set_font("helvetica", "B", 12)
        pdf.set_text_color(*TINTA)
        pdf.cell(60, 7, f"{MESES[mes - 1]} {ano}")

        pdf.set_font("helvetica", size=8)
        pdf.set_text_color(*CINZA)
        pdf.cell(0, 7, f"Entradas {formatar_reais(entra)}   |   "
                       f"Saidas {formatar_reais(sai)}   |   "
                       f"Saldo {formatar_reais(entra - sai)}", align="R")
        pdf.ln(9)

        pdf.set_font("helvetica", size=8.5)
        with pdf.table(
            col_widths=(18, 18, 38, 74, 26),
            text_align=("LEFT", "LEFT", "LEFT", "LEFT", "RIGHT"),
            line_height=5.5,
            headings_style=FontFace(emphasis="BOLD", color=BRANCO, fill_color=VERDE),
            cell_fill_color=(246, 249, 247),
            cell_fill_mode="ROWS",
        ) as tabela:
            cabecalho = tabela.row()
            for titulo in ("Data", "Tipo", "Categoria", "Descricao", "Valor"):
                cabecalho.cell(titulo)

            for movimento in do_mes:
                linha = tabela.row()
                dia, mes_txt, ano_txt = (movimento["data"][8:10],
                                         movimento["data"][5:7],
                                         movimento["data"][0:4])
                linha.cell(f"{dia}/{mes_txt}/{ano_txt}")
                linha.cell("Entrada" if movimento["tipo"] == "entrada" else "Despesa")
                linha.cell(movimento["categoria_nome"])
                linha.cell(movimento["descricao"] or "")
                sinal = "+" if movimento["tipo"] == "entrada" else "-"
                linha.cell(f"{sinal} {formatar_reais(movimento['valor'])}")

        pdf.ln(8)

    return bytes(pdf.output())
