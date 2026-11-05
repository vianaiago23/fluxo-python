
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
# "Aluguel" também é nome de categoria da conta nova; o que não pode aparecer
# é a descrição do lançamento da outra conta.
checar("conta nova nao ve dados da outra",
       "Projeto Y" not in corpo2 and '<span class="desc">Aluguel' not in corpo2)
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
           sem_estouro(r) and "Nenhum lançamento foi encontrado" in r.get_data(as_text=True))
    checar(f"importar {nome}: nao grava nada", total_lancamentos(id_imp) == 0)

r = tentar(lambda: cli_imp.post("/importar", data={}, follow_redirects=True))
checar("importar sem escolher arquivo: avisa", sem_estouro(r) and "Nenhum arquivo foi escolhido" in r.get_data(as_text=True))

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
    "valor nan": [("10.00", "2026-09-14"), ("nan", "2026-09-15")],
    "valor infinito": [("10.00", "2026-09-14"), ("inf", "2026-09-15")],
    "data que nao existe": [("10.00", "2026-09-14"), ("5.00", "2026-02-31")],
}
for nome, linhas in casos.items():
    antes = total_lancamentos(id_imp)
    r = confirmar(cli_imp, linhas)
    depois = total_lancamentos(id_imp)
    checar(f"confirmar com {nome}: nao estoura erro", sem_estouro(r))
    # Regra do grupo: a linha ruim fica de fora, a boa entra, e a tela avisa.
    checar(f"confirmar com {nome}: so a linha boa entra", depois == antes + 1)
    checar(f"confirmar com {nome}: avisa que uma ficou de fora",
           sem_estouro(r) and "de fora" in r.get_data(as_text=True))

with app.test_request_context():
    gravados_imp = banco.listar_todos_lancamentos(id_imp)
checar("nenhuma linha invalida chegou ao banco",
       all(l["valor"] > 0 and len(l["data"]) == 10 for l in gravados_imp))

antes = total_lancamentos(id_imp)
r = confirmar(cli_imp, [("10.00", "2026-09-14"), ("5.00", "2026-09-15")])
checar("confirmar com tudo certo grava as 2 linhas", sem_estouro(r) and total_lancamentos(id_imp) == antes + 2)


# ======================================================================
# ITEM 30 — repetição de lançamento (campo "repetir")
# ======================================================================
cli_rep, id_rep = conta_limpa("repete@a.com")
with app.test_request_context():
    cat_rep = banco.listar_categorias(id_rep, "despesa")[0]["id"]


def lancar(cliente, data, repetir, descricao, valor="100,00"):
    dados = {"categoria_id": cat_rep, "valor": valor, "data": data,
             "descricao": descricao, "repetir": repetir}
    return tentar(lambda: cliente.post("/lancamento/novo", data=dados))


lancar(cli_rep, "2026-03-15", "3", "rep3")
checar("repetir 3: cria 3 lancamentos", len(datas_de(id_rep, "rep3")) == 3)
checar("repetir 3: um em cada mes seguinte, no mesmo dia",
       datas_de(id_rep, "rep3") == ["2026-03-15", "2026-04-15", "2026-05-15"])

lancar(cli_rep, "2025-11-15", "3", "virada")
checar("repetir atravessa a virada do ano",
       datas_de(id_rep, "virada") == ["2025-11-15", "2025-12-15", "2026-01-15"])

lancar(cli_rep, "2026-06-10", "1", "rep1")
checar("repetir 1: cria so 1 lancamento", len(datas_de(id_rep, "rep1")) == 1)
lancar(cli_rep, "2026-06-10", "", "repvazio")
checar("repetir vazio: cria so 1 lancamento", len(datas_de(id_rep, "repvazio")) == 1)
lancar(cli_rep, "2026-06-10", "0", "rep0")
checar("repetir 0: cria 1 lancamento", len(datas_de(id_rep, "rep0")) == 1)
lancar(cli_rep, "2026-06-10", "-5", "repneg")
checar("repetir negativo: cria 1 lancamento", len(datas_de(id_rep, "repneg")) == 1)

lancar(cli_rep, "2026-01-10", "100", "rep100")
datas = datas_de(id_rep, "rep100")
checar("repetir 100: o sistema limita a 24 lancamentos", len(datas) == 24)
checar("repetir 24: o ultimo cai 23 meses depois", datas[-1] == "2027-12-10")

lancar(cli_rep, "2026-04-05", "2", "mesmovalor", valor="1.234,56")
with app.test_request_context():
    linhas = [l for l in banco.listar_todos_lancamentos(id_rep) if l["descricao"] == "mesmovalor"]
checar("repetir: todos com o mesmo valor, tipo e categoria",
       len(linhas) == 2 and all(l["valor"] == 1234.56 and l["tipo"] == "despesa"
                                and l["categoria_id"] == cat_rep for l in linhas))

# O caso do dia 31. HOJE o código usa o ÚLTIMO DIA do mês quando o dia não existe
# (31/01 -> 28/02) e volta ao dia 31 nos meses que têm. Se o grupo decidir outra
# regra, é só mudar as datas esperadas abaixo.
lancar(cli_rep, "2026-01-31", "4", "dia31")
checar("dia 31: fevereiro cai no ultimo dia do mes (28)",
       datas_de(id_rep, "dia31") == ["2026-01-31", "2026-02-28", "2026-03-31", "2026-04-30"])
lancar(cli_rep, "2024-01-31", "2", "bissexto")
checar("dia 31: em ano bissexto fevereiro cai no dia 29",
       datas_de(id_rep, "bissexto") == ["2024-01-31", "2024-02-29"])
lancar(cli_rep, "2026-01-30", "2", "dia30")
checar("dia 30: fevereiro tambem cai no ultimo dia", datas_de(id_rep, "dia30") == ["2026-01-30", "2026-02-28"])

# Entradas que o formulário não deveria deixar estourar
antes = total_lancamentos(id_rep)
for nome, repetir, data in (("repetir que nao e numero", "abc", "2026-05-01"),
                            ("repetir com decimal", "2.5", "2026-05-01"),
                            ("data que nao e data", "1", "abc"),
                            ("data com mes 13", "1", "2026-13-45")):
    r = lancar(cli_rep, data, repetir, "estranho")
    checar(f"{nome}: nao estoura erro", sem_estouro(r))
