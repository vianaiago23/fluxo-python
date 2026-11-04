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
    checar("pedido novo nao derruba o link anterior", banco.buscar_token_valido(token_1) is not None)
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

# publicado, sem envio de e-mail, a recuperação fica fora do ar
modulo_app = sys.modules["app"]
modulo_app.RECUPERACAO_DISPONIVEL = False
checar("sem envio de e-mail, o login nao oferece o link",
       "/recuperar" not in anonimo.get("/entrar").get_data(as_text=True))
r = anonimo.post("/recuperar", data={"email": "rec@a.com"})
checar("sem envio de e-mail, /recuperar volta para o login",
       r.status_code == 302 and "/entrar" in r.headers.get("Location", ""))
with app.test_request_context():
    checar("sem envio de e-mail, nenhum token e criado", not banco.pedido_recente(id_rec))
modulo_app.RECUPERACAO_DISPONIVEL = True

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


def tokens_da_conta(usuario_id):
    with app.test_request_context():
        return banco.conectar().execute(
            "SELECT COUNT(*) AS n FROM tokens_recuperacao WHERE usuario_id = ?", (usuario_id,)
        ).fetchone()["n"]


r_repetido = anonimo.post("/recuperar", data={"email": "rec@a.com"})
checar("pedido repetido em seguida nao gera outro link", tokens_da_conta(id_rec) == 1)
checar("pedido repetido recebe a mesma resposta", r_repetido.data == r_existe.data)

with app.test_request_context():
    conexao = banco.conectar()
    conexao.execute("UPDATE tokens_recuperacao SET expira_em = ? WHERE usuario_id = ?",
                    (banco._instante(banco.MINUTOS_VALIDADE_TOKEN - banco.MINUTOS_ENTRE_PEDIDOS - 1), id_rec))
    conexao.commit()
anonimo.post("/recuperar", data={"email": "rec@a.com"})
checar("passado o intervalo, a conta pode pedir de novo", tokens_da_conta(id_rec) == 2)

with app.test_request_context():
    conexao = banco.conectar()
    conexao.execute("UPDATE tokens_recuperacao SET expira_em = ? WHERE usuario_id = ?",
                    (constantes.hoje().isoformat(), id_rec))
    conexao.commit()
    checar("token antigo, so com a data, nao trava pedido novo", not banco.pedido_recente(id_rec))
    conexao = banco.conectar()
    conexao.execute("DELETE FROM tokens_recuperacao WHERE usuario_id = ?", (id_rec,))
    conexao.commit()

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

# --- trocar a senha encerra as outras sessões
def esta_logado(cliente):
    return cliente.get("/configuracoes").status_code == 200


def login_em_cliente_novo(email, senha):
    cliente = app.test_client()
    cliente.post("/entrar", data={"modo": "login", "email": email, "senha": senha})
    return cliente


outro_aparelho = login_em_cliente_novo("troca@a.com", "senha-nova")
checar("segunda sessao comeca logada", esta_logado(outro_aparelho))
corpo = trocar("senha-nova", "senha-terceira", "senha-terceira")
checar("quem trocou a senha continua logado", "Senha alterada" in corpo and esta_logado(c_troca))
checar("troca de senha derruba a outra sessao", not esta_logado(outro_aparelho))

outro_aparelho = login_em_cliente_novo("troca@a.com", "senha-terceira")
with app.test_request_context():
    token = banco.criar_token(banco.buscar_usuario_por_email("troca@a.com")["id"])
app.test_client().post(f"/recuperar/{token}", data={"senha": "senha-quarta", "confirmacao": "senha-quarta"})
checar("recuperacao de senha derruba as sessoes abertas", not esta_logado(outro_aparelho))

with app.test_request_context():
    id_sem_marca = banco.buscar_usuario_por_email("troca@a.com")["id"]
sem_marca = app.test_client()
with sem_marca.session_transaction() as sessao_antiga:
    sessao_antiga["usuario_id"] = id_sem_marca
checar("sessao sem a marca da senha nao vale", not esta_logado(sem_marca))

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


# ======================================================================
# PESSOA 4 — funções de apoio para os testes dos itens 27 a 32
# ======================================================================
import io                                     # noqa: E402


def conta_limpa(email, perfil="arquiteto"):
    """Cria uma conta nova, já com as categorias do perfil. Devolve (cliente, id)."""
    cliente = app.test_client()
    cliente.post("/entrar", data={"modo": "cadastro", "email": email, "senha": "senha123"})
    cliente.post("/perfil", data={"perfil": perfil})
    with app.test_request_context():
        usuario_id = banco.buscar_usuario_por_email(email)["id"]
    return cliente, usuario_id


