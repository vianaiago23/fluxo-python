"""Cálculos sobre os lançamentos: evolução do saldo e o comentário do mês."""

import banco
from constantes import MESES, MESES_CURTOS, formatar_reais


def mes_anterior(ano, mes):
    return (ano - 1, 12) if mes == 1 else (ano, mes - 1)


def resumo_do_mes(usuario_id, ano, mes):
    entradas = banco.somar_mes(usuario_id, ano, mes, "entrada")
    despesas = banco.somar_mes(usuario_id, ano, mes, "despesa")
    # Arredonda: 0,30 - (0,10 + 0,20) daria -0,00000000000000006 em ponto flutuante.
    return entradas, despesas, round(entradas - despesas, 2)


def resumo_do_ano(usuario_id, ano):
    """Os doze meses do ano, com entradas, despesas e saldo, e o total do ano.

    Começa com os doze meses zerados e preenche com o que veio do banco:
    montar só com o que voltou faria os meses vazios sumirem da tabela.
    """
    meses = [{"mes": numero, "nome": MESES[numero - 1], "curto": MESES_CURTOS[numero - 1],
              "entradas": 0.0, "despesas": 0.0}
             for numero in range(1, 13)]
    for linha in banco.somar_ano(usuario_id, ano):
        meses[linha["mes"] - 1].update(entradas=linha["entradas"], despesas=linha["despesas"])
    for mes in meses:
        mes["saldo"] = round(mes["entradas"] - mes["despesas"], 2)

    total = {chave: round(sum(m[chave] for m in meses), 2)
             for chave in ("entradas", "despesas", "saldo")}
    return meses, total


def serie_saldo(usuario_id, ano, mes, quantidade=6):
    """Saldo dos últimos meses, do mais antigo para o mais recente."""
    rotulos, valores = [], []
    ano_atual, mes_atual = ano, mes
    for _ in range(quantidade):
        rotulos.append(MESES_CURTOS[mes_atual - 1])
        _, _, saldo = resumo_do_mes(usuario_id, ano_atual, mes_atual)
        valores.append(round(saldo, 2))
        ano_atual, mes_atual = mes_anterior(ano_atual, mes_atual)
    return list(reversed(rotulos)), list(reversed(valores))


def montar_insight(usuario_id, ano, mes):
    """Frase curta destacando o que mais chama atenção no mês."""
    entradas, despesas, saldo = resumo_do_mes(usuario_id, ano, mes)
    if entradas == 0 and despesas == 0:
        return "Comece registrando as entradas e despesas deste mês para ver seus números aqui."

    ano_ant, mes_ant = mes_anterior(ano, mes)
    atuais = {l["id"]: l for l in banco.total_por_categoria(usuario_id, ano, mes, "despesa")}
    anteriores = {l["id"]: l for l in banco.total_por_categoria(usuario_id, ano_ant, mes_ant, "despesa")}

    maior_alta = None
    for categoria_id, atual in atuais.items():
        antes = anteriores.get(categoria_id)
        if not antes or antes["total"] <= 0 or atual["total"] <= antes["total"]:
            continue
        alta = (atual["total"] - antes["total"]) / antes["total"] * 100
        if alta > 15 and (maior_alta is None or alta > maior_alta[1]):
            maior_alta = (atual["nome"], alta)

    if maior_alta:
        nome, alta = maior_alta
        return (f"Seus gastos com {nome} subiram {alta:.0f}% "
                f"em relação a {MESES[mes_ant - 1]}.")

    if saldo < 0:
        return (f"As despesas superaram as entradas em "
                f"{formatar_reais(abs(saldo))} este mês.")

    _, _, saldo_anterior = resumo_do_mes(usuario_id, ano_ant, mes_ant)
    if saldo_anterior != 0 and saldo > saldo_anterior:
        return (f"Você guardou {formatar_reais(saldo)} este mês, "
                f"{formatar_reais(saldo - saldo_anterior)} a mais que em "
                f"{MESES[mes_ant - 1]}.")

    return (f"Você guardou {formatar_reais(saldo)} este mês. "
            f"Considere reservar uma parte como reserva de emergência.")
