# =========================================================
# score.py (VERSÃO PROFISSIONAL INSTITUCIONAL)
# =========================================================

import math


# =========================================================
# HELPERS
# =========================================================

def limpar(v):
    try:
        if v is None:
            return None
        v = float(v)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except:
        return None

def clamp(valor, minimo=0, maximo=10):
    return max(min(valor, maximo), minimo)


# =========================================================
# NOTAS DE RENTABILIDADE E PREÇO
# =========================================================

def nota_roe(roe, setor):
    roe = limpar(roe)
    if roe is None: return 0

    if setor in ["banco", "seguradora"]: alvo = 18
    elif setor in ["eletrica", "saneamento"]: alvo = 12
    elif setor == "telecom": alvo = 10
    elif setor == "crescimento": alvo = 20
    else: alvo = 15

    nota = (roe / alvo) * 10
    return round(clamp(nota), 2)


def nota_margem(margem, setor):
    margem = limpar(margem)
    if margem is None: return 5

    if setor in ["banco", "seguradora"]: alvo = 25
    elif setor in ["eletrica", "saneamento"]: alvo = 20
    elif setor == "telecom": alvo = 15
    elif setor in ["commodities", "mineracao"]: alvo = 18
    else: alvo = 12

    nota = (margem / alvo) * 10
    return round(clamp(nota), 2)


def nota_pl(pl, setor):
    pl = limpar(pl)
    if pl is None or pl <= 0: return 0

    if setor in ["banco", "seguradora"]:
        if pl <= 6: return 10
        elif pl <= 8: return 8
        elif pl <= 10: return 6
        elif pl <= 12: return 4
        return 2

    elif setor in ["eletrica", "saneamento"]:
        if pl <= 8: return 10
        elif pl <= 10: return 8
        elif pl <= 12: return 6
        elif pl <= 15: return 4
        return 2

    elif setor == "telecom":
        if pl <= 10: return 10
        elif pl <= 13: return 8
        elif pl <= 16: return 6
        elif pl <= 20: return 4
        return 2

    elif setor in ["commodities", "mineracao", "papel"]:
        if pl <= 4: return 10
        elif pl <= 6: return 8
        elif pl <= 8: return 6
        elif pl <= 10: return 4
        return 2

    elif setor == "crescimento":
        if pl <= 20: return 10
        elif pl <= 25: return 8
        elif pl <= 35: return 6
        elif pl <= 45: return 4
        return 2

    else:
        if pl <= 8: return 10
        elif pl <= 10: return 8
        elif pl <= 15: return 6
        elif pl <= 20: return 4
        return 2


def nota_pvp(pvp, setor):
    pvp = limpar(pvp)
    if pvp is None or pvp <= 0: return 5

    if setor == "banco":
        if pvp <= 1: return 10
        elif pvp <= 1.5: return 8
        elif pvp <= 2: return 6
        elif pvp <= 2.5: return 4
        return 2

    elif setor in ["eletrica", "saneamento"]:
        if pvp <= 1: return 10
        elif pvp <= 1.5: return 8
        elif pvp <= 2: return 6
        elif pvp <= 3: return 4
        return 2

    else:
        nota = 10 - (pvp * 2)
        return round(clamp(nota), 2)


# =========================================================
# DIVIDENDOS E CAIXA
# =========================================================

def nota_dy(dy, payout, setor):
    dy = limpar(dy)
    if dy is None: return 0

    if setor in ["eletrica", "saneamento", "banco", "seguradora"]: alvo = 8
    elif setor in ["commodities", "mineracao"]: alvo = 10
    elif setor == "crescimento": alvo = 3
    else: alvo = 5

    nota = (dy / alvo) * 10
    return round(clamp(nota), 2)


def nota_divida(divida, setor):
    divida = limpar(divida)
    if divida is None: return 5

    if setor in ["banco", "seguradora"]: return 10
    if setor in ["eletrica", "saneamento"]:
        if divida <= 1.5: return 10
        elif divida <= 2.5: return 8
        elif divida <= 3.5: return 6
        elif divida <= 4.5: return 4
        return 2

    nota = 10 - (divida * 4)
    return round(clamp(nota), 2)


def nota_fcf(fcf, lucro):
    fcf = limpar(fcf)
    lucro = limpar(lucro)

    if fcf is None or lucro is None: return 5
    if lucro <= 0: return 0

    conversao = fcf / lucro
    if conversao >= 1: return 10

    nota = conversao * 10
    return round(clamp(nota), 2)


def nota_crescimento(crescimento):
    crescimento = limpar(crescimento)
    if crescimento is None: return 0

    nota = crescimento / 2
    return round(clamp(nota), 2)


# =========================================================
# NOVAS MÉTRICAS INSTITUCIONAIS: EVA E RISCO
# =========================================================

def nota_spread(spread, setor):
    spread = limpar(spread)
    
    if spread is None: return 5
    if setor in ["banco", "seguradora"]: return 5 
    
    if spread >= 10: return 10
    elif spread >= 5: return 8
    elif spread >= 2: return 6
    elif spread >= 0: return 4
    
    return 0 


def nota_estabilidade(cv_lucro):
    cv_lucro = limpar(cv_lucro)
    
    if cv_lucro is None: return 5
    
    # CORREÇÃO: Limites afrouxados para não destruir as empresas Cíclicas
    if cv_lucro <= 0.25: return 10   # Relógio Suíço 
    elif cv_lucro <= 0.60: return 8
    elif cv_lucro <= 1.00: return 6
    elif cv_lucro <= 2.00: return 4
    
    return 2 # Montanha-russa severa


