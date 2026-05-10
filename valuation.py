# =========================================================
# valuation.py (VERSÃO PROFISSIONAL CORRIGIDA E CALIBRADA)
# =========================================================

import math
from score import calcular_score, fator_score

def is_valid(v): 
    return v is not None and not math.isnan(v) and not math.isinf(v)

def media_ponderada(valores_pesos):
    validos = [(v, p) for v, p in valores_pesos if is_valid(v)]
    if not validos: return None
    soma_p = sum(p for _, p in validos)
    return sum(v * (p / soma_p) for v, p in validos)

def dcf_dois_estagios(fcf_acao, taxa_desconto, crescimento_curto, g_perp=0.03, anos=5):
    try:
        if not is_valid(fcf_acao) or fcf_acao <= 0: return None
        ke = max(taxa_desconto, 0.08)
        g1 = min(crescimento_curto / 100, 0.15)
        vp_fluxos = sum([(fcf_acao * (1 + g1)**t) / (1 + ke)**t for t in range(1, anos + 1)])
        v_terminal = (fcf_acao * (1 + g1)**anos * (1 + g_perp)) / (ke - g_perp)
        return vp_fluxos + (v_terminal / (1 + ke)**anos)
    except: 
        return None

def graham(lpa, vpa):
    return math.sqrt(22.5 * lpa * vpa) if is_valid(lpa) and is_valid(vpa) and lpa > 0 and vpa > 0 else None

def pl_justo(lpa, setor, roe, crescimento, margem):
    if not is_valid(lpa) or lpa <= 0: return None
    teto = {"banco": 11, "eletrica": 12, "commodities": 8, "crescimento": 22}.get(setor, 10)
    base = 6 + (roe * 0.15 if is_valid(roe) else 0) + (crescimento * 0.20 if is_valid(crescimento) else 0)
    return lpa * max(4, min(base, teto))

# =====================================================
# FUNÇÃO CORRIGIDA: P/VP JUSTO PARA FINANCEIRAS E SEGURADORAS
# =====================================================
def pvp_justo(roe, taxa_desconto, crescimento=0):
    try:
        if not is_valid(roe) or not is_valid(taxa_desconto): return None
        
        # Teto subiu para 0.60 para permitir ROE alto de Seguradoras
        roe_norm = min(roe / 100, 0.60) 
        g = max((crescimento or 0) / 100, 0)
        ke = max(taxa_desconto, 0.11)
        if g >= ke - 0.02: g = max(0, ke - 0.02)
        numerador = roe_norm - g
        denominador = ke - g
        
        if denominador <= 0: return None
        
        # Multiplicador máximo subiu de 2.5 para 8.0x
        return max(min(numerador / denominador, 8.0), 0.5) 
    except: return None