checar("entradas estranhas nao gravam lancamento", total_lancamentos(id_rep) == antes)

# O Python entende datas como "20260914" e "2026-W37-1": o sistema precisa gravar AAAA-MM-DD
for texto, esperado in (("20260914", "2026-09-14"), ("2026-W37-1", "2026-09-07")):
    r = lancar(cli_rep, texto, "1", "formato " + texto)
    checar(f"data no formato {texto}: nao estoura erro", sem_estouro(r))
    checar(f"data no formato {texto}: grava como AAAA-MM-DD", datas_de(id_rep, "formato " + texto) == [esperado])

for valor in ("nan", "inf"):
    antes = total_lancamentos(id_rep)
    r = lancar(cli_rep, "2026-05-01", "1", "valor " + valor, valor=valor)
    checar(f"valor '{valor}' no formulario: nao estoura erro e nao grava",
           sem_estouro(r) and total_lancamentos(id_rep) == antes)


# ======================================================================
# ITEM 31 — metas: alerta em 80% e em 100%
# ======================================================================
cli_meta, id_meta = conta_limpa("meta@a.com")
ano_h, mes_h = constantes.hoje().year, constantes.hoje().month
dia_hoje = constantes.hoje().isoformat()
with app.test_request_context():
    cat_gasto = banco.listar_categorias(id_meta, "despesa")[0]["id"]
    cat_entrada = banco.listar_categorias(id_meta, "entrada")[0]["id"]


def metas_do_mes():
    with app.test_request_context():
        return [dict(m) for m in banco.listar_metas(id_meta, ano_h, mes_h)]


def gastar(valor):
    cli_meta.post("/lancamento/novo", data={"categoria_id": cat_gasto, "valor": valor,
                                            "data": dia_hoje, "descricao": "gasto da meta", "repetir": "1"})


cli_meta.post("/meta/nova", data={"categoria_id": cat_gasto, "valor_limite": "1.000,00"})
checar("meta criada com o limite informado",
       len(metas_do_mes()) == 1 and metas_do_mes()[0]["valor_limite"] == 1000.0)
checar("meta recem criada comeca com gasto zero", metas_do_mes()[0]["gasto"] == 0)


def percentual():
    meta = metas_do_mes()[0]
    return meta["gasto"] / meta["valor_limite"] * 100


gastar("799,00")
checar("gasto de 799 de 1000 esta abaixo de 80%", percentual() < 80)
gastar("1,00")
checar("gasto de 800 de 1000 chega em 80%", percentual() == 80)
gastar("199,00")
checar("gasto de 999 de 1000 ainda esta abaixo de 100%", 80 < percentual() < 100)
gastar("1,00")
checar("gasto de 1000 de 1000 chega em 100%", percentual() == 100)
gastar("50,00")
checar("gasto acima do limite passa de 100%", percentual() > 100)

# FALTA: conferir o AVISO na tela do painel (depende do texto do painel.html)

cli_meta.post("/meta/nova", data={"categoria_id": cat_gasto, "valor_limite": "2.000,00"})
checar("meta repetida na mesma categoria atualiza o limite, sem duplicar",
       len(metas_do_mes()) == 1 and metas_do_mes()[0]["valor_limite"] == 2000.0)

for nome, categoria, limite in (("categoria de entrada", cat_entrada, "500,00"),
                                ("limite zero", cat_gasto + 1, "0"),
                                ("limite negativo", cat_gasto + 1, "-50"),
                                ("limite que nao e numero", cat_gasto + 1, "abc"),
                                ("categoria inexistente", 999999, "500,00"),
                                ("categoria que nao e numero", "abc", "500,00")):
    r = tentar(lambda: cli_meta.post("/meta/nova", data={"categoria_id": categoria, "valor_limite": limite}))
    checar(f"meta com {nome}: nao e aceita", sem_estouro(r) and len(metas_do_mes()) == 1)
r = cli_meta.post("/meta/nova", data={"categoria_id": cat_entrada, "valor_limite": "500,00"}, follow_redirects=True)
checar("meta em categoria de entrada: avisa o motivo", "Escolha a categoria" in r.get_data(as_text=True))


# ======================================================================
# ITEM 31 (parte da tela) — o painel mostra o aviso da meta
# ======================================================================
import re                                     # noqa: E402

cli_tela, id_tela = conta_limpa("meta_tela@a.com")
dia_tela = constantes.hoje().isoformat()
with app.test_request_context():
    cat_tela = banco.listar_categorias(id_tela, "despesa")[0]["id"]


def cor_da_barra():
    """Cor da barra da meta no painel: --income (verde), --gold (amarelo) ou --danger (vermelho)."""
    corpo = cli_tela.get("/").get_data(as_text=True)
    achado = re.search(r'bar-fill"[^>]*?background:\s*var\((--[a-z]+)\)', corpo, re.DOTALL)
    return achado.group(1) if achado else None


def gastar_na_tela(valor):
    cli_tela.post("/lancamento/novo", data={"categoria_id": cat_tela, "valor": valor, "data": dia_tela,
                                            "descricao": "gasto", "repetir": "1"})


cli_tela.post("/meta/nova", data={"categoria_id": cat_tela, "valor_limite": "1.000,00"})
checar("painel: meta sem gasto fica verde", cor_da_barra() == "--income")
gastar_na_tela("799,00")
checar("painel: 79,9% do limite ainda e verde", cor_da_barra() == "--income")
gastar_na_tela("1,00")
checar("painel: 80% do limite vira aviso amarelo", cor_da_barra() == "--gold")
gastar_na_tela("199,00")
checar("painel: 99,9% do limite continua amarelo", cor_da_barra() == "--gold")
gastar_na_tela("1,00")
# HOJE: com o gasto IGUAL ao limite a barra ainda e amarela; so fica vermelha ao ultrapassar.
# Se o grupo quiser vermelho ja nos 100%, mude no painel.html (pct > 100 vira pct >= 100)
# e troque o esperado abaixo para "--danger".
checar("painel: 100% do limite ainda e amarelo (vermelho so acima)", cor_da_barra() == "--gold")
gastar_na_tela("0,01")
checar("painel: acima do limite fica vermelho", cor_da_barra() == "--danger")
# ======================================================================
# ITEM 32 — isolamento entre contas em TODA ação com número
# ======================================================================
cli_a, id_a = conta_limpa("isola_a@a.com")
cli_b, id_b = conta_limpa("isola_b@a.com")
anonimo_iso = app.test_client()
ano_i, mes_i = constantes.hoje().year, constantes.hoje().month
dia_i = constantes.hoje().isoformat()

