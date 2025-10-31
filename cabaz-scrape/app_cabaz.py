import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from pathlib import Path

# Portuguese month names mapping
PORTUGUESE_MONTHS = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

def parse_portuguese_date(date_str):
    """Parse Portuguese date format like '5 de janeiro de 2022'"""
    parts = date_str.strip().split()
    day = int(parts[0])
    month_name = parts[2]
    year = int(parts[4])
    month = PORTUGUESE_MONTHS[month_name]
    return datetime(year, month, day)

@st.cache_data
def load_data():
    """Load and process the food basket data"""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    csv_path = script_dir / 'infogram_data_with_btc.csv'
    df = pd.read_csv(csv_path)

    # Parse dates
    df['Date_parsed'] = df['Date'].apply(parse_portuguese_date)

    # Sort by date
    df = df.sort_values('Date_parsed')

    return df

def format_btc(value):
    """Format BTC value with appropriate precision"""
    return f"{value:.8f} BTC"

def format_eur(value):
    """Format EUR value"""
    return f"€{value:.2f}"

def main():
    st.set_page_config(
        page_title="Cabaz Alimentar - EUR vs BTC",
        page_icon="🛒",
        layout="wide"
    )

    # Custom CSS for better styling
    st.markdown("""
        <style>
        .main-title {
            font-size: 2.5rem;
            font-weight: bold;
            margin-bottom: 2rem;
        }
        .stats-container {
            background-color: #1E1E1E;
            padding: 1rem;
            border-radius: 0.5rem;
            margin-bottom: 1rem;
        }
        .stat-label {
            color: #888;
            font-size: 0.9rem;
        }
        .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        </style>
    """, unsafe_allow_html=True)

    # Load data
    df = load_data()

    # Sidebar
    st.sidebar.header("Controlos")

    # Date range selector
    min_date = df['Date_parsed'].min().date()
    max_date = df['Date_parsed'].max().date()

    # Initialize session state for dates if not exists
    if 'start_date' not in st.session_state:
        st.session_state.start_date = min_date
    if 'end_date' not in st.session_state:
        st.session_state.end_date = max_date

    # Date range input
    date_range = st.sidebar.date_input(
        "Selecionar intervalo de datas:",
        value=(st.session_state.start_date, st.session_state.end_date),
        min_value=min_date,
        max_value=max_date
    )

    # Update session state from date_range
    if len(date_range) == 2:
        st.session_state.start_date, st.session_state.end_date = date_range
        start_date, end_date = date_range
    else:
        start_date = st.session_state.start_date
        end_date = st.session_state.end_date

    # Logarithmic scale checkbox
    log_scale_btc = st.sidebar.checkbox("Escala logarítmica para BTC", value=False)

    # Quick period buttons
    st.sidebar.markdown("### Atalhos")
    col1, col2 = st.sidebar.columns(2)

    today = max_date

    # Check each button independently and update session state
    if col1.button("1 Ano"):
        st.session_state.start_date = today - timedelta(days=365)
        st.session_state.end_date = today
        st.rerun()

    if col2.button("2 Anos"):
        st.session_state.start_date = today - timedelta(days=365*2)
        st.session_state.end_date = today
        st.rerun()

    col3, col4 = st.sidebar.columns(2)

    if col3.button("3 Anos"):
        st.session_state.start_date = today - timedelta(days=365*3)
        st.session_state.end_date = today
        st.rerun()

    if col4.button("Tudo"):
        st.session_state.start_date = min_date
        st.session_state.end_date = max_date
        st.rerun()

    # Filter data by date range
    mask = (df['Date_parsed'].dt.date >= start_date) & (df['Date_parsed'].dt.date <= end_date)
    filtered_df = df[mask].copy()

    # Statistics
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Estatísticas")

    if len(filtered_df) > 0:
        # Calculate period in months
        period_days = (end_date - start_date).days
        period_months = round(period_days / 30)

        # Current values (latest in the filtered range)
        latest = filtered_df.iloc[-1]

        st.sidebar.metric("Período selecionado", f"{period_months} meses")
        st.sidebar.metric("Preço atual do cabaz alimentar em EUR", format_eur(latest['Price']))
        st.sidebar.metric("Preço atual do cabaz alimentar em BTC (atual)", format_btc(latest['Price_in_BTC']))

    # Main content
    st.markdown('<div class="main-title">🛒 Cabaz Alimentar em Portugal - EUR vs BTC</div>', unsafe_allow_html=True)

    if len(filtered_df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    # Explanatory text
    st.markdown("""
    <div style='background-color: #1a1a1a; padding: 1.5rem; border-radius: 0.5rem; margin-bottom: 1.5rem; border-left: 4px solid #f39c12;'>
        <p style='font-size: 1.1rem; line-height: 1.6; margin-bottom: 1rem;'>
        Nos últimos anos, o aumento da oferta monetária tem contribuindo à inflação, fazendo com que os preços dos produtos no supermercado aumentem constantemente.
        \n Isto significa que os teus euros compram cada vez menos produtos. 
        \n A Bitcoin, com a sua oferta limitada a 21 milhões de unidades, surge como uma ferramenta de proteção do poder de compra. 
        \n Como podes comprovar no gráfico abaixo, o mesmo cabaz alimentar que fica cada vez mais caro em euros, fica progressivamente mais barato quando medido em Bitcoin.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Calculate EUR variation for impact statement
    if len(filtered_df) > 1:
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]
        eur_change = ((latest['Price'] - first['Price']) / first['Price']) * 100

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
                <span style='color: white;'>No período selecionado, o cabaz alimentar está</span>
                <span style='color: {color}; font-weight: bold;'> {abs_change:.1f}% mais {price_word}</span><span style='color: white;'>.</span>
            </p>
            <p style='font-size: 1.3rem; color: #bbb; margin-top: 0.5rem;'>
                Quanto aumentou o teu salário?
            </p>
        </div>
        """, unsafe_allow_html=True)

    # Create the dual-axis chart
    fig = go.Figure()

    # Add EUR trace (left axis)
    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price'],
        name='Cabaz [EUR]',
        line=dict(color='#2ecc71', width=2),
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Preço: €%{y:.2f}<extra></extra>'
    ))

    # Add BTC trace (right axis)
    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price_in_BTC'],
        name='Cabaz [BTC]',
        line=dict(color='#f39c12', width=2),
        yaxis='y2',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Preço: %{y:.8f} BTC<extra></extra>'
    ))

    # Update layout with dual axes
    fig.update_layout(
        xaxis=dict(
            title='Data',
            gridcolor='#333',
            showgrid=True
        ),
        yaxis=dict(
            title=dict(text='Preço do Cabaz [EUR]', font=dict(color='#2ecc71')),
            tickfont=dict(color='#2ecc71'),
            gridcolor='#333',
            showgrid=True,
            side='left'
        ),
        yaxis2=dict(
            title=dict(text='Preço do Cabaz [BTC]', font=dict(color='#f39c12')),
            tickfont=dict(color='#f39c12'),
            overlaying='y',
            side='right',
            type='log' if log_scale_btc else 'linear',
            showgrid=False
        ),
        hovermode='x unified',
        plot_bgcolor='#0e1117',
        paper_bgcolor='#0e1117',
        font=dict(color='white'),
        height=600,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    st.plotly_chart(fig, use_container_width=True)

    # Comparative Analysis
    st.markdown("---")
    st.subheader("📈 Análise Comparativa")

    if len(filtered_df) > 1:
        # Calculate variations
        first = filtered_df.iloc[0]
        latest = filtered_df.iloc[-1]

        # EUR absolute and percentage variation
        eur_absolute = latest['Price'] - first['Price']
        eur_percent = (eur_absolute / first['Price']) * 100
        eur_sign = "+ " if eur_absolute >= 0 else "- "

        # BTC absolute and percentage variation
        btc_absolute = latest['Price_in_BTC'] - first['Price_in_BTC']
        btc_percent = (btc_absolute / first['Price_in_BTC']) * 100
        btc_sign = "+ " if btc_absolute >= 0 else "- "


        # Create three columns
        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Variação EUR",
                f"{eur_sign}€{abs(eur_absolute):.2f}",
                f"{eur_percent:.2f}%",
                delta_color="inverse"  # Red for increase, green for decrease
            )

        with col2:
            st.metric(
                "Variação BTC",
                f"{btc_sign}{abs(btc_absolute):.8f} BTC",
                f"{btc_percent:.2f}%",
                delta_color="inverse"  # Red for increase, green for decrease
            )


    # Display data table
    st.markdown("---")
    st.subheader("📊 Dados")
    with st.expander("Ver tabela de dados"):
        display_df = filtered_df[['Date_parsed', 'Price', 'Price_in_BTC']].copy()
        display_df.columns = ['Data', 'Preço Cabaz (EUR)', 'Preço Cabaz (BTC)']
        display_df['Data'] = display_df['Data'].dt.strftime('%Y-%m-%d')
        display_df['Preço Cabaz (EUR)'] = display_df['Preço Cabaz (EUR)'].apply(lambda x: f"€{x:.2f}")
        display_df['Preço Cabaz (BTC)'] = display_df['Preço Cabaz (BTC)'].apply(lambda x: f"{x:.8f}")
        st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray;'>
        <small>Dados: BTC/EUR na corretora Kraken via Investing.com e cabaz alimentar via DECO PRO TESTE</small>
        </div>
        """,
        unsafe_allow_html=True
    )

if __name__ == '__main__':
    main()
