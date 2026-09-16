"""Valores fixos usados em todo o sistema."""

# Cores das categorias, pensadas para ter contraste sobre fundo branco.
PALETA = [
    "#005227", "#2F7A4F", "#7FA891", "#9AA5A0", "#4A5C55",
    "#B0872B", "#A8442A", "#35617F", "#6E5A7D", "#C7B9A2",
]

VERDE = "#005227"
VERMELHO = "#B23A1F"
PRATA = "#AEB8B2"
TINTA = "#0F241A"
CINZA = "#69786F"

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
    "generico": {
        "rotulo": "Genérico / Outro negócio",
        "entrada": ["Vendas", "Serviços", "Outros"],
        "despesa": ["Aluguel", "Fornecedores", "Transporte",
                    "Marketing", "Impostos", "Outros"],
    },
}


def formatar_reais(valor):
    """Formata um número no padrão brasileiro: 1234.5 -> 'R$ 1.234,50'."""
    texto = f"{abs(valor or 0):,.2f}"
    texto = texto.replace(",", "#").replace(".", ",").replace("#", ".")
    sinal = "-" if (valor or 0) < 0 else ""
    return f"{sinal}R$ {texto}"
