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
    checar("token novo ainda nao expirou", banco.buscar_token_valido(token_2) is not None)
    checar("token vale por no maximo 1 hora", linha_token["expira_em"] <= banco._instante(60))
    checar("banco guarda so o hash do token", linha_token["token"] != token_2)
    checar("o valor guardado no banco nao abre o link", banco.buscar_token(linha_token["token"]) is None)
    checar("buscar_token nao acha token inventado", banco.buscar_token("inventado") is None)
    conexao = banco.conectar()
    conexao.execute("DELETE FROM usuarios WHERE id = ?", (id_token,))
    conexao.commit()
    checar("apagar o usuario apaga os tokens dele", banco.buscar_token(token_2) is None)


def consegue_entrar(email, senha):
    r = app.test_client().post("/entrar", data={"modo": "login", "email": email, "senha": senha})
    return r.status_code == 302


# --- recuperação de senha
with app.test_request_context():
    id_rec = banco.criar_usuario("rec@a.com", "senha-antiga")

anonimo = app.test_client()
checar("tela de recuperar abre", anonimo.get("/recuperar").status_code == 200)
checar("login tem link para recuperar", "/recuperar" in anonimo.get("/entrar").get_data(as_text=True))
r_existe = anonimo.post("/recuperar", data={"email": "rec@a.com"})
r_nao_existe = anonimo.post("/recuperar", data={"email": "ninguem@a.com"})
checar("recuperar mostra a mensagem combinada",
       "Se existir uma conta com esse e-mail" in r_existe.get_data(as_text=True))
checar("resposta igual para e-mail existente e inexistente",
       r_existe.status_code == r_nao_existe.status_code and r_existe.data == r_nao_existe.data)

with app.test_request_context():
    conexao = banco.conectar()
    pedidos = conexao.execute(
        "SELECT usuario_id FROM tokens_recuperacao WHERE usuario_id = ?", (id_rec,)).fetchall()
    total = conexao.execute("SELECT COUNT(*) AS n FROM tokens_recuperacao").fetchone()["n"]
checar("pedido cria token so para a conta que existe", len(pedidos) == 1 and total == 1)

with app.test_request_context():
    token = banco.criar_token(id_rec)
checar("token valido abre o formulario", anonimo.get(f"/recuperar/{token}").status_code == 200)

r = anonimo.post(f"/recuperar/{token}", data={"senha": "123", "confirmacao": "123"})
checar("senha curta recusada na recuperacao",
       "6 ou mais" in r.get_data(as_text=True) and consegue_entrar("rec@a.com", "senha-antiga"))
r = anonimo.post(f"/recuperar/{token}", data={"senha": "senha-nova", "confirmacao": "outra-coisa"})
checar("confirmacao diferente recusada na recuperacao",
       "confirmação" in r.get_data(as_text=True) and consegue_entrar("rec@a.com", "senha-antiga"))

r = anonimo.post(f"/recuperar/{token}", data={"senha": "senha-nova", "confirmacao": "senha-nova"})
checar("token valido troca a senha", r.status_code == 302 and "/entrar" in r.headers.get("Location", ""))
checar("senha nova entra depois da recuperacao", consegue_entrar("rec@a.com", "senha-nova"))
checar("senha antiga nao entra depois da recuperacao", not consegue_entrar("rec@a.com", "senha-antiga"))
checar("aviso de sucesso aparece no login",
       "Senha alterada" in anonimo.get("/entrar").get_data(as_text=True))
with app.test_request_context():
    checar("senha nao fica em texto puro", banco.conectar().execute(
        "SELECT senha_hash FROM usuarios WHERE id = ?", (id_rec,)).fetchone()["senha_hash"] != "senha-nova")

r = anonimo.post(f"/recuperar/{token}", data={"senha": "invasor123", "confirmacao": "invasor123"})
checar("token ja usado recusado", r.status_code == 400 and not consegue_entrar("rec@a.com", "invasor123"))
checar("token ja usado nem abre o formulario", anonimo.get(f"/recuperar/{token}").status_code == 400)

with app.test_request_context():
    token = banco.criar_token(id_rec)
    conexao = banco.conectar()
    conexao.execute("UPDATE tokens_recuperacao SET expira_em = ? WHERE usuario_id = ?",
                    (banco._instante(-1), id_rec))
    conexao.commit()
r = anonimo.post(f"/recuperar/{token}", data={"senha": "invasor123", "confirmacao": "invasor123"})
checar("token expirado ha um minuto recusado",
       r.status_code == 400 and not consegue_entrar("rec@a.com", "invasor123"))

with app.test_request_context():
    conexao = banco.conectar()
    conexao.execute("UPDATE tokens_recuperacao SET expira_em = ? WHERE usuario_id = ?",
                    (banco._instante(1), id_rec))
    conexao.commit()
checar("token vale ate o ultimo minuto da validade", anonimo.get(f"/recuperar/{token}").status_code == 200)

r = anonimo.post("/recuperar/inventado", data={"senha": "invasor123", "confirmacao": "invasor123"})
checar("token inventado recusado", r.status_code == 400 and not consegue_entrar("rec@a.com", "invasor123"))

# se a gravação da senha falhar no meio, o token não pode ser perdido
gravar_de_verdade = banco._gravar_senha


def gravar_com_falha(*_args):
    raise RuntimeError("falha simulada")


banco._gravar_senha = gravar_com_falha
try:
    with app.test_request_context():
        banco.redefinir_senha(token, "senha-perdida")
