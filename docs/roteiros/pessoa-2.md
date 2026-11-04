# Roteiro — Pessoa 2: segurança da conta (itens 11 a 18)

Frente mais pesada: mexe no login e no banco. Comece lendo a função
`entrar()` no `app.py` (linha 92) e as funções `criar_usuario()` e
`autenticar()` no `banco.py` (linhas 116 e 130).

**Regra do projeto:** SQL só dentro do `banco.py`. Se precisar de um dado
novo, crie uma função lá e chame dela.

---

## 11. Tela de "esqueci minha senha" e a rota

**Arquivos:** `templates/entrar.html`, `app.py`

**O que fazer:** a tela de login tem duas abas, controladas pela variável
`modo`. Acrescente abaixo do botão um link "Esqueci minha senha" apontando
para uma rota nova `/recuperar`, que mostra um formulário com um campo só, de
e-mail.

Por enquanto não envie nada: receba o e-mail e mostre sempre a mesma
mensagem — *"Se existir uma conta com esse e-mail, enviamos as instruções."*

**Atenção:** a mensagem tem que ser idêntica existindo a conta ou não. Se
mudar, qualquer um descobre quem tem conta testando e-mails.

**Pronto quando:** `/recuperar` abre, aceita o envio, mostra a mensagem, e
`python testar_fumaca.py` continua 28/28.

---

## 12. Tabela de token no banco

**Arquivo:** `banco.py`

**O que fazer:** acrescente ao `ESQUEMA` (começo do arquivo) uma tabela para
os pedidos de recuperação:

- `usuario_id` apontando para `usuarios(id)`, com `ON DELETE CASCADE`
- o token (um texto aleatório)
- quando expira
- se já foi usado

Crie as funções `criar_token(usuario_id)` e `buscar_token(token)`.

**Atenção:** gere o token com `secrets.token_urlsafe(32)`, nunca com
`random` — o `random` é previsível e dá para adivinhar o próximo. Guarde a
expiração como texto ISO, com data e hora em UTC: o link vale 1 hora, e o
`hoje()` só guarda o dia. No banco fica só o hash do token, nunca o texto do link.

**Pronto quando:** apagar um usuário apaga os tokens dele junto (teste isso),
e `criar_token()` devolve textos diferentes a cada chamada.

---

## 13. Validar o token e trocar a senha

**Arquivos:** `app.py`, `banco.py`, `templates/`

**O que fazer:** rota `/recuperar/<token>` que mostra o formulário de senha
nova. Ao enviar: confere que o token existe, não expirou e não foi usado;
troca a senha; marca o token como usado.

**Atenção três vezes:**
1. Token usado **não** pode servir de novo — senão quem interceptar o link
   entra quando quiser.
2. Token expirado idem. Compare com a data de agora, não confie no que vem
   da URL.
3. Use `generate_password_hash` do Werkzeug, igual o `criar_usuario()` faz.
   Nunca grave senha em texto puro.

**Pronto quando:** o fluxo inteiro funciona e um token já usado dá erro.

---

## 14. Teste automático da recuperação

**Arquivo:** `testar_fumaca.py`

**O que fazer:** siga o padrão `checar("o que espero", condição)`. Cubra:
token válido troca a senha; token expirado é recusado; token já usado é
recusado; token inventado é recusado; e a mensagem de `/recuperar` é a mesma
para e-mail existente e inexistente.

**Dica:** para testar expiração sem esperar, crie o token e altere a data de
expiração direto no banco para uma data passada.

---

## 15. Troca de senha em Configurações

**Arquivos:** `app.py` (função `configuracoes`, linha 270), `templates/configuracoes.html`

**O que fazer:** formulário com senha atual, senha nova e confirmação. A tela
já funciona por "ações" (`request.form["acao"]`) — siga o mesmo padrão,
acrescentando uma ação `trocar_senha`.

**Atenção:** exija a senha atual e confira com `check_password_hash`. Sem
isso, quem sentar no computador com a sessão aberta troca a senha e toma a
conta.

---

## 16. Teste da troca de senha

Cubra: senha atual errada é recusada; confirmação diferente é recusada; senha
curta demais é recusada (o cadastro exige 6); e, depois de trocar, a senha
antiga não entra mais e a nova entra.

---

## 17. Exclusão de conta

**Arquivos:** `app.py`, `banco.py`, `templates/configuracoes.html`

**O que fazer:** já existe `apagar_dados(usuario_id)` no `banco.py` (linha
363) — leia antes, talvez sirva de base. Crie a exclusão da conta inteira:
apaga o usuário, e o `ON DELETE CASCADE` leva categorias, lançamentos e metas
junto. Depois, `session.clear()` e manda para a tela de login.

**Atenção:** peça confirmação de verdade — que a pessoa digite a senha, ou a
palavra EXCLUIR. Um botão solto numa tela de configurações apaga conta sem
querer, e não tem como desfazer.

---

## 18. Teste da exclusão

Crie uma conta, dê a ela categorias, lançamentos e metas, apague a conta e
confirme que **nada** sobrou em nenhuma das quatro tabelas. Confirme também
que a conta de outro usuário continuou intacta.
