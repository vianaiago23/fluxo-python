# Roteiro — Pessoa 5: documentação (itens 35 a 42)

Pasta `docs/`. Não precisa programar: precisa ler o código e explicar.

A fonte para tudo sobre o banco é a variável `ESQUEMA`, no começo do
`banco.py`. É o SQL que cria as tabelas — está tudo ali.

---

## 35. Criar `docs/banco-de-dados.md`

Estrutura do documento e uma visão geral: o sistema usa SQLite, quatro
tabelas, e quem conversa com elas é só o `banco.py`. Explique também onde o
banco fica nos dois casos — arquivo `fluxo.db` na máquina de cada um, e o
mesmo SQLite hospedado no Turso quando publicado. O `README.md` tem um
resumo disso que serve de ponto de partida.

---

## 36. Tabelas `usuarios` e `categorias`

Cada coluna: nome, tipo, se aceita vazio, e para que serve. Explique por que
`email` é `UNIQUE` e por que a senha é guardada como `senha_hash` e não como
texto.

---

## 37. Tabela `lancamentos`

Cada coluna. E a pergunta interessante: ela guarda `usuario_id` e `tipo`,
sendo que dava para chegar nos dois pela categoria. Isso é repetição de
propósito — descubra por quê (pense em quantas tabelas o banco precisaria
juntar para montar o painel do mês, e no que acontece se a categoria mudar de
tipo depois). Explique no documento.

---

## 38. Tabela `metas` e o índice

Cada coluna. Explique por que `categoria_id` é `UNIQUE` aqui — o que isso
impede de acontecer.

Depois, o índice `idx_lancamentos_usuario_data`: que consulta ele acelera, e
por que as colunas estão nessa ordem.

---

## 39. Chaves estrangeiras e restrições

Explique, com exemplo do que aconteceria sem cada uma:

- `REFERENCES usuarios(id) ON DELETE CASCADE` — o que acontece ao apagar uma conta
- `CHECK (tipo IN ('entrada', 'despesa'))` — o que impede de entrar no banco
- `CHECK (valor > 0)` — por que o sinal fica no `tipo` e não no valor
- `PRAGMA foreign_keys = ON` — por que precisa ser ligado em toda conexão

---

## 40. Criar `docs/plano-de-negocios.md`

Problema, solução e público-alvo. Existe um plano em PDF que o Iago pode te
passar — use como base, mas confira os números em vez de copiar.

---

## 41. Plano de negócios: mercado e números

Concorrentes e o que diferencia o Fluxo; preço; custos fixos e variáveis;
projeção de receita e ponto de equilíbrio, em tabela.

**Atenção:** cite a fonte de cada número de mercado. Dado sem fonte é a
primeira coisa que o professor questiona.

---

## 42. README com imagens

Tire print das telas principais — login, painel, lançamento, importação de
extrato, relatório — e acrescente ao `README.md`. Guarde as imagens em
`docs/imagens/`.

**Atenção:** use a conta de exemplo (`python dados_exemplo.py`), nunca uma
conta com dado real. Print com dado de verdade vai parar no repositório e não
sai mais do histórico.