with app.test_request_context():
    desp_b = [c["id"] for c in banco.listar_categorias(id_b, "despesa")]
    desp_a = [c["id"] for c in banco.listar_categorias(id_a, "despesa")]
cat_b_lanc, cat_b_meta, cat_b_livre = desp_b[0], desp_b[1], desp_b[2]

cli_b.post("/lancamento/novo", data={"categoria_id": cat_b_lanc, "valor": "80,00", "data": dia_i,
                                     "descricao": "Segredo B", "repetir": "1"})
cli_b.post("/meta/nova", data={"categoria_id": cat_b_meta, "valor_limite": "500,00"})
with app.test_request_context():
    lanc_b = banco.listar_todos_lancamentos(id_b)[0]["id"]
    meta_b = banco.listar_metas(id_b, ano_i, mes_i)[0]["id"]
    nome_b = banco.buscar_categoria(id_b, cat_b_livre)["nome"]
    cor_b = banco.buscar_categoria(id_b, cat_b_livre)["cor"]


def lanc_de_b():
    with app.test_request_context():
        return banco.buscar_lancamento(id_b, lanc_b)


def metas_de(usuario_id):
    with app.test_request_context():
        return [dict(m) for m in banco.listar_metas(usuario_id, ano_i, mes_i)]


def categoria_de_b():
    with app.test_request_context():
        return banco.buscar_categoria(id_b, cat_b_livre)


# --- editar lançamento (abrir a tela e enviar o formulário)
r = tentar(lambda: cli_a.get(f"/lancamento/{lanc_b}/editar"))
checar("editar lancamento alheio: a tela nao abre", sem_estouro(r) and r.status_code == 302
       and "Segredo B" not in r.get_data(as_text=True))
r = tentar(lambda: cli_a.post(f"/lancamento/{lanc_b}/editar", data={
    "categoria_id": desp_a[0], "valor": "1,00", "data": dia_i, "descricao": "INVADIDO", "repetir": "1"}))
checar("editar lancamento alheio: nao altera o original",
       sem_estouro(r) and lanc_de_b()["descricao"] == "Segredo B" and lanc_de_b()["valor"] == 80.0)
checar("editar lancamento alheio: nao cria nada na conta A", total_lancamentos(id_a) == 0)

# --- excluir lançamento
r = tentar(lambda: cli_a.post(f"/lancamento/{lanc_b}/excluir"))
checar("excluir lancamento alheio: nao apaga", sem_estouro(r) and lanc_de_b() is not None)

# --- excluir meta
r = tentar(lambda: cli_a.post(f"/meta/{meta_b}/excluir"))
checar("excluir meta alheia: nao apaga", sem_estouro(r) and len(metas_de(id_b)) == 1)

# --- renomear, trocar cor e excluir categoria (o número vem no formulário)
r = tentar(lambda: cli_a.post("/configuracoes", data={
    "acao": "renomear_categoria", "categoria_id": cat_b_livre, "nome": "INVADIDA"}))
checar("renomear categoria alheia: nao renomeia", sem_estouro(r) and categoria_de_b()["nome"] == nome_b)
r = tentar(lambda: cli_a.post("/configuracoes", data={
    "acao": "cor_categoria", "categoria_id": cat_b_livre, "cor": "#000000"}))
checar("trocar cor de categoria alheia: nao troca", sem_estouro(r) and categoria_de_b()["cor"] == cor_b)
# a categoria livre não tem lançamentos: se o isolamento falhar, ela seria mesmo apagada
r = tentar(lambda: cli_a.post("/configuracoes", data={"acao": "excluir_categoria", "categoria_id": cat_b_livre}))
checar("excluir categoria alheia: nao apaga", sem_estouro(r) and categoria_de_b() is not None)

# --- usar o número de outra conta ao CRIAR coisas
antes_b = total_lancamentos(id_b)
r = tentar(lambda: cli_a.post("/lancamento/novo", data={
    "categoria_id": cat_b_lanc, "valor": "10,00", "data": dia_i, "descricao": "com categoria alheia", "repetir": "1"}))
checar("novo lancamento com categoria alheia: nao grava em nenhuma conta",
       sem_estouro(r) and total_lancamentos(id_a) == 0 and total_lancamentos(id_b) == antes_b)
r = tentar(lambda: cli_a.post("/meta/nova", data={"categoria_id": cat_b_meta, "valor_limite": "1,00"}))
checar("nova meta com categoria alheia: nao cria nem altera a meta de B",
       sem_estouro(r) and metas_de(id_a) == [] and metas_de(id_b)[0]["valor_limite"] == 500.0)
r = tentar(lambda: cli_a.post("/importar/confirmar", data={
    "incluir": ["0"], "categoria_0": str(cat_b_lanc), "valor_0": "10.00",
    "data_0": dia_i, "descricao_0": "importado alheio"}))
checar("importar para categoria alheia: nao grava em nenhuma conta",
       sem_estouro(r) and total_lancamentos(id_a) == 0 and total_lancamentos(id_b) == antes_b)

# --- sem login, nada disso funciona
for nome, url, dados in (("editar", f"/lancamento/{lanc_b}/editar", {"categoria_id": cat_b_lanc, "valor": "1", "data": dia_i}),
                         ("excluir lancamento", f"/lancamento/{lanc_b}/excluir", {}),
                         ("excluir meta", f"/meta/{meta_b}/excluir", {}),
                         ("excluir categoria", "/configuracoes", {"acao": "excluir_categoria", "categoria_id": cat_b_livre})):
    r = tentar(lambda: anonimo_iso.post(url, data=dados))
    checar(f"{nome} sem login: manda para o login", sem_estouro(r) and "/entrar" in r.headers.get("Location", ""))
checar("sem login: nada do B foi mexido",
       lanc_de_b() is not None and len(metas_de(id_b)) == 1 and categoria_de_b()["nome"] == nome_b)

