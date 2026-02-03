import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import os
import re

# ── Page configuration ──
st.set_page_config(
    page_title="Ethiopia Financial Inclusion Dashboard",
    page_icon="📊",
    layout="wide"
)

# ── Title & introduction ──
st.title("Ethiopia Financial Inclusion Dashboard")
st.markdown("""
Forecasting **Account Ownership (ACCESS)** and **Digital Payment Usage** to 2027  
Data enriched & analyzed for 10 Academy KAIM Week 10 Challenge  
Last updated: Feb 2026
""")

# ── Load data function ──
@st.cache_data
def load_data():
    # Get project root (go up one level from dashboard/)
    dashboard_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(dashboard_dir)

    enriched_path = os.path.join(project_root, 'data', 'processed', 'ethiopia_fi_enriched.csv')
    forecast_path = os.path.join(project_root, 'data', 'processed', 'forecast_account_ownership_2026_2027.csv')

    df = pd.DataFrame()
    forecast = pd.DataFrame()

    # Load enriched data
    if os.path.exists(enriched_path):
        try:
            df = pd.read_csv(enriched_path)
        except Exception as e:
            st.error(f"Error reading enriched CSV: {e}")
    else:
        st.error(f"Enriched data file not found: {enriched_path}")

    # Load forecast (optional)
    if os.path.exists(forecast_path):
        try:
            forecast = pd.read_csv(forecast_path)
        except Exception as e:
            st.warning(f"Forecast file could not be loaded: {e}")
    else:
        st.info("Forecast file not found — forecast section will be empty")

    return df, forecast

df, forecast = load_data()

# ── Create obs_year if missing ──
if 'obs_year' not in df.columns and not df.empty:
    with st.spinner("Creating obs_year column..."):
        df['obs_date_dt'] = pd.to_datetime(df['observation_date'], errors='coerce', format='mixed')

        def extract_year(x):
            if pd.isna(x):
                return np.nan
            x_str = str(x).strip()
            match = re.search(r'(\d{4})', x_str)
            if match:
                return int(match.group(1))
            try:
                return int(float(x_str))
            except:
                return np.nan

        df['fiscal_year_clean'] = df['fiscal_year'].apply(extract_year)
        df['obs_year'] = df['obs_date_dt'].dt.year.astype('Int64')
        df['obs_year'] = df['obs_year'].fillna(df['fiscal_year_clean'].astype('Int64'))

    st.success("obs_year column created successfully")
    st.write("Available years:", sorted(df['obs_year'].dropna().unique().tolist()))

# ── Sidebar filters ──
st.sidebar.header("Filters")

# Indicator selector (only those present in data)
available_indicators = df[df['record_type'] == 'observation']['indicator_code'].unique().tolist()
indicator = st.sidebar.selectbox(
    "Select Indicator",
    options=available_indicators if available_indicators else ["ACC_OWNERSHIP"],
    index=0 if "ACC_OWNERSHIP" in available_indicators else 0
)

gender = st.sidebar.radio("Gender", ["all", "male", "female"])
location = st.sidebar.radio("Location", ["national", "urban", "rural"])

# ── Filter data for historical plot ──
filtered_df = df[
    (df['indicator_code'] == indicator) &
    (df['gender'] == gender) &
    (df['location'] == location) &
    (df['record_type'] == 'observation') &
    (df['obs_year'].notna())
].copy()

# ── Section 1: Historical Trend ──
st.header("1. Historical Trend")
if not filtered_df.empty:
    fig1 = px.line(
        filtered_df.sort_values('obs_year'),
        x='obs_year',
        y='value_numeric',
        title=f"{indicator} over Time ({gender.capitalize()}, {location.capitalize()})",
        labels={'obs_year': 'Year', 'value_numeric': 'Value'},
        markers=True,
        template="plotly_dark"
    )
    fig1.update_layout(
        xaxis_title="Year",
        yaxis_title="Value",
        hovermode="x unified"
    )
    st.plotly_chart(fig1, use_container_width=True)
