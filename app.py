from pathlib import Path

import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

st.set_page_config(
    page_title="Retail Intelligence ML",
    page_icon=":material/monitoring:",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(ttl="1h", max_entries=3)
def carregar_dados() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Carrega as três bases usadas pelo dashboard."""
    vendas = pd.read_csv(
        DATA_DIR / "vendas_limpas.csv.gz",
        parse_dates=["InvoiceDate"],
        dtype={"InvoiceNo": str, "StockCode": str},
    )
    segmentacao = pd.read_csv(DATA_DIR / "segmentacao_clientes.csv")
    propensao = pd.read_csv(DATA_DIR / "resultado_propensao.csv")
    return vendas, segmentacao, propensao


def moeda(valor: float) -> str:
    numero_formatado = (
        f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    )
    return f"£ {numero_formatado}"


def numero(valor: int | float) -> str:
    return f"{int(valor):,}".replace(",", ".")


def card_metrica(titulo: str, valor: str, descricao: str) -> None:
    with st.container(border=True, height="stretch"):
        st.metric(titulo, valor)
        st.caption(descricao)


# O cabeçalho aparece antes da leitura das bases para resposta visual imediata.
st.title("Retail Intelligence ML", icon=":material/monitoring:")
st.write(
    "Inteligência comercial para acompanhar desempenho, compreender perfis "
    "de clientes e priorizar oportunidades de recompra."
)
with st.container(horizontal=True):
    st.badge("Análise comercial", icon=":material/query_stats:", color="blue")
    st.badge("Segmentação K-Means", icon=":material/hub:", color="violet")
    st.badge("Machine Learning", icon=":material/model_training:", color="green")

try:
    with st.skeleton(height=90):
        vendas, segmentacao, propensao = carregar_dados()
except FileNotFoundError as erro:
    st.error(
        f"Não foi possível localizar uma das bases: `{erro.filename}`.",
        icon=":material/error:",
    )
    st.stop()
except Exception as erro:
    st.error(f"Não foi possível carregar os dados: {erro}", icon=":material/error:")
    st.stop()

for base in (segmentacao, propensao):
    if "CustomerID" in base.columns:
        base["CustomerID"] = pd.to_numeric(base["CustomerID"], errors="coerce")

data_inicio = vendas["InvoiceDate"].min().strftime("%d/%m/%Y")
data_fim = vendas["InvoiceDate"].max().strftime("%d/%m/%Y")
st.caption(f"Base analisada: {data_inicio} a {data_fim} · Valores em libra esterlina")

aba_geral, aba_segmentacao, aba_recompra = st.tabs(
    [
        ":material/space_dashboard: Visão geral",
        ":material/groups: Segmentação de clientes",
        ":material/autorenew: Propensão de recompra",
    ]
)


with aba_geral:
    faturamento = vendas["TotalPrice"].sum()
    pedidos = vendas["InvoiceNo"].nunique()
    clientes = vendas["CustomerID"].nunique()
    produtos = vendas["StockCode"].nunique()
    ticket_medio = vendas.groupby("InvoiceNo")["TotalPrice"].sum().mean()
    participacao_uk = (
        vendas.loc[vendas["Country"] == "United Kingdom", "TotalPrice"].sum()
        / faturamento
        * 100
    )

    st.header("Visão executiva", icon=":material/analytics:")
    st.caption("Principais indicadores consolidados da operação comercial.")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        card_metrica("Faturamento", moeda(faturamento), "Receita comercial líquida")
    with col2:
        card_metrica("Pedidos", numero(pedidos), "Faturas comerciais únicas")
    with col3:
        card_metrica("Clientes", numero(clientes), "Clientes com identificação")
    with col4:
        card_metrica("Ticket médio", moeda(ticket_medio), "Valor médio por pedido")

    with st.container(border=True):
        apoio1, apoio2, apoio3 = st.columns([1, 1, 2], vertical_alignment="center")
        apoio1.metric("Produtos no portfólio", numero(produtos))
        apoio2.metric("Receita do Reino Unido", f"{participacao_uk:.1f}%")
        apoio3.caption(
            "A operação apresenta forte concentração geográfica no mercado britânico. "
            "A leitura por país ajuda a dimensionar essa dependência comercial."
        )

    st.subheader("Evolução do faturamento", icon=":material/show_chart:")
    st.caption(
        "Receita mensal da base comercial. Dezembro de 2011 foi removido por estar incompleto."
    )
    faturamento_mensal = (
        vendas.set_index("InvoiceDate").resample("ME")["TotalPrice"].sum()
    )
    faturamento_mensal = faturamento_mensal[
        faturamento_mensal.index < "2011-12-01"
    ].rename("Faturamento").reset_index()
    st.line_chart(
        faturamento_mensal,
        x="InvoiceDate",
        y="Faturamento",
        x_label="Mês",
        y_label="Faturamento (£)",
        color="primary",
        height=340,
    )

    st.subheader("Desempenho de produtos", icon=":material/inventory_2:")
    st.caption(
        "Rankings de produtos físicos; códigos administrativos DOT, POST e M foram excluídos."
    )
    vendas_produtos = vendas[
        ~vendas["StockCode"].isin(["DOT", "POST", "M"])
    ].copy()
    produtos_quantidade = (
        vendas_produtos.groupby("Description", as_index=False)["Quantity"]
        .sum()
        .nlargest(10, "Quantity")
        .rename(columns={"Description": "Produto", "Quantity": "Quantidade"})
    )
    produtos_receita = (
        vendas_produtos.groupby("Description", as_index=False)["TotalPrice"]
        .sum()
        .nlargest(10, "TotalPrice")
        .rename(columns={"Description": "Produto", "TotalPrice": "Faturamento"})
    )
    grafico1, grafico2 = st.columns(2)
    with grafico1.container(border=True, height="stretch"):
        st.markdown("**Top 10 por quantidade vendida**")
        st.bar_chart(
            produtos_quantidade,
            x="Produto",
            y="Quantidade",
            horizontal=True,
            sort="-Quantidade",
            color="blue",
            height=380,
        )
    with grafico2.container(border=True, height="stretch"):
        st.markdown("**Top 10 por faturamento**")
        st.bar_chart(
            produtos_receita,
            x="Produto",
            y="Faturamento",
            horizontal=True,
            sort="-Faturamento",
            color="green",
            height=380,
        )

    st.subheader("Mercados com maior faturamento", icon=":material/public:")
    faturamento_pais = (
        vendas.groupby("Country", as_index=False)["TotalPrice"]
        .sum()
        .nlargest(10, "TotalPrice")
        .rename(columns={"Country": "País", "TotalPrice": "Faturamento"})
    )
    with st.container(border=True):
        st.bar_chart(
            faturamento_pais,
            x="País",
            y="Faturamento",
            horizontal=True,
            sort="-Faturamento",
            color="violet",
            height=390,
        )
        st.caption(
            f"O Reino Unido representa aproximadamente {participacao_uk:.1f}% "
            "do faturamento total."
        )


with aba_segmentacao:
    st.header("Segmentação de clientes", icon=":material/groups:")
    st.caption(
        "Agrupamento comportamental por K-Means a partir de recência, frequência e valor monetário."
    )
    contagem_clusters = segmentacao["Cluster_nome"].value_counts()
    clusters = [
        ("Alto valor / VIP", "VIP", "Clientes de maior valor e engajamento"),
        ("Regulares / Intermediários", "Regulares", "Relacionamento comercial recorrente"),
        ("Recentes / Baixo engajamento", "Recentes", "Clientes novos a desenvolver"),
        ("Inativos / Perdidos", "Inativos", "Prioridade para reativação"),
    ]
    cols = st.columns(4)
    for coluna, (chave, titulo, descricao) in zip(cols, clusters):
        with coluna:
            card_metrica(titulo, numero(contagem_clusters.get(chave, 0)), descricao)

    receita_cluster = (
        segmentacao.groupby("Cluster_nome")["Monetary"].sum().sort_values(ascending=False)
    )
    percentual_cluster = receita_cluster / receita_cluster.sum() * 100
    tabela_receita_cluster = pd.DataFrame(
        {
            "Segmento": receita_cluster.index,
            "Receita": receita_cluster.values,
            "Participação": percentual_cluster.values,
        }
    )
    visual, tabela = st.columns([1.2, 1])
    with visual.container(border=True, height="stretch"):
        st.markdown("**Participação da receita por segmento**")
        st.bar_chart(
            tabela_receita_cluster,
            x="Segmento",
            y="Participação",
            horizontal=True,
            sort="-Participação",
            color="blue",
            height=330,
        )
    with tabela.container(border=True, height="stretch"):
        st.markdown("**Receita consolidada**")
        st.dataframe(
            tabela_receita_cluster,
            hide_index=True,
            height=330,
            column_config={
                "Receita": st.column_config.NumberColumn("Receita", format="£ %.2f"),
                "Participação": st.column_config.ProgressColumn(
                    "Participação", format="%.2f%%", min_value=0, max_value=100
                ),
            },
        )

    st.subheader("Perfil médio dos segmentos", icon=":material/insights:")
    perfil_cluster = (
        segmentacao.groupby("Cluster_nome")
        .agg(
            Clientes=("CustomerID", "count"),
            Recency_media=("Recency", "mean"),
            Frequency_media=("Frequency", "mean"),
            Monetary_medio=("Monetary", "mean"),
        )
        .reset_index()
    )
    st.dataframe(
        perfil_cluster,
        hide_index=True,
        column_config={
            "Cluster_nome": st.column_config.TextColumn("Segmento"),
            "Clientes": st.column_config.NumberColumn("Clientes", format="%d"),
            "Recency_media": st.column_config.NumberColumn("Recência média", format="%.1f dias"),
            "Frequency_media": st.column_config.NumberColumn("Frequência média", format="%.2f"),
            "Monetary_medio": st.column_config.NumberColumn("Gasto médio", format="£ %.2f"),
        },
    )

    st.subheader("Explorar clientes", icon=":material/manage_search:")
    segmentos_disponiveis = ["Todos"] + sorted(
        segmentacao["Cluster_nome"].dropna().unique().tolist()
    )
    filtro_segmento = st.selectbox(
        "Filtrar por segmento", segmentos_disponiveis, key="filtro_segmento", width=360
    )
    tabela_segmentacao = segmentacao.copy()
    if filtro_segmento != "Todos":
        tabela_segmentacao = tabela_segmentacao[
            tabela_segmentacao["Cluster_nome"] == filtro_segmento
        ]
    colunas_segmentacao = [
        c for c in ["CustomerID", "Recency", "Frequency", "Monetary", "Cluster_nome"]
        if c in tabela_segmentacao.columns
    ]
    st.caption(f"{numero(len(tabela_segmentacao))} clientes encontrados")
    st.dataframe(
        tabela_segmentacao[colunas_segmentacao].sort_values("Monetary", ascending=False),
        hide_index=True,
        height=430,
        column_config={
            "CustomerID": st.column_config.NumberColumn("Cliente", format="%.0f"),
            "Recency": st.column_config.NumberColumn("Recência", format="%d dias"),
            "Frequency": st.column_config.NumberColumn("Frequência", format="%d"),
            "Monetary": st.column_config.NumberColumn("Valor total", format="£ %.2f"),
            "Cluster_nome": st.column_config.TextColumn("Segmento"),
        },
    )


with aba_recompra:
    st.header("Propensão de recompra", icon=":material/autorenew:")
    st.caption(
        "Probabilidade estimada pelo Random Forest para priorizar ações comerciais por cliente."
    )
    contagem_propensao = propensao["Propensao"].value_counts()
    cards_propensao = [
        ("Alta", "Alta propensão", "Prioridade para conversão"),
        ("Média", "Média propensão", "Oportunidade para nutrição"),
        ("Baixa", "Baixa propensão", "Estratégia de reativação"),
    ]
    cols = st.columns(3)
    for coluna, (chave, titulo, descricao) in zip(cols, cards_propensao):
        with coluna:
            card_metrica(titulo, numero(contagem_propensao.get(chave, 0)), descricao)

    st.subheader("Desempenho do modelo", icon=":material/model_training:")
    st.caption("Métricas no conjunto de teste com threshold de classificação igual a 0,50.")
    metricas = [
        ("Accuracy", "71,1%", "Acertos totais"),
        ("Recall", "63,4%", "Recompradores identificados"),
        ("F1-score", "59,8%", "Equilíbrio precisão/recall"),
        ("ROC-AUC", "74,5%", "Capacidade de ordenação"),
    ]
    cols = st.columns(4)
    for coluna, (titulo, valor, descricao) in zip(cols, metricas):
        with coluna:
            card_metrica(titulo, valor, descricao)

    st.subheader("Carteira por probabilidade", icon=":material/filter_alt:")
    filtro_propensao = st.segmented_control(
        "Filtrar por propensão",
        ["Todos", "Alta", "Média", "Baixa"],
        default="Todos",
        key="filtro_propensao",
    )
    tabela_propensao = propensao.copy()
    if filtro_propensao and filtro_propensao != "Todos":
        tabela_propensao = tabela_propensao[
            tabela_propensao["Propensao"] == filtro_propensao
        ]
    tabela_propensao["Probabilidade (%)"] = (
        tabela_propensao["ProbabilidadeRecompra"] * 100
    ).round(1)
    tabela_propensao = tabela_propensao.sort_values(
        "ProbabilidadeRecompra", ascending=False
    )
    colunas_propensao = [
        c for c in [
            "CustomerID", "Recency", "Frequency", "Monetary", "TicketMedio",
            "ProdutosDistintos", "TempoCliente", "Probabilidade (%)", "Propensao",
        ] if c in tabela_propensao.columns
    ]
    st.caption(f"{numero(len(tabela_propensao))} clientes encontrados")
    config_propensao = {
        "CustomerID": st.column_config.NumberColumn("Cliente", format="%.0f"),
        "Recency": st.column_config.NumberColumn("Recência", format="%d dias"),
        "Frequency": st.column_config.NumberColumn("Frequência", format="%d"),
        "Monetary": st.column_config.NumberColumn("Valor total", format="£ %.2f"),
        "TicketMedio": st.column_config.NumberColumn("Ticket médio", format="£ %.2f"),
        "ProdutosDistintos": st.column_config.NumberColumn("Produtos distintos", format="%d"),
        "TempoCliente": st.column_config.NumberColumn("Tempo de cliente", format="%d dias"),
        "Probabilidade (%)": st.column_config.ProgressColumn(
            "Probabilidade", format="%.1f%%", min_value=0, max_value=100
        ),
        "Propensao": st.column_config.TextColumn("Propensão"),
    }
    st.dataframe(
        tabela_propensao[colunas_propensao],
        hide_index=True,
        height=450,
        column_config=config_propensao,
    )

    st.subheader("Top oportunidades", icon=":material/leaderboard:")
    st.caption("Dez clientes com maior probabilidade estimada de realizar uma nova compra.")
    top_recompra = tabela_propensao.head(10)
    colunas_top = [
        c for c in ["CustomerID", "Probabilidade (%)", "Propensao", "Frequency", "Monetary"]
        if c in top_recompra.columns
    ]
    st.dataframe(
        top_recompra[colunas_top],
        hide_index=True,
        column_config=config_propensao,
    )

st.caption("Retail Intelligence ML · Projeto de portfólio em Data Science e Engenharia de IA")
