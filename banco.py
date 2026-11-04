"""Camada de banco de dados (SQLite).

Todo o SQL do sistema fica aqui. As rotas e as telas nunca escrevem
consultas direto — elas chamam as funções deste arquivo.

O banco é o mesmo nos dois lugares em que o sistema roda:

* no computador, é o arquivo ``fluxo.db`` criado ao lado deste código;
* publicado na internet, é o mesmo SQLite hospedado no Turso, acessado por
  HTTP. Isso é necessário porque o servidor da Vercel descarta o disco a cada
  requisição: um arquivo local ali seria apagado junto com os dados.

As duas bibliotecas seguem a mesma interface (DB-API 2.0), então o SQL abaixo
não muda de um caso para o outro.
"""

import hashlib
import os
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import turso_serverless
from flask import g
from werkzeug.security import check_password_hash, generate_password_hash

from constantes import PALETA, PERFIS, hoje

CAMINHO_BANCO = Path(__file__).parent / "fluxo.db"

TURSO_URL = os.environ.get("TURSO_DATABASE_URL")
TURSO_TOKEN = os.environ.get("TURSO_AUTH_TOKEN")
NA_NUVEM = bool(TURSO_URL)

# Cada biblioteca tem a sua própria exceção para "esse valor já existe".
ErroIntegridade = (sqlite3.IntegrityError, turso_serverless.IntegrityError)

ESQUEMA = """
CREATE TABLE IF NOT EXISTS usuarios (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    email        TEXT    NOT NULL UNIQUE,
    senha_hash   TEXT    NOT NULL,
    nome_negocio TEXT    NOT NULL DEFAULT 'Meu Negócio',
    criado_em    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS categorias (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo       TEXT    NOT NULL CHECK (tipo IN ('entrada', 'despesa')),
    nome       TEXT    NOT NULL,
    cor        TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS lancamentos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    tipo         TEXT    NOT NULL CHECK (tipo IN ('entrada', 'despesa')),
    valor        REAL    NOT NULL CHECK (valor > 0),
    data         TEXT    NOT NULL,
    descricao    TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS metas (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL UNIQUE REFERENCES categorias(id) ON DELETE CASCADE,
    valor_limite REAL    NOT NULL CHECK (valor_limite > 0)
);

CREATE TABLE IF NOT EXISTS tokens_recuperacao (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    token      TEXT    NOT NULL UNIQUE,
    expira_em  TEXT    NOT NULL,
    usado      INTEGER NOT NULL DEFAULT 0 CHECK (usado IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_lancamentos_usuario_data
    ON lancamentos (usuario_id, data);
"""

MINUTOS_VALIDADE_TOKEN = 60
MINUTOS_ENTRE_PEDIDOS = 5


# ------------------------------------------------------------------ conexão

def abrir_conexao():
    """Abre uma conexão nova: no Turso, se houver credencial; senão no arquivo."""
    if NA_NUVEM:
        conexao = turso_serverless.connect(TURSO_URL, auth_token=TURSO_TOKEN)
        conexao.row_factory = turso_serverless.Row
    else:
        conexao = sqlite3.connect(CAMINHO_BANCO)
        conexao.row_factory = sqlite3.Row

    try:
        conexao.execute("PRAGMA foreign_keys = ON")
    except (sqlite3.Error, turso_serverless.Error):
        pass   # no servidor do Turso as chaves estrangeiras já vêm ligadas
    return conexao


def conectar():
    """Devolve a conexão da requisição atual, abrindo uma se preciso."""
    if "banco" not in g:
        g.banco = abrir_conexao()
    return g.banco


def fechar(_erro=None):
    banco = g.pop("banco", None)
    if banco is not None:
        banco.close()


def criar_tabelas():
    """Cria o banco e as tabelas, se ainda não existirem."""
    banco = abrir_conexao()
    banco.executescript(ESQUEMA)
    banco.commit()
    banco.close()


# ------------------------------------------------------------------ usuários

def criar_usuario(email, senha):
    """Cadastra um usuário. Devolve o id, ou None se o e-mail já existe."""
    banco = conectar()
    try:
        cursor = banco.execute(
            "INSERT INTO usuarios (email, senha_hash, criado_em) VALUES (?, ?, ?)",
            (email.strip().lower(), generate_password_hash(senha), hoje().isoformat()),
        )
        banco.commit()
        return cursor.lastrowid
    except ErroIntegridade:
        return None


