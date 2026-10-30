# Roteiro — Pessoa 6: perfis de negócio e interface (itens 43 a 50)

Arquivos: `constantes.py`, `templates/`, `static/estilo.css`.
É a frente mais acessível para quem está começando — os quatro primeiros
itens são edição de uma lista.

---

## 43 a 46. Novos perfis de negócio

**Arquivo:** `constantes.py`, dicionário `PERFIS`

No primeiro acesso, o usuário escolhe um modelo e o sistema cria as
categorias dele. Hoje existem três: arquiteto, vendedor de carros e genérico.

Acrescente quatro, um por commit:

| Item | Perfil |
|---|---|
| 43 | salão de beleza |
| 44 | oficina mecânica |
| 45 | professor particular |
| 46 | delivery / lanchonete |

Cada um precisa de `rotulo`, uma lista `entrada` e uma lista `despesa`. Copie
a forma de um que já existe.

**Atenção:** não passe de 10 categorias por tipo. A paleta de cores
(`PALETA`, no mesmo arquivo) tem 10 cores e elas começam a repetir depois
disso, o que deixa o gráfico de rosca confuso.

**Pronto quando:** criar conta nova, escolher o perfil novo, e as categorias
aparecerem certas no painel. E `python testar_fumaca.py` continuar 28/28 — o
teste confere a quantidade de categorias do perfil "arquiteto", então não
mexa nesse.

---

## 47. Mensagens de erro mais claras

**Arquivos:** `app.py` (procure por `flash(`), `templates/`

Leia todas as mensagens de erro do sistema. Várias só dizem que deu errado,
sem dizer o que fazer. Reescreva dizendo o problema **e** a saída.

Exemplo: *"Informe um valor maior que zero"* é melhor que *"Valor inválido"*.

---

## 48. `alt` nas imagens e foco pelo teclado

Toda imagem precisa de `alt` descrevendo o que mostra — inclusive os gráficos,
que hoje são `<img>` gerados pelo servidor. Para gráfico, descreva o que ele
representa, não "gráfico".

Depois, navegue o sistema inteiro usando só a tecla Tab. Onde você não
conseguir ver onde está, falta indicação de foco no CSS.

---

## 49. Contraste

Confira se todo texto é legível sobre o fundo dele. Os casos mais prováveis
são os textos em cinza (`CINZA` e `PRATA`, no `constantes.py`) sobre fundo
branco, e os rótulos pequenos do painel.

Existem medidores de contraste on-line gratuitos: a regra usada no mercado é
4,5 para texto normal e 3 para texto grande.

---

## 50. ⏳ Layout no celular

*Encosta nos itens 19 e 20 (Pessoa 3) — combine antes.*

**Arquivo:** `static/estilo.css`, que já tem 5 regras `@media`.

Abra o sistema no celular, ou no navegador estreitando a janela, e arrume o
que quebrar: painel, formulário de lançamento, formulário de meta e a tela de
importação.

**Atenção:** os filtros novos da Pessoa 3 vão entrar no painel. Faça este item
depois que eles estiverem no repositório, senão você arruma uma tela que vai
mudar.