else:
    st.info("No data available for the selected filters and indicator.")

# ── Section 2: Forecast ──
st.header("2. Forecast 2026–2027 (Account Ownership)")
if not forecast.empty and 'obs_year' in forecast.columns:
    fig2 = go.Figure()

    # Historical (from main df)
    hist_own = df[
        (df['indicator_code'] == 'ACC_OWNERSHIP') &
        (df['gender'] == 'all') &
        (df['location'] == 'national') &
        (df['record_type'] == 'observation')
    ].sort_values('obs_year')

    fig2.add_trace(go.Scatter(
        x=hist_own['obs_year'],
        y=hist_own['value_numeric'],
        mode='lines+markers',
        name='Historical Actual',
        line=dict(color='blue')
    ))

    # Forecast
    fig2.add_trace(go.Scatter(
        x=forecast['obs_year'],
        y=forecast['forecast'],
        mode='lines',
        name='Forecast',
        line=dict(color='red', dash='dash')
    ))

    # Approximate interval band
    if 'lower_95' in forecast.columns and 'upper_95' in forecast.columns:
        fig2.add_trace(go.Scatter(
            x=pd.concat([forecast['obs_year'], forecast['obs_year'][::-1]]),
            y=pd.concat([forecast['upper_95'], forecast['lower_95'][::-1]]),
            fill='toself',
            fillcolor='rgba(255, 0, 0, 0.1)',
            line=dict(color='rgba(255,255,255,0)'),
            showlegend=False,
            name='95% Approx Interval'
        ))

    fig2.update_layout(
        title="Account Ownership Forecast to 2027",
        xaxis_title="Year",
        yaxis_title="% of adults 15+",
        hovermode="x unified",
        template="plotly_dark"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(
        forecast[['obs_year', 'forecast', 'lower_95', 'upper_95']].style.format({
            'forecast': '{:.2f}%',
            'lower_95': '{:.2f}',
            'upper_95': '{:.2f}'
        })
    )
else:
    st.warning("Forecast data not available or missing required columns. Run Task 4 notebook first.")

# ── Section 3: Key Metrics ──
st.header("3. Latest Key Metrics")
col1, col2, col3 = st.columns(3)

latest_year = df['obs_year'].max() if 'obs_year' in df.columns else None

if latest_year:
    latest_own = df[
        (df['indicator_code'] == 'ACC_OWNERSHIP') &
        (df['obs_year'] == latest_year) &
        (df['gender'] == 'all')
    ]['value_numeric'].values

    if len(latest_own) > 0:
        col1.metric("Latest Account Ownership", f"{latest_own[0]:.1f}%")

    latest_tele = df[
        (df['indicator_code'] == 'USG_TELEBIRR_USERS') &
        (df['obs_year'] == latest_year)
    ]['value_numeric'].values

    if len(latest_tele) > 0:
        col2.metric("Latest Telebirr Users", f"{latest_tele[0]:,.1f} M")

    latest_p2p = df[
        (df['indicator_code'] == 'USG_CROSSOVER') &
        (df['obs_year'] == latest_year)
    ]['value_numeric'].values

    if len(latest_p2p) > 0:
        delta = "P2P Dominant" if latest_p2p[0] > 1 else "ATM Dominant"
        col3.metric("P2P / ATM Ratio", f"{latest_p2p[0]:.2f}", delta=delta)
else:
    st.info("Cannot show latest metrics — obs_year column missing or no data.")

# ── Section 4: Major Events ──
st.header("4. Major Events Timeline")
events = df[df['record_type'] == 'event'][[
    'obs_year', 'indicator', 'category', 'notes'
]].dropna(subset=['obs_year']).sort_values('obs_year')

if not events.empty:
    st.dataframe(
        events.style.set_properties(**{'text-align': 'left'})
    )
else:
    st.info("No events found in the dataset.")