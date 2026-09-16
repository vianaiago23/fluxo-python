"""Fluxo — controle financeiro.

Aplicação web feita em Python com Flask. O servidor monta as telas,
guarda os dados no SQLite, desenha os gráficos e gera o relatório em PDF.
"""

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
from constantes import MESES, PALETA, PERFIS, formatar_reais

app = Flask(__name__)
app.secret_key = os.environ.get("FLUXO_SEGREDO", "chave-de-desenvolvimento-trocar-em-producao")
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


@app.before_request
def carregar_usuario():
    g.usuario = None
    if "usuario_id" in session:
        g.usuario = banco.buscar_usuario(session["usuario_id"])
        if g.usuario is None:          # conta apagada: derruba a sessão
            session.clear()


def mes_escolhido():
    """Lê ano e mês da URL; sem isso, usa o mês corrente."""
    hoje = date.today()
    try:
        ano = int(request.args.get("ano", hoje.year))
        mes = int(request.args.get("mes", hoje.month))
    except ValueError:
        return hoje.year, hoje.month
    return (ano, mes) if 1 <= mes <= 12 else (hoje.year, hoje.month)


def valor_do_formulario(campo):
    bruto = (request.form.get(campo) or "").replace(".", "").replace(",", ".")
    try:
        return float(bruto)
    except ValueError:
        return 0.0


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
            if len(senha) < 6:
                flash("A senha precisa ter 6 ou mais caracteres.", "erro")
            else:
                usuario_id = banco.criar_usuario(email, senha)
                if usuario_id is None:
                    flash("Já existe uma conta com esse e-mail.", "erro")
                else:
                    session["usuario_id"] = usuario_id
                    return redirect(url_for("perfil"))
        else:
            usuario_id = banco.autenticar(email, senha)
            if usuario_id is None:
                flash("E-mail ou senha incorretos.", "erro")
            else:
                session["usuario_id"] = usuario_id
                return redirect(url_for("painel"))

    return render_template("entrar.html", modo=modo)


@app.route("/sair")
def sair():
    session.clear()
    return redirect(url_for("entrar"))


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
    lancamentos = banco.listar_lancamentos_do_mes(usuario_id, ano, mes)
    mostrar_todos = request.args.get("todos") == "1"

    return render_template(
        "painel.html",
        ano=ano, mes=mes,
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
        hoje=date.today().isoformat(),
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
        categoria_id = request.form.get("categoria_id")
        limite = valor_do_formulario("valor_limite")
        if categoria_id and limite > 0:
            banco.salvar_meta(usuario_id, int(categoria_id), limite)
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
        categoria_id = request.form.get(f"categoria_{indice}")
        if not categoria_id:
            continue
        banco.criar_lancamento(
            usuario_id,
            request.form.get(f"tipo_{indice}"),
            int(categoria_id),
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
