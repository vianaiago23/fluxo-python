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

print(f"\n{n - len(falhas)}/{n} verificacoes passaram")
if falhas:
    print("FALHAS:", *falhas, sep="\n  - ")
    sys.exit(1)
print("tudo certo")
