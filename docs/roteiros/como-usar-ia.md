# Como usar uma IA para te ajudar na sua parte

Pode usar. O que não funciona é pedir "faça o item 19 inteiro", colar o
resultado e commitar: na hora de explicar o que você fez, não vai ter como.
E, na prática, o código vem quase certo e quebra em algum detalhe que só quem
leu o projeto percebe.

O que funciona é dar contexto e pedir ajuda em pedaços.

## Passo 1 — dê o contexto

Cole isto na primeira mensagem, trocando o que está entre colchetes:

---

> Estou trabalhando num sistema web de controle financeiro chamado Fluxo,
> feito em Python com Flask e SQLite. É um trabalho de faculdade, em grupo,
> e eu fiquei responsável por uma parte específica.
>
> Como o sistema é organizado:
> - `app.py` — as rotas (o que acontece em cada endereço do site)
> - `banco.py` — **todo** o SQL. Nenhum outro arquivo consulta o banco direto
> - `analise.py` — cálculos de saldo e o comentário do mês
> - `graficos.py` — gráficos em matplotlib, devolvidos como PNG
> - `extrato.py` — leitura de extrato bancário em CSV e OFX
> - `relatorio.py` — relatório em PDF (fpdf2)
> - `constantes.py` — cores, meses, modelos de categoria, data no fuso do Brasil
> - `templates/` — as telas em HTML (Jinja2)
> - `testar_fumaca.py` — teste automático, 28 verificações
>
> O banco tem quatro tabelas: `usuarios`, `categorias`, `lancamentos` e
> `metas`. O esquema completo está no começo do `banco.py`.
>
> Regras do projeto que eu preciso seguir:
> - SQL só dentro do `banco.py`
> - toda consulta filtra pelo usuário logado (um usuário nunca pode alcançar
>   dado de outro)
> - consultas usam parâmetros `?`, nunca texto montado na mão
> - datas usam a função `hoje()` do `constantes.py`, não `date.today()`
> - antes de commitar, `python testar_fumaca.py` tem que dar 28/28
>
> **Minha tarefa é:** [cole aqui o texto do seu item, tirado do seu roteiro]
>
> Não escreva a solução inteira de uma vez. Me explique primeiro como você
> faria e quais arquivos mexem. Eu escrevo o código e te mostro para você
> revisar.

---

## Passo 2 — trabalhe em pedaços

Peça uma coisa por vez: "como eu leio esse parâmetro da URL?", "essa consulta
está filtrando pelo usuário certo?", "por que esse teste falhou?".

Mande o seu código para ela revisar. É aí que a ajuda rende mais.

## Passo 3 — antes de commitar

- [ ] Eu entendi cada linha do que estou enviando?
- [ ] Consigo explicar na apresentação por que fiz assim?
- [ ] `python testar_fumaca.py` deu 28/28?
- [ ] `git status` não mostra `.env.local`, `fluxo.db` nem `.venv/`?

Se a resposta de alguma for não, não commite ainda.

## Coisas que a IA costuma errar neste projeto

- **Esquecer o filtro de usuário.** Ela escreve
  `WHERE categoria_id = ?` e esquece o `AND usuario_id = ?`. Esse bug já
  aconteceu aqui de verdade e foi corrigido no commit `42f8d2d`.
- **Usar `date.today()`.** O servidor roda em UTC; às 21h no Brasil isso
  grava a data do dia seguinte. Use `hoje()`.
- **Montar SQL com f-string.** Abre injeção de SQL. Use `?`.
- **Sugerir SQLAlchemy ou outro framework.** O projeto usa `sqlite3` puro de
  propósito. Não troque.
- **Escrever `matplotlib.pyplot` fora do `graficos.py`.** Os gráficos ficam
  todos lá.
