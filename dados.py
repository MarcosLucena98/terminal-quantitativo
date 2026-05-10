import yfinance as yf
import pandas as pd
import requests
from config import PREMIO_RISCO_MERCADO, WACC_TETO, WACC_PISO

# =========================================================
# SESSÃO CUSTOMIZADA: BYPASS DO BLOQUEIO ANTI-BOT DO YAHOO
# =========================================================
sessao_yf = requests.Session()
sessao_yf.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
})

MAPA_SETORES = {
    "financial services": "banco",
    "utilities": "eletrica",
    "energy": "commodities",
    "basic materials": "commodities",
    "industrials": "crescimento",
    "consumer defensive": "consumo",
    "real estate": "fiis",
    "communication services": "telecom",
    "consumer cyclical": "consumo"
}

def calcular_cagr(inicio, fim, anos):
    try:
        if inicio <= 0 or fim <= 0 or anos <= 0: return None
        return (((fim / inicio) ** (1 / anos) - 1) * 100)
    except: return None

def extrair_media_historica(df_financeiro, chaves_possiveis, anos=5):
    if df_financeiro is None or df_financeiro.empty: return None
    for chave in chaves_possiveis:
        if chave in df_financeiro.index:
            serie = df_financeiro.loc[chave].dropna()
            if not serie.empty: return serie.head(anos).mean()
    return None

