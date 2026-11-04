"""Geração dos gráficos em Python (matplotlib), devolvidos como PNG.

Cada função monta a figura na memória e devolve os bytes da imagem,
que as rotas do Flask entregam como se fossem um arquivo.
"""

import io
import os

from constantes import CINZA, PRATA, VERDE, VERMELHO

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


def _para_png(figura):
    plt = _pyplot()
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png", dpi=160, transparent=True,
                   bbox_inches="tight", pad_inches=0.04)
    plt.close(figura)
    buffer.seek(0)
    return buffer.getvalue()


def rosca(fatias):
    """Gráfico de rosca. `fatias` é uma lista de (nome, valor, cor)."""
    plt = _pyplot()
    fatias = [f for f in fatias if f[1] > 0]
    figura, eixo = plt.subplots(figsize=(2.6, 2.6))

    if not fatias:
        eixo.text(0.5, 0.5, "Sem dados\nneste mês", ha="center", va="center",
                  fontsize=9, color=CINZA)
        eixo.axis("off")
        return _para_png(figura)

    valores = [f[1] for f in fatias]
    cores = [f[2] for f in fatias]
    eixo.pie(valores, colors=cores, startangle=90, counterclock=False,
             wedgeprops={"width": 0.30, "edgecolor": "white", "linewidth": 2})
    eixo.axis("equal")
    return _para_png(figura)


def barras_saldo(rotulos, valores):
    """Barras do saldo dos últimos meses: verde quando sobra, vermelho quando falta."""
    plt = _pyplot()
    figura, eixo = plt.subplots(figsize=(9.4, 1.9))
    cores = [VERDE if v >= 0 else VERMELHO for v in valores]
    eixo.bar(rotulos, valores, color=cores, width=0.55, zorder=3)

    eixo.axhline(0, color=PRATA, linewidth=0.8, zorder=2)
    eixo.grid(axis="y", color="#E6EBE8", linewidth=0.8, zorder=0)
    eixo.set_axisbelow(True)

    for lado in ("top", "right", "left", "bottom"):
        eixo.spines[lado].set_visible(False)

    eixo.tick_params(axis="both", length=0, labelsize=9, colors=CINZA)
    eixo.yaxis.set_major_formatter(
        lambda valor, _pos: f"{valor/1000:.0f} mil" if abs(valor) >= 1000 else f"{valor:.0f}"
    )
    return _para_png(figura)


def barras_ano(rotulos, entradas, despesas):
    """Entradas e despesas de cada mês lado a lado: verde e vermelho.

    O eixo dos valores começa sempre em zero. Começando noutro ponto, uma
    diferença pequena entre dois meses pareceria enorme.
    """
    plt = _pyplot()
    figura, eixo = plt.subplots(figsize=(9.4, 2.6))

    if not any(entradas) and not any(despesas):
        eixo.text(0.5, 0.5, "Sem lançamentos neste ano", ha="center", va="center",
                  fontsize=9, color=CINZA, transform=eixo.transAxes)
        eixo.axis("off")
        return _para_png(figura)

    posicoes = range(len(rotulos))
    largura = 0.38
    eixo.bar([p - largura / 2 for p in posicoes], entradas, width=largura,
             color=VERDE, label="Entradas", zorder=3)
    eixo.bar([p + largura / 2 for p in posicoes], despesas, width=largura,
             color=VERMELHO, label="Despesas", zorder=3)

    eixo.set_xticks(list(posicoes), rotulos)
    eixo.set_ylim(bottom=0)
    eixo.grid(axis="y", color="#E6EBE8", linewidth=0.8, zorder=0)
    eixo.set_axisbelow(True)

    for lado in ("top", "right", "left", "bottom"):
        eixo.spines[lado].set_visible(False)

    eixo.tick_params(axis="both", length=0, labelsize=9, colors=CINZA)
    eixo.yaxis.set_major_formatter(
        lambda valor, _pos: f"{valor/1000:.0f} mil" if abs(valor) >= 1000 else f"{valor:.0f}"
    )
    eixo.legend(loc="upper left", bbox_to_anchor=(0, 1.18), ncol=2, frameon=False,
                fontsize=8.5, labelcolor=CINZA, handlelength=1, handleheight=1)
    return _para_png(figura)