except RuntimeError:
    pass
banco._gravar_senha = gravar_de_verdade
checar("falha ao gravar a senha nao queima o token",
       anonimo.get(f"/recuperar/{token}").status_code == 200)

# --- troca de senha em Configurações
c_troca = app.test_client()
c_troca.post("/entrar", data={"modo": "cadastro", "email": "troca@a.com", "senha": "senha-antiga"})


def trocar(atual, nova, confirmacao):
    r = c_troca.post("/configuracoes", follow_redirects=True, data={
        "acao": "trocar_senha", "senha_atual": atual, "senha_nova": nova, "confirmacao": confirmacao})
    return r.get_data(as_text=True)


corpo = trocar("errada", "senha-nova", "senha-nova")
checar("senha atual errada recusada",
       "senha atual está incorreta" in corpo and not consegue_entrar("troca@a.com", "senha-nova"))
corpo = trocar("senha-antiga", "senha-nova", "outra-coisa")
checar("confirmacao diferente recusada",
       "confirmação" in corpo and not consegue_entrar("troca@a.com", "senha-nova"))
corpo = trocar("senha-antiga", "12345", "12345")
checar("senha curta demais recusada",
       "6 ou mais" in corpo and not consegue_entrar("troca@a.com", "12345"))
checar("senha antiga segue valendo apos as recusas", consegue_entrar("troca@a.com", "senha-antiga"))

with app.test_request_context():
    token = banco.criar_token(banco.buscar_usuario_por_email("troca@a.com")["id"])
corpo = trocar("senha-antiga", "senha-nova", "senha-nova")
checar("troca de senha confirma o sucesso", "Senha alterada" in corpo)
checar("senha antiga nao entra apos a troca", not consegue_entrar("troca@a.com", "senha-antiga"))
checar("senha nova entra apos a troca", consegue_entrar("troca@a.com", "senha-nova"))
checar("trocar a senha cancela link de recuperacao pendente",
       app.test_client().get(f"/recuperar/{token}").status_code == 400)

# --- exclusão de conta
TABELAS_DO_USUARIO = {"categorias": "usuario_id", "lancamentos": "usuario_id", "metas": "usuario_id",
                      "tokens_recuperacao": "usuario_id", "usuarios": "id"}


def contar_linhas(usuario_id):
    with app.test_request_context():
        conexao = banco.conectar()
        return {tabela: conexao.execute(
            f"SELECT COUNT(*) AS n FROM {tabela} WHERE {coluna} = ?", (usuario_id,)).fetchone()["n"]
            for tabela, coluna in TABELAS_DO_USUARIO.items()}


def criar_conta_com_dados(email):
    cliente = app.test_client()
    cliente.post("/entrar", data={"modo": "cadastro", "email": email, "senha": "senha123"})
    cliente.post("/perfil", data={"perfil": "generico"})
    with app.test_request_context():
        usuario_id = banco.buscar_usuario_por_email(email)["id"]
        despesa = banco.listar_categorias(usuario_id, "despesa")[0]["id"]
        banco.criar_token(usuario_id)
    cliente.post("/lancamento/novo", data={"categoria_id": despesa, "valor": "50,00",
                                           "data": hoje, "descricao": "Compra", "repetir": "1"})
    cliente.post("/meta/nova", data={"categoria_id": despesa, "valor_limite": "100,00"})
    return cliente, usuario_id


c_sai, id_sai = criar_conta_com_dados("sai@a.com")
_, id_fica = criar_conta_com_dados("fica@a.com")
antes_sai, antes_fica = contar_linhas(id_sai), contar_linhas(id_fica)
checar("conta a excluir comeca com dados em todas as tabelas", all(antes_sai.values()))

r = c_sai.post("/configuracoes", follow_redirects=True, data={"acao": "excluir_conta", "senha": "errada"})
checar("exclusao com senha errada recusada",
       "não foi excluída" in r.get_data(as_text=True) and contar_linhas(id_sai) == antes_sai)
c_sai.post("/configuracoes", data={"acao": "excluir_conta"})
checar("exclusao sem senha recusada", contar_linhas(id_sai) == antes_sai)

r = c_sai.post("/configuracoes", data={"acao": "excluir_conta", "senha": "senha123"})
checar("exclusao manda para o login", r.status_code == 302 and "/entrar" in r.headers.get("Location", ""))
checar("nada sobra em nenhuma tabela", not any(contar_linhas(id_sai).values()))
checar("a conta de outro usuario continua intacta", contar_linhas(id_fica) == antes_fica)
checar("outro usuario continua entrando", consegue_entrar("fica@a.com", "senha123"))
checar("conta excluida nao entra mais", not consegue_entrar("sai@a.com", "senha123"))
checar("aviso de exclusao aparece no login", "foi excluída" in c_sai.get("/entrar").get_data(as_text=True))
checar("sessao encerrada apos a exclusao", "/entrar" in c_sai.get("/").headers.get("Location", ""))

_, id_sem_fk = criar_conta_com_dados("semfk@a.com")
with app.test_request_context():
    banco.conectar().execute("PRAGMA foreign_keys = OFF")
    banco.excluir_conta(id_sem_fk)
checar("exclusao apaga tudo mesmo sem chaves estrangeiras", not any(contar_linhas(id_sem_fk).values()))

print(f"\n{n - len(falhas)}/{n} verificacoes passaram")
if falhas:
    print("FALHAS:", *falhas, sep="\n  - ")
    sys.exit(1)
print("tudo certo")
