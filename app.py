# =========================================================
# app.py (VERSÃO CLOUD: B3 SCRAPING + GOOGLE SHEETS)
# =========================================================

import streamlit as st
import plotly.express as px
import pandas as pd
import requests
from streamlit_gsheets import GSheetsConnection

from main import gerar_analise
from config import TICKERS as TICKERS_PADRAO

# =========================================================
# CONFIGURAÇÕES E MAPAS
# =========================================================

ICON_MAP = {
    "banco": "🏦",
    "eletrica": "⚡",
    "commodities": "🛢️",
    "papel": "🌲",
    "crescimento": "🚀",
    "consumo": "🛒",
    "fiis": "🏢",
    "saneamento": "🚰",
    "mineracao": "⛏️",
    "construcao": "🏗️",
    "seguradora": "🛡️",
    "telecom": "📡"
}

st.set_page_config(
    page_title="Terminal Quantitativo",
    layout="wide",
    page_icon="📈"
)

# =========================================================
# CSS PERSONALIZADO
# =========================================================

st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #1a1c24;
        padding: 15px;
        border-radius: 12px;
        border: 1px solid #2d2f3b;
        border-left: 4px solid #00ff88;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #2d2f3b;
        border-radius: 12px;
        overflow: hidden;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CAPTURA AUTOMÁTICA DE TODOS OS TICKERS DA B3
# =========================================================
@st.cache_data(ttl="24h")
def obter_todos_tickers_b3():
    try:
        url = 'https://www.fundamentus.com.br/resultado.php'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req = requests.get(url, headers=headers, timeout=10)
        
        tabelas = pd.read_html(req.text, decimal=',', thousands='.')
        df_fund = tabelas[0]
        
        tickers = [f"{papel.strip()}.SA" for papel in df_fund['Papel'].unique() if isinstance(papel, str)]
        return sorted(list(set(tickers)))
    except Exception as e:
        st.sidebar.warning("Falha ao buscar B3. Usando lista padrão.")
        return sorted(TICKERS_PADRAO)

# =========================================================
# HEADER
# =========================================================

st.title("📈 Terminal Quantitativo de Ações")
st.caption("Valuation Multi-Modelo | Score Multifator | Gestão de Carteira Cloud")

# =========================================================
# CONTROLE DE SESSÃO
# =========================================================

if 'df' not in st.session_state:
    st.session_state['df'] = None

# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.header("⚙️ Controle e Ativos")
    
    # Puxa todos os tickers e cruza com a sua lista de ações do config.py
    todos_tickers = obter_todos_tickers_b3()
    padrao_validos = [t for t in TICKERS_PADRAO if t in todos_tickers]
    if not padrao_validos: 
        padrao_validos = todos_tickers[:15]
    
    # Componente Multiselect Interativo
    lista_tickers = st.multiselect(
        "Selecione os ativos para análise:",
        options=todos_tickers,
        default=padrao_validos,
        help="Pesquise e selecione as ações. Dica: Não selecione dezenas de uma vez para evitar bloqueio no Yahoo Finance."
    )

    if st.button("🚀 Sincronizar Mercado", use_container_width=True):
        if len(lista_tickers) == 0:
            st.warning("Por favor, selecione pelo menos um ativo.")
        else:
            with st.spinner(f"Processando {len(lista_tickers)} ativos..."):
                df = gerar_analise(lista_tickers)
                if not df.empty:
                    df['Setor Original'] = df['Setor']
                    df['Setor'] = df['Setor'].apply(lambda s: f"{ICON_MAP.get(s, '📊')} {s.title()}")
                    st.session_state['df'] = df
                    
                    # =================================================
                    # SALVAR HISTÓRICO NO GOOGLE SHEETS
                    # =================================================
                    try:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        df_hist = df.copy()
                        df_hist['Data_Extracao'] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        try:
                            hist_antigo = conn.read(worksheet="Historico", ttl=0)
                            hist_antigo = hist_antigo.dropna(how="all") 
                            hist_novo = pd.concat([hist_antigo, df_hist], ignore_index=True)
                        except:
                            hist_novo = df_hist
                            
                        conn.update(worksheet="Historico", data=hist_novo)
                        st.success("Dados e Histórico sincronizados na nuvem.")
                    except Exception as e:
                        st.warning("Dados atualizados, mas falha ao salvar o histórico. Verifica se criaste a aba 'Historico' na folha de cálculo.")
                else:
                    st.error("Falha na sincronização.")

    st.divider()
    st.markdown("""
    ### 📌 Premissas Institucionais
    - **Selic Dinâmica:** API Banco Central
    - **ERP Mercado:** 6.0%
    - **Haircut Estatal:** 25%
    - **WACC Piso/Teto:** 8.0% / 20.0%
    """)

