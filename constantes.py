"""Valores fixos usados em todo o sistema."""

from datetime import datetime
from zoneinfo import ZoneInfo

# O servidor na nuvem roda com o relogio em UTC. Sem isto, um lancamento feito
# as 21h no Brasil seria gravado com a data do dia seguinte.
FUSO_BRASIL = ZoneInfo("America/Sao_Paulo")


def hoje():
    """Data de hoje no horario de Brasilia."""
    return datetime.now(FUSO_BRASIL).date()

# Cores das categorias, pensadas para ter contraste sobre fundo branco.
PALETA = [
    "#005227", "#2F7A4F", "#7FA891", "#9AA5A0", "#4A5C55",
    "#B0872B", "#A8442A", "#35617F", "#6E5A7D", "#C7B9A2",
]

# As mesmas cores, clareadas para ter contraste sobre o azul escuro do tema
# escuro. O banco guarda sempre a cor da PALETA; esta só muda o que é desenhado.
PALETA_ESCURA = dict(zip(PALETA, [
    "#2BC47E", "#5FD39B", "#9CCDB3", "#B4C0BA", "#8FA8B8",
    "#E3B341", "#FF8A70", "#6FB2DE", "#B59AD0", "#DCCFB8",
]))

TEMAS = ("escuro", "claro")
TEMA_PADRAO = "escuro"


def cor_no_tema(cor, tema):
    """Cor de uma categoria como ela deve aparecer no tema escolhido."""
    return PALETA_ESCURA.get(cor, cor) if tema == "escuro" else cor


VERDE = "#005227"
VERMELHO = "#B23A1F"
PRATA = "#AEB8B2"
TINTA = "#0F241A"
# Cinza dos textos secundarios. Escurecido para passar de 4,5:1 inclusive
# sobre os fundos cinza-claro dos cartoes e botoes (antes era #69786F).
CINZA = "#5A6961"

# Teto de um lancamento. Nao existe limite tecnico: serve para pegar erro de
# digitacao, como somar zeros a mais, antes de sujar o historico.
VALOR_MAXIMO = 10_000_000.0

MESES = [
    "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

MESES_CURTOS = [
    "Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
    "Jul", "Ago", "Set", "Out", "Nov", "Dez",
]

# Modelos de categorias oferecidos no primeiro acesso.
PERFIS = {
    "pessoal": {
        "rotulo": "Pessoal / Finanças da casa",
        "entrada": ["Salário", "Renda Extra", "Outros"],
        "despesa": ["Moradia", "Alimentação", "Lazer", "Transporte",
                    "Saúde", "Educação", "Outros"],
    },
    "arquiteto": {
        "rotulo": "Arquiteto(a) / Projetista",
        "entrada": ["Projetos", "Comissão", "Acompanhamento de Projeto"],
        "despesa": ["Aluguel do Escritório", "Materiais e Impressões",
                    "Transporte", "Marketing", "Impostos", "Outros"],
    },
    "carros": {
        "rotulo": "Vendedor(a) de Carros",
        "entrada": ["Venda de Carros", "Comissão", "Outros"],
        "despesa": ["Combustível", "Documentação", "Marketing",
                    "Comissão de Terceiros", "Impostos", "Outros"],
    },
    "salao": {
        "rotulo": "Salão de Beleza",
        "entrada": ["Cortes e Escovas", "Coloração", "Manicure e Pedicure",
                    "Estética", "Venda de Produtos", "Outros"],
        "despesa": ["Aluguel do Salão", "Produtos e Cosméticos",
                    "Comissão de Profissionais", "Energia e Água",
                    "Equipamentos", "Marketing", "Impostos", "Outros"],
    },
    "oficina": {
        "rotulo": "Oficina Mecânica",
        "entrada": ["Mão de Obra", "Venda de Peças", "Revisão",
                    "Funilaria e Pintura", "Outros"],
        "despesa": ["Aluguel da Oficina", "Compra de Peças", "Ferramentas",
                    "Salários", "Energia e Água", "Descarte de Resíduos",
                    "Impostos", "Outros"],
    },
    "professor": {
        "rotulo": "Professor(a) Particular",
        "entrada": ["Aulas Presenciais", "Aulas On-line", "Pacotes Mensais",
                    "Material Didático", "Outros"],
        "despesa": ["Transporte", "Livros e Material", "Internet",
                    "Plataformas e Aplicativos", "Marketing", "Impostos",
                    "Outros"],
    },
    "delivery": {
        "rotulo": "Delivery / Lanchonete",
        "entrada": ["Vendas no Balcão", "Pedidos por Aplicativo",
                    "Pedidos por WhatsApp", "Bebidas", "Outros"],
        "despesa": ["Ingredientes", "Embalagens", "Taxa dos Aplicativos",
                    "Entregadores", "Gás e Energia", "Aluguel", "Marketing",
                    "Impostos", "Outros"],
    },
    "generico": {
        "rotulo": "Genérico / Outro negócio",
        "entrada": ["Vendas", "Serviços", "Outros"],
        "despesa": ["Aluguel", "Fornecedores", "Transporte",
                    "Marketing", "Impostos", "Outros"],
    },
}


def formatar_reais(valor):
    """Formata um número no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    valor = round(valor or 0, 2)   # sem isto, -0,001 sairia como "-R$ 0,00"
    texto = f"{abs(valor):,.2f}"
    texto = texto.replace(",", "#").replace(".", ",").replace("#", ".")
    sinal = "-" if valor < 0 else ""
    return f"{sinal}R$ {texto}"
