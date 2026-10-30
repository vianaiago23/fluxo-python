# Roteiro — Pessoa 3: filtros e relatórios (itens 19 a 26)

Arquivos: `banco.py`, `app.py`, `analise.py`, `templates/painel.html`.

**Regra do projeto:** SQL só dentro do `banco.py`.

Comece lendo `listar_lancamentos_do_mes()` (`banco.py`, linha 248) e a função
`painel()` (`app.py`, linha 149).

---

## 19. Filtro por categoria

**O que fazer:** no painel, um seletor com as categorias do usuário. Escolhida
uma, a lista mostra só os lançamentos dela. Passe a escolha pela URL, como o
sistema já faz com `?ano=` e `?mes=` (veja `mes_escolhido()`, linha 69).

**Atenção:** a consulta tem que continuar filtrando por `usuario_id`. Se você
filtrar só por `categoria_id`, um usuário consegue ver lançamento de outro
trocando o número na URL. Esse bug já existiu neste projeto.

**Pronto quando:** o filtro funciona, e trocar o número da categoria na URL
para uma de outra conta não mostra nada.

---

## 20. Filtro por período

**O que fazer:** dois campos de data, inicial e final. Quando preenchidos,
substituem o filtro de mês.

**Atenção:** as datas no banco são texto no formato `AAAA-MM-DD`. Nesse
formato, comparação de texto funciona como comparação de data (`BETWEEN`
resolve). Se inverter para `DD/MM/AAAA`, para de funcionar.

---

## 21. Teste dos dois filtros

**Arquivo:** `testar_fumaca.py`. Cubra: filtro por categoria mostra só ela;
período recorta certo; data inicial maior que a final não quebra a tela; e o
isolamento entre contas descrito no item 19.

---

## 22. Consulta do relatório anual

**Arquivo:** `banco.py`

**O que fazer:** uma função que, dado o usuário e o ano, devolve entrada e
despesa de cada um dos doze meses. Olhe `somar_mes()` (linha 318) e
`serie_saldo()` do `analise.py` — dá para fazer em uma consulta só, agrupando
por mês, em vez de doze consultas.

**Dica:** no SQLite, `strftime('%m', data)` extrai o mês de uma data em texto.

---

## 23. Tela do relatório anual

Rota nova mostrando os doze meses em tabela: entradas, despesas e saldo de
cada um, e o total do ano.

**Atenção:** mês sem lançamento tem que aparecer zerado, não sumir da tabela.
Se você montar a tabela só com o que voltou do banco, os meses vazios somem.

---

## 24. Gráfico comparando os meses

**Arquivo:** `graficos.py`

Siga o padrão das funções que já existem: montar a figura, devolver bytes PNG
pela `_para_png()`. Use as cores do `constantes.py` (`VERDE`, `VERMELHO`),
não invente.

**Atenção:** o eixo dos valores tem que começar em zero. Começando noutro
ponto, uma diferença pequena parece enorme.

---

## 25. Teste do relatório anual

Cubra: ano sem lançamento nenhum devolve doze meses zerados; os totais batem
com a soma dos lançamentos; e um usuário não vê o ano do outro.

---

## 26. Ordenação da lista de lançamentos

Permitir ordenar por data e por valor, crescente e decrescente.

**Atenção:** monte a ordenação a partir de uma lista fixa de opções no código.
Se você colocar na consulta SQL o texto que veio da URL, abre uma porta de
injeção de SQL — é a única parte do sistema onde isso seria possível, porque
`ORDER BY` não aceita parâmetro `?`.