def tentar(acao):
    """Roda a ação. Se o servidor estourar erro, devolve None em vez de parar o teste."""
    try:
        return acao()
    except Exception:
        return None


def sem_estouro(resposta):
    return resposta is not None and resposta.status_code < 500


def total_lancamentos(usuario_id):
    with app.test_request_context():
        return len(banco.listar_todos_lancamentos(usuario_id))


def datas_de(usuario_id, descricao):
    with app.test_request_context():
        return [l["data"] for l in banco.listar_todos_lancamentos(usuario_id)
                if l["descricao"] == descricao]


# ======================================================================
# ITEM 27 — importação de extrato em CSV
# ======================================================================
import extrato as leitor                      # noqa: E402

csv_br = ("Data;Descrição;Valor\n"
          "14/09/2026;Mercado;-1.234,56\n"
          "15/09/2026;Salário;5000,00\n"
          "16/09/26;Café;-12,50\n")
lidos = leitor.ler_csv(csv_br)
checar("csv (;) le as 3 linhas", len(lidos) == 3)
checar("csv (;) data DD/MM/AAAA vira AAAA-MM-DD", lidos[0]["data"] == "2026-09-14")
checar("csv (;) data com ano de 2 digitos", lidos[2]["data"] == "2026-09-16")
checar("csv (;) valor com milhar e virgula decimal", lidos[0]["valor"] == 1234.56)
checar("csv (;) valor negativo vira despesa", lidos[0]["tipo"] == "despesa")
checar("csv (;) valor positivo vira entrada", lidos[1]["tipo"] == "entrada")
checar("csv (;) descricao mantem o acento", lidos[1]["descricao"] == "Salário")
checar("csv (;) o valor guardado e sempre positivo", all(l["valor"] > 0 for l in lidos))

csv_us = ("date,description,amount\n"
          "2026-09-14,Mercado,-50.25\n"
          "2026-09-15,Pix recebido,100.00\n")
lidos = leitor.ler_csv(csv_us)
checar("csv (,) le as 2 linhas", len(lidos) == 2)
checar("csv (,) data AAAA-MM-DD fica igual", lidos[0]["data"] == "2026-09-14")
checar("csv (,) valor com ponto decimal", lidos[0]["valor"] == 50.25 and lidos[0]["tipo"] == "despesa")
checar("csv (,) entrada com ponto decimal", lidos[1]["valor"] == 100.0 and lidos[1]["tipo"] == "entrada")

lidos = leitor.ler_csv("Data;Histórico;Valor\n01/10/2026;Conta de luz;(R$ 230,90)\n"
                       "02/10/2026;Cliente;R$ 1.000,00\n")
checar("csv: valor entre parenteses e despesa", lidos[0]["valor"] == 230.9 and lidos[0]["tipo"] == "despesa")
checar("csv: R$ com milhar e entrada", lidos[1]["valor"] == 1000.0 and lidos[1]["tipo"] == "entrada")
checar("csv: coluna 'Histórico' vira a descricao", lidos[0]["descricao"] == "Conta de luz")

lidos = leitor.ler_csv("14/09/2026;Padaria;-8,00\n15/09/2026;Pix;20,00\n")
checar("csv sem cabecalho le data, descricao e valor", len(lidos) == 2 and lidos[0]["descricao"] == "Padaria")

lidos = leitor.ler_csv("Data;Descrição;Valor\n\n14/09/2026;A;-1,00\n\n\n15/09/2026;B;2,00\n")
checar("csv ignora linhas em branco", len(lidos) == 2)

lidos = leitor.ler_csv("Valor;Descrição;Data\n-9,90;Lanche;14/09/2026\n")
checar("csv com as colunas em outra ordem", lidos[0]["data"] == "2026-09-14" and lidos[0]["valor"] == 9.9)

bruto = "Data;Descrição;Valor\n14/09/2026;Pão;-3,50\n".encode("latin-1")
lidos = leitor.ler_extrato("banco.csv", bruto)
checar("arquivo CSV em latin-1 mantem o acento", len(lidos) == 1 and lidos[0]["descricao"] == "Pão")
bruto = "Data;Descrição;Valor\n14/09/2026;Pão;-3,50\n".encode("utf-8-sig")
lidos = leitor.ler_extrato("banco.csv", bruto)
checar("arquivo CSV em UTF-8 com BOM le o cabecalho", len(lidos) == 1 and lidos[0]["descricao"] == "Pão")

