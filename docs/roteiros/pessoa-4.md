# Roteiro — Pessoa 4: testes (itens 27 a 34)

Arquivo: `testar_fumaca.py`. Abra e leia antes de começar — ele já tem 28
verificações e o padrão a seguir é:

```python
checar("o que eu espero que aconteca", condição_que_tem_que_ser_verdadeira)
```

O teste roda num banco temporário, nunca no seu `fluxo.db`. Para ver como as
funções de leitura de extrato funcionam, abra o `extrato.py`: as três
principais são `ler_csv()`, `ler_ofx()` e `ler_extrato()`.

---

## 27. Teste da importação em CSV

**O que fazer:** monte, dentro do próprio teste, o texto de um CSV de extrato
com três ou quatro linhas, e confira que `ler_csv()` devolve os lançamentos
certos: data, valor e descrição.

**Atenção:** o `extrato.py` aceita formatos diferentes de data e de valor
(vírgula ou ponto como decimal, data com barra ou com traço). Teste mais de
um formato — é aí que costuma quebrar.

---

## 28. Teste da importação em OFX

Mesma ideia, com um trecho de OFX. O formato é marcado por etiquetas tipo
`<STMTTRN>`, `<DTPOSTED>`, `<TRNAMT>`, `<MEMO>`. Confira que valor negativo
vira despesa e positivo vira entrada.

---

## 29. Teste de arquivo inválido

Cubra: arquivo vazio; texto que não é nem CSV nem OFX; CSV sem a coluna de
valor; e uma linha com valor que não é número.

**O que tem que acontecer:** o sistema avisa e não grava nada. Nunca pode
estourar erro na cara do usuário nem gravar lançamento pela metade.

---

## 30. Teste da repetição de lançamento

O formulário de lançamento tem o campo `repetir`, que cria o mesmo lançamento
em vários meses seguidos. Confira: quantidade certa de lançamentos; datas nos
meses certos; e o caso do dia 31 — repetindo a partir de 31 de janeiro, o que
acontece em fevereiro? Veja o que o código faz hoje e decida com o grupo se
está certo.

---

## 31. Teste das metas

Cubra o alerta em 80% e em 100% do limite. Crie uma meta, lance despesas até
passar de cada faixa e confira que o painel mostra o aviso. Teste também meta
em categoria de entrada — não deveria ser aceita.

---

## 32. Ampliar o teste de isolamento

Já existem verificações disso no arquivo. Amplie para cobrir **toda** ação que
recebe um número na URL: editar lançamento, excluir lançamento, excluir meta,
renomear categoria, excluir categoria.

Para cada uma: crie duas contas, e tente, logado na conta A, agir sobre o item
da conta B. Tem que falhar sempre.

**Por que isso importa:** esse bug já existiu neste projeto — em metas e na
importação — e foi corrigido no commit `42f8d2d`. É o erro mais fácil de
cometer de novo quando se acrescenta rota nova.

---

## 33. ⏳ Teste das páginas de erro

*Espera o item 6 (Iago).*

Confira que endereço inexistente devolve 404 com a página do sistema, e que a
página de erro **não** mostra detalhe técnico — nada de caminho de arquivo,
nome de tabela ou traceback.

---

## 34. Correção do que os testes revelarem

Os testes vão achar coisa quebrada — essa é a função deles. Corrija e commite
uma por vez, descrevendo o problema na mensagem.
