"""Fluxo — controle financeiro.

Aplicação web feita em Python com Flask. O servidor monta as telas,
guarda os dados no SQLite, desenha os gráficos e gera o relatório em PDF.
"""

import hmac
import os
from datetime import date
from functools import wraps

from flask import (Flask, Response, flash, g, redirect, render_template,
                   request, session, url_for)

import analise
import banco
import extrato as leitor_extrato
import graficos
import relatorio
from constantes import MESES, PALETA, PERFIS, formatar_reais, hoje

# A Vercel define esta variável sozinha quando o sistema está publicado.
NA_VERCEL = bool(os.environ.get("VERCEL"))

MENSAGEM_RECUPERACAO = "Se existir uma conta com esse e-mail, enviamos as instruções."
SENHA_MINIMA = 6

# Publicado, o sistema ainda não envia e-mail: oferecer a recuperação seria
# prometer uma mensagem que nunca chega. Quando o envio existir, é só ligar.
RECUPERACAO_DISPONIVEL = not NA_VERCEL

segredo = os.environ.get("FLUXO_SEGREDO")
if not segredo:
    if NA_VERCEL:
        raise RuntimeError(
            "Falta a variável de ambiente FLUXO_SEGREDO. Ela assina os cookies "
            "de login: sem um valor fixo e secreto, qualquer pessoa poderia "
            "forjar uma sessão. Cadastre-a nas configurações do projeto."
        )
    segredo = "chave-de-desenvolvimento-trocar-em-producao"

app = Flask(__name__)
app.secret_key = segredo
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,      # o JavaScript da página não lê o cookie
    SESSION_COOKIE_SAMESITE="Lax",     # outro site não usa a sessão do usuário
    SESSION_COOKIE_SECURE=NA_VERCEL,   # publicado, o cookie só viaja em HTTPS
)
app.teardown_appcontext(banco.fechar)

# deixa as funções de formatação disponíveis dentro dos templates
app.jinja_env.globals.update(formatar_reais=formatar_reais, MESES=MESES, PALETA=PALETA)

banco.criar_tabelas()   # cria o fluxo.db na primeira vez que o sistema sobe


# ------------------------------------------------------------------- apoio

def exige_login(rota):
    """Impede o acesso às telas internas sem estar logado."""
    @wraps(rota)
    def verificar(*args, **kwargs):
        if "usuario_id" not in session:
            return redirect(url_for("entrar"))
        return rota(*args, **kwargs)
    return verificar


def marca_da_senha(usuario):
    """Resumo da senha atual, guardado na sessão. O cookie pode ser lido por
    quem o tem, por isso a marca é assinada e não revela o hash da senha."""
    return hmac.new(app.secret_key.encode(), usuario["senha_hash"].encode(), "sha256").hexdigest()


def abrir_sessao(usuario_id):
    session["usuario_id"] = usuario_id
    session["marca_senha"] = marca_da_senha(banco.buscar_usuario(usuario_id))


@app.before_request
def carregar_usuario():
    g.usuario = None
    if "usuario_id" in session:
        usuario = banco.buscar_usuario(session["usuario_id"])
        # Conta apagada ou senha trocada desde o login: derruba a sessão.
        if usuario and hmac.compare_digest(session.get("marca_senha", ""), marca_da_senha(usuario)):
            g.usuario = usuario
        else:
            session.clear()


def mes_escolhido():
    """Lê ano e mês da URL; sem isso, usa o mês corrente."""
    data_de_hoje = hoje()
    try:
        ano = int(request.args.get("ano", data_de_hoje.year))
        mes = int(request.args.get("mes", data_de_hoje.month))
    except ValueError:
        return data_de_hoje.year, data_de_hoje.month
    if 1 <= mes <= 12:
        return ano, mes
    return data_de_hoje.year, data_de_hoje.month


def ano_escolhido():
    """Lê ?ano= da URL; sem isso, ou fora de 1 a 9999, usa o ano corrente."""
    try:
        ano = int(request.args.get("ano", ""))
    except ValueError:
        return hoje().year
    return ano if 1 <= ano <= 9999 else hoje().year


def categoria_escolhida():
    """Lê ?categoria= da URL. Devolve o número, ou None para não filtrar.

    Não confere de quem é a categoria: a consulta já filtra pelo usuário,
    então uma categoria de outra conta simplesmente não mostra nada.
    """
    try:
        numero = int(request.args.get("categoria", ""))
    except ValueError:
        return None
    # Fora dessa faixa o SQLite recusa o número e a tela quebraria.
    return numero if 0 < numero < 2**63 else None


