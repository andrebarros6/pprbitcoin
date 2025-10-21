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

# Title
st.title("🏠 Preço por m² em Portugal - EUR vs BTC")
st.markdown("---")

# Load and process data
@st.cache_data
def load_data():
    # Load BTC data
    btc_eur = pd.read_csv(r"BTC_EUR Kraken Historical Data (1).csv")
    btc_eur['Date'] = pd.to_datetime(btc_eur['Date'])
    btc_eur['Price'] = btc_eur['Price'].str.replace(',', '').astype(float)

    # Load real estate data
    imob_pt = pd.read_csv(r"m2-casas-PT.csv")
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
use_log_scale = st.sidebar.checkbox("Escala logarítmica para BTC", value=True)

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

# Display summary statistics
st.sidebar.markdown("---")
st.sidebar.markdown("### Estatísticas")
st.sidebar.metric("Período selecionado", f"{len(filtered_df)} meses")
st.sidebar.metric("EUR/m² (atual)", f"€{filtered_df['Preco m2 [EUR]'].iloc[-1]:,.0f}")
st.sidebar.metric("BTC/m² (atual)", f"{filtered_df['Preco m2 [BTC]'].iloc[-1]:.6f} BTC")

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

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Variação EUR/m²",
        f"€{filtered_df['Preco m2 [EUR]'].iloc[-1]:,.0f}",
        f"{((filtered_df['Preco m2 [EUR]'].iloc[-1] / filtered_df['Preco m2 [EUR]'].iloc[0]) - 1) * 100:.2f}%"
    )

with col2:
    st.metric(
        "Variação BTC/m²",
        f"{filtered_df['Preco m2 [BTC]'].iloc[-1]:.6f}",
        f"{((filtered_df['Preco m2 [BTC]'].iloc[-1] / filtered_df['Preco m2 [BTC]'].iloc[0]) - 1) * 100:.2f}%"
    )

with col3:
    st.metric(
        "Preço BTC",
        f"€{filtered_df['Price'].iloc[-1]:,.2f}",
        f"{((filtered_df['Price'].iloc[-1] / filtered_df['Price'].iloc[0]) - 1) * 100:.2f}%"
    )

# Display data table
st.markdown("---")
st.subheader("📊 Dados")
with st.expander("Ver tabela de dados"):
    display_df = filtered_df[['Date', 'Preco m2 [EUR]', 'Preco m2 [BTC]', 'Price']].copy()
    display_df.columns = ['Data', 'EUR/m²', 'BTC/m²', 'Preço BTC (EUR)']
    display_df['Data'] = display_df['Data'].dt.strftime('%Y-%m-%d')
    display_df['EUR/m²'] = display_df['EUR/m²'].apply(lambda x: f"€{x:,.0f}")
    display_df['BTC/m²'] = display_df['BTC/m²'].apply(lambda x: f"{x:.6f}")
    display_df['Preço BTC (EUR)'] = display_df['Preço BTC (EUR)'].apply(lambda x: f"€{x:,.2f}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <small>Dados: Kraken (BTC/EUR) via Investing.com e mercado imobiliário português via idealista.pt</small>
    </div>
    """,
    unsafe_allow_html=True
)