# --- id que não existe, e número que não é número
for url in ("/lancamento/999999/editar", "/lancamento/999999/excluir", "/meta/999999/excluir"):
    r = tentar(lambda: (cli_a.get(url) if url.endswith("editar") else cli_a.post(url)))
    checar(f"{url}: nao estoura erro", sem_estouro(r))
for acao in ("renomear_categoria", "cor_categoria", "excluir_categoria"):
    r = tentar(lambda: cli_a.post("/configuracoes", data={"acao": acao, "categoria_id": "abc", "nome": "x"}))
    checar(f"{acao} com id que nao e numero: nao estoura erro", sem_estouro(r))
r = tentar(lambda: cli_a.post("/lancamento/novo", data={
    "categoria_id": "abc", "valor": "10,00", "data": dia_i, "descricao": "x", "repetir": "1"}))
checar("novo lancamento com categoria que nao e numero: nao estoura erro", sem_estouro(r))

# --- controle: o DONO consegue fazer cada ação (prova que os testes acima não passam "no vazio")
cli_a.post("/lancamento/novo", data={"categoria_id": desp_a[0], "valor": "20,00", "data": dia_i,
                                     "descricao": "meu lancamento", "repetir": "1"})
with app.test_request_context():
    meu = banco.listar_todos_lancamentos(id_a)[0]["id"]
cli_a.post(f"/lancamento/{meu}/editar", data={"categoria_id": desp_a[0], "valor": "30,00",
                                              "data": dia_i, "descricao": "meu editado", "repetir": "1"})
with app.test_request_context():
    editado = banco.buscar_lancamento(id_a, meu)
checar("controle: o dono consegue editar o proprio lancamento", editado["descricao"] == "meu editado")
cli_a.post(f"/lancamento/{meu}/excluir")
checar("controle: o dono consegue excluir o proprio lancamento", total_lancamentos(id_a) == 0)
cli_a.post("/meta/nova", data={"categoria_id": desp_a[1], "valor_limite": "100,00"})
cli_a.post(f"/meta/{metas_de(id_a)[0]['id']}/excluir")
checar("controle: o dono consegue excluir a propria meta", metas_de(id_a) == [])
cli_a.post("/configuracoes", data={"acao": "renomear_categoria", "categoria_id": desp_a[2], "nome": "Renomeada"})
with app.test_request_context():
    nome_a = banco.buscar_categoria(id_a, desp_a[2])["nome"]
checar("controle: o dono consegue renomear a propria categoria", nome_a == "Renomeada")
cli_a.post("/configuracoes", data={"acao": "excluir_categoria", "categoria_id": desp_a[2]})
with app.test_request_context():
    sumiu = banco.buscar_categoria(id_a, desp_a[2]) is None
checar("controle: o dono consegue excluir a propria categoria livre", sumiu)

# --- filtros do painel: categoria e período
c_filtro = app.test_client()
c_filtro.post("/entrar", data={"modo": "cadastro", "email": "filtro@a.com", "senha": "senha123"})
c_filtro.post("/perfil", data={"perfil": "arquiteto"})
with app.test_request_context():
    id_filtro = banco.buscar_usuario_por_email("filtro@a.com")["id"]
    cat_entrada = banco.listar_categorias(id_filtro, "entrada")[0]["id"]
    cat_despesa = banco.listar_categorias(id_filtro, "despesa")[0]["id"]
for categoria, data_mov, descricao in ((cat_entrada, "2025-01-10", "Filtro-jan"),
                                       (cat_despesa, "2025-02-15", "Filtro-fev"),
                                       (cat_entrada, "2025-03-20", "Filtro-mar")):
    c_filtro.post("/lancamento/novo", data={"categoria_id": categoria, "valor": "100,00",
                                            "data": data_mov, "descricao": descricao, "repetir": "1"})


def descricoes_no_painel(cliente, consulta):
    corpo = cliente.get("/?todos=1&" + consulta).get_data(as_text=True)
    return {d for d in ("Filtro-jan", "Filtro-fev", "Filtro-mar")
            if f'<span class="desc">{d}' in corpo}


checar("filtro por categoria mostra so ela",
       descricoes_no_painel(c_filtro, f"de=2025-01-01&ate=2025-12-31&categoria={cat_entrada}")
       == {"Filtro-jan", "Filtro-mar"})
checar("filtro por categoria funciona junto com o mes",
       descricoes_no_painel(c_filtro, f"ano=2025&mes=2&categoria={cat_entrada}") == set())
checar("sem filtro, o mes mostra tudo dele",
       descricoes_no_painel(c_filtro, "ano=2025&mes=2") == {"Filtro-fev"})
checar("periodo recorta certo",
       descricoes_no_painel(c_filtro, "de=2025-02-01&ate=2025-03-31") == {"Filtro-fev", "Filtro-mar"})
checar("periodo inclui as duas pontas",
       descricoes_no_painel(c_filtro, "de=2025-01-10&ate=2025-02-15") == {"Filtro-jan", "Filtro-fev"})
checar("periodo substitui o filtro de mes",
       descricoes_no_painel(c_filtro, "ano=2025&mes=1&de=2025-03-01&ate=2025-03-31") == {"Filtro-mar"})
checar("periodo so com data inicial fica aberto no fim",
       descricoes_no_painel(c_filtro, "de=2025-02-01") == {"Filtro-fev", "Filtro-mar"})
checar("periodo e categoria juntos",
       descricoes_no_painel(c_filtro, f"de=2025-02-01&ate=2025-12-31&categoria={cat_entrada}")
       == {"Filtro-mar"})

r = c_filtro.get("/?de=2025-12-31&ate=2025-01-01")
checar("data inicial maior que a final nao quebra a tela",
       r.status_code == 200 and "depois da final" in r.get_data(as_text=True)
       and descricoes_no_painel(c_filtro, "de=2025-12-31&ate=2025-01-01") == set())
checar("data invalida na URL nao quebra a tela",
       c_filtro.get("/?de=2025-02-30&ate=lixo").status_code == 200)
checar("categoria invalida na URL nao quebra a tela",
       c_filtro.get("/?categoria=99999999999999999999999").status_code == 200)

# outra conta trocando o número da categoria na URL
c_intruso = app.test_client()
c_intruso.post("/entrar", data={"modo": "cadastro", "email": "intruso@a.com", "senha": "senha123"})
c_intruso.post("/perfil", data={"perfil": "arquiteto"})
checar("categoria de outra conta na URL nao mostra nada",
       descricoes_no_painel(c_intruso, f"de=2025-01-01&ate=2025-12-31&categoria={cat_entrada}") == set())