# Os dois checks abaixo apontam fragilidades reais do extrato.py
checar("csv: data com traco no formato DD-MM-AAAA",
       len(leitor.ler_csv("Data;Descrição;Valor\n14-09-2026;Mercado;-10,00\n")) == 1)
checar("csv: data impossivel (31/02) e recusada",
       leitor.ler_csv("Data;Descrição;Valor\n31/02/2026;Mercado;-10,00\n") == [])


# ======================================================================
# ITEM 28 — importação de extrato em OFX
# ======================================================================
ofx_sgml = """OFXHEADER:100
DATA:OFXSGML
VERSION:102

<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260914120000[-3:BRT]
<TRNAMT>-89.90
<FITID>001
<MEMO>Supermercado
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260915
<TRNAMT>2500.00
<FITID>002
<MEMO>Pagamento cliente
</STMTTRN>
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260916
<TRNAMT>-15.00
<FITID>003
<MEMO>Estacionamento
</STMTTRN>
</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>
"""
lidos = leitor.ler_ofx(ofx_sgml)
checar("ofx le as 3 movimentacoes", len(lidos) == 3)
checar("ofx valor negativo vira despesa", lidos[0]["tipo"] == "despesa" and lidos[0]["valor"] == 89.9)
checar("ofx valor positivo vira entrada", lidos[1]["tipo"] == "entrada" and lidos[1]["valor"] == 2500.0)
checar("ofx data com hora e fuso vira AAAA-MM-DD", lidos[0]["data"] == "2026-09-14")
checar("ofx data simples (so AAAAMMDD)", lidos[1]["data"] == "2026-09-15")
checar("ofx descricao vem do MEMO", lidos[1]["descricao"] == "Pagamento cliente")
checar("ofx o valor guardado e sempre positivo", all(l["valor"] > 0 for l in lidos))

ofx_xml = ("<OFX><STMTTRN><DTPOSTED>20260916</DTPOSTED><TRNAMT>-10.00</TRNAMT>"
           "<NAME>Padaria</NAME></STMTTRN></OFX>")
lidos = leitor.ler_ofx(ofx_xml)
checar("ofx em XML (com tags de fechamento) tambem le", len(lidos) == 1 and lidos[0]["valor"] == 10.0)
checar("ofx sem MEMO usa o NAME como descricao", lidos[0]["descricao"] == "Padaria")

lidos = leitor.ler_ofx("<STMTTRN><DTPOSTED>20260917<TRNAMT>-50,00<MEMO>Virgula</STMTTRN>")
checar("ofx com virgula decimal no valor", len(lidos) == 1 and lidos[0]["valor"] == 50.0)

lidos = leitor.ler_ofx("<STMTTRN><DTPOSTED>20260917<TRNAMT>0.00<MEMO>Zero</STMTTRN>")
checar("ofx ignora movimentacao de valor zero", lidos == [])

lidos = leitor.ler_extrato("EXTRATO.OFX", ofx_sgml.encode("utf-8"))
checar("ler_extrato escolhe OFX pela extensao (maiuscula tambem)", len(lidos) == 3)
lidos = leitor.ler_extrato("extrato.ofx", ofx_sgml.replace("Supermercado", "Pão").encode("latin-1"))
checar("ofx em latin-1 mantem o acento", lidos[0]["descricao"] == "Pão")

checar("ofx sem nenhuma STMTTRN devolve lista vazia", leitor.ler_ofx("<OFX><BANKMSGSRSV1></BANKMSGSRSV1></OFX>") == [])

# Fragilidade real do extrato.py: a data do OFX nao e conferida
checar("ofx: data que nao e data e recusada",
       leitor.ler_ofx("<STMTTRN><DTPOSTED>ABCDEFGH<TRNAMT>-5.00<MEMO>X</STMTTRN>") == [])


# ======================================================================
# ITEM 29 — arquivo inválido: avisa e não grava nada
# ======================================================================
# --- a leitura em si: nunca estoura erro, só devolve lista vazia
for nome, conteudo in (("vazio", b""), ("so linhas em branco", b"\n  \n\n"),
                       ("texto qualquer", b"isto nao e um extrato"),
                       ("binario", bytes(range(256)) * 8)):
    for extensao in (".csv", ".ofx"):
        resultado = tentar(lambda: leitor.ler_extrato("arquivo" + extensao, conteudo))
        checar(f"leitura de {nome} ({extensao}) devolve lista vazia sem estourar", resultado == [])

