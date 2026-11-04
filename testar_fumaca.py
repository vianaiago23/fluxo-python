"""Teste de fumaça: percorre o sistema inteiro no banco local (SQLite em arquivo).

Roda contra um banco temporário, nunca contra o fluxo.db do dia a dia.
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
os.environ.pop("TURSO_DATABASE_URL", None)   # garante o modo local

import banco                                  # noqa: E402
TEMP = Path(tempfile.mkdtemp()) / "teste.db"
banco.CAMINHO_BANCO = TEMP                    # desvia para o banco temporário

import constantes                             # noqa: E402
from app import app                           # noqa: E402

app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
falhas = []
n = 0


def checar(rotulo, condicao):
    global n
    n += 1
    if condicao:
        print(f"  ok   {rotulo}")
    else:
        print(f"  FALHA {rotulo}")
        falhas.append(rotulo)


print("modo:", "nuvem" if banco.NA_NUVEM else "local (arquivo)")
checar("banco local, nao na nuvem", banco.NA_NUVEM is False)
from datetime import datetime  # noqa: E402
checar("hoje() usa o fuso de Brasilia",
       constantes.hoje() == datetime.now(constantes.FUSO_BRASIL).date())

c = app.test_client()

# --- cadastro
r = c.post("/entrar", data={"modo": "cadastro", "email": "a@a.com", "senha": "senha123"})
checar("cadastro redireciona para o perfil", r.headers.get("Location", "").endswith("/perfil"))

r = c.post("/perfil", data={"perfil": "arquiteto"})
checar("perfil aplicado, vai para o painel", r.headers.get("Location", "") in ("/", "http://localhost/"))

# --- categorias criadas pelo perfil
with app.test_request_context():
    from flask import g, session as sessao
    sessao["usuario_id"] = 1
    entradas = banco.listar_categorias(1, "entrada")
    despesas = banco.listar_categorias(1, "despesa")
checar("categorias de entrada criadas", len(entradas) == 3)
checar("categorias de despesa criadas", len(despesas) == 6)
checar("linha acessivel por nome de coluna", entradas[0]["nome"] == "Projetos")
checar("dict(linha) funciona", isinstance(dict(entradas[0]), dict))

id_entrada, id_despesa = entradas[0]["id"], despesas[0]["id"]

# --- lançamentos
hoje = constantes.hoje().isoformat()
r = c.post("/lancamento/novo", data={"categoria_id": id_entrada, "valor": "1.500,00",
                                     "data": hoje, "descricao": "Projeto X", "repetir": "1"})
checar("lancamento de entrada salvo", r.status_code in (200, 302))
r = c.post("/lancamento/novo", data={"categoria_id": id_despesa, "valor": "400,50",
                                     "data": hoje, "descricao": "Aluguel", "repetir": "1"})
checar("lancamento de despesa salvo", r.status_code in (200, 302))

r = c.get("/")
corpo = r.get_data(as_text=True)
checar("painel abre", r.status_code == 200)
checar("painel mostra a entrada", "Projeto X" in corpo)
checar("painel mostra a despesa", "Aluguel" in corpo)
checar("painel mostra o saldo 1.099,50", "1.099,50" in corpo)

# --- edição (não deve duplicar)
with app.test_request_context():
    lancs = banco.listar_todos_lancamentos(1)
checar("dois lancamentos no banco", len(lancs) == 2)
alvo = [l for l in lancs if l["descricao"] == "Projeto X"][0]
c.post(f"/lancamento/{alvo['id']}/editar", data={"categoria_id": id_entrada, "valor": "2.000,00",
                                                 "data": hoje, "descricao": "Projeto Y", "repetir": "1"})
with app.test_request_context():
    lancs = banco.listar_todos_lancamentos(1)
checar("edicao nao duplicou", len(lancs) == 2)
checar("edicao alterou a descricao", any(l["descricao"] == "Projeto Y" for l in lancs))

# --- meta
r = c.post("/meta/nova", data={"categoria_id": id_despesa, "valor_limite": "1.000,00"})
with app.test_request_context():
    metas = banco.listar_metas(1, constantes.hoje().year, constantes.hoje().month)
checar("meta criada", len(metas) == 1)

# --- gráficos (matplotlib) e PDF (fpdf2)
for tipo in ("entradas", "despesas", "saldo"):
    r = c.get(f"/grafico/{tipo}.png")
    checar(f"grafico {tipo} gera PNG", r.status_code == 200 and r.data[:4] == b"\x89PNG")

r = c.get("/relatorio.pdf")
checar("relatorio gera PDF", r.status_code == 200 and r.data[:4] == b"%PDF")

# --- isolamento entre contas
c2 = app.test_client()
c2.post("/entrar", data={"modo": "cadastro", "email": "b@b.com", "senha": "senha123"})
c2.post("/perfil", data={"perfil": "generico"})
corpo2 = c2.get("/").get_data(as_text=True)
checar("conta nova nao ve dados da outra", "Projeto Y" not in corpo2 and "Aluguel" not in corpo2)
r = c2.post(f"/lancamento/{alvo['id']}/excluir")
with app.test_request_context():
    lancs = banco.listar_todos_lancamentos(1)
checar("outra conta nao apaga lancamento alheio", len(lancs) == 2)

# --- e-mail duplicado
r = c.post("/entrar", data={"modo": "cadastro", "email": "a@a.com", "senha": "senha123"})
with app.test_request_context():
    checar("ErroIntegridade capturado (e-mail repetido)", banco.criar_usuario("a@a.com", "x123456") is None)

# --- login e logout
c3 = app.test_client()
r = c3.post("/entrar", data={"modo": "login", "email": "a@a.com", "senha": "senha123"})
checar("login funciona", r.headers.get("Location", "") in ("/", "http://localhost/"))
c3.get("/sair")
r = c3.post("/entrar", data={"modo": "login", "email": "a@a.com", "senha": "errada"})
checar("senha errada barrada", r.status_code == 200 and "incorretos" in r.get_data(as_text=True))
r = c3.get("/")
checar("sem login redireciona para /entrar", "/entrar" in r.headers.get("Location", ""))

# --- tokens de recuperação
with app.test_request_context():
    id_token = banco.criar_usuario("token@a.com", "senha123")
    token_1 = banco.criar_token(id_token)
    token_2 = banco.criar_token(id_token)
    checar("criar_token gera textos diferentes", token_1 != token_2)
    checar("pedido novo cancela o token anterior", banco.buscar_token(token_1) is None)
    linha_token = banco.buscar_token(token_2)
    checar("buscar_token acha o dono do token", linha_token["usuario_id"] == id_token)
    checar("token novo nasce sem uso", linha_token["usado"] == 0)
    checar("token novo ainda nao expirou", linha_token["expira_em"] > constantes.hoje().isoformat())
    checar("buscar_token nao acha token inventado", banco.buscar_token("inventado") is None)
    conexao = banco.conectar()
    conexao.execute("DELETE FROM usuarios WHERE id = ?", (id_token,))
    conexao.commit()
    checar("apagar o usuario apaga os tokens dele", banco.buscar_token(token_2) is None)

print(f"\n{n - len(falhas)}/{n} verificacoes passaram")
if falhas:
    print("FALHAS:", *falhas, sep="\n  - ")
    sys.exit(1)
print("tudo certo")
