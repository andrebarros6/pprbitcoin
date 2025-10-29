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
    df = pd.read_csv('infogram_data_with_btc.csv')

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
    st.sidebar.subheader("Selecionar intervalo de datas:")
    min_date = df['Date_parsed'].min().date()
    max_date = df['Date_parsed'].max().date()

    # Quick period buttons
    st.sidebar.subheader("Atalhos")
    col1, col2 = st.sidebar.columns(2)

    today = max_date

    if col1.button("1 Ano"):
        start_date = today - timedelta(days=365)
        end_date = today
    elif col2.button("3 Anos"):
        start_date = today - timedelta(days=365*3)
        end_date = today
    elif col1.button("5 Anos"):
        start_date = today - timedelta(days=365*5)
        end_date = today
    elif col2.button("Tudo"):
        start_date = min_date
        end_date = max_date
    else:
        # Default date range
        start_date = st.sidebar.date_input(
            "Data inicial",
            value=min_date,
            min_value=min_date,
            max_value=max_date
        )
        end_date = st.sidebar.date_input(
            "Data final",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )

    # Logarithmic scale checkbox
    log_scale_btc = st.sidebar.checkbox("Escala logarítmica para BTC", value=True)

    # Filter data by date range
    mask = (df['Date_parsed'].dt.date >= start_date) & (df['Date_parsed'].dt.date <= end_date)
    filtered_df = df[mask].copy()

    # Statistics
    st.sidebar.markdown("---")
    st.sidebar.subheader("Estatísticas")

    if len(filtered_df) > 0:
        # Calculate period in months
        period_days = (end_date - start_date).days
        period_months = round(period_days / 30)

        st.sidebar.markdown("**Período selecionado**")
        st.sidebar.markdown(f"### {period_months} meses")

        # Current values (latest in the filtered range)
        latest = filtered_df.iloc[-1]

        st.sidebar.markdown("**EUR (atual)**")
        st.sidebar.markdown(f"### {format_eur(latest['Price'])}")

        st.sidebar.markdown("**BTC (atual)**")
        st.sidebar.markdown(f"### {format_btc(latest['Price_in_BTC'])}")

        # Calculate percentage changes
        if len(filtered_df) > 1:
            first = filtered_df.iloc[0]
            eur_change = ((latest['Price'] - first['Price']) / first['Price']) * 100
            btc_change = ((latest['Price_in_BTC'] - first['Price_in_BTC']) / first['Price_in_BTC']) * 100

            st.sidebar.markdown("**Variação EUR**")
            color_eur = "green" if eur_change >= 0 else "red"
            st.sidebar.markdown(f"<span style='color:{color_eur}; font-size:1.2rem; font-weight:bold;'>{eur_change:+.2f}%</span>", unsafe_allow_html=True)

            st.sidebar.markdown("**Variação BTC**")
            color_btc = "red" if btc_change >= 0 else "green"  # Inverted: lower BTC price is better
            st.sidebar.markdown(f"<span style='color:{color_btc}; font-size:1.2rem; font-weight:bold;'>{btc_change:+.2f}%</span>", unsafe_allow_html=True)

    # Main content
    st.markdown('<div class="main-title">🛒 Cabaz Alimentar em Portugal - EUR vs BTC</div>', unsafe_allow_html=True)

    if len(filtered_df) == 0:
        st.warning("Nenhum dado disponível para o período selecionado.")
        return

    # Create the dual-axis chart
    fig = go.Figure()

    # Add EUR trace (left axis)
    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price'],
        name='Preço [EUR]',
        line=dict(color='#2ecc71', width=2),
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Preço: €%{y:.2f}<extra></extra>'
    ))

    # Add BTC trace (right axis)
    fig.add_trace(go.Scatter(
        x=filtered_df['Date_parsed'],
        y=filtered_df['Price_in_BTC'],
        name='Preço [BTC]',
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
            title=dict(text='Preço por Cabaz [EUR]', font=dict(color='#2ecc71')),
            tickfont=dict(color='#2ecc71'),
            gridcolor='#333',
            showgrid=True,
            side='left'
        ),
        yaxis2=dict(
            title=dict(text='Preço por Cabaz [BTC]', font=dict(color='#f39c12')),
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

    # Additional insights
    st.markdown("---")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Preço Mínimo (EUR)",
            format_eur(filtered_df['Price'].min()),
            delta=None
        )

    with col2:
        st.metric(
            "Preço Máximo (EUR)",
            format_eur(filtered_df['Price'].max()),
            delta=None
        )

    with col3:
        st.metric(
            "Preço Médio (EUR)",
            format_eur(filtered_df['Price'].mean()),
            delta=None
        )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Preço Mínimo (BTC)",
            format_btc(filtered_df['Price_in_BTC'].min()),
            delta=None
        )

    with col2:
        st.metric(
            "Preço Máximo (BTC)",
            format_btc(filtered_df['Price_in_BTC'].max()),
            delta=None
        )

    with col3:
        st.metric(
            "Preço Médio (BTC)",
            format_btc(filtered_df['Price_in_BTC'].mean()),
            delta=None
        )

    # Show raw data option
    if st.checkbox("Mostrar dados"):
        st.dataframe(
            filtered_df[['Date', 'Price', 'BTC_Price_EUR', 'Price_in_BTC']].rename(columns={
                'Date': 'Data',
                'Price': 'Preço (EUR)',
                'BTC_Price_EUR': 'Preço Bitcoin (EUR)',
                'Price_in_BTC': 'Preço (BTC)'
            }),
            use_container_width=True
        )

if __name__ == '__main__':
    main()
