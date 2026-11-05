# Como trabalhar neste projeto

Guia para quem vai mexer no Fluxo. Não precisa saber Python a fundo: as
tarefas do fim deste arquivo estão descritas com o que fazer e onde.

## 1. Preparar a máquina

Precisa ter o Python 3.12 ou mais novo instalado.

```bash
git clone <endereço-do-repositório>
cd fluxo-python
python3 -m venv .venv
source .venv/bin/activate      # no Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra <http://localhost:5001> no navegador. Na primeira vez o arquivo
`fluxo.db` é criado sozinho, já com as tabelas, **na sua máquina**. Cada
pessoa tem o seu, então você pode cadastrar, apagar e testar à vontade sem
atrapalhar ninguém.

Para encher o banco com dados de exemplo e não começar do zero:

```bash
python dados_exemplo.py
```

> Você **não** precisa de senha nem de token para desenvolver. As credenciais
> do banco hospedado só servem para publicar, e ficam só com quem publica.

## 2. Antes de enviar qualquer mudança

Rode os testes. Levam poucos segundos:

```bash
python testar_fumaca.py
```

Se terminar com `tudo certo`, pode enviar. Se alguma verificação falhar,
a saída diz qual — conserte antes de commitar.

## 3. Como enviar

```bash
git pull                       # pega o que os outros já enviaram
git add <os arquivos que você mexeu>
git commit -m "descreve o que você fez"
git push
```

Algumas combinações:

- **Mensagem de commit**: em português, minúsculas, dizendo o que mudou.
  Bom: `adiciona teste de importacao de extrato CSV`.
  Ruim: `update`, `mudanças`, `teste`.
- **Commits pequenos**, um assunto por vez. É mais fácil de revisar e, se
  quebrar alguma coisa, dá para achar o que foi.
- **Dê `git pull` antes de começar** a mexer, todo dia. Evita conflito.

### O que nunca entra no repositório

Já está tudo no `.gitignore`, mas para saber o porquê:

| Arquivo | Motivo |
|---|---|
| `.env.local` | tem o token do banco hospedado |
| `fluxo.db` | é o banco da sua máquina, só seu |
| `.venv/` | são as bibliotecas, cada um instala as suas |
| `__pycache__/` | arquivos temporários do Python |

Se você vir algum desses aparecendo no `git status`, **não** dê `git add .`.

## 4. Onde fica cada coisa

| Arquivo | O que tem dentro |
|---|---|
| `app.py` | as rotas: o que acontece em cada endereço do site |
| `banco.py` | todo o SQL. Nenhum outro arquivo consulta o banco direto |
| `analise.py` | cálculos: evolução do saldo e o comentário do mês |
| `graficos.py` | os gráficos, feitos com matplotlib |
| `extrato.py` | leitura de extrato bancário em CSV e OFX |
| `relatorio.py` | o relatório em PDF |
| `constantes.py` | cores, meses, modelos de categoria |
| `templates/` | as telas, em HTML |
| `static/estilo.css` | a aparência |

Regra que vale a pena manter: **consulta ao banco só no `banco.py`**. Se a sua
tarefa precisa de um dado novo, crie uma função lá e chame dela.

## 5. Tarefas em aberto

Cada uma é independente — dá para duas pessoas trabalharem ao mesmo tempo sem
tropeçar. Avise no grupo qual você pegou.

### A. Testar o sistema publicado e relatar os erros
Entre em <https://fluxo-python.vercel.app>, crie uma conta e use o sistema de
verdade: lance entradas e despesas, crie meta, importe um extrato, exporte o
PDF. Anote tudo que parecer errado ou confuso. Abra uma *issue* no GitHub para
cada problema, com o passo a passo de como reproduzir.

### B. Ampliar os testes automáticos
Arquivo: `testar_fumaca.py`. Hoje ele não cobre duas partes importantes:
- **importação de extrato** (`extrato.py`): montar um CSV e um OFX de exemplo
  e conferir que viram lançamentos corretos;
- **repetição de lançamento**: o campo "repetir" cria o mesmo lançamento em
  vários meses seguidos; conferir que cria a quantidade certa, nas datas certas.

Siga o padrão que já está no arquivo: uma função `checar("o que espero", condição)`.

### C. Documentação do banco de dados no repositório *(feito: `docs/banco-de-dados.md`)*
Criar `docs/banco-de-dados.md` descrevendo as quatro tabelas (`usuarios`,
`categorias`, `lancamentos`, `metas`): para que serve cada uma, cada coluna,
as chaves estrangeiras e por que existem as restrições (`CHECK`, `UNIQUE`). O
esquema está no começo do `banco.py`, e já existe um relatório em PDF que pode
servir de base.

### D. Plano de negócios no repositório *(feito: `docs/plano-de-negocios.md`)*
Criar `docs/plano-de-negocios.md`. Existe hoje só em PDF; passar para texto no
repositório, com os números em tabela.

### E. Mais perfis de categorias *(feito: `PERFIS`, em `constantes.py`)*
Arquivo: `constantes.py`, dicionário `PERFIS`. Hoje tem três (arquiteto,
vendedor de carros, genérico). Acrescentar outros — salão de beleza, oficina,
professor particular, delivery — com categorias de entrada e de despesa que
façam sentido para cada um. É a tarefa mais fácil para começar.

### F. Revisão dos textos e da acessibilidade
Ler todas as telas (`templates/`) procurando: mensagens de erro confusas,
rótulo que não explica o campo, falta de `alt` em imagem, contraste ruim.
Corrigir o que achar.
