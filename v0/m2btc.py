import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Preço m² Portugal: EUR vs BTC",
    page_icon="🏠",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .stats-container {
        background-color: #1E1E1E;
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Title
st.title("🏠 Preço por m² em Portugal - EUR vs BTC")
st.markdown("---")

# Load and process data
@st.cache_data
def load_data():
    # Get the directory where this script is located
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load BTC data
    btc_eur = pd.read_csv(os.path.join(script_dir, "BTC_EUR Kraken Historical Data (1).csv"))
    btc_eur['Date'] = pd.to_datetime(btc_eur['Date'])
    btc_eur['Price'] = btc_eur['Price'].str.replace(',', '').astype(float)

    # Load real estate data
    imob_pt = pd.read_csv(os.path.join(script_dir, "m2-casas-PT.csv"))
    imob_pt['Date'] = pd.to_datetime(imob_pt['Mes'], format='%d-%m-%Y')

    # Merge datasets
    df = btc_eur.merge(imob_pt[['Date', 'Preco m2 [EUR]']], on='Date', how='right')
    df = df[['Date', 'Price', 'Preco m2 [EUR]']].copy()
    df['Preco m2 [BTC]'] = df['Preco m2 [EUR]'] / df['Price']
    df = df.sort_values('Date', ascending=True).reset_index(drop=True)

    return df

# Load data
df = load_data()

# Sidebar controls
st.sidebar.header("Controlos")

# Date range slider
min_date = df['Date'].min().date()
max_date = df['Date'].max().date()

date_range = st.sidebar.date_input(
    "Selecionar intervalo de datas:",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Log scale toggle
use_log_scale = st.sidebar.checkbox("Escala logarítmica para BTC", value=False)

# Preset date ranges
st.sidebar.markdown("### Atalhos")
col1, col2 = st.sidebar.columns(2)
if col1.button("1 Ano"):
    date_range = (max_date.replace(year=max_date.year - 1), max_date)
if col2.button("3 Anos"):
    date_range = (max_date.replace(year=max_date.year - 3), max_date)

col3, col4 = st.sidebar.columns(2)
if col3.button("5 Anos"):
    date_range = (max_date.replace(year=max_date.year - 5), max_date)
if col4.button("Tudo"):
    date_range = (min_date, max_date)

# Filter data based on date range
if len(date_range) == 2:
    start_date, end_date = date_range
    filtered_df = df[(df['Date'].dt.date >= start_date) & (df['Date'].dt.date <= end_date)]
else:
    filtered_df = df

# Check if we have data
if len(filtered_df) == 0:
    st.warning("Nenhum dado disponível para o período selecionado.")
    st.stop()

# Display summary statistics
st.sidebar.markdown("---")
st.sidebar.markdown("### Estatísticas")
st.sidebar.metric("Período selecionado", f"{len(filtered_df)} meses")
st.sidebar.metric("EUR/m² (atual)", f"€{filtered_df['Preco m2 [EUR]'].iloc[-1]:,.0f}")
st.sidebar.metric("BTC/m² (atual)", f"{filtered_df['Preco m2 [BTC]'].iloc[-1]:.6f} BTC")

# Explanatory text
st.markdown("""
<div style='background-color: #1a1a1a; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1.5rem; border-left: 4px solid #f39c12;'>
    <p style='font-size: 1.1rem; line-height: 1.6; margin-bottom: 1rem;'>
    Nos últimos anos, o aumento da oferta monetária tem contribuído para a inflação, fazendo com que os preços dos imóveis em Portugal aumentem constantemente.
    \n Isto significa que os teus euros compram cada vez menos metros quadrados.
    \n A Bitcoin, com a sua oferta limitada a 21 milhões de unidades, surge como uma ferramenta de proteção do poder de compra.
    \n Como podes comprovar no gráfico abaixo, o mesmo metro quadrado que fica cada vez mais caro em euros, fica progressivamente mais barato quando medido em Bitcoin.
    </p>
</div>
""", unsafe_allow_html=True)

# Calculate EUR variation for impact statement
if len(filtered_df) > 1:
    first = filtered_df.iloc[0]
    latest = filtered_df.iloc[-1]
    eur_change = ((latest['Preco m2 [EUR]'] - first['Preco m2 [EUR]']) / first['Preco m2 [EUR]']) * 100

    # Determine word and color based on price change
    if eur_change > 0:
        # Price increased - more expensive (red)
        price_word = "caro"
        color = "#e74c3c"  # Red
    else:
        # Price decreased - cheaper (green)
        price_word = "barato"
        color = "#2ecc71"  # Green

    abs_change = abs(eur_change)

    # Impact statement with dynamic percentage
    st.markdown(f"""
    <div style='text-align: center; padding: 1.5rem; margin-bottom: 2rem;'>
        <p style='font-size: 1.5rem; margin: 0;'>
            <span style='color: white;'>No período selecionado, o imóvel está</span>
            <span style='color: {color}; font-weight: bold;'> {abs_change:.1f}% mais {price_word}</span><span style='color: white;'>.</span>
        </p>
        <p style='font-size: 1.3rem; color: #bbb; margin-top: 0.5rem;'>
            Quanto aumentou o teu salário?
        </p>
    </div>
    """, unsafe_allow_html=True)

# Create Plotly figure
fig = make_subplots(specs=[[{"secondary_y": True}]])

# Add EUR price trace
fig.add_trace(
    go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Preco m2 [EUR]'],
        name='Preço/m² [EUR]',
        mode='lines+markers',
        marker=dict(color='green', size=6),
        line=dict(color='green', width=2),
        hovertemplate='<b>Data:</b> %{x|%Y-%m-%d}<br><b>EUR:</b> €%{y:,.0f}<extra></extra>'
    ),
    secondary_y=False
)

# Add BTC price trace
fig.add_trace(
    go.Scatter(
        x=filtered_df['Date'],
        y=filtered_df['Preco m2 [BTC]'],
        name='Preço/m² [BTC]',
        mode='lines+markers',
        marker=dict(color='orange', size=6, symbol='square'),
        line=dict(color='orange', width=2),
        hovertemplate='<b>Data:</b> %{x|%Y-%m-%d}<br><b>BTC:</b> %{y:.6f}<extra></extra>'
    ),
    secondary_y=True
)

# Update axes
fig.update_xaxes(title_text="Data")
fig.update_yaxes(
    title_text="<b>Preço por m² (EUR)</b>",
    secondary_y=False,
    title_font=dict(color='green'),
    gridcolor='rgba(0, 128, 0, 0.15)'  # Dim green for EUR axis
)

y_axis_type = "log" if use_log_scale else "linear"
fig.update_yaxes(
    title_text="<b>Preço por m² (BTC)</b>",
    secondary_y=True,
    type=y_axis_type,
    title_font=dict(color='orange'),
    gridcolor='rgba(255, 165, 0, 0.15)'  # Dim orange for BTC axis
)

# Update layout
fig.update_layout(
    hovermode='x unified',
    height=600,
    showlegend=True,
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1
    )
)

