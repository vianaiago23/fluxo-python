# Plano de negócios do Fluxo

Este plano parte do documento em PDF do grupo (*Plano de Negócios — Fluxo*,
Projeto Integrador de Transição, 2026). Os números e as afirmações sobre o produto
foram conferidos em novembro de 2026, com o código do sistema e com fontes externas.
O que mudou em relação ao PDF está em [Correções em relação ao PDF](#correções-em-relação-ao-pdf).

## Ideia e proposta de valor

O Fluxo é um sistema de controle financeiro pessoal, para pessoas físicas e
autônomos, que elimina o trabalho de anotar gasto por gasto: importa o extrato do
banco, acompanha metas por categoria e mostra para onde o dinheiro está indo.

> Importe seu extrato, defina metas e veja para onde vai o seu dinheiro, sem esforço.

## Filosofia do produto

**Missão:** ajudar pessoas físicas e autônomos a entender para onde vai o seu
dinheiro, prevenindo o endividamento com um controle financeiro simples, visual e
automatizado.

**Visão:** ser reconhecido como o sistema de controle financeiro mais simples de
adotar no dia a dia, especialmente para quem tem renda variável e para quem nunca
conseguiu manter uma planilha por muito tempo.

**Valores:**

- **Simplicidade:** menos digitação e mais clareza.
- **Transparência financeira:** entender de forma visual e imediata para onde vai o dinheiro.
- **Prevenção, não apenas registro:** metas e alertas ajudam a agir antes de se endividar.
- **Design que não cansa:** feito para o uso diário.

**Identidade visual:** modo escuro com contraste de verde sobre azul escuro e
tipografia Inter. O verde remete a dinheiro, e o azul escuro dá um visual sóbrio e
moderno, longe da estética de planilha. Quem preferir pode trocar para o modo claro
em Configurações.

## Problema

Quem trabalha por conta própria nem sempre sabe quanto sobrou no fim do mês. A renda
muda de um mês para o outro, e o dinheiro do negócio se mistura com as contas do
dia a dia. Sem esse controle, fica difícil perceber a tempo que um gasto saiu do
planejado.

Esse público é grande, e o risco de se endividar é real no país:

| Indicador | Número | Referência | Fonte |
|---|---|---|---|
| Trabalhadores por conta própria no Brasil | 26,1 milhões | trimestre de junho a agosto de 2026 | [IBGE, PNAD Contínua][ibge] |
| Pessoas inadimplentes no Brasil | 84,2 milhões | setembro de 2026 | [Serasa, Mapa da Inadimplência, via Tribuna do Sertão][serasa] |

Os dois números medem coisas diferentes e não se somam: nem todo inadimplente é
autônomo, e vice-versa.

As ferramentas disponíveis também cobram um preço, em dinheiro ou em esforço:

- **Planilhas** dependem de digitar cada movimentação e de manter as fórmulas.
- **Aplicativos de lançamento manual** têm o mesmo trabalho repetitivo.
- **Conexão automática com o banco** costuma ficar nos planos pagos e exige
  autorizar o acesso às contas. A cobertura também varia: o plano Conectado do
  [Organizze][organizze-home], por exemplo, anuncia mais de 10 bancos.

A hipótese do grupo é que esse esforço leva muita gente a abandonar o controle
financeiro. Ela ainda não foi medida com usuários e deve ser testada.

## Solução

O caminho fica entre o lançamento manual e a conexão bancária: a pessoa baixa o
extrato no site do banco, envia o arquivo ao Fluxo e revisa os lançamentos antes de
gravar. Assim, digita menos, não precisa conectar a conta do banco e continua no
controle das categorias.

### O que o sistema já faz

Todos estes recursos estão no código deste repositório:

| Recurso | Como ajuda |
|---|---|
| Importação de extrato em CSV e OFX, com tela de revisão | reduz a digitação |
| Painel mensal com entradas, despesas, saldo e comentário automático | mostra o resultado do mês em uma tela |
| Gráficos por categoria e evolução do saldo em 6 meses | mostra para onde o dinheiro foi |
| Metas por categoria, com aviso em texto a partir de 80% e acima de 100% do limite | avisa antes e depois de estourar o limite |
| Modelos de categorias para uso pessoal e por tipo de negócio | a conta já começa com categorias adequadas |
| Lançamentos que se repetem por vários meses | evita digitar contas fixas de novo |
| Relatório anual e exportação em PDF e CSV | facilita acompanhar o ano e enviar os números a alguém |
| Modo escuro, padrão do sistema, e modo claro | identidade visual pensada para o uso diário |

Os modelos prontos cobrem finanças pessoais (Moradia, Alimentação, Lazer, Transporte
e outras), arquiteto, vendedor de carros, salão de beleza, oficina
mecânica, professor particular e delivery ou lanchonete, além de um genérico.

### O que ainda não existe

O PDF do grupo prevê estes itens, mas eles dependem de algo que o código sozinho não
resolve. Para evitar prometer o que o produto não entrega, ficam como próximos passos:

| Item | O que falta para existir |
|---|---|
| Sincronização bancária | contratar um provedor de Open Finance, com contrato e credenciais |
| Notificação push após 3 dias sem uso | decidir por um canal de envio e agendar a tarefa no servidor; o push no navegador exigiria JavaScript, que o projeto evita |
| Medição de usuários ativos por dia (DAU) | escolher uma ferramenta de análise e tratar a privacidade dos dados de uso |
| Aplicativo nas lojas de celular | hoje o sistema funciona pelo navegador do celular |
| Cobrança da assinatura | contratar o meio de pagamento e desenvolver a cobrança |

## Público-alvo

| Prioridade | Segmento | O que procura no Fluxo |
|---|---|---|
| Principal | Autônomos e donos de pequenos negócios com renda variável | saber quanto sobrou de fato no mês, com categorias do próprio ramo |
| Secundário | Pessoas endividadas ou com risco de se endividar | definir um limite por categoria e ser avisadas antes de estourar |
| Secundário | Jovens que nunca mantiveram uma planilha | um jeito simples de começar, direto do navegador |

O foco principal são os autônomos porque é onde o produto se diferencia mais: os
modelos de categorias são feitos por ramo de atividade. Os outros dois segmentos são
atendidos pelo modelo de finanças pessoais, pelas metas e pelo visual em modo escuro.

## Mercado

| Indicador | Número | Referência | Fonte |
|---|---|---|---|
| Trabalhadores por conta própria | 26,1 milhões | junho a agosto de 2026 | [IBGE, PNAD Contínua][ibge] |
| Microempreendedores individuais (MEI) ativos | 12,3 milhões | outubro de 2026 | [Leadjet, base de CNPJs optantes pelo MEI][leadjet] |

O número de MEIs muda bastante conforme a base e o critério de contagem, então deve
ser lido como ordem de grandeza. Muitos MEIs também trabalham por conta própria:
os dois grupos se sobrepõem e não devem ser somados.

### Concorrentes

Preços conferidos em 5 de novembro de 2026.

| Concorrente | Preço | Conexão com banco | O que diferencia o Fluxo |
|---|---|---|---|
| [Mobills][mobills] | Premium a R$ 99,90 por ano | sim, no Premium ([comparativo][comparativo]) | categorias prontas por ramo de negócio |
| [Organizze][organizze-planos] | Manual: R$ 39/mês ou 12x de R$ 29,90. Conectado: R$ 49/mês ou 12x de R$ 39,90. Conectado Plus: R$ 79/mês ou 12x de R$ 69,90 | sim, a partir do Conectado | custaria menos que o plano mais barato, com foco em autônomos |
| [Minhas Economias][minhas-economias] | download grátis; a página não informa o preço de planos pagos | sim, por Open Finance | categorias prontas por ramo de negócio |
| [Money Lover][money-lover] | Premium vitalício listado a R$ 129,90 na App Store brasileira | não verificado | categorias prontas por ramo de negócio |

### O que diferencia o Fluxo

1. **Categorias por ramo de negócio.** Quem abre uma oficina ou um salão já começa
   com categorias do seu dia a dia.
2. **Importação sem conectar a conta.** A pessoa envia o extrato e revisa cada
   lançamento, sem autorizar nenhum acesso às contas do banco.
3. **Sem instalação.** O sistema funciona pelo navegador, no computador e no celular.

Esses pontos também têm limites. O Fluxo não tem conexão automática, a importação
ainda exige baixar o extrato todo mês, e os concorrentes têm mais tempo de mercado.
Alguns concorrentes também podem ter categorias editáveis ou importação de arquivo:
os produtos não foram testados um a um, então a comparação precisa ser validada.

## Modelo de receita e preço

**Decisão: uma assinatura única de R$ 14,90 por mês, paga no cartão de crédito**,
com 7 dias de teste grátis, como faz o [Organizze][organizze-planos]. O valor ainda
não passou por pesquisa com clientes e deve ser revisto depois dos primeiros testes.

| Produto | Custo por ano |
|---|---|
| Mobills Premium | R$ 99,90 |
| **Fluxo** | **R$ 178,80** |
| Organizze Manual, no plano anual | R$ 358,80 |
| Organizze Conectado, no plano anual | R$ 478,80 |

O preço fica entre os dois concorrentes pagos por assinatura. O principal risco é o
Mobills, que custa menos e ainda oferece conexão bancária. Para justificar a
diferença, o Fluxo precisa convencer pelo foco em autônomos, o que deve ser validado
com esse público.

A cobrança ainda não existe no sistema e teria de ser desenvolvida.

## Custos

Valores em dólar convertidos pela [PTAX de venda de 04/11/2026][ptax], R$ 5,4778.

### Custos fixos por mês

| Item | Valor por mês | Base | Fonte |
|---|---|---|---|
| Hospedagem (Vercel Pro) | R$ 109,56 | US$ 20; o plano gratuito Hobby não permite uso comercial | [Vercel][vercel] |
| Banco de dados (Turso Developer) | R$ 27,33 | US$ 4,99; 10 dias de restauração, contra 1 dia no plano grátis | [Turso][turso] |
| Domínio `.com.br` | R$ 3,33 | R$ 40 por ano | [Registro.br][registro] |
| Envio de e-mail (Resend Free) | R$ 0,00 | até 3.000 por mês e 100 por dia | [Resend][resend] |
| Contabilidade | R$ 169,00 | menor plano para serviços; varia com o faturamento | [Contabilizei][contabilizei] |
| Marketing | R$ 300,00 | orçamento decidido neste plano | não se aplica |
| **Subtotal sem pró-labore** | **R$ 609,22** | | |
| Pró-labore de uma pessoa | R$ 1.621,00 | um salário mínimo de 2026 | [Receita Federal][receita-mei] |
| **Total com pró-labore** | **R$ 2.230,22** | | |

Não estão incluídos o custo de abrir a empresa nem o uso acima dos limites dos planos.
Em nenhum cenário há salário para o restante da equipe.

### Custos variáveis por assinante

| Item | Regra | Por mês |
|---|---|---|
| Tarifa do cartão ([Asaas][asaas]) | R$ 0,49 + 2,99% (tarifa padrão) | R$ 0,94 |
| Imposto com Fator R de 28% ou mais (Anexo III) | 6% da receita | R$ 0,89 |
| Imposto com Fator R abaixo de 28% (Anexo V) | 15,5% da receita | R$ 2,31 |

A empresa não poderia ser MEI: as atividades de desenvolvimento de software não estão
na lista permitida ([WJR Contabilidade][cnae]). Por isso a conta usa o Simples
Nacional, na faixa inicial. O imposto depende do Fator R, a relação entre folha de
pagamento e receita ([Meu Contador Online][fator-r]). A regra deve ser confirmada com
um contador, e as tabelas simplificam o Fator R usando valores de um único mês.

## Ponto de equilíbrio

| Cenário | Custos fixos | Sobra por assinante | Assinantes necessários | Receita por mês |
|---|---:|---:|---:|---:|
| Sem pró-labore (Anexo V) | R$ 609,22 | R$ 11,65 | **53** | R$ 789,70 |
| Com pró-labore (Anexo III) | R$ 2.230,22 | R$ 13,07 | **171** | R$ 2.547,90 |

O primeiro cenário só cobre as contas da operação e não remunera ninguém. O segundo é
a referência para o negócio se sustentar, com uma pessoa recebendo um salário mínimo.

## Projeção de receita

As quantidades de assinantes abaixo são **metas de trabalho, e não previsões**: o
Fluxo ainda não tem clientes pagantes nem histórico de conversão. A conta usa o
cenário com pró-labore.

### Cenários no 12º mês

| Cenário | Assinantes | Receita por mês | Tarifas | Imposto | Custos fixos | Resultado por mês |
|---|---:|---:|---:|---:|---:|---:|
| Pessimista | 50 | R$ 745,00 | R$ 46,78 | R$ 44,70 (6%) | R$ 2.230,22 | **−R$ 1.576,70** |
| Base | 200 | R$ 2.980,00 | R$ 187,10 | R$ 178,80 (6%) | R$ 2.230,22 | **R$ 383,87** |
| Otimista | 500 | R$ 7.450,00 | R$ 467,76 | R$ 1.154,75 (15,5%) | R$ 2.230,22 | **R$ 3.597,27** |

No cenário base, 200 assinantes equivalem a cerca de 0,0008% dos 26,1 milhões de
trabalhadores por conta própria. A porcentagem parece pequena, mas não prova que
conquistá-los seja fácil: o custo de atrair cada cliente ainda não foi medido, e
R$ 300 por mês de marketing podem não bastar.

### Evolução no cenário base

| Mês | Assinantes | Receita por mês | Resultado por mês |
|---:|---:|---:|---:|
| 3 | 20 | R$ 298,00 | −R$ 1.968,81 |
| 6 | 50 | R$ 745,00 | −R$ 1.576,70 |
| 9 | 100 | R$ 1.490,00 | −R$ 923,17 |
| 12 | 200 | R$ 2.980,00 | R$ 383,87 |

Nessa trajetória, o resultado só fica positivo depois de 171 assinantes, e os meses
anteriores precisam de dinheiro próprio. A projeção também não desconta cancelamentos.

## Estratégia de marketing

**O produto como marketing:**

- **Importação em destaque:** o botão "Importar extrato", com a promessa de parar de
  digitar gasto por gasto.
- **Clareza visual:** vídeos mostrando os gráficos e a divisão de despesas por categoria.
- **Exportar PDF:** atrativo para quem precisa enviar relatórios financeiros rapidamente.

**Retenção:**

- **Gráfico de evolução:** o quadro de evolução do saldo nos últimos 6 meses incentiva
  a voltar para acompanhar o resultado.
- **Alertas de meta:** aviso no painel quando uma categoria se aproxima do orçamento
  ou passa dele.
- **Lembrete de acesso:** aviso depois de 3 dias sem uso, com a mensagem de que os
  dados estão desatualizados. Depende de um canal de envio, ainda não implementado.

**Aquisição e métricas:**

- **Anúncios (TikTok, Reels e Meta):** gravações de tela do sistema em uso real, com a
  pessoa cumprindo a meta de gastos.
- **Métrica principal, usuários ativos por dia (DAU):** indica se as pessoas voltam para
  acompanhar as metas. A medição ainda precisa ser implementada.

## Cronograma de execução

Planejado para 7 semanas, de 17 de agosto a 30 de setembro de 2026, com uma parte do
sistema funcionando ao fim de cada semana.

| Semana | Período | O que será feito | Entrega |
|---:|---|---|---|
| 1 | 17 a 23/08 | Definição das telas, menu de navegação, cores e identidade visual | Estrutura navegável |
| 2 | 24 a 30/08 | Painel com saldo do mês e gráficos de entradas e despesas por categoria | Painel funcionando |
| 3 | 31/08 a 06/09 | Cadastro de entradas e saídas, categorias e navegação entre os meses | Registro completo |
| 4 | 07 a 13/09 | Cadastro de usuário e salvamento dos dados na nuvem | Dados salvos por usuário |
| 5 | 14 a 20/09 | Importação de extrato, metas de gasto e relatório em PDF | Versão completa |
| 6 | 21 a 27/09 | Uso com pessoas reais, correção de erros e ajustes para celular | Versão estável |
| 7 | 28 a 30/09 | Revisão final, publicação na internet e apresentação | Sistema no ar |

## Considerações finais

O Fluxo se posiciona como uma alternativa simples frente a concorrentes consolidados,
unindo importação de extrato, metas de gasto e uma identidade visual própria. O
principal desafio é provar, com usuários reais, que o foco em autônomos justifica a
assinatura diante de opções mais baratas e com conexão bancária.

## Correções em relação ao PDF

Este plano segue o PDF, com exceção do que a conferência mostrou estar desatualizado:

| O PDF diz | O que foi conferido | Decisão |
|---|---|---|
| "GuiaBolso (Olivia)" é um concorrente atual | São dois aplicativos diferentes, e ambos foram encerrados em 2022: o Guiabolso foi comprado pelo PicPay, e a Olivia, pelo Nubank ([Finsiders][finsiders]) | fora da lista de concorrentes |
| Organizze tem lançamento majoritariamente manual | O [site][organizze-home] anuncia conexão bancária a partir do plano Conectado | tabela de concorrentes atualizada |
| Minhas Economias é 100% gratuito e de registro manual | O [site][minhas-economias] anuncia conexão por Open Finance | tabela de concorrentes atualizada |
| O perfil inclui sincronização bancária | Exige contratar um provedor de Open Finance | listado como próximo passo |
| Notificação push após 3 dias sem uso | Exige um canal de envio e uma tarefa agendada | listado como próximo passo |
| "Importação em 1 clique" | A importação envia um arquivo e passa por uma tela de revisão | texto ajustado |

[ibge]: https://biblioteca.ibge.gov.br/visualizacao/periodicos/3086/pnacm_2026_ago.pdf
[serasa]: https://www.tribunadosertao.com.br/geral/2026/11/02/1011781-serasa-aponta-842-milhoes-de-inadimplentes-no-brasil
[organizze-home]: https://www.organizze.com.br/
[finsiders]: https://finsidersbrasil.com.br/noticias-sobre-fintechs/guiabolso-comprado-pelo-picpay-sera-encerrado-em-novembro-finsiders/
[leadjet]: https://leadjet.com.br/quantos-meis-tem-no-brasil/
[mobills]: https://www.mobills.com.br/planos/
[comparativo]: https://ganherecompensa.com.br/blog/apps-para-controlar-gastos-top-8-2026-gratuitos-pagos
[organizze-planos]: https://www.organizze.com.br/planos
[minhas-economias]: https://www.minhaseconomias.com.br/
[money-lover]: https://apps.apple.com/br/app/money-lover-gerente-de-despesa/id486312413
[ptax]: https://www.bcb.gov.br/estabilidadefinanceira/historicocotacoes
[vercel]: https://vercel.com/pricing
[turso]: https://turso.tech/pricing
[registro]: https://registro.br/dominio/
[resend]: https://resend.com/pricing
[contabilizei]: https://www.contabilizei.com.br/contabilidade-online/servicos-de-contabilidade-precos/
[receita-mei]: https://www8.receita.fazenda.gov.br/simplesnacional/noticias/NoticiaCompleta.aspx?id=c3b2044c-ff97-432a-b33c-ecf2a3df6dc3
[asaas]: https://www.asaas.com/precos-e-taxas
[cnae]: https://wjrcontabilidade.com.br/blog/cnae/desenvolvimento-de-software/
[fator-r]: https://www.meucontadoronline.com.br/blog/cnae-desenvolvimento-sistemas-sob-encomenda-impostos/
