"""Leitura de extratos bancários nos formatos CSV e OFX.

Cada banco exporta de um jeito, então a leitura é tolerante: descobre o
separador, procura as colunas pelo nome do cabeçalho e aceita datas e
valores em formatos diferentes.
"""

import csv
import io
import math
import re
from datetime import date

PALAVRAS_DATA = ("data", "date")
PALAVRAS_DESCRICAO = ("desc", "histor", "memo", "lancamento", "lançamento")
PALAVRAS_VALOR = ("valor", "amount", "montante")


def converter_data(texto):
    """Aceita 2026-09-14, 14/09/2026, 14-09-2026 e 14/09/26. Devolve 'AAAA-MM-DD' ou None."""
    texto = (texto or "").strip()
    if achado := re.match(r"^(\d{4})-(\d{2})-(\d{2})", texto):
        ano, mes, dia = achado.groups()
    elif achado := re.match(r"^(\d{2})[/-](\d{2})[/-](\d{4})", texto):
        dia, mes, ano = achado.groups()
    elif achado := re.match(r"^(\d{2})/(\d{2})/(\d{2})$", texto):
        dia, mes, ano2 = achado.groups()
        ano = f"20{ano2}"
    else:
        return None
    try:
        date(int(ano), int(mes), int(dia))
    except ValueError:
        return None   # data que não existe, como 31/02
    return f"{ano}-{mes}-{dia}"

def converter_valor(texto):
    """Aceita 'R$ 1.234,56', '-1234.56' e '(1.234,56)'. Devolve float ou None."""
    texto = (texto or "").strip()
    if not texto:
        return None
    negativo = texto.startswith("-") or (texto.startswith("(") and texto.endswith(")"))
    texto = re.sub(r"[R$\s()\-]", "", texto, flags=re.IGNORECASE)
    if "," in texto and "." in texto:
        texto = texto.replace(".", "").replace(",", ".")   # 1.234,56
    elif "," in texto:
        texto = texto.replace(",", ".")                     # 1234,56
    try:
        valor = float(texto)
    except ValueError:
        return None
    if not math.isfinite(valor):
        return None   # float() aceita "nan" e "inf", que não são dinheiro
    return -valor if negativo else valor


def _indice_por_palavras(cabecalho, palavras):
    for posicao, titulo in enumerate(cabecalho):
        if any(palavra in titulo for palavra in palavras):
            return posicao
    return -1


def ler_csv(texto):
    linhas = [l for l in texto.splitlines() if l.strip()]
    if not linhas:
        return []

    separador = ";" if linhas[0].count(";") >= linhas[0].count(",") else ","
    tabela = list(csv.reader(linhas, delimiter=separador))

    cabecalho = [c.strip().lower() for c in tabela[0]]
    col_data = _indice_por_palavras(cabecalho, PALAVRAS_DATA)
    col_valor = _indice_por_palavras(cabecalho, PALAVRAS_VALOR)
    tem_cabecalho = col_data >= 0 and col_valor >= 0

    if tem_cabecalho:
        col_descricao = _indice_por_palavras(cabecalho, PALAVRAS_DESCRICAO)
        if col_descricao < 0:
            col_descricao = 1
        primeira_linha = 1
    else:
        col_data, col_descricao, col_valor = 0, 1, 2
        primeira_linha = 0

    movimentos = []
    for colunas in tabela[primeira_linha:]:
        if len(colunas) <= max(col_data, col_valor):
            continue
        data = converter_data(colunas[col_data])
        valor = converter_valor(colunas[col_valor])
        if data is None or valor is None or valor == 0:
            continue
        descricao = colunas[col_descricao].strip() if col_descricao < len(colunas) else ""
        movimentos.append({
            "data": data,
            "descricao": descricao,
            "valor": abs(valor),
            "tipo": "entrada" if valor > 0 else "despesa",
        })
    return movimentos


def ler_ofx(texto):
    """O OFX marca cada movimentação com <STMTTRN>."""
    movimentos = []
    for bloco in re.split(r"<STMTTRN>", texto, flags=re.IGNORECASE)[1:]:
        bloco = re.split(r"</STMTTRN>|<STMTTRN>", bloco, flags=re.IGNORECASE)[0]

        def campo(etiqueta):
            achado = re.search(rf"<{etiqueta}>([^<\r\n]+)", bloco, flags=re.IGNORECASE)
            return achado.group(1).strip() if achado else ""

        carimbo = campo("DTPOSTED")
        data = converter_data(f"{carimbo[0:4]}-{carimbo[4:6]}-{carimbo[6:8]}")
        valor = converter_valor(campo("TRNAMT"))
        if data is None or valor is None or valor == 0:
            continue
        movimentos.append({
            "data": data,
            "descricao": campo("MEMO") or campo("NAME"),
            "valor": abs(valor),
            "tipo": "entrada" if valor > 0 else "despesa",
        })
    return movimentos


def ler_extrato(nome_arquivo, conteudo):
    """Escolhe o leitor pela extensão do arquivo enviado."""
    if isinstance(conteudo, bytes):
        for codificacao in ("utf-8-sig", "latin-1"):
            try:
                texto = conteudo.decode(codificacao)
                break
            except UnicodeDecodeError:
                continue
        else:
            return []
    else:
        texto = conteudo

    if nome_arquivo.lower().endswith(".ofx"):
        return ler_ofx(texto)
    return ler_csv(texto)