def data_da_url(campo):
    """Lê uma data AAAA-MM-DD da URL. Devolve o texto, ou None se não for data."""
    bruto = request.args.get(campo, "")
    try:
        # O fromisoformat aceita outros formatos (20260131); o banco só entende este.
        return bruto if len(bruto) == 10 and date.fromisoformat(bruto) else None
    except ValueError:
        return None


def periodo_escolhido():
    """Lê ?de= e ?ate= da URL. Devolve (inicio, fim); qualquer um pode ser None."""
    return data_da_url("de"), data_da_url("ate")


def valor_do_formulario(campo):
    bruto = (request.form.get(campo) or "").replace(".", "").replace(",", ".")
    try:
        return float(bruto)
    except ValueError:
        return 0.0


def problema_na_senha_nova(senha, confirmacao):
    """Devolve o que há de errado com a senha nova, ou None se está tudo certo."""
    if len(senha) < SENHA_MINIMA:
        return f"A senha precisa ter {SENHA_MINIMA} ou mais caracteres."
    if senha != confirmacao:
        return "A confirmação não é igual à senha nova."
    return None


# ------------------------------------------------------------------- acesso

@app.route("/entrar", methods=["GET", "POST"])
def entrar():
    if "usuario_id" in session:
        return redirect(url_for("painel"))

    modo = request.form.get("modo", request.args.get("modo", "login"))

    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        senha = request.form.get("senha") or ""

        if not email or not senha:
            flash("Preencha e-mail e senha.", "erro")
        elif modo == "cadastro":
            if len(senha) < SENHA_MINIMA:
                flash(f"A senha precisa ter {SENHA_MINIMA} ou mais caracteres.", "erro")
            else:
                usuario_id = banco.criar_usuario(email, senha)
                if usuario_id is None:
                    flash("Já existe uma conta com esse e-mail.", "erro")
                else:
                    abrir_sessao(usuario_id)
                    return redirect(url_for("perfil"))
        else:
            usuario_id = banco.autenticar(email, senha)
            if usuario_id is None:
                flash("E-mail ou senha incorretos.", "erro")
            else:
                abrir_sessao(usuario_id)
                return redirect(url_for("painel"))

    return render_template("entrar.html", modo=modo,
                           recuperacao_disponivel=RECUPERACAO_DISPONIVEL)


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("entrar"))


@app.route("/recuperar", methods=["GET", "POST"])
def recuperar():
    if "usuario_id" in session:
        return redirect(url_for("painel"))
    if not RECUPERACAO_DISPONIVEL:
        return redirect(url_for("entrar"))

    if request.method == "POST":
        usuario = banco.buscar_usuario_por_email(request.form.get("email") or "")
        if usuario and not banco.pedido_recente(usuario["id"]):
            token = banco.criar_token(usuario["id"])
            # Ainda não há envio de e-mail. Em desenvolvimento o link sai no
            # terminal; publicado, nunca: log não é lugar de credencial.
            if not NA_VERCEL:
                print("Link de recuperação:",
                      url_for("redefinir_senha", token=token, _external=True))
        # A resposta é a mesma existindo a conta ou não: se mudasse, qualquer
        # um descobriria quem tem conta testando e-mails.
        return render_template("recuperar.html", mensagem=MENSAGEM_RECUPERACAO)

    return render_template("recuperar.html", mensagem=None)


@app.route("/recuperar/<token>", methods=["GET", "POST"])
def redefinir_senha(token):
    valido = banco.buscar_token_valido(token) is not None

    if valido and request.method == "POST":
        senha = request.form.get("senha") or ""
        problema = problema_na_senha_nova(senha, request.form.get("confirmacao") or "")
        if problema:
            flash(problema, "erro")
        elif banco.redefinir_senha(token, senha):
            session.clear()
            flash("Senha alterada. Entre com a senha nova.", "ok")
            return redirect(url_for("entrar"))
        else:
            valido = False

    return render_template("nova_senha.html", valido=valido), (200 if valido else 400)


@app.route("/perfil", methods=["GET", "POST"])
@exige_login
def perfil():
    """Primeiro acesso: escolha do modelo de categorias."""
    if request.method == "POST":
        escolha = request.form.get("perfil")
        if escolha in PERFIS:
            banco.aplicar_perfil(session["usuario_id"], escolha)
            return redirect(url_for("painel"))
        flash("Escolha um dos modelos.", "erro")
    return render_template("perfil.html", perfis=PERFIS)


