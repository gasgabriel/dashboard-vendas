"""Painel de vendas. Rode com: streamlit run painel/app.py"""
import sys
from pathlib import Path

# o Streamlit só coloca a pasta painel/ no caminho; precisamos da raiz para achar "pipeline"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st  # noqa: E402

from pipeline import consultas  # noqa: E402
from pipeline.carga import conectar  # noqa: E402
from pipeline.formato import brl, inteiro  # noqa: E402

st.set_page_config(page_title="Painel de vendas", layout="wide")
st.title("Painel de vendas")


@st.cache_data(ttl=60)
def carregar_opcoes():
    with conectar(tentativas=3) as conn:
        return consultas.periodo_disponivel(conn), consultas.regioes_disponiveis(conn)


@st.cache_data(ttl=60)
def carregar_dados(inicio, fim, regioes):
    regioes = list(regioes)
    with conectar(tentativas=3) as conn:
        return {
            "kpis": consultas.kpis(conn, inicio, fim, regioes),
            "por_mes": consultas.receita_por_mes(conn, inicio, fim, regioes),
            "top": consultas.top_produtos(conn, inicio, fim, regioes),
            "categoria": consultas.receita_por_categoria(conn, inicio, fim, regioes),
            "ranking": consultas.ranking_vendedores(conn, inicio, fim, regioes),
        }


@st.cache_data(ttl=60)
def carregar_execucao():
    with conectar(tentativas=3) as conn:
        ultima = consultas.ultima_execucao(conn)
        cargas = consultas.cargas_da_execucao(conn, int(ultima["id"])) if ultima else None
        return ultima, cargas


(primeira, ultima_data), todas_regioes = carregar_opcoes()
if primeira is None:
    st.warning("Ainda não há dados no banco. Rode o pipeline: python -m pipeline")
    st.stop()

# ---- filtros ----
st.sidebar.header("Filtros")
periodo = st.sidebar.date_input("Período", value=(primeira, ultima_data),
                                min_value=primeira, max_value=ultima_data)
regioes = st.sidebar.multiselect("Regiões", todas_regioes, default=todas_regioes)
if len(periodo) != 2:
    st.info("Escolha a data inicial e a final no filtro de período.")
    st.stop()
if not regioes:
    st.info("Escolha pelo menos uma região.")
    st.stop()
inicio, fim = periodo

dados = carregar_dados(inicio, fim, tuple(regioes))
k = dados["kpis"]
if k["vendas"] == 0:
    st.info("Nenhuma venda nesse período e nessas regiões.")
    st.stop()

# ---- números principais ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Receita total", brl(k["receita_total"]))
c2.metric("Vendas", inteiro(k["vendas"]))
c3.metric("Itens vendidos", inteiro(k["itens"]))
c4.metric("Ticket médio", brl(k["ticket_medio"]))

# ---- gráficos ----
st.subheader("Receita por mês")
st.bar_chart(dados["por_mes"].set_index("mes")["receita"])
with st.expander("Variação e acumulado por mês"):
    st.dataframe(dados["por_mes"], hide_index=True)

esquerda, direita = st.columns(2)
with esquerda:
    st.subheader("Top 5 produtos")
    st.bar_chart(dados["top"].set_index("produto")["receita"])
with direita:
    st.subheader("Receita por categoria")
    st.bar_chart(dados["categoria"].set_index("categoria")["receita"])

st.subheader("Ranking de vendedores por região")
st.dataframe(dados["ranking"], hide_index=True)

# ---- confiança nos dados ----
st.divider()
ultima, cargas = carregar_execucao()
if ultima:
    st.caption(f"Última carga: {ultima['inicio']:%d/%m/%Y %H:%M} · status: {ultima['status']}")
    with st.expander("Qualidade dos dados na última carga"):
        st.dataframe(cargas, hide_index=True)