with app.test_request_context():
    id_intruso = banco.buscar_usuario_por_email("intruso@a.com")["id"]
    checar("consulta com categoria alheia volta vazia",
           banco.listar_lancamentos(id_intruso, categoria_id=cat_entrada) == [])

# --- relatório anual
import analise  # noqa: E402

c_anual = app.test_client()
c_anual.post("/entrar", data={"modo": "cadastro", "email": "anual@a.com", "senha": "senha123"})
c_anual.post("/perfil", data={"perfil": "generico"})
with app.test_request_context():
    id_anual = banco.buscar_usuario_por_email("anual@a.com")["id"]
    entrada_anual = banco.listar_categorias(id_anual, "entrada")[0]["id"]
    despesa_anual = banco.listar_categorias(id_anual, "despesa")[0]["id"]
for categoria, valor, data_mov in ((entrada_anual, "1.000,10", "2024-01-01"),
                                   (entrada_anual, "1.500,25", "2024-01-31"),
                                   (despesa_anual, "300,40", "2024-01-15"),
                                   (despesa_anual, "999,99", "2024-06-10"),
                                   (entrada_anual, "2.000,00", "2024-12-31"),
                                   (entrada_anual, "7.777,00", "2023-12-31"),    # ano anterior
                                   (despesa_anual, "8.888,00", "2025-01-01")):   # ano seguinte
    c_anual.post("/lancamento/novo", data={"categoria_id": categoria, "valor": valor,
                                           "data": data_mov, "descricao": "", "repetir": "1"})

with app.test_request_context():
    meses_vazios, total_vazio = analise.resumo_do_ano(id_anual, 2010)
    meses_2024, total_2024 = analise.resumo_do_ano(id_anual, 2024)
    meses_intruso, total_intruso = analise.resumo_do_ano(id_intruso, 2024)
    do_ano = [l for l in banco.listar_todos_lancamentos(id_anual) if l["data"].startswith("2024")]
    por_mes_somar_mes = [(banco.somar_mes(id_anual, 2024, m, "entrada"),
                          banco.somar_mes(id_anual, 2024, m, "despesa")) for m in range(1, 13)]


def zerado(meses, total):
    return (len(meses) == 12 and [m["mes"] for m in meses] == list(range(1, 13))
            and all(m["entradas"] == m["despesas"] == m["saldo"] == 0 for m in meses)
            and total == {"entradas": 0, "despesas": 0, "saldo": 0})


checar("ano sem lancamento devolve doze meses zerados", zerado(meses_vazios, total_vazio))
checar("ano com lancamento tambem traz os doze meses", len(meses_2024) == 12)
checar("mes sem lancamento aparece zerado",
       meses_2024[2]["entradas"] == 0 and meses_2024[2]["despesas"] == 0)
checar("cada mes bate com somar_mes",
       [(round(m["entradas"], 2), round(m["despesas"], 2)) for m in meses_2024]
       == [(round(e, 2), round(d, 2)) for e, d in por_mes_somar_mes])
checar("total de entradas bate com a soma dos lancamentos",
       total_2024["entradas"] == round(sum(l["valor"] for l in do_ano if l["tipo"] == "entrada"), 2)
       == 4500.35)
checar("total de despesas bate com a soma dos lancamentos",
       total_2024["despesas"] == round(sum(l["valor"] for l in do_ano if l["tipo"] == "despesa"), 2)
       == 1300.39)
checar("saldo do ano e entradas menos despesas", total_2024["saldo"] == 3199.96)
checar("primeiro e ultimo dia do ano entram, anos vizinhos nao",
       meses_2024[0]["entradas"] == 2500.35 and meses_2024[11]["entradas"] == 2000.0)
checar("um usuario nao ve o ano do outro", zerado(meses_intruso, total_intruso))

r = c_anual.get("/anual?ano=2024")
corpo = r.get_data(as_text=True)
checar("tela do relatorio anual abre", r.status_code == 200)
checar("tela mostra os doze meses", all(nome in corpo for nome in constantes.MESES))
checar("tela mostra o total do ano", "4.500,35" in corpo and "3.199,96" in corpo)
checar("tela do outro usuario nao mostra os valores",
       "4.500,35" not in c_intruso.get("/anual?ano=2024").get_data(as_text=True))
checar("ano invalido na URL nao quebra a tela", c_anual.get("/anual?ano=lixo").status_code == 200)
for ano_grafico in ("2024", "2010"):
    r = c_anual.get(f"/grafico/anual.png?ano={ano_grafico}")
    checar(f"grafico anual de {ano_grafico} gera PNG", r.status_code == 200 and r.data[:4] == b"\x89PNG")

# --- ordenação da lista de lançamentos
with app.test_request_context():
    def valores_em_ordem(ordem):
        return [(l["data"], l["valor"]) for l in
                banco.listar_lancamentos(id_anual, "2024-01-01", "2024-12-31", ordem=ordem)]

    por_data_desc = valores_em_ordem("data_desc")
    por_data_asc = valores_em_ordem("data_asc")
    por_valor_desc = valores_em_ordem("valor_desc")
    por_valor_asc = valores_em_ordem("valor_asc")
    padrao = valores_em_ordem(banco.ORDENACAO_PADRAO)
    tentativa_injecao = valores_em_ordem("l.valor; DROP TABLE lancamentos; --")
    tabela_inteira = banco.conectar().execute(
        "SELECT COUNT(*) AS n FROM lancamentos").fetchone()["n"] > 0

checar("ordenacao por data, mais recente primeiro",
       [d for d, _ in por_data_desc] == sorted((d for d, _ in por_data_desc), reverse=True))
checar("ordenacao por data, mais antiga primeiro",
       [d for d, _ in por_data_asc] == sorted(d for d, _ in por_data_asc))
checar("ordenacao por valor, maior primeiro",
       [v for _, v in por_valor_desc] == sorted((v for _, v in por_valor_desc), reverse=True))
checar("ordenacao por valor, menor primeiro",
       [v for _, v in por_valor_asc] == sorted(v for _, v in por_valor_asc))