# ------------------------------------------------------------------- painel

@app.route("/")
@exige_login
def painel():
    usuario_id = session["usuario_id"]
    if not banco.listar_categorias(usuario_id):
        return redirect(url_for("perfil"))

    ano, mes = mes_escolhido()
    entradas, despesas, saldo = analise.resumo_do_mes(usuario_id, ano, mes)
    categoria_id = categoria_escolhida()
    inicio, fim = periodo_escolhido()
    periodo_invertido = bool(inicio and fim and inicio > fim)

    if periodo_invertido:
        lancamentos = []
    elif inicio or fim:
        # Com data preenchida, o período substitui o mês na lista.
        lancamentos = banco.listar_lancamentos(usuario_id, inicio, fim, categoria_id)
    else:
        lancamentos = banco.listar_lancamentos_do_mes(usuario_id, ano, mes, categoria_id)
    mostrar_todos = request.args.get("todos") == "1"

    # Filtros ativos, para os links do painel não perderem a escolha.
    filtros = {chave: valor for chave, valor in
               (("categoria", categoria_id), ("de", inicio), ("ate", fim))
               if valor is not None}

    return render_template(
        "painel.html",
        ano=ano, mes=mes,
        filtros=filtros,
        categoria_id=categoria_id,
        inicio=inicio, fim=fim,
        periodo_invertido=periodo_invertido,
        categorias_entrada=banco.listar_categorias(usuario_id, "entrada"),
        categorias_despesa=banco.listar_categorias(usuario_id, "despesa"),
        anterior=analise.mes_anterior(ano, mes),
        seguinte=(ano + 1, 1) if mes == 12 else (ano, mes + 1),
        entradas=entradas, despesas=despesas, saldo=saldo,
        por_entrada=banco.total_por_categoria(usuario_id, ano, mes, "entrada"),
        por_despesa=banco.total_por_categoria(usuario_id, ano, mes, "despesa"),
        metas=banco.listar_metas(usuario_id, ano, mes),
        lancamentos=lancamentos if mostrar_todos else lancamentos[:5],
        total_lancamentos=len(lancamentos),
        mostrar_todos=mostrar_todos,
        insight=analise.montar_insight(usuario_id, ano, mes),
    )


@app.get("/anual")
@exige_login
def relatorio_anual():
    """Os doze meses do ano em tabela, com o total no fim."""
    ano = ano_escolhido()
    meses, total = analise.resumo_do_ano(session["usuario_id"], ano)
    return render_template("anual.html", ano=ano, meses=meses, total=total)


# -------------------------------------------------------------- lançamentos

@app.route("/lancamento/novo", methods=["GET", "POST"])
@app.route("/lancamento/<int:lancamento_id>/editar", methods=["GET", "POST"])
@exige_login
def editar_lancamento(lancamento_id=None):
    usuario_id = session["usuario_id"]
    atual = banco.buscar_lancamento(usuario_id, lancamento_id) if lancamento_id else None
    if lancamento_id and atual is None:
        return redirect(url_for("painel"))

    if request.method == "POST":
        categoria_id = request.form.get("categoria_id")
        valor = valor_do_formulario("valor")
        data_mov = request.form.get("data") or ""
        descricao = request.form.get("descricao") or ""
        repetir = int(request.form.get("repetir") or 1)

        # o tipo não é escolhido à mão: vem da categoria selecionada
        categoria = banco.buscar_categoria(usuario_id, int(categoria_id)) if categoria_id else None
        tipo = categoria["tipo"] if categoria else "entrada"

        if categoria is None:
            flash("Escolha uma categoria.", "erro")
        elif valor <= 0:
            flash("Informe um valor maior que zero.", "erro")
        elif not data_mov:
            flash("Escolha uma data.", "erro")
        else:
            if atual:
                banco.atualizar_lancamento(usuario_id, lancamento_id, tipo,
                                           int(categoria_id), valor, data_mov, descricao)
            else:
                ano, mes, dia = (int(p) for p in data_mov.split("-"))
                for repeticao in range(max(1, min(repetir, 24))):
                    total = mes - 1 + repeticao
                    ano_alvo = ano + total // 12
                    mes_alvo = total % 12 + 1
                    ultimo_dia = [31, 29 if ano_alvo % 4 == 0 else 28, 31, 30, 31, 30,
                                  31, 31, 30, 31, 30, 31][mes_alvo - 1]
                    data_alvo = f"{ano_alvo:04d}-{mes_alvo:02d}-{min(dia, ultimo_dia):02d}"
                    banco.criar_lancamento(usuario_id, tipo, int(categoria_id),
                                           valor, data_alvo, descricao)
            return redirect(url_for("painel", ano=data_mov[:4], mes=int(data_mov[5:7])))

    return render_template(
        "lancamento.html",
        atual=atual,
        entradas=banco.listar_categorias(usuario_id, "entrada"),
        despesas=banco.listar_categorias(usuario_id, "despesa"),
        hoje=hoje().isoformat(),
    )


