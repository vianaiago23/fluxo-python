"""Prepara e confere o banco hospedado no Turso.

Rode uma vez, antes de publicar, com as credenciais no ambiente:

    export TURSO_DATABASE_URL="libsql://...turso.io"
    export TURSO_AUTH_TOKEN="..."
    python preparar_nuvem.py

O script cria as tabelas (se ainda nao existirem), confere se a
estrutura ficou igual a do banco local e grava e apaga um registro de teste
para provar que o sistema consegue ler e escrever na nuvem.
"""

import os
import re
import sys

# O Python instalado no macOS costuma vir sem os certificados raiz, e sem eles
# a conexao HTTPS com o Turso falha. O pacote certifi traz a lista.
if not os.environ.get("SSL_CERT_FILE"):
    try:
        import certifi
        os.environ["SSL_CERT_FILE"] = certifi.where()
    except ModuleNotFoundError:
        pass

import banco

# A lista sai do proprio esquema, em vez de ser escrita aqui a mao: assim,
# quem criar uma tabela nova no banco.py nao precisa lembrar de mexer neste
# arquivo. Ja aconteceu de a lista envelhecer e o script dizer que estava
# tudo certo com uma tabela faltando no servidor.
TABELAS_ESPERADAS = set(re.findall(
    r"CREATE TABLE IF NOT EXISTS\s+([a-z_]+)", banco.ESQUEMA))


def main():
    if not banco.NA_NUVEM:
        print("Nao achei TURSO_DATABASE_URL no ambiente. Exporte as credenciais "
              "antes de rodar (veja o comentario no inicio deste arquivo).")
        return 1

    print(f"banco: {banco.TURSO_URL}")
    if not banco.TURSO_TOKEN:
        print("Falta TURSO_AUTH_TOKEN.")
        return 1

    print("criando as tabelas, se preciso...")
    banco.criar_tabelas()

    conexao = banco.abrir_conexao()

    nomes = {l["name"] for l in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'")}
    faltando = TABELAS_ESPERADAS - nomes
    if faltando:
        print("FALHA: nao foram criadas as tabelas:", ", ".join(sorted(faltando)))
        return 1
    print(f"tabelas no banco ({len(TABELAS_ESPERADAS)}):",
          ", ".join(sorted(TABELAS_ESPERADAS)))

    indices = {l["name"] for l in conexao.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'")}
    print("indice de consulta:",
          "ok" if "idx_lancamentos_usuario_data" in indices else "FALTANDO")

    print("testando escrita e leitura...")
    conexao.execute(
        "INSERT INTO usuarios (email, senha_hash, criado_em) VALUES (?, ?, ?)",
        ("teste-de-conexao@fluxo.local", "x", "2026-01-01"))
    conexao.commit()
    linha = conexao.execute(
        "SELECT id, email FROM usuarios WHERE email = ?",
        ("teste-de-conexao@fluxo.local",)).fetchone()
    if linha is None:
        print("FALHA: gravou mas nao conseguiu ler de volta.")
        return 1
    print(f"  gravou e leu o registro de teste (id {linha['id']})")

    conexao.execute("DELETE FROM usuarios WHERE email = ?",
                    ("teste-de-conexao@fluxo.local",))
    conexao.commit()
    sobrou = conexao.execute(
        "SELECT COUNT(*) AS n FROM usuarios WHERE email = ?",
        ("teste-de-conexao@fluxo.local",)).fetchone()["n"]
    print("  apagou o registro de teste:", "ok" if sobrou == 0 else "FALHA")

    contas = conexao.execute("SELECT COUNT(*) AS n FROM usuarios").fetchone()["n"]
    conexao.close()

    print(f"\nbanco pronto. contas cadastradas hoje: {contas}")
    return 0 if sobrou == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
