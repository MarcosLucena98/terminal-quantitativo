import yfinance as yf
import pandas as pd
from config import PREMIO_RISCO_MERCADO, WACC_TETO, WACC_PISO

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
        acao = yf.Ticker(ticker)
        info = acao.info or {}
        
        # =================================================
        # EXTRAÇÃO BLINDADA DE PREÇO (PLANO A e PLANO B)
        # =================================================
        preco = info.get("currentPrice") or info.get("regularMarketPrice")
        
        # PLANO B: Se o Yahoo "esquecer" de enviar o preço, puxamos pelo histórico diário
        if not preco:
            hist = acao.history(period="1d")
            if not hist.empty:
                preco = float(hist['Close'].iloc[-1])
                
        # Se mesmo assim não achar (ação paralisada/sem liquidez), pula e avisa
        if not preco or preco <= 0:
            print(f"⚠️ Preço não encontrado para {ticker}. Ativo ignorado.")
            return None 

        financials = acao.financials
        cashflow = acao.cashflow
        
        shares = info.get("sharesOutstanding")
        beta = info.get("beta", 1.0) or 1.0
        margem = info.get("profitMargins", 0) or 0
        
        setor_original = info.get("sector", "").lower()
        setor = MAPA_SETORES.get(setor_original, setor_original)

        # =================================================
        # AJUSTES SETORIAIS MANUAIS (OVERRIDE DO YFINANCE)
        # =================================================
        if ticker.startswith(("KLBN", "SUZB", "RANI")): 
            setor = "papel"
        elif ticker.startswith(("CYRE", "EZTC", "MRVE", "DIRR", "TEND", "CURY")): 
            setor = "construcao"
        elif ticker.startswith(("SBSP", "SAPR", "CSMG")): 
            setor = "saneamento"
        elif ticker.startswith(("BBSE", "CXSE", "PSSA")): 
            setor = "seguradora"
        elif ticker.startswith(("VALE", "CMIN")): 
            setor = "mineracao"
        elif ticker.startswith(("B3SA", "POMO")): 
            setor = "crescimento"
        elif ticker.startswith(("LREN", "BHIA")):
            setor = "consumo"
        elif ticker.startswith(("BEEF", "RAIZ")):
            setor = "commodities"

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
        dy_ajustado = min((info.get("dividendYield", 0) or 0) * 100, 12.0)
        dividendos_bazin = (dy_ajustado / 100) * preco if preco else 0

        # =================================================
        # HIGIENIZAÇÃO DE CAGR E CÁLCULO DE FCF
        # =================================================
        lucro_medio = extrair_media_historica(financials, ["Net Income", "Net Income Common Stockholders"])
        cagr_lucro = round(info.get("earningsQuarterlyGrowth", 0) * 100, 2) if info.get("earningsQuarterlyGrowth") else 0

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
            "ROE (%)": round(info.get("returnOnEquity", 0) * 100, 2) if info.get("returnOnEquity") else 0,
            "Margem (%)": round(margem * 100, 2) if margem else 0,
            "P/L": round(info.get("trailingPE", 0), 2) if info.get("trailingPE") else None,
            "P/VP": round(info.get("priceToBook", 0), 2) if info.get("priceToBook") else None,
            "Dívida/PL": round(info.get("debtToEquity", 0) / 100, 2) if info.get("debtToEquity") else 0,
            "EBITDA/Ação": (info.get("ebitda", 0) / shares) if (shares and info.get("ebitda")) else 0,
            "FCF/Ação (Médio)": fcf_medio_acao,
            "LPA (Médio)": (lucro_medio / shares) if (lucro_medio and shares) else info.get("trailingEps"),
            "VPA": info.get("bookValue", 0),
            "CAPM (%)": round(taxa_desconto * 100, 2), 
            "FCF Yield (%)": round(fcf_yield, 2),
            "ROIC (%)": round(roic * 100, 2) if roic else 0,
            "Spread ROIC-WACC (%)": round(spread_wacc * 100, 2) if spread_wacc else 0,
            "Volatilidade Lucro": round(cv_lucro, 2) if cv_lucro is not None else None,
            "CAGR Lucro (%)": cagr_lucro,
            "Taxa Desconto": taxa_desconto
        }
    except Exception as e:
        print(f"Erro em {ticker}: {e}")
        return None