# =========================================================
# LÓGICA PRINCIPAL
# =========================================================

df = st.session_state['df']

if df is not None and not df.empty:
    
    # KPIs Rápidos
    df_desc = df.dropna(subset=['Desconto (%)']).sort_values(by="Desconto (%)", ascending=False)
    melhor_score = df.sort_values(by="Score", ascending=False).iloc[0]

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🏆 Melhor Score", melhor_score['Ticker'], f"{melhor_score['Score']:.2f}")
    col2.metric("🚀 Maior Upside", df_desc.iloc[0]['Ticker'], f"{df_desc.iloc[0]['Desconto (%)']:.2f}%")
    col3.metric("💰 DY Médio", "Carteira", f"{df['DY (%)'].mean():.2f}%")
    col4.metric("📊 ROIC Médio", "Carteira", f"{df['ROIC (%)'].mean():.2f}%")
    col5.metric("📦 Ativos", "Processados", len(df))

    st.divider()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏆 Ranking", "🔍 Raio-X", "🎯 Matriz Quant", "📈 Histórico", "💼 Minha Carteira"])

    # --- TAB 1: RANKING ---
    with tab1:
        st.subheader("🏆 Ranking Quantitativo")
        c1, c2, c3 = st.columns(3)
        with c1: score_min = st.slider("Score Mínimo", 0.0, 10.0, 6.0, 0.1)
        with c2: upside_min = st.slider("Upside Mínimo (%)", -50.0, 200.0, 0.0, 1.0)
        with c3: setor_filtro = st.selectbox("Filtrar Setor", ["Todos"] + sorted(df['Setor'].unique()))

        df_f = df[(df["Score"] >= score_min) & (df["Desconto (%)"] >= upside_min)].copy()
        if setor_filtro != "Todos": df_f = df_f[df_f["Setor"] == setor_filtro]

        def color_rec(val):
            color = {"Forte Compra": "#00ff88", "Compra": "#8affc1", "Neutro": "#ffd700"}.get(val, "#ff4d4d")
            return f'color: black; background-color: {color}'

        cols_view = [
            "Ticker", "Setor", "Preço", 
            "Preço Justo Real", "Preço Justo Bazin", 
            "Desconto (%)", "DY (%)", "Score", "Recomendação"
        ]
        
        st.dataframe(
            df_f[cols_view].style.format({
                "Preço": "R$ {:.2f}", 
                "Preço Justo Real": "R$ {:.2f}",
                "Preço Justo Bazin": "R$ {:.2f}",
                "Desconto (%)": "{:.2f}%", 
                "DY (%)": "{:.2f}%", 
                "Score": "{:.2f}"
            })
            .background_gradient(subset=["Score"], cmap="Greens")
            .background_gradient(subset=["Desconto (%)"], cmap="RdYlGn")
            .map(color_rec, subset=["Recomendação"]),
            use_container_width=True, height=500
        )

    # --- TAB 2: RAIO-X ---
    with tab2:
        st.subheader("🔍 Detalhamento do Ativo")
        selecionado = st.selectbox("Selecione um Ativo", df['Ticker'].unique())
        ativo = df[df['Ticker'] == selecionado].iloc[0]

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Preço Atual", f"R$ {ativo['Preço']:.2f}")
        m2.metric("Preço Justo Real", f"R$ {ativo['Preço Justo Real']:.2f}", f"{ativo['Desconto (%)']:.2f}%")
        m3.metric("Bazin (Informativo)", f"R$ {ativo.get('Preço Justo Bazin', 0):.2f}")
        m4.metric("Score de Qualidade", f"{ativo['Score']:.2f}", ativo['Recomendação'])

        st.divider()

        i1, i2, i3, i4 = st.columns(4)
        spread = ativo.get('Spread ROIC-WACC (%)', 0)
        color_spread = "normal" if spread >= 0 else "inverse"
        i1.metric("ROIC (%)", f"{ativo.get('ROIC (%)', 0):.2f}%", f"Spread: {spread:.2f}%", delta_color=color_spread)
        i2.metric("FCF Yield (%)", f"{ativo.get('FCF Yield (%)', 0):.2f}%", "Geração de Caixa")
        vol = ativo.get('Volatilidade Lucro', 0)
        i3.metric("Volatilidade Lucro", f"{vol:.2f}", "Risco (Menor é melhor)", delta_color="inverse")
        i4.metric("DY Atual (%)", f"{ativo['DY (%)']:.2f}%", f"R$ {ativo.get('Dividendos 12M', 0):.2f}/ano")

        modelos_data = {
            "Modelo": ["Atual", "Justo Real", "Bazin", "DCF"],
            "Valor": [
                ativo['Preço'], ativo['Preço Justo Real'], 
                ativo.get('Preço Justo Bazin', 0), ativo.get('Valor Justo DCF', 0)
            ]
        }
        fig_comp = px.bar(
            modelos_data, x="Modelo", y="Valor", color="Modelo",
            template="plotly_dark", title=f"Comparativo de Modelos: {selecionado}",
            text_auto='.2f'
        )
        st.plotly_chart(fig_comp, use_container_width=True)

    # --- TAB 3: MATRIZ ---
    with tab3:
        st.subheader("🎯 Matriz Risco x Retorno")
        fig = px.scatter(
            df_desc, x="Score", y="Desconto (%)", size="DY (%)", color="Setor",
            hover_name="Ticker", text="Ticker", template="plotly_dark", height=600
        )
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        fig.add_vline(x=7, line_dash="dash", line_color="green")
        st.plotly_chart(fig, use_container_width=True)

    # --- TAB 4: HISTÓRICO EM NUVEM ---
    with tab4:
        st.subheader("📈 Evolução do Valuation (Google Sheets)")
        st.markdown("*Os dados agora são gravados eternamente na nuvem e não são perdidos no reinício do servidor.*")
        ativo_h = st.selectbox("Ativo Histórico", df['Ticker'].unique(), key="h_box")
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            h = conn.read(worksheet="Historico", ttl="1m")
            h = h.dropna(subset=['Ticker'])
            h = h[h['Ticker'] == ativo_h]
            
            if not h.empty:
                h['Data_Extracao'] = pd.to_datetime(h['Data_Extracao'])
                fig_h = px.line(h, x='Data_Extracao', y=['Preço', 'Preço Justo Real'], template="plotly_dark", title=f"Evolução: {ativo_h}")
                st.plotly_chart(fig_h, use_container_width=True)
                st.dataframe(h.sort_values(by="Data_Extracao", ascending=False), use_container_width=True)
            else: 
                st.info("Sem dados de histórico na nuvem para este ativo. Clica em 'Sincronizar' para guardar a primeira foto.")
        except: 
            st.warning("Banco de dados histórico não encontrado. Verifica se a aba 'Historico' existe na folha de cálculo.")

    # --- TAB 5: MINHA CARTEIRA (PERSISTENTE NA NUVEM) ---
    with tab5:
        st.subheader("💼 Gestão de Carteira na Nuvem (Google Sheets)")
        
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            df_nuvem = conn.read(worksheet="Carteira", ttl="1m")
            df_nuvem = df_nuvem.dropna(subset=["Ticker"])
        except Exception as e:
            st.warning("⚠️ Conexão com Google Sheets não configurada ou falhou. Usando banco em memória temporária.")
            df_nuvem = pd.DataFrame(columns=["Ticker", "Quantidade", "PM"])

        st.markdown("Edita as tuas Quantidades e Preços Médios abaixo e clica em **Salvar na Nuvem** para não perder os dados.")

        tickers_base = pd.DataFrame({"Ticker": df['Ticker']})
        carteira_merged = pd.merge(tickers_base, df_nuvem, on="Ticker", how="left").fillna(0)
        
        carteira_merged["Quantidade"] = carteira_merged["Quantidade"].astype(int)
        carteira_merged["PM"] = carteira_merged["PM"].astype(float)

        edited_df = st.data_editor(
            carteira_merged,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Ticker": st.column_config.Column("Ativo", disabled=True),
                "Quantidade": st.column_config.NumberColumn("Quantidade", min_value=0, step=1),
                "PM": st.column_config.NumberColumn("Preço Médio (R$)", min_value=0.0, step=0.01, format="%.2f")
            }
        )

        if st.button("💾 Salvar Alterações na Nuvem"):
            try:
                df_para_salvar = edited_df[edited_df["Quantidade"] > 0]
                conn.update(worksheet="Carteira", data=df_para_salvar)
                st.success("✅ Carteira sincronizada com o Google Sheets com sucesso!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Erro ao salvar: {e}. Verifica se a conexão Sheets está ativa.")

        carteira_ativa = edited_df[edited_df["Quantidade"] > 0]
        
        if not carteira_ativa.empty:
            df_merge = pd.merge(carteira_ativa, df[['Ticker', 'Preço', 'Dividendos 12M', 'Setor']], on="Ticker")
            
            df_merge["Valor Investido"] = df_merge["Quantidade"] * df_merge["PM"]
            df_merge["Saldo Atual"] = df_merge["Quantidade"] * df_merge["Preço"]
            df_merge["Lucro/Prejuízo (R$)"] = df_merge["Saldo Atual"] - df_merge["Valor Investido"]
            
            df_merge["PM_Valido"] = df_merge["PM"].apply(lambda x: x if x > 0 else 1) 
            df_merge["Rentabilidade (%)"] = ((df_merge["Preço"] / df_merge["PM_Valido"]) - 1) * 100
            df_merge["YOC (%)"] = (df_merge.get("Dividendos 12M", 0) / df_merge["PM_Valido"]) * 100
            
            df_merge["Dividendos Estimados (R$)"] = df_merge["Quantidade"] * df_merge.get("Dividendos 12M", 0)
            
            st.divider()
            st.markdown("### 📊 Painel de Desempenho Real")
            
            total_investido = df_merge["Valor Investido"].sum()
            total_atual = df_merge["Saldo Atual"].sum()
            lucro_total = total_atual - total_investido
            rent_total = (lucro_total / total_investido) * 100 if total_investido > 0 else 0
            div_total = df_merge["Dividendos Estimados (R$)"].sum()
            yoc_medio = (div_total / total_investido) * 100 if total_investido > 0 else 0
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Investido", f"R$ {total_investido:,.2f}")
            c2.metric("Saldo Atual", f"R$ {total_atual:,.2f}", f"{rent_total:.2f}%")
            
            cor_lucro = "normal" if lucro_total >= 0 else "inverse"
            c3.metric("Lucro/Prejuízo", f"R$ {lucro_total:,.2f}", delta_color=cor_lucro)
            c4.metric("Dividendos 12M (Estimados)", f"R$ {div_total:,.2f}", f"YOC Médio: {yoc_medio:.2f}%")
            
            st.dataframe(
                df_merge[[
                    "Ticker", "Setor", "Quantidade", "PM", "Preço", 
                    "Valor Investido", "Saldo Atual", "Lucro/Prejuízo (R$)", 
                    "Rentabilidade (%)", "YOC (%)", "Dividendos Estimados (R$)"
                ]].style.format({
                    "PM": "R$ {:.2f}",
                    "Preço": "R$ {:.2f}",
                    "Valor Investido": "R$ {:,.2f}",
                    "Saldo Atual": "R$ {:,.2f}",
                    "Lucro/Prejuízo (R$)": "R$ {:,.2f}",
                    "Rentabilidade (%)": "{:.2f}%",
                    "YOC (%)": "{:.2f}%",
                    "Dividendos Estimados (R$)": "R$ {:,.2f}"
                }).background_gradient(subset=["Rentabilidade (%)", "Lucro/Prejuízo (R$)"], cmap="RdYlGn"),
                use_container_width=True
            )
            
            # NOVO: GRÁFICO DE DISTRIBUIÇÃO POR SETOR
            st.markdown("### 🥧 Exposição por Setores")
            df_setores = df_merge.groupby("Setor")["Saldo Atual"].sum().reset_index()
            fig_setores = px.pie(df_setores, values="Saldo Atual", names="Setor", template="plotly_dark", hole=0.4)
            st.plotly_chart(fig_setores, use_container_width=True)
            
        else:
            st.info("👆 Edita a tabela acima adicionando as tuas quantidades para gerar o painel de carteira.")

else:
    st.info("A aguardar sincronização. Seleciona os ativos no painel lateral e clica em 'Sincronizar Mercado'.")