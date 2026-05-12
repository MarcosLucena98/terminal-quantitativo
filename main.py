# main.py

import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor

from dados import buscar_dados
from valuation import calcular_valuation
from score import calcular_score
from banco_dados import salvar_no_banco, exportar_relatorio

# =========================================================
# SELIC BASE
# =========================================================

def obter_selic():
    """Busca a taxa Selic anualizada em tempo real via API do Banco Central do Brasil."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        dados = response.json()
        
        selic_anual = float(dados[0]['valor']) / 100
        print(f"[API BCB] Selic atualizada capturada: {selic_anual*100:.2f}%")
        return selic_anual
    except Exception as e:
        print(f"Erro ao buscar Selic do BCB, usando taxa padrão (10%). Erro: {e}")
        return 0.10 

# =========================================================
# PARALELISMO
# =========================================================

def buscar_dados_multiplos(selic, lista_tickers):
    resultados = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futuros = [executor.submit(buscar_dados, ticker, selic) for ticker in lista_tickers]
        for futuro in futuros:
            try:
                resultado = futuro.result()
                if resultado:
                    resultados.append(resultado)
            except Exception as erro:
                print(f"Erro Thread: {erro}")
    return pd.DataFrame(resultados)

# =========================================================
# ENGINE PRINCIPAL
# =========================================================

def gerar_analise(lista_tickers):
    selic = obter_selic()
    print(f"Iniciando busca paralela de {len(lista_tickers)} ativos... (Selic base: {selic*100:.2f}%)")

    # EXTRAÇÃO
    df = buscar_dados_multiplos(selic, lista_tickers)
    if df.empty:
        return pd.DataFrame()

    # SCORE
    df["Score"] = df.apply(calcular_score, axis=1)

    # VALUATION
    valuation_df = df.apply(calcular_valuation, axis=1, result_type="expand")
    valuation_df = valuation_df.loc[:, ~valuation_df.columns.duplicated()]
    if "Score" in valuation_df.columns:
        valuation_df = valuation_df.drop(columns=["Score"])

    df = pd.concat([df, valuation_df], axis=1)

    # ORDENAÇÃO E HISTÓRICO
    df = df.sort_values(by="Score", ascending=False)
    salvar_no_banco(df)
    exportar_relatorio(df)
    print("\nAnálise concluída.")

    return df