checar("csv sem a coluna de valor devolve lista vazia",
       leitor.ler_csv("Data;Descrição;Categoria\n14/09/2026;Mercado;Alimentação\n") == [])

lidos = leitor.ler_csv("Data;Descrição;Valor\n14/09/2026;Boa;-10,00\n"
                       "15/09/2026;Ruim;abc\n16/09/2026;Boa2;20,00\n")
checar("linha com valor que nao e numero fica de fora", [l["descricao"] for l in lidos] == ["Boa", "Boa2"])

# Fragilidade real: float() aceita "nan" e "inf", que não são valores de dinheiro
checar("valor 'nan' nao e aceito", leitor.ler_csv("Data;Descrição;Valor\n14/09/2026;X;nan\n") == [])
checar("valor 'inf' nao e aceito", leitor.ler_csv("Data;Descrição;Valor\n14/09/2026;X;inf\n") == [])

# --- pela tela: avisa e não grava
cli_imp, id_imp = conta_limpa("importa@a.com")


def enviar_extrato(cliente, nome, conteudo):
    return cliente.post("/importar", data={"extrato": (io.BytesIO(conteudo), nome)},
                        content_type="multipart/form-data", follow_redirects=True)


for nome, conteudo in (("vazio.csv", b""), ("texto.csv", b"isto nao e um extrato"),
                       ("texto.ofx", b"isto nao e um extrato"),
                       ("semvalor.csv", "Data;Descrição;Categoria\n14/09/2026;A;B\n".encode())):
    r = tentar(lambda: enviar_extrato(cli_imp, nome, conteudo))
    checar(f"importar {nome}: avisa que nao leu nada",
           sem_estouro(r) and "Não foi possível ler" in r.get_data(as_text=True))
    checar(f"importar {nome}: nao grava nada", total_lancamentos(id_imp) == 0)

r = tentar(lambda: cli_imp.post("/importar", data={}, follow_redirects=True))
checar("importar sem escolher arquivo: avisa", sem_estouro(r) and "Escolha um arquivo" in r.get_data(as_text=True))

csv_misto = "Data;Descrição;Valor\n14/09/2026;Boa;-10,00\n15/09/2026;Ruim;abc\n".encode()
r = tentar(lambda: enviar_extrato(cli_imp, "misto.csv", csv_misto))
checar("importar CSV com uma linha ruim: mostra a revisao", sem_estouro(r) and r.status_code == 200)
checar("importar CSV com uma linha ruim: ainda nao grava (so grava ao confirmar)", total_lancamentos(id_imp) == 0)

# --- a confirmação: campo adulterado ou vazio na tela de revisão
with app.test_request_context():
    cat_imp = banco.listar_categorias(id_imp, "despesa")[0]["id"]


def confirmar(cliente, linhas):
    """linhas: lista de (valor, data). Todas marcadas para importar."""
    dados = {"incluir": [str(i) for i in range(len(linhas))]}
    for i, (valor, data) in enumerate(linhas):
        dados.update({f"categoria_{i}": str(cat_imp), f"valor_{i}": valor,
                      f"data_{i}": data, f"descricao_{i}": f"linha {i}"})
    return tentar(lambda: cliente.post("/importar/confirmar", data=dados, follow_redirects=True))


casos = {
    "valor que nao e numero": [("10.00", "2026-09-14"), ("abc", "2026-09-15")],
    "valor vazio": [("10.00", "2026-09-14"), ("", "2026-09-15")],
    "valor negativo": [("10.00", "2026-09-14"), ("-5", "2026-09-15")],
    "valor zero": [("10.00", "2026-09-14"), ("0", "2026-09-15")],
    "data vazia": [("10.00", "2026-09-14"), ("5.00", "")],
}
for nome, linhas in casos.items():
    antes = total_lancamentos(id_imp)
    r = confirmar(cli_imp, linhas)
    depois = total_lancamentos(id_imp)
    checar(f"confirmar com {nome}: nao estoura erro", sem_estouro(r))
    checar(f"confirmar com {nome}: nao grava lancamento pela metade", depois == antes)

antes = total_lancamentos(id_imp)
r = confirmar(cli_imp, [("10.00", "2026-09-14"), ("5.00", "2026-09-15")])
checar("confirmar com tudo certo grava as 2 linhas", sem_estouro(r) and total_lancamentos(id_imp) == antes + 2)

print(f"\n{n - len(falhas)}/{n} verificacoes passaram")
if falhas:
    print("FALHAS:", *falhas, sep="\n  - ")
    sys.exit(1)
print("tudo certo")
