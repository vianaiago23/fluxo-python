"""Geração dos gráficos em Python (matplotlib), devolvidos como PNG.

Cada função monta a figura na memória e devolve os bytes da imagem,
que as rotas do Flask entregam como se fossem um arquivo.
"""

import io
import os

from constantes import CINZA, PRATA, VERDE, VERMELHO

# Cores de cada tema. O fundo do gráfico é transparente: quem aparece atrás é o
# cartão da página, por isso a borda da rosca usa a cor do cartão.
CORES = {
    "claro": {"texto": CINZA, "grade": "#E6EBE8", "borda": "white", "eixo": PRATA,
              "verde": VERDE, "vermelho": VERMELHO},
    "escuro": {"texto": "#A9BAC6", "grade": "#2A4766", "borda": "#10233A", "eixo": "#7E93A5",
               "verde": "#2BC47E", "vermelho": "#FF8A70"},
}

# O matplotlib é a biblioteca mais pesada do projeto: importá-lo custa alguns
# segundos. Como a maioria das visitas nunca pede um gráfico — a tela de login
# não tem nenhum — ele só é carregado quando o primeiro gráfico é desenhado.
# Depois disso fica na memória, e as chamadas seguintes são imediatas.
_plt = None


def _pyplot():
    """Carrega o matplotlib na primeira vez que um gráfico é pedido."""
    global _plt
    if _plt is None:
        # A pasta pessoal do servidor na nuvem é somente leitura, e o
        # matplotlib precisa de algum lugar para o cache de fontes.
        if os.environ.get("VERCEL"):
            os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")

        import matplotlib

        matplotlib.use("Agg")   # sem interface gráfica: só gera o arquivo

        import matplotlib.pyplot

        _plt = matplotlib.pyplot
    return _plt


def _rotulo_do_eixo(valor, _posicao):
    """Formata o numero do eixo: 2500 vira "2 mil", 300 fica "300".

    O arredondamento usa round(), que devolve inteiro. Com f"{valor:.0f}" o
    zero negativo (-0.0, que aparece quando o grafico nao tem dado) virava a
    etiqueta "-0" no eixo.
    """
    if abs(valor) >= 1000:
        return f"{round(valor / 1000):d} mil"
    return f"{round(valor):d}"


def _para_png(figura):
    plt = _pyplot()
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png", dpi=160, transparent=True,
                   bbox_inches="tight", pad_inches=0.04)
    plt.close(figura)
    buffer.seek(0)
    return buffer.getvalue()


def rosca(fatias, tema="claro"):
    """Gráfico de rosca. `fatias` é uma lista de (nome, valor, cor)."""
    plt = _pyplot()
    cores_tema = CORES[tema]
    fatias = [f for f in fatias if f[1] > 0]
    figura, eixo = plt.subplots(figsize=(2.6, 2.6))

    if not fatias:
        eixo.text(0.5, 0.5, "Sem dados\nneste mês", ha="center", va="center",
                  fontsize=9, color=cores_tema["texto"])
        eixo.axis("off")
        return _para_png(figura)

    valores = [f[1] for f in fatias]
    cores = [f[2] for f in fatias]
    eixo.pie(valores, colors=cores, startangle=90, counterclock=False,
             wedgeprops={"width": 0.30, "edgecolor": cores_tema["borda"], "linewidth": 2})
    eixo.axis("equal")
    return _para_png(figura)


def barras_saldo(rotulos, valores, tema="claro"):
    """Barras do saldo dos últimos meses: verde quando sobra, vermelho quando falta."""
    plt = _pyplot()
    cores_tema = CORES[tema]
    figura, eixo = plt.subplots(figsize=(9.4, 1.9))

    if not any(valores):
        # Sem nenhum movimento, o eixo se degenera e repete "0" em todas as
        # marcas. Os outros graficos ja avisam nesse caso; este faz igual.
        eixo.text(0.5, 0.5, "Sem lançamentos nestes meses", ha="center",
                  va="center", fontsize=9, color=cores_tema["texto"], transform=eixo.transAxes)
        eixo.axis("off")
        return _para_png(figura)

    cores = [cores_tema["verde"] if v >= 0 else cores_tema["vermelho"] for v in valores]
    eixo.bar(rotulos, valores, color=cores, width=0.55, zorder=3)

    eixo.axhline(0, color=cores_tema["eixo"], linewidth=0.8, zorder=2)
    eixo.grid(axis="y", color=cores_tema["grade"], linewidth=0.8, zorder=0)
    eixo.set_axisbelow(True)

    for lado in ("top", "right", "left", "bottom"):
        eixo.spines[lado].set_visible(False)

    eixo.tick_params(axis="both", length=0, labelsize=9, colors=cores_tema["texto"])
    eixo.yaxis.set_major_formatter(_rotulo_do_eixo)
    return _para_png(figura)


def barras_ano(rotulos, entradas, despesas, tema="claro"):
    """Entradas e despesas de cada mês lado a lado: verde e vermelho.

    O eixo dos valores começa sempre em zero. Começando noutro ponto, uma
    diferença pequena entre dois meses pareceria enorme.
    """
    plt = _pyplot()
    cores_tema = CORES[tema]
    figura, eixo = plt.subplots(figsize=(9.4, 2.6))

    if not any(entradas) and not any(despesas):
        eixo.text(0.5, 0.5, "Sem lançamentos neste ano", ha="center", va="center",
                  fontsize=9, color=cores_tema["texto"], transform=eixo.transAxes)
        eixo.axis("off")
        return _para_png(figura)

    posicoes = range(len(rotulos))
    largura = 0.38
    eixo.bar([p - largura / 2 for p in posicoes], entradas, width=largura,
             color=cores_tema["verde"], label="Entradas", zorder=3)
    eixo.bar([p + largura / 2 for p in posicoes], despesas, width=largura,
             color=cores_tema["vermelho"], label="Despesas", zorder=3)

    eixo.set_xticks(list(posicoes), rotulos)
    eixo.set_ylim(bottom=0)
    eixo.grid(axis="y", color=cores_tema["grade"], linewidth=0.8, zorder=0)
    eixo.set_axisbelow(True)

    for lado in ("top", "right", "left", "bottom"):
        eixo.spines[lado].set_visible(False)

    eixo.tick_params(axis="both", length=0, labelsize=9, colors=cores_tema["texto"])
    eixo.yaxis.set_major_formatter(_rotulo_do_eixo)
    eixo.legend(loc="upper left", bbox_to_anchor=(0, 1.18), ncol=2, frameon=False,
                fontsize=8.5, labelcolor=cores_tema["texto"], handlelength=1, handleheight=1)
    return _para_png(figura)
