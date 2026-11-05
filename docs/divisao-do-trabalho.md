# Divisão do trabalho — Fluxo

Seis pessoas, 50 entregas. Cada frente mexe em arquivos diferentes, de
propósito: dá para todo mundo trabalhar ao mesmo tempo sem conflito.

**Antes de começar, leia o `CONTRIBUTING.md`** na raiz do projeto. Ele explica
como instalar, como rodar e o que nunca pode ser enviado ao repositório.

Regra que vale para todos:

```bash
git pull                      # sempre antes de começar
python testar_fumaca.py       # sempre antes de commitar — tem que dar "tudo certo"
git add <só os arquivos que você mexeu>
git commit -m "mensagem em português, dizendo o que mudou"
git push
```

| Frente | Quem | Entregas |
|---|---|---|
| Publicação e núcleo | Iago | 10 |
| Segurança da conta | Pessoa 2 | 8 |
| Filtros e relatórios | Pessoa 3 | 8 |
| Testes | Pessoa 4 | 8 |
| Documentação | Pessoa 5 | 8 |
| Perfis e interface | Pessoa 6 | 8 |

**Ordem:** o Iago envia a base (itens 1 a 5) e, a partir daí, todas as frentes
correm em paralelo. Duas tarefas esperam alguém — estão marcadas com ⏳.

---

## Iago — 10 entregas

Frente: publicação e o miolo do sistema. Inclui o que depende das credenciais
da Vercel e do banco hospedado, que estão só com ele.

1. Publicação na Vercel com o banco hospedado no Turso *(feito)*
2. Teste automático do sistema, 28 verificações *(feito)*
3. Guia para os integrantes — `CONTRIBUTING.md` *(feito)*
4. Divisão do trabalho — este arquivo *(feito)*
5. Conecta o repositório do GitHub à Vercel: a partir daí todo `git push` publica sozinho
6. Páginas de erro 404 e 500 com a cara do sistema — hoje aparece a tela crua do servidor
7. Reduz o tempo da primeira visita: carregar o matplotlib só quando o gráfico for pedido
8. Validação de entrada: barra data no futuro e valor fora do razoável
9. ⏳ Aplica no banco hospedado a nova tabela de token e confere que subiu certo *(depende do item 12)*
10. Correção dos problemas que o grupo encontrar ao testar

## Pessoa 2 — Segurança da conta — 8 entregas

Arquivos: `app.py`, `banco.py`, `templates/`. É a frente mais pesada: mexe no
banco e no login. Comece lendo como a função `entrar()` funciona hoje.

11. Tela de "esqueci minha senha" e a rota que recebe o e-mail *(feito; no site publicado, só entra no ar quando o sistema enviar e-mail)*
12. Tabela de token temporário no banco: guarda o código, de quem é e quando expira *(feito)*
13. Validação do token e troca efetiva da senha *(feito)*
14. Teste automático da recuperação de senha, incluindo token expirado *(feito)*
15. Troca de senha dentro de Configurações, para quem já está logado *(feito)*
16. Teste automático da troca de senha, incluindo senha atual errada *(feito)*
17. Exclusão de conta: apaga o usuário e tudo que é dele *(feito)*
18. Teste automático da exclusão: confirma que lançamentos, categorias e metas somem junto *(feito)*

## Pessoa 3 — Filtros e relatórios — 8 entregas

Arquivos: `app.py`, `banco.py`, `analise.py`, `templates/painel.html`.
Lembre: consulta ao banco só no `banco.py`.

19. Filtro de lançamentos por categoria no painel *(feito)*
20. Filtro de lançamentos por período (data inicial e final) *(feito)*
21. Teste automático dos dois filtros *(feito)*
22. Relatório anual: a consulta no `banco.py` que soma mês a mês *(feito)*
23. Relatório anual: a tela mostrando os doze meses *(feito)*
24. Relatório anual: gráfico comparando os meses do ano *(feito)*
25. Teste automático do relatório anual *(feito)*
26. Ordenação da lista de lançamentos por data e por valor *(feito)*

## Pessoa 4 — Testes — 8 entregas

Arquivo: `testar_fumaca.py`. Siga o padrão que já está lá:
`checar("o que eu espero", condição)`.

27. Teste da importação de extrato em CSV: montar um arquivo de exemplo e conferir que vira lançamento certo
28. Teste da importação em OFX
29. Teste de arquivo inválido: vazio, formato errado, coluna faltando
30. Teste da repetição: o campo "repetir" cria o lançamento em vários meses; conferir quantidade e datas
31. Teste das metas: alerta ao passar de 80% e de 100% do limite
32. Amplia o teste de isolamento: uma conta não pode editar nem ver nada da outra
33. ⏳ Teste das páginas de erro *(depende do item 6)*
34. Correção do que os testes revelarem

## Pessoa 5 — Documentação — 8 entregas

Pasta `docs/`. A fonte para o banco é o esquema no começo do `banco.py`.

35. Cria `docs/banco-de-dados.md`: estrutura do documento e visão geral das quatro tabelas
36. Descreve `usuarios` e `categorias`: cada coluna, tipo e para que serve
37. Descreve `lancamentos`: colunas, e por que guarda `usuario_id` e `tipo` mesmo dando para chegar neles pela categoria
38. Descreve `metas`, o porquê do `UNIQUE` na categoria, e o índice `idx_lancamentos_usuario_data`
39. Explica as chaves estrangeiras, o `ON DELETE CASCADE` e as restrições `CHECK`
40. Cria `docs/plano-de-negocios.md`: problema, solução e público-alvo
41. Plano de negócios: concorrentes, preço, custos e ponto de equilíbrio em tabela
42. README: imagens das telas do sistema e revisão do texto

## Pessoa 6 — Perfis de negócio e interface — 8 entregas

Arquivos: `constantes.py` (dicionário `PERFIS`), `templates/`, `static/estilo.css`.
É a frente mais acessível para quem está começando.

43. Perfil "salão de beleza": categorias de entrada e de despesa *(feito)*
44. Perfil "oficina mecânica" *(feito)*
45. Perfil "professor particular" *(feito)*
46. Perfil "delivery / lanchonete" *(feito)*
47. Mensagens de erro mais claras — hoje algumas só dizem que deu errado *(feito)*
48. `alt` em todas as imagens e foco visível ao navegar pelo teclado *(feito)*
49. Contraste: conferir se todo texto é legível sobre o fundo *(feito)*
50. Layout no celular: painel e formulários *(feito)*

---

## Quem mexe em quê

| Frente | Arquivos principais |
|---|---|
| Iago | `app.py`, `graficos.py`, `templates/erro.html` |
| Segurança da conta | `app.py`, `banco.py`, `templates/entrar.html`, `configuracoes.html` |
| Filtros e relatórios | `banco.py`, `analise.py`, `templates/painel.html` |
| Testes | `testar_fumaca.py` |
| Documentação | `docs/`, `README.md` |
| Perfis e interface | `constantes.py`, `templates/`, `static/estilo.css` |

Duas frentes encostam no `banco.py` e duas no `app.py`. Não é problema se
cada um mexer na sua parte do arquivo — mas avise no grupo antes de começar,
e dê `git pull` no mesmo dia.

Se o `git push` reclamar que o repositório mudou, é porque alguém enviou algo
no meio do caminho:

```bash
git pull
python testar_fumaca.py
git push
```
