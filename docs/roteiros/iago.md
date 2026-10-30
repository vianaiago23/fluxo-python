# Roteiro — Iago (itens 1 a 10)

Frente: publicação e o miolo do sistema. Inclui o que depende das credenciais
da Vercel e do Turso.

---

## 1 a 4 — feitos

Publicação na Vercel com banco no Turso, teste automático, `CONTRIBUTING.md` e
a divisão do trabalho. Já estão na pasta, faltando só o commit.

---

## 5. Conectar o GitHub à Vercel

**Onde:** painel da Vercel, projeto `fluxo-python` → Settings → Git

**O que fazer:** ligar o repositório `vianaiago23/fluxo-python` ao projeto. A
partir daí, todo `git push` na `main` publica o site sozinho — inclusive os
pushes dos colegas.

**Atenção:** depois de conectar, pare de usar `vercel deploy` na mão. Se usar
os dois, o site pode ficar com uma versão diferente da que está no GitHub.

**Pronto quando:** você der um push qualquer e, no painel da Vercel, aparecer
uma implantação nova com a mensagem daquele commit.

---

## 6. Páginas de erro 404 e 500

**Arquivos:** `app.py`, `templates/erro.html` (novo)

**O que fazer:** hoje, endereço errado ou falha no servidor mostram a tela
crua do Flask — fundo branco, letra preta, nada a ver com o sistema. Crie um
template `erro.html` que estenda o `base.html` e registre dois tratadores:

```python
@app.errorhandler(404)
@app.errorhandler(500)
```

Cada um devolve o template com uma mensagem adequada e o código certo (o
Flask espera que você devolva uma tupla: conteúdo e número).

**Atenção:** na página de 500 **não** mostre o erro técnico. Quem está vendo é
o usuário, e a mensagem de erro pode revelar caminho de arquivo e estrutura do
banco. Mensagem curta e um link para voltar ao painel.

**Pronto quando:** abrir `/qualquercoisa` mostra sua página com a cara do
sistema, e `python testar_fumaca.py` continua dando 28/28.

---

## 7. Reduzir o tempo da primeira visita

**Arquivo:** `graficos.py`

**O que fazer:** hoje o `import matplotlib` acontece quando o arquivo é
carregado, ou seja, em toda partida do servidor — mesmo que a pessoa só abra
a tela de login. É o que faz a primeira visita demorar ~4 segundos.

Mova o `import matplotlib` e o `import matplotlib.pyplot` para **dentro** das
funções `rosca()` e `barras_saldo()`, que são as únicas que usam.

**Atenção:** a linha `matplotlib.use("Agg")` tem que continuar vindo **antes**
do `import matplotlib.pyplot`, senão ele tenta abrir janela gráfica e quebra
no servidor.

**Pronto quando:** `curl -o /dev/null -w "%{time_total}" https://fluxo-python.vercel.app/entrar`
depois de um tempo parado der bem menos que os ~4s de hoje, e os gráficos
continuarem aparecendo no painel.

---

## 8. Validação de entrada

**Arquivos:** `app.py` (função `editar_lancamento`, linha 180)

**O que fazer:** hoje dá para cadastrar lançamento com data em 2099 e valor de
R$ 900 milhões. Barre:

- data posterior a hoje (use a função `hoje()` do `constantes.py`, não
  `date.today()` — o servidor roda em UTC)
- valor acima de um teto razoável, por exemplo R$ 10 milhões

Em cada caso, `flash()` com a explicação e devolva o formulário preenchido.

**Atenção:** o banco já tem `CHECK (valor > 0)`, então valor negativo já é
barrado lá. Essa validação é para dar mensagem boa ao usuário antes de chegar
no banco.

**Pronto quando:** tentar salvar com data futura mostra o aviso e não grava.

---

## 9. ⏳ Aplicar a tabela de token no banco hospedado

*Espera o item 12 (Pessoa 2) estar no repositório.*

**O que fazer:** quando a Pessoa 2 criar a tabela de recuperação de senha, ela
vale só na máquina dela — o `fluxo.db` de cada um é local. Para valer no site,
rode contra o Turso:

```bash
git pull
npx vercel env pull
set -a; . ./.env.local; set +a
python preparar_nuvem.py
```

Acrescente a tabela nova à lista `TABELAS_ESPERADAS` do `preparar_nuvem.py`
para o script conferir que ela subiu.

**Atenção:** o `.env.local` tem o token do banco. Nunca commite esse arquivo —
já está no `.gitignore`, só não force.

**Pronto quando:** o script listar a tabela nova e a recuperação de senha
funcionar no site publicado, não só na sua máquina.

---

## 10. Correções do que o grupo encontrar

**O que fazer:** conforme as pessoas forem testando, vão achar problemas que
não estão na lista. Corrija e commite um por vez, descrevendo o problema na
mensagem: `corrige grafico vazio quando o mes nao tem lancamento`.
