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

def converter_valor(texto, ponto_decimal=False):
    """Aceita 'R$ 1.234,56', 'R$ -50,00', '123,45-', '(1.234,56)' e '1,234.56'.

    Devolve float ou None. Sem vírgula, ponto seguido de três dígitos é milhar
    (1.500 = mil e quinhentos), a menos que `ponto_decimal` diga que o ponto é
    sempre decimal, como no OFX.
    """
    texto = (texto or "").strip()
    if not texto:
        return None
    # O sinal pode vir antes ou depois do R$, e alguns bancos o põem no fim.
    negativo = "-" in texto or (texto.startswith("(") and texto.endswith(")"))
    texto = re.sub(r"[R$\s()\-]", "", texto, flags=re.IGNORECASE)
    if "," in texto and "." in texto:
        # O separador que aparece por último é o decimal.
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")   # 1.234,56
        else:
            texto = texto.replace(",", "")                     # 1,234.56
    elif "," in texto:
        texto = (texto.replace(",", "") if texto.count(",") > 1   # 1,234,567
                 else texto.replace(",", "."))                    # 1234,56
    elif not ponto_decimal and re.fullmatch(r"\d{1,3}(\.\d{3})+", texto):
        texto = texto.replace(".", "")                            # 1.500
    try:
        valor = float(texto)
    except ValueError:
        return None
    if not math.isfinite(valor):
        return None   # float() aceita "nan" e "inf", que não são dinheiro
    return -valor if negativo else valor


def _indice_por_palavras(cabecalho, palavras, evitar=()):
    """Primeira coluna com uma das palavras no título e sem nenhuma das `evitar`."""
    for posicao, titulo in enumerate(cabecalho):
        if (any(palavra in titulo for palavra in palavras)
                and not any(palavra in titulo for palavra in evitar)):
            return posicao
    return -1


def _achar_cabecalho(linhas):
    """Procura o cabeçalho nas primeiras linhas: há banco que escreve algo antes dele.

    Devolve (linha do cabeçalho, separador, data, descrição, valor), ou None.
    """
    for posicao, linha in enumerate(linhas[:20]):
        separador = ";" if linha.count(";") >= linha.count(",") else ","
        cabecalho = [c.strip().lower() for c in next(csv.reader([linha], delimiter=separador), [])]
        col_data = _indice_por_palavras(cabecalho, PALAVRAS_DATA)
        # "Data Valor" e "Data Lançamento" são datas, não valor nem descrição.
        col_valor = _indice_por_palavras(cabecalho, PALAVRAS_VALOR, evitar=PALAVRAS_DATA)
        if col_data >= 0 and col_valor >= 0:
            col_descricao = _indice_por_palavras(cabecalho, PALAVRAS_DESCRICAO, evitar=PALAVRAS_DATA)
            if col_descricao < 0:
                # Sem título reconhecido: a primeira coluna que não seja data nem valor.
                livres = [p for p in range(len(cabecalho)) if p not in (col_data, col_valor)]
                col_descricao = livres[0] if livres else -1
            return posicao, separador, col_data, col_descricao, col_valor
    return None


def ler_csv(texto):
    linhas = [l for l in texto.splitlines() if l.strip()]
    if not linhas:
        return []

    achado = _achar_cabecalho(linhas)
    if achado:
        posicao, separador, col_data, col_descricao, col_valor = achado
        primeira_linha = posicao + 1
    else:
        separador = ";" if linhas[0].count(";") >= linhas[0].count(",") else ","
        col_data, col_descricao, col_valor = 0, 1, 2
        primeira_linha = 0
    tabela = list(csv.reader(linhas, delimiter=separador))

    movimentos = []
    for colunas in tabela[primeira_linha:]:
        if len(colunas) <= max(col_data, col_valor):
            continue
        data = converter_data(colunas[col_data])
        valor = converter_valor(colunas[col_valor])
        if data is None or valor is None or valor == 0:
            continue
        descricao = colunas[col_descricao].strip() if 0 <= col_descricao < len(colunas) else ""
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
        valor = converter_valor(campo("TRNAMT"), ponto_decimal=True)
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