def calcular_valuation(linha):
    setor = linha.get("Setor")
    preco = linha.get("Preço")
    lpa, vpa = linha.get("LPA (Médio)"), linha.get("VPA")
    
    # =====================================================
    # PREPARAÇÃO E MODELOS BASE
    # =====================================================
    v_graham = graham(lpa, vpa)
    v_bazin = (linha.get("Dividendos 12M") / 0.06) if linha.get("Dividendos 12M") else None
    
    # Ajuste de Perpetuidade para Telecom (Crescimento baixo no longo prazo)
    g_perpetuo_setor = 0.02 if setor == "telecom" else 0.03
    
    v_pl = pl_justo(lpa, setor, linha.get("ROE (%)"), linha.get("CAGR Lucro (%)"), linha.get("Margem (%)"))
    v_dcf = dcf_dois_estagios(
        linha.get("FCF/Ação (Médio)"), 
        linha.get("Taxa Desconto"), 
        linha.get("CAGR Lucro (%)"), 
        g_perp=g_perpetuo_setor
    )

    # Trava DCF primária
    if is_valid(v_dcf) and is_valid(preco): 
        v_dcf = min(v_dcf, preco * 2.5)

    # =====================================================
    # PONDERAÇÃO SETORIAL IDEAL
    # =====================================================
    if setor in ["banco", "seguradora"]:
        # SUBSTITUIÇÃO DO GRAHAM PELO P/VP JUSTO
        m_pvp = pvp_justo(linha.get("ROE (%)"), linha.get("Taxa Desconto"), linha.get("CAGR Lucro (%)"))
        v_pvp = (vpa * m_pvp) if is_valid(vpa) and is_valid(m_pvp) else None
        v_real = media_ponderada([(v_pl, 0.7), (v_pvp, 0.3)])
        
    elif setor in ["eletrica", "saneamento", "telecom"]:
        v_real = media_ponderada([(v_dcf, 0.4), (v_pl, 0.6)])
        
    elif setor in ["mineracao"]:
        # Ajustado para 5.5 para dar fôlego a mineradoras premium (ex: VALE3)
        v_ev = (linha.get("EBITDA/Ação") * 5.5) if linha.get("EBITDA/Ação") else None
        v_real = media_ponderada([(v_ev, 0.5), (v_graham, 0.3), (v_pl, 0.2)])
        
    elif setor in ["commodities", "papel"]:
        # Ajustado para 4.5 conforme regra institucional para commodity BR
        v_ev = (linha.get("EBITDA/Ação") * 4.5) if linha.get("EBITDA/Ação") else None
        v_real = media_ponderada([(v_ev, 0.5), (v_graham, 0.3), (v_pl, 0.2)])
        
    elif setor in ["crescimento", "construcao"]:
        v_real = media_ponderada([(v_dcf, 0.45), (v_pl, 0.55)])
        
    else:
        v_real = media_ponderada([(v_pl, 0.5), (v_dcf, 0.3), (v_graham, 0.2)])

    # =====================================================
    # AJUSTE POR QUALIDADE (SCORE)
    # =====================================================
    score = calcular_score(linha)
    if is_valid(v_real): 
        v_real *= fator_score(score)
    
    # =====================================================
    # DESCONTOS ESTRUTURAIS (HAIRCUTS)
    # =====================================================
    ticker = linha.get("Ticker", "")
    estatais = ["BBAS3", "PETR4", "PETR3", "CMIG4", "CMIG3", "SAPR11", "SAPR4", "SBSP3", "CSMG3", "CXSE3"]
    
    if is_valid(v_real):
        # 1. Risco Político (Desconto de 25%)
        if ticker in estatais:
            v_real *= 0.75
            
        # 2. Risco Cíclico de Incorporação (Desconto de 20%)
        if setor == "construcao":
            v_real *= 0.80

    # =====================================================
    # TRAVA DE SEGURANÇA FINAL (CAP DE UPSIDE)
    # =====================================================
    if is_valid(v_real) and is_valid(preco):
        if setor in ["eletrica", "saneamento", "telecom"]:
            v_real = min(v_real, preco * 1.7)  # Cap reduzido para 70%
        elif setor in ["commodities", "mineracao", "papel"]:
            v_real = min(v_real, preco * 1.5)  # Cap reduzido para 50%
        elif setor in ["banco", "seguradora"]:
            v_real = min(v_real, preco * 1.8)  # Cap reduzido para 80%
        elif setor == "construcao":
            v_real = min(v_real, preco * 1.6)  # Cap reduzido para 60%
        else:
            v_real = min(v_real, preco * 2.0)  # Máximo absoluto global de 100%

    # Cálculo do desconto recolocado para enviar ao dicionário final
    desconto = ((v_real - preco) / preco * 100) if is_valid(v_real) and is_valid(preco) else 0
            
    return {
        "Preço Justo Real": round(v_real, 2) if v_real else None,
        "Preço Justo Bazin": round(v_bazin, 2) if v_bazin else None,
        "Valor Justo DCF": round(v_dcf, 2) if v_dcf else None,
        "Desconto (%)": round(desconto, 2),
        "Score": round(score, 2),
        "Recomendação": "Forte Compra" if desconto >= 25 and score >= 7 else "Compra" if desconto >= 10 else "Caro" if desconto < 0 else "Neutro"
    }