def buscar_dados(ticker, selic_atual):
    try:
        # INJEÇÃO DA SESSÃO AQUI PARA EVITAR O ERRO 'INVALID CRUMB'
        acao = yf.Ticker(ticker, session=sessao_yf)
        
        info = acao.info
        financials = acao.financials
        cashflow = acao.cashflow
        
        # Variáveis base extraídas cedo para uso em cálculos posteriores
        preco = info.get("currentPrice") or info.get("regularMarketPrice")
        shares = info.get("sharesOutstanding")
        beta = info.get("beta") if info.get("beta") is not None else 1.0
        margem = info.get("profitMargins", 0)
        
        setor_original = info.get("sector", "").lower()
        setor = MAPA_SETORES.get(setor_original, setor_original)

        # =================================================
        # AJUSTES SETORIAIS MANUAIS (OVERRIDE DO YFINANCE)
        # =================================================
        if ticker.startswith(("KLBN", "SUZB")): 
            setor = "papel"
        elif ticker.startswith(("CYRE", "EZTC", "MRVE", "DIRR", "TEND", "CURY")): 
            setor = "construcao"
        elif ticker.startswith(("SBSP", "SAPR", "CSMG")): 
            setor = "saneamento"
        elif ticker.startswith(("BBSE", "CXSE", "PSSA")): 
            setor = "seguradora"
        elif ticker.startswith(("VALE", "CMIN")): 
            setor = "mineracao"
        elif ticker.startswith(("B3SA")): 
            setor = "crescimento"

        # =================================================
        # CAPM AJUSTADO
        # =================================================
        selic_longo_prazo = min(selic_atual, 0.10)
        taxa_desconto = max(WACC_PISO, min(selic_longo_prazo + (beta * PREMIO_RISCO_MERCADO), WACC_TETO))

        # =================================================
        # ROIC & SPREAD DE CRIAÇÃO DE VALOR (EVA)
        # =================================================
        roic = 0
        spread_wacc = 0
        
        if setor not in ["banco", "seguradora"]:
            ebit = extrair_media_historica(financials, ["EBIT", "Operating Income"])
            tax_rate = 0.34  
            
            divida_total = info.get("totalDebt", 0)
            caixa = info.get("totalCash", 0)
            patrimonio = info.get("totalStockholderEquity", 0)
            
            capital_investido = (divida_total + patrimonio) - caixa
            
            if ebit and capital_investido and capital_investido > 0:
                nopat = ebit * (1 - tax_rate)
                roic_bruto = nopat / capital_investido
                roic = max(0, min(roic_bruto, 0.50)) 
                spread_wacc = roic - taxa_desconto

        # =================================================
        # ESTABILIDADE (VOLATILIDADE DE LUCRO)
        # =================================================
        cv_lucro = None 
        
        if "Net Income" in financials.index:
            lucros_hist = financials.loc["Net Income"].dropna()
            if len(lucros_hist) >= 3:
                desvio_padrao = lucros_hist.std()
                media_lucro_hist = lucros_hist.mean()
                if media_lucro_hist != 0:
                    cv_bruto = abs(desvio_padrao / abs(media_lucro_hist))
                    cv_lucro = min(cv_bruto, 5.0) 

        # =================================================
        # HIGIENIZAÇÃO DE DIVIDENDOS (TRAVA BAZIN)
        # =================================================
        dividendos = acao.dividends
        dividendos.index = dividendos.index.tz_localize(None)
        inicio_12m = pd.Timestamp.now().tz_localize(None) - pd.DateOffset(years=1)
        dy_bruto = (dividendos[dividendos.index >= inicio_12m].sum() / preco) * 100 if preco else 0
        
        dy_ajustado = min(dy_bruto, 12.0)
        dividendos_bazin = (dy_ajustado / 100) * preco

        # =================================================
        # HIGIENIZAÇÃO DE CAGR E CÁLCULO DE FCF
        # =================================================
        lucro_medio = extrair_media_historica(financials, ["Net Income", "Net Income Common Stockholders"])
        cagr_lucro = 0
        if "Net Income" in financials.index:
            lucros = financials.loc["Net Income"].dropna()
            lucros_pos = lucros[lucros > 0]
            if len(lucros_pos) >= 2:
                cagr_bruto = calcular_cagr(lucros_pos.iloc[-1], lucros_pos.iloc[0], len(lucros_pos)-1)
                cagr_lucro = max(0, min(cagr_bruto, 20.0)) if cagr_bruto else 0

        # Calcula FCF por Ação antes do FCF Yield
        fcf_medio_total = extrair_media_historica(cashflow, ["Free Cash Flow"])
        fcf_medio_acao = (fcf_medio_total / shares) if (fcf_medio_total and shares) else 0

        # =================================================
        # FCF YIELD INSTITUCIONAL
        # =================================================
        fcf_yield = 0
        if preco and fcf_medio_acao and preco > 0:
            fcf_yield = (fcf_medio_acao / preco) * 100

        # =================================================
        # RETORNO CONSOLIDADO
        # =================================================
        return {
            "Ticker": ticker.replace(".SA", ""),
            "Setor": setor,
            "Empresa": info.get("longName", ticker),
            "Preço": round(preco, 2) if preco else None,
            "DY (%)": round(dy_ajustado, 2),
            "Dividendos 12M": round(dividendos_bazin, 2),
            "ROE (%)": round(info.get("returnOnEquity", 0) * 100, 2),
            "Margem (%)": round(margem * 100, 2) if margem else 0,
            "P/L": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else None,
            "P/VP": round(info.get("priceToBook", 0), 2) if info.get("priceToBook") else None,
            "Dívida/PL": round(info.get("debtToEquity", 0), 2),
            "EBITDA/Ação": (info.get("ebitda", 0) / shares) if shares else 0,
            "FCF/Ação (Médio)": fcf_medio_acao,
            "LPA (Médio)": (lucro_medio / shares) if (lucro_medio and shares) else info.get("trailingEps"),
            "VPA": info.get("bookValue"),
            "CAPM (%)": round(taxa_desconto * 100, 2), 
            "FCF Yield (%)": round(fcf_yield, 2),
            "ROIC (%)": round(roic * 100, 2) if roic else 0,
            "Spread ROIC-WACC (%)": round(spread_wacc * 100, 2) if spread_wacc else 0,
            "Volatilidade Lucro": round(cv_lucro, 2) if cv_lucro is not None else None,
            "CAGR Lucro (%)": round(cagr_lucro, 2),
            "Taxa Desconto": taxa_desconto
        }
    except Exception as e:
        print(f"Erro em {ticker}: {e}")
        return None
