# Fluxo — controle financeiro

Sistema web de controle financeiro para autônomos e pequenos negócios,
feito em **Python**. O servidor monta as telas, guarda os dados, desenha
os gráficos e gera o relatório em PDF.

## Tecnologias

| Camada | Ferramenta |
|---|---|
| Linguagem | Python 3.14 |
| Servidor web | Flask |
| Banco de dados | SQLite (módulo `sqlite3` da biblioteca padrão) |
| Telas | Jinja2 (sistema de templates do Flask) |
| Gráficos | matplotlib |
| Relatório em PDF | fpdf2 |
| Senhas | Werkzeug (hash com salt) |

O projeto **não usa JavaScript**: toda a lógica — login, cálculos, regras,
importação de extrato e geração dos gráficos e do PDF — roda em Python no
servidor. O navegador recebe apenas HTML e CSS já prontos.

## Como rodar

```bash
cd fluxo-python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Depois abra <http://localhost:5000> no navegador.

Na primeira execução o arquivo `fluxo.db` é criado sozinho, já com as tabelas.

## Estrutura

```
fluxo-python/
├── app.py           rotas: o que acontece em cada endereço do site
├── banco.py         todo o SQL; as outras partes nunca consultam direto
├── analise.py       cálculos: evolução do saldo e o comentário do mês
├── graficos.py      gráficos de rosca e de barras (matplotlib → PNG)
├── extrato.py       leitura de extratos bancários em CSV e OFX
├── relatorio.py     montagem do relatório em PDF
├── constantes.py    cores, meses, modelos de categorias
├── templates/       as telas em HTML (Jinja2)
├── static/          folha de estilo e ícones
└── fluxo.db         banco de dados (criado ao rodar)
```

## Banco de dados

Quatro tabelas relacionadas:

- **usuarios** — conta de acesso (e-mail, senha com hash, nome do negócio)
- **categorias** — categorias de entrada e de despesa de cada usuário
- **lancamentos** — cada movimentação: valor, data, categoria e descrição
- **metas** — limite mensal de gasto por categoria

As chaves estrangeiras estão ativas (`PRAGMA foreign_keys = ON`), e apagar
um usuário apaga em cascata tudo que é dele.

## Funcionalidades

- Cadastro e login com senha protegida por hash
- Painel mensal: entradas, despesas, saldo e comentário automático
- Gráficos de rosca por categoria e evolução do saldo em 6 meses
- Lançamentos com repetição por vários meses
- Metas de gasto por categoria, com alerta ao passar de 80% e de 100%
- Importação de extrato bancário em CSV e OFX, com tela de revisão
- Relatório completo em PDF, separado por mês

## Segurança

- As senhas nunca são guardadas em texto puro: o banco só tem o hash.
- Toda tela interna exige login (decorador `@exige_login`).
- Todas as consultas filtram pelo usuário da sessão, então um usuário não
  alcança os dados de outro.
- As consultas usam parâmetros (`?`), o que evita injeção de SQL.