checar("ordenacao nao perde nem duplica lancamento",
       sorted(por_valor_asc) == sorted(por_data_desc) and len(por_data_desc) == 5)
checar("ordenacao desconhecida usa a padrao, sem ir para o SQL",
       tentativa_injecao == padrao and tabela_inteira)

corpo = c_anual.get("/?de=2024-01-01&ate=2024-12-31&todos=1&ordem=valor_desc").get_data(as_text=True)
posicoes = [corpo.find(v) for v in ("2.000,00", "1.500,25", "1.000,10", "999,99", "300,40")]
checar("painel ordena por valor pela URL", -1 not in posicoes and posicoes == sorted(posicoes))
checar("painel marca a ordenacao escolhida", 'value="valor_desc" selected' in corpo)
checar("links do painel mantem a ordenacao", "ordem=valor_desc" in corpo)
r = c_anual.get("/?ordem=l.valor;%20DROP%20TABLE%20lancamentos;--")
checar("ordenacao invalida na URL nao quebra a tela", r.status_code == 200)

# --- validação de data e de valor no lançamento

from datetime import timedelta  # noqa: E402

with app.test_request_context():
    antes_de_tudo = len(banco.listar_todos_lancamentos(1))

amanha = (constantes.hoje() + timedelta(days=1)).isoformat()
r = c.post("/lancamento/novo", data={"categoria_id": id_entrada, "valor": "100,00",
                                     "data": amanha, "descricao": "futuro", "repetir": "1"})
with app.test_request_context():
    depois = banco.listar_todos_lancamentos(1)
checar("data no futuro e recusada", len(depois) == antes_de_tudo)
checar("data no futuro explica o motivo", "futuro" in r.get_data(as_text=True))

r = c.post("/lancamento/novo", data={"categoria_id": id_entrada, "valor": "99.999.999,00",
                                     "data": hoje, "descricao": "absurdo", "repetir": "1"})
with app.test_request_context():
    depois = banco.listar_todos_lancamentos(1)
checar("valor acima do teto e recusado", len(depois) == antes_de_tudo)
checar("valor acima do teto informa o limite", "limite" in r.get_data(as_text=True))

r = c.post("/lancamento/novo", data={"categoria_id": id_entrada, "valor": "10,00",
                                     "data": "31/02/2026", "descricao": "data torta", "repetir": "1"})
with app.test_request_context():
    depois = banco.listar_todos_lancamentos(1)
checar("data mal formada nao derruba a tela", r.status_code == 200)
checar("data mal formada nao grava nada", len(depois) == antes_de_tudo)

r = c.post("/lancamento/novo", data={"categoria_id": id_entrada, "valor": "10,00",
                                     "data": constantes.hoje().isoformat(),
                                     "descricao": "hoje vale", "repetir": "1"})
with app.test_request_context():
    depois = banco.listar_todos_lancamentos(1)
checar("lancamento de hoje continua sendo aceito", len(depois) == antes_de_tudo + 1)

# --- etiquetas do eixo dos graficos

from graficos import _rotulo_do_eixo  # noqa: E402

checar("eixo nao mostra zero negativo", _rotulo_do_eixo(-0.0, None) == "0")
checar("eixo nao mostra -0 ao arredondar", _rotulo_do_eixo(-0.4, None) == "0")
checar("eixo mostra valor pequeno inteiro", _rotulo_do_eixo(300.0, None) == "300")
checar("eixo mantem o sinal de valor negativo", _rotulo_do_eixo(-400.0, None) == "-400")
checar("eixo encurta milhar", _rotulo_do_eixo(2500.0, None) == "2 mil")
checar("eixo encurta milhar negativo", _rotulo_do_eixo(-2500.0, None) == "-2 mil")

import graficos  # noqa: E402

meses = ["Jun", "Jul", "Ago", "Set", "Out", "Nov"]
vazio = graficos.barras_saldo(meses, [0, 0, 0, 0, 0, 0])
cheio = graficos.barras_saldo(meses, [0, 0, 0, 0, 0, 5000])
checar("grafico de saldo sem movimento gera PNG", vazio[:4] == b"\x89PNG")
checar("grafico de saldo com movimento gera PNG", cheio[:4] == b"\x89PNG")
checar("sem movimento o grafico vira aviso, nao eixo zerado", vazio != cheio)

# --- a importacao recusa o mesmo que o formulario recusa

def importar_uma(valor, data):
    """Manda uma linha pela tela de revisao do extrato e devolve se gravou."""
    with app.test_request_context():
        antes = len(banco.listar_todos_lancamentos(1))
    c.post("/importar/confirmar", data={
        "incluir": "0", "categoria_0": id_entrada,
        "valor_0": valor, "data_0": data, "descricao_0": "do extrato",
    })
    with app.test_request_context():
        agora = banco.listar_todos_lancamentos(1)
    return len(agora) > antes, agora

amanha_iso = (constantes.hoje() + timedelta(days=1)).isoformat()
gravou, _ = importar_uma("100.0", amanha_iso)
checar("importacao recusa data no futuro", not gravou)

gravou, _ = importar_uma("99999999.0", hoje)
checar("importacao recusa valor acima do teto", not gravou)

gravou, _ = importar_uma("abc", hoje)
checar("importacao nao quebra com valor invalido", not gravou)

gravou, _ = importar_uma("0", hoje)
checar("importacao recusa valor zero", not gravou)

gravou, lancs = importar_uma("7400.0", hoje)
checar("importacao aceita linha valida", gravou)
importado = [l for l in lancs if l["descricao"] == "do extrato"]
checar("importacao grava o valor com ponto decimal, sem multiplicar",
       len(importado) == 1 and abs(importado[0]["valor"] - 7400.0) < 0.01)


# ======================================================================
# ITEM 33 — páginas de erro: a do sistema, sem detalhe técnico
# ======================================================================
anonimo_erro = app.test_client()
cli_erro, id_erro = conta_limpa("erro@a.com")

# Nada disto pode aparecer para quem está olhando a tela de erro
TERMOS_TECNICOS = ("Traceback", 'File "', ".py", "sqlite", "SELECT ", "INSERT ", "DROP TABLE",
                   "Werkzeug", "Flask", "RuntimeError", "Exception", "senha_hash",
                   "tokens_recuperacao", "usuarios", "lancamentos", "C:\\", "/home/")


