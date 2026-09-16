# Streamlit app code. This cell is kept for reference and is not run inside Jupyter.
"""Streamlit app for the Community Development Priority Dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


APP_DIR = Path(__file__).resolve().parent
DATA_PATH = APP_DIR / "data" / "community_indicators.csv"

COLORS = {
    "ink": "#17324D",
    "navy": "#0B3954",
    "teal": "#087E8B",
    "coral": "#E76F51",
    "gold": "#F4A261",
    "paper": "#F6F8FB",
    "muted": "#5B6B7A",
}

GROUPS = {
    "All residents": "total",
    "Male residents": "male",
    "Female residents": "female",
}

METRICS = {
    "Community priority score": {
        "column": "priority_score_{group}",
        "label": "Priority score",
        "suffix": "/100",
        "colors": ["#EEF4F7", "#F4A261", "#D1495B"],
        "help": "A higher score indicates greater relative need across five indicators.",
    },
    "Poverty rate": {
        "column": "poverty_rate_{group}",
        "label": "Poverty rate",
        "suffix": "%",
        "colors": ["#FFF4E8", "#F4A261", "#B23A48"],
        "help": "Share of people whose income was below the federal poverty threshold.",
    },
    "Unemployment rate": {
        "column": "unemployment_rate",
        "label": "Unemployment rate",
        "suffix": "%",
        "colors": ["#EDF6F9", "#66A5AD", "#B23A48"],
        "help": "Annual mean of monthly seasonally adjusted BLS LAUS unemployment rates.",
    },
    "Households without internet": {
        "column": "no_internet_rate",
        "label": "No internet",
        "suffix": "%",
        "colors": ["#F1F8F8", "#57A0A8", "#0B3954"],
        "help": "Share of households reporting no internet access.",
    },
    "Bachelor's degree or higher": {
        "column": "bachelors_plus_rate",
        "label": "Bachelor's degree or higher",
        "suffix": "%",
        "colors": ["#F1F8F8", "#67B7A5", "#087E8B"],
        "help": "Share of the population age 25+ with a bachelor's or advanced degree.",
    },
    "Public-transit commute share": {
        "column": "public_transit_rate",
        "label": "Public-transit share",
        "suffix": "%",
        "colors": ["#F4F0FA", "#8B78B8", "#4B3F72"],
        "help": "Share of workers age 16+ commuting by public transportation.",
    },
}


@st.cache_data
def load_data() -> pd.DataFrame:
    """Load the prepared dataset, building it from public sources if needed."""
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            from build_data import build_dataset
            build_dataset(DATA_PATH)
        except Exception as exc:
            st.error(
                "The data file is not available yet and the automatic download failed. "
                "Please reboot the app or check the Streamlit logs."
            )
            st.exception(exc)
            st.stop()

    data = pd.read_csv(DATA_PATH, dtype={"state_fips": "string"})
    required = {
        "state",
        "state_code",
        "region",
        "year",
        "unemployment_rate",
        "poverty_rate_total",
        "no_internet_rate",
        "bachelors_plus_rate",
        "public_transit_rate",
        "priority_score_total",
    }
    missing = required - set(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    return data


def metric_column(metric_name: str, group_key: str) -> str:
    """Return the dataset column for the selected metric."""
    return METRICS[metric_name]["column"].format(group=group_key)


def base_layout(fig: go.Figure, title: str, height: int = 430) -> go.Figure:
    """Apply the same basic layout to each chart."""
    fig.update_layout(
        title={"text": title, "font": {"size": 19, "color": COLORS["ink"]}},
        height=height,
        margin=dict(l=16, r=16, t=58, b=16),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", color=COLORS["ink"]),
        hoverlabel=dict(bgcolor="white", font_size=13, font_family="Arial"),
    )
    return fig


st.set_page_config(
    page_title="Community Development Priority Dashboard",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    f"""
    <style>
    .stApp {{ background: {COLORS['paper']}; }}
    .block-container {{ padding-top: 1.6rem; max-width: 1480px; }}
    [data-testid="stSidebar"] {{ background: #FFFFFF; border-right: 1px solid #DFE7EE; }}
    [data-testid="stMetric"] {{
        background: #FFFFFF; border: 1px solid #DFE7EE; border-radius: 14px;
        padding: 14px 16px; box-shadow: 0 2px 8px rgba(11,57,84,.05);
    }}
    .hero {{
        background: linear-gradient(120deg, {COLORS['navy']} 0%, {COLORS['teal']} 100%);
        color: white; padding: 24px 28px; border-radius: 18px; margin-bottom: 18px;
        box-shadow: 0 8px 22px rgba(11,57,84,.18);
    }}
    .hero h1 {{ font-size: clamp(1.55rem, 3vw, 2.45rem); margin: 0 0 6px 0; }}
    .hero p {{ font-size: clamp(.92rem, 1.6vw, 1.05rem); margin: 0; opacity: .92; }}
    .note {{ color: {COLORS['muted']}; font-size: .9rem; }}
    @media (max-width: 768px) {{
        .block-container {{ padding-left: .75rem; padding-right: .75rem; }}
        .hero {{ padding: 18px; border-radius: 14px; }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)


data = load_data()

st.markdown(
    """
    <section class="hero">
      <h1>Community Development Priority Dashboard</h1>
      <p>Compare community development indicators across U.S. states and look more closely at areas with higher relative need.</p>
    </section>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Explore the data")
    year = st.select_slider("Year", options=sorted(data["year"].unique()), value=int(data["year"].max()))
    population_group = st.selectbox(
        "Population group",
        options=list(GROUPS),
        help="The selected group changes the poverty component and the related priority score.",
    )
    metric_name = st.selectbox("Map layer", options=list(METRICS))
    regions = st.multiselect(
        "Census regions",
        options=sorted(data["region"].unique()),
        default=sorted(data["region"].unique()),
    )
    st.divider()
    st.caption("Tip: Hover for exact values. Drag to pan, use the mouse wheel or toolbar to zoom, and double-click to reset the map.")
    with st.expander("How is the score calculated?"):
        st.markdown(
            "The score is a weighted state percentile: **poverty 30%**, **unemployment 25%**, "
            "**no internet 20%**, **education opportunity gap 15%**, and **public-transit gap 10%**. "
            "It is a screening tool, not a funding formula."
        )

group_key = GROUPS[population_group]
priority_col = f"priority_score_{group_key}"
poverty_col = f"poverty_rate_{group_key}"
selected_metric_col = metric_column(metric_name, group_key)
selected_metric = METRICS[metric_name]

year_data = data[(data["year"] == year) & data["region"].isin(regions)].copy()
if year_data.empty:
    st.warning("Select at least one Census region to display the dashboard.")
    st.stop()

highest = year_data.nlargest(1, priority_col).iloc[0]
kpi1, kpi2, kpi3, kpi4 = st.columns(4)
kpi1.metric("States displayed", f"{len(year_data)}")
kpi2.metric("Average priority", f"{year_data[priority_col].mean():.1f}/100")
kpi3.metric("Highest relative need", highest["state"])
kpi4.metric("Average unemployment", f"{year_data['unemployment_rate'].mean():.1f}%")

st.info(
    f"Reading the map: **{selected_metric['label']}** is shown for **{population_group.lower()}** in **{year}**. "
    f"{selected_metric['help']}"
)

map_col, rank_col = st.columns([1.65, 1], gap="large")
with map_col:
    map_fig = px.choropleth(
        year_data,
        locations="state_code",
        locationmode="USA-states",
        scope="usa",
        color=selected_metric_col,
        color_continuous_scale=selected_metric["colors"],
        custom_data=["state", "region", priority_col, poverty_col, "unemployment_rate", "no_internet_rate"],
        labels={selected_metric_col: selected_metric["label"]},
    )
    map_fig.update_traces(
        marker_line_color="white",
        marker_line_width=0.8,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Region: %{customdata[1]}<br>"
            f"{selected_metric['label']}: %{{z:.1f}}{selected_metric['suffix']}<br>"
            "Priority score: %{customdata[2]:.1f}/100<br>"
            "Poverty: %{customdata[3]:.1f}%<br>"
            "Unemployment: %{customdata[4]:.1f}%<br>"
            "No internet: %{customdata[5]:.1f}%<extra></extra>"
        ),
    )
    map_fig.update_geos(bgcolor="rgba(0,0,0,0)", lakecolor="#DCEEF4", showlakes=True)
    map_fig.update_coloraxes(colorbar_title=selected_metric["label"], colorbar_thickness=14)
    base_layout(map_fig, f"{selected_metric['label']} by state", 500)
    st.plotly_chart(
        map_fig,
        width="stretch",
        config={"displaylogo": False, "scrollZoom": True, "modeBarButtonsToRemove": ["lasso2d", "select2d"]},
    )

with rank_col:
    ranked = year_data.nlargest(10, priority_col).sort_values(priority_col)
    bar_fig = px.bar(
        ranked,
        x=priority_col,
        y="state",
        orientation="h",
        color=priority_col,
        color_continuous_scale=["#F4C69D", COLORS["coral"], "#B23A48"],
        text=priority_col,
        labels={priority_col: "Priority score", "state": ""},
    )
    bar_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside", hovertemplate="<b>%{y}</b><br>Score: %{x:.1f}/100<extra></extra>")
    bar_fig.update_layout(coloraxis_showscale=False, xaxis_range=[0, 105])
    bar_fig.update_xaxes(showgrid=True, gridcolor="#E8EDF2", title="Score (0-100)")
    bar_fig.update_yaxes(showgrid=False)
    base_layout(bar_fig, "Top 10 relative priorities", 500)
    st.plotly_chart(bar_fig, width="stretch", config={"displaylogo": False})

trend_col, relationship_col = st.columns([1, 1.25], gap="large")
with trend_col:
    state_options = sorted(year_data["state"].unique())
    default_state = highest["state"] if highest["state"] in state_options else state_options[0]
    selected_state = st.selectbox("State for trend", state_options, index=state_options.index(default_state))
    trend = data[data["state"] == selected_state].sort_values("year")
    trend_fig = px.line(
        trend,
        x="year",
        y=selected_metric_col,
        markers=True,
        labels={"year": "Year", selected_metric_col: selected_metric["label"]},
    )
    trend_fig.update_traces(line_color=COLORS["teal"], line_width=3, marker_size=9, hovertemplate=f"%{{x}}: %{{y:.1f}}{selected_metric['suffix']}<extra></extra>")
    trend_fig.update_xaxes(dtick=1, showgrid=False)
    trend_fig.update_yaxes(showgrid=True, gridcolor="#E8EDF2")
    base_layout(trend_fig, f"{selected_state}: change over time", 400)
    st.plotly_chart(trend_fig, width="stretch", config={"displaylogo": False})

with relationship_col:
    relationship_fig = px.scatter(
        year_data,
        x=poverty_col,
        y="unemployment_rate",
        size="no_internet_rate",
        color=priority_col,
        hover_name="state",
        color_continuous_scale=["#A9D6D9", COLORS["gold"], "#B23A48"],
        size_max=34,
        labels={
            poverty_col: "Poverty rate (%)",
            "unemployment_rate": "Unemployment rate (%)",
            "no_internet_rate": "No internet (%)",
            priority_col: "Priority score",
        },
    )
    relationship_fig.update_traces(marker=dict(line=dict(color="white", width=1)), hovertemplate="<b>%{hovertext}</b><br>Poverty: %{x:.1f}%<br>Unemployment: %{y:.1f}%<br>No internet: %{marker.size:.1f}%<extra></extra>")
    relationship_fig.update_xaxes(showgrid=True, gridcolor="#E8EDF2")
    relationship_fig.update_yaxes(showgrid=True, gridcolor="#E8EDF2")
    base_layout(relationship_fig, "How economic and digital needs overlap", 400)
    st.plotly_chart(relationship_fig, width="stretch", config={"displaylogo": False})

st.subheader("Underlying data")
st.caption("Sort any column, search within the table, or download the filtered records for additional analysis.")
display_columns = [
    "state",
    "region",
    "year",
    priority_col,
    poverty_col,
    "unemployment_rate",
    "no_internet_rate",
    "bachelors_plus_rate",
    "public_transit_rate",
]
display_data = year_data[display_columns].sort_values(priority_col, ascending=False).rename(
    columns={
        "state": "State",
        "region": "Region",
        "year": "Year",
        priority_col: "Priority Score",
        poverty_col: "Poverty Rate (%)",
        "unemployment_rate": "Unemployment Rate (%)",
        "no_internet_rate": "No Internet (%)",
        "bachelors_plus_rate": "Bachelor's+ (%)",
        "public_transit_rate": "Public Transit (%)",
    }
)
st.dataframe(
    display_data,
    width="stretch",
    hide_index=True,
    column_config={
        "Priority Score": st.column_config.ProgressColumn(format="%.1f", min_value=0, max_value=100),
    },
)
st.download_button(
    "Download filtered data (CSV)",
    data=display_data.to_csv(index=False).encode("utf-8"),
    file_name=f"community_priorities_{year}_{group_key}.csv",
    mime="text/csv",
)

with st.expander("Metric definitions, sources, and limitations"):
    st.markdown(
        """
        - **Priority score:** Relative state percentile, weighted across poverty, unemployment, internet access, education, and transit. It supports screening and comparison; it does not measure project cost or causal impact.
        - **Poverty rate:** ACS B17001, population for whom poverty status was determined.
        - **Unemployment rate:** BLS LAUS, mean of 12 monthly seasonally adjusted estimates.
        - **No internet:** ACS B28002, households reporting no internet access.
        - **Bachelor's degree or higher:** ACS B15003, population age 25+.
        - **Public-transit commute share:** ACS B08301, workers age 16+; it is a proxy for transportation infrastructure, not a direct measure of route availability.

        State averages can conceal neighborhood-level inequity. ACS values are estimates and have sampling error. Review local data and community input before making funding decisions.
        """
    )

st.markdown(
    "<p class='note'>Sources: U.S. Census Bureau ACS 1-year detailed tables (2022-2024) and U.S. Bureau of Labor Statistics LAUS. Prepared for educational community-development planning.</p>",
    unsafe_allow_html=True,
)
