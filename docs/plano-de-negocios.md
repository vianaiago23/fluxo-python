# Plano de negócios do Fluxo

Este plano parte do documento em PDF do grupo (*Plano de Negócios — Fluxo*,
Projeto Integrador de Transição, 2026). Os números e as afirmações sobre o produto
foram conferidos em novembro de 2026, com o código do sistema e com fontes externas.
O que mudou em relação ao PDF está em [Correções em relação ao PDF](#correções-em-relação-ao-pdf).

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

O Fluxo é um sistema web de controle financeiro para autônomos e pequenos negócios.
A proposta do grupo se resume em uma frase: **importe seu extrato, defina metas e
veja para onde vai o seu dinheiro**.

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
| Metas por categoria, com aviso a partir de 80% e acima de 100% do limite | avisa antes e depois de estourar o limite |
| Modelos de categorias por tipo de negócio | a conta já começa com categorias adequadas |
| Lançamentos que se repetem por vários meses | evita digitar contas fixas de novo |
| Relatório anual e relatório em PDF | facilita acompanhar o ano e enviar os números a alguém |

Os modelos prontos cobrem arquiteto, vendedor de carros, salão de beleza, oficina
mecânica, professor particular e delivery ou lanchonete, além de um genérico.

### O que ainda não existe

Para evitar prometer o que o produto não entrega, estes itens continuam como ideias
para o futuro: conexão automática com bancos, aplicativo nas lojas de celular,
notificações push, modo escuro, exportação em CSV e cobrança de assinatura.

## Público-alvo

| Prioridade | Segmento | O que procura no Fluxo |
|---|---|---|
| Principal | Autônomos e donos de pequenos negócios com renda variável | saber quanto sobrou de fato no mês, com categorias do próprio ramo |
| Secundário | Pessoas endividadas ou com risco de se endividar | definir um limite por categoria e ser avisadas antes de estourar |
| Secundário | Jovens que nunca mantiveram uma planilha | um jeito simples de começar, direto do navegador |

O foco principal são os autônomos porque é onde o produto se diferencia mais: os
modelos de categorias são feitos por ramo de atividade. Os outros dois segmentos,
presentes no PDF, são atendidos pelos mesmos recursos, sem nada específico para eles.

## Correções em relação ao PDF

| O PDF diz | O que foi conferido | Decisão |
|---|---|---|
| "GuiaBolso (Olivia)" é um concorrente atual | São dois aplicativos diferentes, e ambos foram encerrados em 2022: o Guiabolso foi comprado pelo PicPay, e a Olivia, pelo Nubank ([Finsiders][finsiders]) | fora da lista de concorrentes |
| Modo escuro é parte da identidade do produto | A interface atual tem fundo claro (`static/estilo.css`) | listado como "ainda não existe" |
| O perfil inclui sincronização bancária | O sistema não se conecta a bancos | listado como "ainda não existe" |
| Exportação em CSV e PDF | O sistema só exporta em PDF; o CSV serve apenas para importar | listado como "ainda não existe" |
| Notificação push após 3 dias sem uso | Não existe no sistema | listado como "ainda não existe" |
| "Importação em 1 clique" | A importação envia um arquivo e passa por uma tela de revisão | texto ajustado |
| Aplicativo de controle financeiro **pessoal** | O sistema e o `README.md` são voltados a autônomos e pequenos negócios | foco principal ajustado |

[ibge]: https://biblioteca.ibge.gov.br/visualizacao/periodicos/3086/pnacm_2026_ago.pdf
[serasa]: https://www.tribunadosertao.com.br/geral/2026/11/02/1011781-serasa-aponta-842-milhoes-de-inadimplentes-no-brasil
[organizze-home]: https://www.organizze.com.br/
[finsiders]: https://finsidersbrasil.com.br/noticias-sobre-fintechs/guiabolso-comprado-pelo-picpay-sera-encerrado-em-novembro-finsiders/