def autenticar(email, senha):
    """Confere e-mail e senha. Devolve o id do usuário, ou None."""
    linha = conectar().execute(
        "SELECT id, senha_hash FROM usuarios WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()
    if linha and check_password_hash(linha["senha_hash"], senha):
        return linha["id"]
    return None


def buscar_usuario(usuario_id):
    return conectar().execute(
        "SELECT id, email, nome_negocio FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()


def renomear_negocio(usuario_id, nome):
    banco = conectar()
    banco.execute("UPDATE usuarios SET nome_negocio = ? WHERE id = ?",
                  (nome.strip() or "Meu Negócio", usuario_id))
    banco.commit()


def conferir_senha(usuario_id, senha):
    linha = conectar().execute(
        "SELECT senha_hash FROM usuarios WHERE id = ?", (usuario_id,)
    ).fetchone()
    return bool(linha) and check_password_hash(linha["senha_hash"], senha)


def buscar_usuario_por_email(email):
    return conectar().execute(
        "SELECT id, email, nome_negocio FROM usuarios WHERE email = ?",
        (email.strip().lower(),),
    ).fetchone()


# ----------------------------------------------------- recuperação de senha

def _instante(minutos=0):
    """Agora + minutos em texto ISO. Sempre em UTC, para dar para comparar os textos."""
    momento = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    return momento.isoformat(timespec="seconds")


def _hash_do_token(token):
    """O banco guarda só o hash: quem lê o banco não consegue usar o link."""
    return hashlib.sha256(token.encode()).hexdigest()


def criar_token(usuario_id):
    """Gera o token de recuperação e devolve o texto que vai no link."""
    token = secrets.token_urlsafe(32)   # imprevisível, ao contrário do random
    banco = conectar()
    # Limpa só o que já não vale. Um link ainda válido continua valendo: se o
    # pedido novo o cancelasse, qualquer um derrubaria o link de outra pessoa.
    banco.execute(
        "DELETE FROM tokens_recuperacao WHERE usuario_id = ? AND (usado = 1 OR expira_em <= ?)",
        (usuario_id, _instante()),
    )
    banco.execute(
        "INSERT INTO tokens_recuperacao (usuario_id, token, expira_em) VALUES (?, ?, ?)",
        (usuario_id, _hash_do_token(token), _instante(MINUTOS_VALIDADE_TOKEN)),
    )
    banco.commit()
    return token


def pedido_recente(usuario_id):
    """Diz se a conta já pediu um link nos últimos minutos.

    Como todo token vale o mesmo tempo, dá para saber quando ele foi criado
    pela expiração. O length ignora tokens antigos, que guardavam só a data.
    """
    limite = _instante(MINUTOS_VALIDADE_TOKEN - MINUTOS_ENTRE_PEDIDOS)
    linha = conectar().execute(
        "SELECT COUNT(*) AS n FROM tokens_recuperacao "
        "WHERE usuario_id = ? AND usado = 0 AND expira_em > ? AND length(expira_em) > 10",
        (usuario_id, limite),
    ).fetchone()
    return linha["n"] > 0


def buscar_token(token):
    return conectar().execute(
        "SELECT * FROM tokens_recuperacao WHERE token = ?", (_hash_do_token(token),)
    ).fetchone()


def buscar_token_valido(token):
    """Devolve o token só se ele existe, não foi usado e não expirou."""
    linha = buscar_token(token)
    if linha and not linha["usado"] and linha["expira_em"] > _instante():
        return linha
    return None


def _gravar_senha(banco, usuario_id, senha_hash):
    """Grava a senha e cancela os pedidos pendentes. Quem chama faz o commit."""
    banco.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?",
                  (senha_hash, usuario_id))
    banco.execute("UPDATE tokens_recuperacao SET usado = 1 WHERE usuario_id = ?",
                  (usuario_id,))


def trocar_senha(usuario_id, senha_nova):
    senha_hash = generate_password_hash(senha_nova)
    banco = conectar()
    _gravar_senha(banco, usuario_id, senha_hash)
    banco.commit()


def redefinir_senha(token, senha_nova):
    """Consome o token e troca a senha. Devolve False se o token não vale.

    As duas coisas vão na mesma transação: se a gravação da senha falhar, o
    token continua valendo e a pessoa pode tentar de novo.
    """
    linha = buscar_token_valido(token)
    if linha is None:
        return False
    senha_hash = generate_password_hash(senha_nova)
    banco = conectar()
    # O "usado = 0" garante que, em dois envios simultâneos, só um passe.
    cursor = banco.execute(
        "UPDATE tokens_recuperacao SET usado = 1 WHERE id = ? AND usado = 0",
        (linha["id"],),
    )
    if cursor.rowcount != 1:
        banco.rollback()
        return False
    _gravar_senha(banco, linha["usuario_id"], senha_hash)
    banco.commit()
    return True


# ---------------------------------------------------------------- categorias

def listar_categorias(usuario_id, tipo=None):
    sql = "SELECT * FROM categorias WHERE usuario_id = ?"
    parametros = [usuario_id]
    if tipo:
        sql += " AND tipo = ?"
        parametros.append(tipo)
    return conectar().execute(sql + " ORDER BY id", parametros).fetchall()


def buscar_categoria(usuario_id, categoria_id):
    return conectar().execute(
        "SELECT * FROM categorias WHERE id = ? AND usuario_id = ?",
        (categoria_id, usuario_id),
    ).fetchone()


def criar_categoria(usuario_id, tipo, nome, cor=None):
    banco = conectar()
    if cor is None:
        quantas = banco.execute(
            "SELECT COUNT(*) AS n FROM categorias WHERE usuario_id = ? AND tipo = ?",
            (usuario_id, tipo),
        ).fetchone()["n"]
        cor = PALETA[quantas % len(PALETA)]
    banco.execute(
        "INSERT INTO categorias (usuario_id, tipo, nome, cor) VALUES (?, ?, ?, ?)",
        (usuario_id, tipo, nome.strip(), cor),
    )
    banco.commit()


def renomear_categoria(usuario_id, categoria_id, nome):
    banco = conectar()
    banco.execute(
        "UPDATE categorias SET nome = ? WHERE id = ? AND usuario_id = ?",
        (nome.strip(), categoria_id, usuario_id),
    )
    banco.commit()


def trocar_cor_categoria(usuario_id, categoria_id, cor):
    banco = conectar()
    banco.execute(
        "UPDATE categorias SET cor = ? WHERE id = ? AND usuario_id = ?",
        (cor, categoria_id, usuario_id),
    )
    banco.commit()


def categoria_tem_lancamentos(usuario_id, categoria_id):
    linha = conectar().execute(
        "SELECT COUNT(*) AS n FROM lancamentos WHERE usuario_id = ? AND categoria_id = ?",
        (usuario_id, categoria_id),
    ).fetchone()
    return linha["n"] > 0


def excluir_categoria(usuario_id, categoria_id):
    """Só apaga se nenhuma movimentação usar a categoria."""
    if categoria_tem_lancamentos(usuario_id, categoria_id):
        return False
    banco = conectar()
    banco.execute("DELETE FROM categorias WHERE id = ? AND usuario_id = ?",
                  (categoria_id, usuario_id))
    banco.commit()
    return True


def aplicar_perfil(usuario_id, chave_perfil):
    """Troca as categorias do usuário pelas do modelo escolhido."""
    perfil = PERFIS[chave_perfil]
    banco = conectar()
    banco.execute("DELETE FROM metas WHERE usuario_id = ?", (usuario_id,))
    banco.execute(
        "DELETE FROM categorias WHERE usuario_id = ? AND id NOT IN "
        "(SELECT DISTINCT categoria_id FROM lancamentos WHERE usuario_id = ?)",
        (usuario_id, usuario_id),
    )
    for tipo in ("entrada", "despesa"):
        for posicao, nome in enumerate(perfil[tipo]):
            banco.execute(
                "INSERT INTO categorias (usuario_id, tipo, nome, cor) VALUES (?, ?, ?, ?)",
                (usuario_id, tipo, nome, PALETA[posicao % len(PALETA)]),
            )
    if chave_perfil != "generico":
        banco.execute("UPDATE usuarios SET nome_negocio = ? WHERE id = ?",
                      (perfil["rotulo"], usuario_id))
    banco.commit()


# --------------------------------------------------------------- lançamentos

def listar_lancamentos_do_mes(usuario_id, ano, mes):
    prefixo = f"{ano:04d}-{mes:02d}"
    return conectar().execute(
        "SELECT l.*, c.nome AS categoria_nome, c.cor AS categoria_cor "
        "FROM lancamentos l JOIN categorias c ON c.id = l.categoria_id "
        "WHERE l.usuario_id = ? AND l.data LIKE ? "
        "ORDER BY l.data DESC, l.id DESC",
        (usuario_id, prefixo + "%"),
    ).fetchall()


def listar_todos_lancamentos(usuario_id):
    return conectar().execute(
        "SELECT l.*, c.nome AS categoria_nome "
        "FROM lancamentos l JOIN categorias c ON c.id = l.categoria_id "
        "WHERE l.usuario_id = ? ORDER BY l.data, l.id",
        (usuario_id,),
    ).fetchall()


def buscar_lancamento(usuario_id, lancamento_id):
    return conectar().execute(
        "SELECT * FROM lancamentos WHERE id = ? AND usuario_id = ?",
        (lancamento_id, usuario_id),
    ).fetchone()


def criar_lancamento(usuario_id, tipo, categoria_id, valor, data_mov, descricao=""):
    banco = conectar()
    banco.execute(
        "INSERT INTO lancamentos (usuario_id, categoria_id, tipo, valor, data, descricao) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (usuario_id, categoria_id, tipo, valor, data_mov, descricao.strip()),
    )
    banco.commit()


def atualizar_lancamento(usuario_id, lancamento_id, tipo, categoria_id,
                         valor, data_mov, descricao=""):
    banco = conectar()
    banco.execute(
        "UPDATE lancamentos SET tipo = ?, categoria_id = ?, valor = ?, data = ?, "
        "descricao = ? WHERE id = ? AND usuario_id = ?",
        (tipo, categoria_id, valor, data_mov, descricao.strip(),
         lancamento_id, usuario_id),
    )
    banco.commit()


def excluir_lancamento(usuario_id, lancamento_id):
    banco = conectar()
    banco.execute("DELETE FROM lancamentos WHERE id = ? AND usuario_id = ?",
                  (lancamento_id, usuario_id))
    banco.commit()


def total_por_categoria(usuario_id, ano, mes, tipo):
    """Soma os valores do mês agrupando por categoria."""
    prefixo = f"{ano:04d}-{mes:02d}"
    return conectar().execute(
        "SELECT c.id, c.nome, c.cor, COALESCE(SUM(l.valor), 0) AS total "
        "FROM categorias c "
        "LEFT JOIN lancamentos l ON l.categoria_id = c.id "
        "AND l.usuario_id = c.usuario_id AND l.data LIKE ? "
        "WHERE c.usuario_id = ? AND c.tipo = ? "
        "GROUP BY c.id ORDER BY total DESC",
        (prefixo + "%", usuario_id, tipo),
    ).fetchall()


def somar_mes(usuario_id, ano, mes, tipo):
    prefixo = f"{ano:04d}-{mes:02d}"
    linha = conectar().execute(
        "SELECT COALESCE(SUM(valor), 0) AS total FROM lancamentos "
        "WHERE usuario_id = ? AND tipo = ? AND data LIKE ?",
        (usuario_id, tipo, prefixo + "%"),
    ).fetchone()
    return linha["total"]


# --------------------------------------------------------------------- metas

def listar_metas(usuario_id, ano, mes):
    """Metas com o quanto já foi gasto no mês."""
    prefixo = f"{ano:04d}-{mes:02d}"
    return conectar().execute(
        "SELECT m.id, m.valor_limite, c.id AS categoria_id, c.nome, c.cor, "
        "COALESCE(("
        "  SELECT SUM(l.valor) FROM lancamentos l "
        "  WHERE l.categoria_id = c.id AND l.usuario_id = m.usuario_id AND l.data LIKE ?"
        "), 0) AS gasto "
        "FROM metas m JOIN categorias c ON c.id = m.categoria_id "
        "WHERE m.usuario_id = ? ORDER BY c.nome",
        (prefixo + "%", usuario_id),
    ).fetchall()


def salvar_meta(usuario_id, categoria_id, valor_limite):
    banco = conectar()
    banco.execute(
        "INSERT INTO metas (usuario_id, categoria_id, valor_limite) VALUES (?, ?, ?) "
        "ON CONFLICT(categoria_id) DO UPDATE SET valor_limite = excluded.valor_limite "
        "WHERE metas.usuario_id = excluded.usuario_id",
        (usuario_id, categoria_id, valor_limite),
    )
    banco.commit()


def excluir_meta(usuario_id, meta_id):
    banco = conectar()
    banco.execute("DELETE FROM metas WHERE id = ? AND usuario_id = ?",
                  (meta_id, usuario_id))
    banco.commit()


def apagar_dados(usuario_id):
    """Apaga tudo do usuário, menos a conta em si."""
    banco = conectar()
    banco.execute("DELETE FROM metas WHERE usuario_id = ?", (usuario_id,))
    banco.execute("DELETE FROM lancamentos WHERE usuario_id = ?", (usuario_id,))
    banco.execute("DELETE FROM categorias WHERE usuario_id = ?", (usuario_id,))
    banco.commit()


def excluir_conta(usuario_id):
    """Apaga o usuário e tudo que é dele, na mesma transação.

    O ON DELETE CASCADE já faria isso, mas depende de as chaves estrangeiras
    estarem ligadas na conexão. Aqui a promessa de apagar tudo não depende disso.
    """
    banco = conectar()
    for tabela in ("metas", "lancamentos", "categorias", "tokens_recuperacao"):
        banco.execute(f"DELETE FROM {tabela} WHERE usuario_id = ?", (usuario_id,))
    banco.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
    banco.commit()