def sem_detalhe_tecnico(corpo):
    return not any(termo in corpo for termo in TERMOS_TECNICOS)


def corpo_de(resposta):
    return resposta.get_data(as_text=True) if resposta is not None else ""


# --- 404: endereço que não existe
for quem, cliente in (("sem login", anonimo_erro), ("logado", cli_erro)):
    r = tentar(lambda: cliente.get("/endereco-que-nao-existe"))
    corpo = corpo_de(r)
    checar(f"404 ({quem}): endereco inexistente devolve 404", r is not None and r.status_code == 404)
    checar(f"404 ({quem}): usa a pagina do sistema", "Página não encontrada" in corpo and "Fluxo" in corpo)
    checar(f"404 ({quem}): tem link para voltar ao inicio", 'href="/"' in corpo)
    checar(f"404 ({quem}): nao mostra detalhe tecnico", sem_detalhe_tecnico(corpo))

r = tentar(lambda: anonimo_erro.post("/endereco-que-nao-existe"))
checar("404 em POST tambem usa a pagina do sistema", r is not None and r.status_code == 404
       and "Página não encontrada" in corpo_de(r))
r = tentar(lambda: anonimo_erro.get("/static/arquivo-que-nao-existe.css"))
checar("404 de arquivo estatico tambem usa a pagina do sistema", r is not None and r.status_code == 404
       and "Página não encontrada" in corpo_de(r))
r = tentar(lambda: cli_erro.get("/lancamento/abc/editar"))
checar("404 de id que nao e numero usa a pagina do sistema", r is not None and r.status_code == 404
       and "Página não encontrada" in corpo_de(r))

# o endereço digitado não pode voltar escrito na página (seria uma brecha para injetar código)
r = tentar(lambda: anonimo_erro.get("/<script>alert(1)</script>"))
checar("404 nao repete na tela o endereco digitado", r is not None and "<script>alert(1)" not in corpo_de(r))
r = tentar(lambda: anonimo_erro.get("/x'; DROP TABLE usuarios;--"))
checar("404 de endereco com SQL nao mostra detalhe tecnico",
       r is not None and r.status_code == 404 and sem_detalhe_tecnico(corpo_de(r)))

# --- 500: falha interna simulada, com uma mensagem cheia de detalhes que NÃO pode vazar
listar_de_verdade = banco.listar_categorias


def listar_com_falha(*_args, **_kwargs):
    raise RuntimeError("falha simulada: tabela usuarios em C:\\segredo\\fluxo.db")


banco.listar_categorias = listar_com_falha
app.config["PROPAGATE_EXCEPTIONS"] = False   # no teste o erro subiria até aqui; queremos a tela que a pessoa veria
app.logger.disabled = True                    # o erro vai para o log do servidor; sem isso sujaria a saída do teste
try:
    r = tentar(lambda: cli_erro.get("/"))
finally:
    banco.listar_categorias = listar_de_verdade
    app.config["PROPAGATE_EXCEPTIONS"] = None
    app.logger.disabled = False
corpo = corpo_de(r)
checar("falha interna devolve 500", r is not None and r.status_code == 500)
checar("500 usa a pagina do sistema", "Alguma coisa quebrou" in corpo and "Fluxo" in corpo)
checar("500 nao mostra a mensagem do erro", "falha simulada" not in corpo and "segredo" not in corpo)
checar("500 nao mostra detalhe tecnico", sem_detalhe_tecnico(corpo))
checar("500 tranquiliza: os dados nao foram perdidos", "não foram perdidos" in corpo)
r = tentar(lambda: cli_erro.get("/"))
checar("depois da falha, o painel volta a abrir", r is not None and r.status_code == 200)

# --- 405: abrir pelo endereço uma rota que só aceita POST (ex.: /lancamento/1/excluir)
r = tentar(lambda: cli_erro.get("/lancamento/1/excluir"))
corpo = corpo_de(r)
checar("metodo errado (405): devolve 405", r is not None and r.status_code == 405)
checar("metodo errado (405): usa a pagina do sistema", "Fluxo" in corpo and 'href="/"' in corpo)
checar("metodo errado (405): nao mostra detalhe tecnico", sem_detalhe_tecnico(corpo))

# ======================================================================
# Correções de bugs: entradas forjadas, extrato, PDF e saldo
# ======================================================================
print("\n--- correcoes de bugs")
import extrato as leitor                      # noqa: E402

for texto, esperado in [("R$ -50,00", -50.0), ("-R$ 50,00", -50.0), ("123,45-", -123.45),
                        ("1.500", 1500.0), ("1.234.567", 1234567.0), ("1,234.56", 1234.56),
                        ("1.234,56", 1234.56), ("10.50", 10.5), ("(R$ 230,90)", -230.9)]:
    checar(f"extrato: {texto} vira {esperado}", leitor.converter_valor(texto) == esperado)
checar("extrato OFX: ponto e sempre decimal",
       leitor.ler_ofx("<STMTTRN><DTPOSTED>20261001<TRNAMT>-1.500<MEMO>x</STMTTRN>")[0]["valor"] == 1.5)
checar("extrato: 'Data Lancamento' nao vira a descricao",
       leitor.ler_csv("Data Lançamento;Histórico;Valor\n01/10/2026;Luz;-10,00\n")[0]["descricao"] == "Luz")
checar("extrato: 'Data Valor' nao vira o valor",
       leitor.ler_csv("Data;Data Valor;Histórico;Valor\n01/10/2026;02/10/2026;Luz;-10,00\n")[0]["valor"] == 10.0)
checar("extrato: acha o cabecalho depois de linhas soltas",
       leitor.ler_csv("Banco X\nData;Valor;Histórico\n01/10/2026;-10,00;Luz\n")[0]["descricao"] == "Luz")

cli_bug, id_bug = conta_limpa("bugs@a.com")
with app.test_request_context():
    cats_bug = banco.listar_categorias(id_bug)
    cat_d = next(l["id"] for l in cats_bug if l["tipo"] == "despesa")
    cat_e = next(l["id"] for l in cats_bug if l["tipo"] == "entrada")