# =========================================================
# PESOS SETORIAIS
# =========================================================

PESOS_SETOR = {
    "banco": {"roe": 0.25, "margem": 0.05, "pl": 0.15, "pvp": 0.20, "crescimento": 0.10, "dy": 0.10, "divida": 0.00, "estabilidade": 0.10, "fcf": 0.05, "spread": 0.00},
    "seguradora": {"roe": 0.25, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.10, "dy": 0.10, "divida": 0.00, "estabilidade": 0.10, "fcf": 0.10, "spread": 0.00},
    "eletrica": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.15, "divida": 0.10, "estabilidade": 0.15, "fcf": 0.05, "spread": 0.05},
    "saneamento": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.15, "divida": 0.10, "estabilidade": 0.15, "fcf": 0.05, "spread": 0.05},
    "telecom": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.15, "divida": 0.10, "estabilidade": 0.10, "fcf": 0.05, "spread": 0.10},
    "commodities": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.10, "divida": 0.10, "estabilidade": 0.20, "fcf": 0.05, "spread": 0.05},
    "mineracao": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.10, "divida": 0.10, "estabilidade": 0.20, "fcf": 0.05, "spread": 0.05},
    "crescimento": {"roe": 0.10, "margem": 0.10, "pl": 0.10, "pvp": 0.10, "crescimento": 0.20, "dy": 0.00, "divida": 0.10, "estabilidade": 0.05, "fcf": 0.05, "spread": 0.20},
    "construcao": {"roe": 0.10, "margem": 0.10, "pl": 0.10, "pvp": 0.10, "crescimento": 0.10, "dy": 0.10, "divida": 0.10, "estabilidade": 0.10, "fcf": 0.05, "spread": 0.15},
    "papel": {"roe": 0.10, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.05, "dy": 0.10, "divida": 0.10, "estabilidade": 0.15, "fcf": 0.05, "spread": 0.10},
    "default": {"roe": 0.15, "margem": 0.10, "pl": 0.15, "pvp": 0.10, "crescimento": 0.10, "dy": 0.10, "divida": 0.10, "estabilidade": 0.10, "fcf": 0.05, "spread": 0.05}
}


# =========================================================
# FATOR SCORE
# =========================================================

def fator_score(score):
    if score >= 9: return 1.15
    elif score >= 8: return 1.08
    elif score >= 7: return 1.03
    elif score >= 5: return 1.00
    elif score >= 3: return 0.90
    return 0.75


# =========================================================
# SCORE FINAL
# =========================================================

def calcular_score(linha):
    try:
        setor = linha.get("Setor")
        pesos = PESOS_SETOR.get(setor, PESOS_SETOR["default"])

        n_roe = nota_roe(linha.get("ROE (%)"), setor)
        n_margem = nota_margem(linha.get("Margem (%)"), setor)
        n_pl = nota_pl(linha.get("P/L"), setor)
        n_pvp = nota_pvp(linha.get("P/VP"), setor)
        n_dy = nota_dy(linha.get("DY (%)"), linha.get("Payout (%)", 0), setor)
        n_divida = nota_divida(linha.get("Dívida/PL"), setor)
        n_crescimento = nota_crescimento(linha.get("CAGR Lucro (%)"))
        n_fcf = nota_fcf(linha.get("FCF/Ação (Médio)"), linha.get("LPA (Médio)"))
        n_estabilidade = nota_estabilidade(linha.get("Volatilidade Lucro"))
        n_spread = nota_spread(linha.get("Spread ROIC-WACC (%)"), setor)

        score_bruto = (
            n_roe * pesos.get("roe", 0) +
            n_margem * pesos.get("margem", 0) +
            n_pl * pesos.get("pl", 0) +
            n_pvp * pesos.get("pvp", 0) +
            n_dy * pesos.get("dy", 0) +
            n_divida * pesos.get("divida", 0) +
            n_crescimento * pesos.get("crescimento", 0) +
            n_estabilidade * pesos.get("estabilidade", 0) +
            n_fcf * pesos.get("fcf", 0) +
            n_spread * pesos.get("spread", 0)
        )

        # CORREÇÃO: Divisão pela soma dos pesos para normalização
        soma_pesos = sum(pesos.values())
        if soma_pesos > 0:
            score_base = score_bruto / soma_pesos
        else:
            score_base = score_bruto

        # =====================================================
        # OVERLAYS QUANTITATIVOS INSTITUCIONAIS 
        # =====================================================
        margem = linha.get("Margem (%)", 0) or 0
        roic = linha.get("ROIC (%)", 0) or 0
        wacc = linha.get("CAPM (%)", 10) or 10
        fcf_yield = linha.get("FCF Yield (%)", 0) or 0

        # 1. Filtro de Margem Líquida
        if margem > 20.0:
            score_base += 0.5
        elif margem < 5.0:
            score_base -= 1.0

        # 2. Filtro de Criação de Valor (ROIC vs WACC)
        if setor not in ["banco", "seguradora"]: 
            if roic > 15.0:
                score_base += 0.5
            elif roic < wacc:
                score_base -= 1.0

        # 3. Filtro de Geração de Caixa (FCF Yield)
        # CORREÇÃO: Elétricas e Saneamento imunes a esse filtro (CAPEX alto natural)
        if setor not in ["banco", "seguradora", "eletrica", "saneamento"]:
            if fcf_yield > 10.0:
                score_base += 0.5
            elif fcf_yield < 3.0:
                score_base -= 0.5

        score_final = clamp(score_base, 0, 10)

        return round(score_final, 2)

    except Exception as e:
        print(f"Erro Score: {e}")
        return 0