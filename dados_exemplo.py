"""Preenche o sistema com dados de demonstração.

Serve para apresentar o projeto sem precisar digitar tudo na hora.
Rode uma vez, com o servidor parado:

    python dados_exemplo.py

Depois entre com:  demo@fluxo.local  /  demo1234
"""

import random
from datetime import date

import banco
from app import app

EMAIL_DEMO = "demo@fluxo.local"
SENHA_DEMO = "demo1234"

# quanto costuma entrar e sair por categoria, para os números fazerem sentido
ENTRADAS = {"Projetos": (6000, 14000), "Comissão": (1200, 4000),
            "Acompanhamento de Projeto": (800, 2500)}
DESPESAS = {"Aluguel do Escritório": (2800, 2800), "Materiais e Impressões": (300, 1400),
            "Transporte": (200, 900), "Marketing": (400, 1200),
            "Impostos": (900, 2200), "Outros": (100, 600)}

DESCRICOES = ["Casa Verde", "Reforma Centro", "Apartamento Beira-Mar",
              "Escritório Vila Nova", "Consultoria", ""]


def mes_anterior(ano, mes, quantos):
    total = (ano * 12 + mes - 1) - quantos
    return total // 12, total % 12 + 1


def main():
    banco.criar_tabelas()

    with app.app_context():
        usuario_id = banco.autenticar(EMAIL_DEMO, SENHA_DEMO)
        if usuario_id is None:
            usuario_id = banco.criar_usuario(EMAIL_DEMO, SENHA_DEMO)
            if usuario_id is None:
                print("Já existe uma conta com esse e-mail e a senha é outra. "
                      "Apague o fluxo.db ou troque o EMAIL_DEMO.")
                return

        banco.apagar_dados(usuario_id)
        banco.aplicar_perfil(usuario_id, "arquiteto")

        por_nome = {c["nome"]: c["id"]
                    for c in banco.listar_categorias(usuario_id)}

        random.seed(7)   # sempre gera os mesmos números
        hoje = date.today()
        total = 0

        for atras in range(5, -1, -1):          # seis meses, do mais antigo ao atual
            ano, mes = mes_anterior(hoje.year, hoje.month, atras)

            for nome, (minimo, maximo) in ENTRADAS.items():
                for _ in range(random.randint(1, 3)):
                    banco.criar_lancamento(
                        usuario_id, "entrada", por_nome[nome],
                        round(random.uniform(minimo, maximo), 2),
                        f"{ano:04d}-{mes:02d}-{random.randint(2, 27):02d}",
                        random.choice(DESCRICOES))
                    total += 1

            for nome, (minimo, maximo) in DESPESAS.items():
                banco.criar_lancamento(
                    usuario_id, "despesa", por_nome[nome],
                    round(random.uniform(minimo, maximo), 2),
                    f"{ano:04d}-{mes:02d}-{random.randint(2, 27):02d}", "")
                total += 1

        banco.salvar_meta(usuario_id, por_nome["Aluguel do Escritório"], 3000)
        banco.salvar_meta(usuario_id, por_nome["Transporte"], 700)
        banco.salvar_meta(usuario_id, por_nome["Marketing"], 900)

    print(f"Pronto: {total} lançamentos em 6 meses.")
    print(f"Entre com {EMAIL_DEMO} / {SENHA_DEMO}")


if __name__ == "__main__":
    main()
