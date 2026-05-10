# config.py

TICKERS = [
    # Sua Carteira Atual
    "CMIG4.SA", "ISAE4.SA", "BBSE3.SA", "ITUB4.SA", "TAEE11.SA",
    "CXSE3.SA", "CPFE3.SA", "BBAS3.SA", "PETR4.SA", "EGIE3.SA",
    
    # Saneamento e Elétricas (Resiliência e Dividendos)
    "SBSP3.SA", "SAPR11.SA", "CSMG3.SA", "ELET3.SA",
    
    # Bancos e Seguros (Geração de Caixa Forte)
    "BBDC4.SA", "SANB11.SA", "BPAC11.SA", "PSSA3.SA",
    
    # Telecom e Papel/Celulose (Defensivas e Exposição ao Dólar)
    "VIVT3.SA", "TIMS3.SA", "KLBN11.SA", "SUZB3.SA",
    
    # Crescimento, Qualidade e Commodities 
    "WEGE3.SA", "VALE3.SA", "PRIO3.SA", "CYRE3.SA", "RAIZ4.SA", "MRVE3.SA",
    "B3SA3.SA", "RENT3.SA", "RADL3.SA", "UNIP3.SA"
]

PASTA_OUTPUT = "output"
ARQUIVO_EXCEL = "ranking_acoes.xlsx"

TAXA_GRAHAM = 22.5
DY_MINIMO = 0.06
CRESCIMENTO_MAXIMO = 15

CRESCIMENTO_PERPETUIDADE = 0.03
PREMIO_RISCO_MERCADO = 0.06     
WACC_TETO = 0.20                
WACC_PISO = 0.08