gigante = "9" * 30
app.config["PROPAGATE_EXCEPTIONS"] = False
for rotulo, pedido, esperado in [
    ("editar com id gigante", lambda: cli_bug.get(f"/lancamento/{gigante}/editar"), 404),
    ("excluir com id gigante", lambda: cli_bug.post(f"/lancamento/{gigante}/excluir"), 404),
    ("excluir meta com id gigante", lambda: cli_bug.post(f"/meta/{gigante}/excluir"), 404),
    ("lancamento com categoria gigante", lambda: cli_bug.post("/lancamento/novo", data={
        "categoria_id": gigante, "valor": "10", "data": hoje}), 200),
    ("meta com categoria invalida", lambda: cli_bug.post("/meta/nova", data={
        "categoria_id": "²", "valor_limite": "10"}), 200),
    ("meta com limite nan", lambda: cli_bug.post("/meta/nova", data={
        "categoria_id": cat_d, "valor_limite": "nan"}), 200),
    ("meta com limite inf", lambda: cli_bug.post("/meta/nova", data={
        "categoria_id": cat_d, "valor_limite": "inf"}), 200),
    ("meta acima do maximo", lambda: cli_bug.post("/meta/nova", data={
        "categoria_id": cat_d, "valor_limite": "99999999,00"}), 200),
    ("configuracoes com categoria gigante", lambda: cli_bug.post("/configuracoes", data={
        "acao": "renomear_categoria", "categoria_id": gigante, "nome": "x"}), 302),
    ("importacao com categoria invalida", lambda: cli_bug.post("/importar/confirmar", data={
        "incluir": "0", "categoria_0": "²", "valor_0": "1", "data_0": hoje}), 302),
]:
    r = pedido()
    checar(f"{rotulo}: responde {esperado}, sem erro 500", r.status_code == esperado)
app.config["PROPAGATE_EXCEPTIONS"] = None
with app.test_request_context():
    checar("metas forjadas nao foram gravadas", not banco.listar_metas(id_bug, 2026, 1))

cli_bug.post("/lancamento/novo", data={"categoria_id": cat_d, "valor": "150.50", "data": hoje})
with app.test_request_context():
    checar("valor com ponto decimal: 150.50 nao vira 15050",
           [l["valor"] for l in banco.listar_todos_lancamentos(id_bug)] == [150.5])

ano_mes_dia = hoje.replace("-", "")
cli_bug.post("/importar/confirmar", data={"incluir": "0", "categoria_0": cat_d, "valor_0": "1",
                                          "data_0": ano_mes_dia, "descricao_0": ""})
with app.test_request_context():
    checar("importacao regrava a data como AAAA-MM-DD",
           all(len(l["data"]) == 10 for l in banco.listar_todos_lancamentos(id_bug)))
r = cli_bug.post("/importar/confirmar", follow_redirects=True, data={
    "incluir": ["0", "1"], "categoria_0": cat_d, "categoria_1": "", "valor_0": "2", "valor_1": "3",
    "data_0": hoje, "data_1": hoje, "descricao_0": "", "descricao_1": ""})
checar("importacao avisa quantas ficaram sem categoria", "1 ficaram de fora por não terem categoria" in corpo_de(r))

cli_bug.post("/configuracoes", data={"acao": "renomear_categoria", "categoria_id": cat_d, "nome": "   "})
cli_bug.post("/configuracoes", data={"acao": "cor_categoria", "categoria_id": cat_d, "cor": "naoecor"})
with app.test_request_context():
    linha = banco.buscar_categoria(id_bug, cat_d)
    checar("categoria nao fica com nome em branco", linha["nome"].strip() != "")
    checar("categoria so aceita cor da paleta", linha["cor"] in constantes.PALETA)
    banco.renomear_categoria(id_bug, cat_d, "D'Água');alert(1);//")
corpo = corpo_de(cli_bug.get("/configuracoes"))
checar("apostrofo no nome nao vira codigo no confirm", "alert(1);//?')" not in corpo and "\\u0027" in corpo)

with app.test_request_context():
    lanc = banco.listar_todos_lancamentos(id_bug)[0]
cli_bug.post(f"/lancamento/{lanc['id']}/editar", data={
    "categoria_id": cat_d, "valor": "10,00", "data": hoje, "descricao": "Café ☕ 日本語 — ok"})
r = tentar(lambda: cli_bug.get("/relatorio.pdf"))
checar("PDF nao quebra com emoji na descricao", r is not None and r.status_code == 200)

r = cli_bug.post(f"/lancamento/{lanc['id']}/excluir", headers={"Referer": "https://site-externo.example/x"})
checar("excluir nao redireciona para outro site", "site-externo" not in r.headers.get("Location", ""))

cli_mod, id_mod = conta_limpa("modelo@a.com")
with app.test_request_context():
    cat_mod = banco.listar_categorias(id_mod, "entrada")[0]["id"]
    banco.criar_lancamento(id_mod, "entrada", cat_mod, 10.0, hoje)
cli_mod.post("/configuracoes", data={"acao": "aplicar_perfil", "perfil": "arquiteto"})
with app.test_request_context():
    nomes_mod = [(l["tipo"], l["nome"]) for l in banco.listar_categorias(id_mod)]
    checar("reaplicar o modelo nao repete categoria", len(nomes_mod) == len(set(nomes_mod)))

_, id_float = conta_limpa("float@a.com")
with app.test_request_context():
    d_f = banco.listar_categorias(id_float, "despesa")[0]["id"]
    e_f = banco.listar_categorias(id_float, "entrada")[0]["id"]
    for v in (0.1, 0.2):
        banco.criar_lancamento(id_float, "despesa", d_f, v, "2026-03-05")
    banco.criar_lancamento(id_float, "entrada", e_f, 0.3, "2026-03-05")
    import analise                            # noqa: E402
    checar("saldo zerado nao vira negativo", analise.resumo_do_mes(id_float, 2026, 3)[2] == 0)
checar("formatar_reais nao mostra -R$ 0,00", constantes.formatar_reais(-0.001) == "R$ 0,00")

r = cli_bug.post("/importar", data={"extrato": (io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)), "grande.csv")},
                 content_type="multipart/form-data")
checar("extrato acima de 5 MB volta para a importacao",
       r.status_code == 302 and "/importar" in r.headers.get("Location", ""))


print(f"\n{n - len(falhas)}/{n} verificacoes passaram")
if falhas:
    print("FALHAS:", *falhas, sep="\n  - ")
    sys.exit(1)
print("tudo certo")
 