@app.post("/lancamento/<int:lancamento_id>/excluir")
@exige_login
def excluir_lancamento(lancamento_id):
    banco.excluir_lancamento(session["usuario_id"], lancamento_id)
    flash("Lançamento excluído.", "ok")
    return redirect(request.referrer or url_for("painel"))


# -------------------------------------------------------------------- metas

@app.route("/meta/nova", methods=["GET", "POST"])
@exige_login
def nova_meta():
    usuario_id = session["usuario_id"]
    categorias = banco.listar_categorias(usuario_id, "despesa")

    if request.method == "POST":
        categoria_id = request.form.get("categoria_id") or ""
        limite = valor_do_formulario("valor_limite")
        # só aceita categoria de despesa que pertença a quem está logado
        categoria = (banco.buscar_categoria(usuario_id, int(categoria_id))
                     if categoria_id.isdigit() else None)
        if categoria and categoria["tipo"] == "despesa" and limite > 0:
            banco.salvar_meta(usuario_id, categoria["id"], limite)
            return redirect(url_for("painel"))
        flash("Escolha a categoria e informe um valor válido.", "erro")

    return render_template("meta.html", categorias=categorias)


@app.post("/meta/<int:meta_id>/excluir")
@exige_login
def excluir_meta(meta_id):
    banco.excluir_meta(session["usuario_id"], meta_id)
    return redirect(url_for("painel"))


# ------------------------------------------------------------ configurações

@app.route("/configuracoes", methods=["GET", "POST"])
@exige_login
def configuracoes():
    usuario_id = session["usuario_id"]

    if request.method == "POST":
        acao = request.form.get("acao")

        if acao == "nome":
            banco.renomear_negocio(usuario_id, request.form.get("nome_negocio", ""))
            flash("Nome atualizado.", "ok")

        elif acao == "nova_categoria":
            nome = (request.form.get("nome") or "").strip()
            tipo = request.form.get("tipo")
            if nome and tipo in ("entrada", "despesa"):
                banco.criar_categoria(usuario_id, tipo, nome)
            else:
                flash("Informe o nome da categoria.", "erro")

        elif acao == "renomear_categoria":
            banco.renomear_categoria(usuario_id, int(request.form["categoria_id"]),
                                     request.form.get("nome", ""))

        elif acao == "cor_categoria":
            banco.trocar_cor_categoria(usuario_id, int(request.form["categoria_id"]),
                                       request.form.get("cor", PALETA[0]))

        elif acao == "excluir_categoria":
            if not banco.excluir_categoria(usuario_id, int(request.form["categoria_id"])):
                flash("Essa categoria tem lançamentos e não pode ser excluída. "
                      "Edite ou remova os lançamentos primeiro.", "erro")

        elif acao == "aplicar_perfil":
            escolha = request.form.get("perfil")
            if escolha in PERFIS:
                banco.aplicar_perfil(usuario_id, escolha)
                flash("Modelo aplicado.", "ok")

        elif acao == "apagar_dados":
            banco.apagar_dados(usuario_id)
            flash("Todos os dados foram apagados.", "ok")
            return redirect(url_for("perfil"))

        elif acao == "trocar_senha":
            senha_nova = request.form.get("senha_nova") or ""
            problema = problema_na_senha_nova(senha_nova, request.form.get("confirmacao") or "")
            # Sem conferir a atual, quem achasse a sessão aberta tomaria a conta.
            if not banco.conferir_senha(usuario_id, request.form.get("senha_atual") or ""):
                flash("A senha atual está incorreta.", "erro")
            elif problema:
                flash(problema, "erro")
            else:
                banco.trocar_senha(usuario_id, senha_nova)
                abrir_sessao(usuario_id)   # só este navegador continua logado
                flash("Senha alterada. Os outros aparelhos foram desconectados.", "ok")

        elif acao == "excluir_conta":
            # Não tem como desfazer: só a senha confirma a exclusão.
            if banco.conferir_senha(usuario_id, request.form.get("senha") or ""):
                banco.excluir_conta(usuario_id)
                session.clear()
                flash("Sua conta foi excluída.", "ok")
                return redirect(url_for("entrar"))
            flash("Senha incorreta. A conta não foi excluída.", "erro")

        return redirect(url_for("configuracoes"))

    return render_template(
        "configuracoes.html",
        entradas=banco.listar_categorias(usuario_id, "entrada"),
        despesas=banco.listar_categorias(usuario_id, "despesa"),
        perfis=PERFIS,
    )


