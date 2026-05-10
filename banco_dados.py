# banco_dados.py (Atualizado com formato Dia-Mês-Ano)

import sqlite3
import pandas as pd
from datetime import datetime
import os
from config import PASTA_OUTPUT, ARQUIVO_EXCEL

PASTA_RELATORIOS = "relatorios"

def salvar_no_banco(df):
    """Salva a fotografia do Valuation atual num banco SQLite."""
    try:
        os.makedirs(PASTA_OUTPUT, exist_ok=True)
        caminho_db = os.path.join(PASTA_OUTPUT, "historico_valuation.db")
        
        df_db = df.copy()
        df_db['Data_Extracao'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        conexao = sqlite3.connect(caminho_db)
        df_db.to_sql('historico_acoes', conexao, if_exists='append', index=False)
        conexao.close()
        
        print(f"[OK] Histórico salvo com sucesso em: {caminho_db}")
        
    except Exception as e:
        print(f"[ERRO] Falha na gravação do banco de dados: {e}")


def exportar_relatorio(df):
    """Exporta o dataframe atual para um ficheiro Excel na pasta de relatórios."""
    try:
        os.makedirs(PASTA_RELATORIOS, exist_ok=True)
        
        # ALTERAÇÃO AQUI: Novo formato Dia-Mês-Ano_Hora-Minuto
        data_atual = datetime.now().strftime("%d-%m-%Y_%Hh%M")
        nome_historico = f"ranking_{data_atual}.xlsx"
        
        caminho_historico = os.path.join(PASTA_RELATORIOS, nome_historico)
        caminho_latest = os.path.join(PASTA_RELATORIOS, ARQUIVO_EXCEL)
        
        df_export = df.copy()
        
        # Guarda a versão com data e a versão "latest" (sempre a mais nova)
        df_export.to_excel(caminho_latest, index=False)
        df_export.to_excel(caminho_historico, index=False)
        
        print(f"[OK] Relatório exportado com sucesso para a pasta: '{PASTA_RELATORIOS}'")
        
    except Exception as e:
        print(f"[ERRO] Falha ao exportar relatório Excel: {e}")