"""Geração dos gráficos em Python (matplotlib), devolvidos como PNG.

Cada função monta a figura na memória e devolve os bytes da imagem,
que as rotas do Flask entregam como se fossem um arquivo.
"""

import io

import matplotlib

matplotlib.use("Agg")  # sem interface gráfica: só gera o arquivo

import matplotlib.pyplot as plt  # noqa: E402

from constantes import CINZA, PRATA, VERDE, VERMELHO  # noqa: E402


def _para_png(figura):
    buffer = io.BytesIO()
    figura.savefig(buffer, format="png", dpi=160, transparent=True,
                   bbox_inches="tight", pad_inches=0.04)
    plt.close(figura)
    buffer.seek(0)
    return buffer.getvalue()


def rosca(fatias):
    """Gráfico de rosca. `fatias` é uma lista de (nome, valor, cor)."""
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