# ---------------------------------------------------------------- importação

@app.route("/importar", methods=["GET", "POST"])
@exige_login
def importar():
    if request.method == "POST":
        arquivo = request.files.get("extrato")
        if not arquivo or not arquivo.filename:
            flash("Escolha um arquivo .csv ou .ofx.", "erro")
            return redirect(url_for("importar"))

        movimentos = leitor_extrato.ler_extrato(arquivo.filename, arquivo.read())
        if not movimentos:
            flash("Não foi possível ler nenhum lançamento desse arquivo.", "erro")
            return redirect(url_for("importar"))

        usuario_id = session["usuario_id"]
        return render_template(
            "importar_revisar.html",
            movimentos=movimentos,
            categorias_entrada=banco.listar_categorias(usuario_id, "entrada"),
            categorias_despesa=banco.listar_categorias(usuario_id, "despesa"),
        )

    return render_template("importar.html")


@app.post("/importar/confirmar")
@exige_login
def confirmar_importacao():
    """Grava só as linhas marcadas na tela de revisão."""
    usuario_id = session["usuario_id"]
    gravados = 0

    for indice in request.form.getlist("incluir"):
        categoria_id = request.form.get(f"categoria_{indice}") or ""
        # a categoria precisa ser do usuário logado; o tipo vem dela, não do formulário
        categoria = (banco.buscar_categoria(usuario_id, int(categoria_id))
                     if categoria_id.isdigit() else None)
        if categoria is None:
            continue
        banco.criar_lancamento(
            usuario_id,
            categoria["tipo"],
            categoria["id"],
            float(request.form.get(f"valor_{indice}")),
            request.form.get(f"data_{indice}"),
            request.form.get(f"descricao_{indice}") or "",
        )
        gravados += 1

    if gravados:
        flash(f"{gravados} lançamento(s) importado(s).", "ok")
    else:
        flash("Nenhum lançamento foi importado.", "erro")
    return redirect(url_for("painel"))


# --------------------------------------------------------- gráficos e PDF

@app.get("/grafico/<tipo>.png")
@exige_login
def grafico(tipo):
    usuario_id = session["usuario_id"]
    ano, mes = mes_escolhido()

    if tipo in ("entradas", "despesas"):
        genero = "entrada" if tipo == "entradas" else "despesa"
        linhas = banco.total_por_categoria(usuario_id, ano, mes, genero)
        imagem = graficos.rosca([(l["nome"], l["total"], l["cor"]) for l in linhas])
    elif tipo == "saldo":
        rotulos, valores = analise.serie_saldo(usuario_id, ano, mes)
        imagem = graficos.barras_saldo(rotulos, valores)
    else:
        return "Gráfico desconhecido", 404

    return Response(imagem, mimetype="image/png",
                    headers={"Cache-Control": "no-store"})


@app.get("/relatorio.pdf")
@exige_login
def baixar_relatorio():
    usuario_id = session["usuario_id"]
    lancamentos = [dict(l) for l in banco.listar_todos_lancamentos(usuario_id)]
    if not lancamentos:
        flash("Nenhum lançamento para exportar ainda.", "erro")
        return redirect(url_for("painel"))

    pdf = relatorio.gerar_pdf(g.usuario["nome_negocio"], lancamentos)
    return Response(
        pdf, mimetype="application/pdf",
        headers={"Content-Disposition": "attachment; filename=fluxo-relatorio.pdf"},
    )


if __name__ == "__main__":
    # No macOS a porta 5000 costuma estar ocupada pelo AirPlay, por isso 5001.
    porta = int(os.environ.get("PORT", 5001))
    app.run(debug=True, port=porta)