# Display plot
st.plotly_chart(fig, use_container_width=True)

# Statistics comparison
st.markdown("---")
st.subheader("📈 Análise Comparativa")

if len(filtered_df) > 1:
    # Calculate variations
    first = filtered_df.iloc[0]
    latest = filtered_df.iloc[-1]

    # EUR absolute and percentage variation
    eur_absolute = latest['Preco m2 [EUR]'] - first['Preco m2 [EUR]']
    eur_percent = (eur_absolute / first['Preco m2 [EUR]']) * 100
    eur_sign = "+ " if eur_absolute >= 0 else "- "

    # BTC absolute and percentage variation
    btc_absolute = latest['Preco m2 [BTC]'] - first['Preco m2 [BTC]']
    btc_percent = (btc_absolute / first['Preco m2 [BTC]']) * 100
    btc_sign = "+ " if btc_absolute >= 0 else "- "

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Variação EUR/m²",
            f"{eur_sign}€{abs(eur_absolute):,.0f}",
            f"{eur_percent:.2f}%",
            delta_color="inverse"  # Red for increase, green for decrease
        )

    with col2:
        st.metric(
            "Variação BTC/m²",
            f"{btc_sign}{abs(btc_absolute):.6f} BTC",
            f"{btc_percent:.2f}%",
            delta_color="inverse"  # Red for increase, green for decrease
        )

# Display data table
st.markdown("---")
st.subheader("📊 Dados")
with st.expander("Ver tabela de dados"):
    display_df = filtered_df[['Date', 'Preco m2 [EUR]', 'Preco m2 [BTC]']].copy()
    display_df.columns = ['Data', 'EUR/m²', 'BTC/m²']
    display_df['Data'] = display_df['Data'].dt.strftime('%Y-%m-%d')
    display_df['EUR/m²'] = display_df['EUR/m²'].apply(lambda x: f"€{x:,.0f}")
    display_df['BTC/m²'] = display_df['BTC/m²'].apply(lambda x: f"{x:.6f}")
    # display_df['Preço BTC (EUR)'] = display_df['Preço BTC (EUR)'].apply(lambda x: f"€{x:,.2f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Dados: BTC/EUR na corretora Kraken via Investing.com e mercado imobiliário português via idealista.pt</small>
    </div>
    """,
    unsafe_allow_html=True
)
