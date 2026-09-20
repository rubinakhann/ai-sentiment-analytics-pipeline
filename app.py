"""
AI-Driven Social Listening & Automated Sentiment Analytics Pipeline
Streamlit Dashboard (app.py)

Reads live data from a Google Sheet (published as CSV), which is kept
up to date by an n8n + Groq (LLaMA-3) pipeline, and renders an
auto-refreshing analytics dashboard with sidebar filters.
"""

import html
import streamlit as st
import pandas as pd
import plotly.express as px

# ---------------------------------------------------------------------
# CONFIG — replace this with YOUR "Publish to web" CSV link from
# Google Sheets: File -> Share -> Publish to web -> CSV
# ---------------------------------------------------------------------
SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRJXaTk7N7hEXb2RgRHPcyydY4uA_hRfO5WXfWDXv-o8UtqxGdXTWxJOW1B3vJTVogX3iPJeKz2mpwO/pub?output=csv"

st.set_page_config(
    page_title="AI Sentiment Analytics Pipeline",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------
# Minor styling polish
# ---------------------------------------------------------------------
st.markdown(
    """
    <style>
    div[data-testid="stMetric"] {
        background-color: rgba(148, 163, 184, 0.08);
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 10px;
        padding: 14px 10px;
    }
    .review-table-wrap {
        max-height: 260px;
        overflow-y: auto;
        border: 1px solid rgba(148, 163, 184, 0.25);
        border-radius: 10px;
    }
    .review-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }
    .review-table thead th {
        position: sticky;
        top: 0;
        background-color: rgba(148, 163, 184, 0.15);
        text-align: left;
        padding: 8px 10px;
        font-weight: 600;
        z-index: 1;
    }
    .review-table td {
        padding: 7px 10px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.15);
        vertical-align: top;
    }
    .review-table tr:hover td {
        background-color: rgba(148, 163, 184, 0.08);
    }
    .sentiment-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-weight: 600;
        font-size: 12px;
        white-space: nowrap;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

SENTIMENT_COLORS = {
    "Positive": ("rgba(46, 204, 113, 0.18)", "#1b7a3d"),
    "Negative": ("rgba(231, 76, 60, 0.18)", "#b83227"),
    "Neutral": ("rgba(149, 165, 166, 0.18)", "#5f6a6a"),
}


@st.cache_data(ttl=60)  # refresh cache every 60 seconds -> "real-time" feel
def load_data(url: str) -> pd.DataFrame:
    df = pd.read_csv(url)
    df.columns = [c.strip() for c in df.columns]
    df = df.dropna(subset=["AI_Sentiment"])
    df["AI_Sentiment"] = df["AI_Sentiment"].str.strip().str.title()
    df["AI_Core_Issue"] = df["AI_Core_Issue"].fillna("None").str.strip()
    if "App_Version" in df.columns:
        df["App_Version"] = df["App_Version"].fillna("Unknown").astype(str).str.strip()
    return df


def kpi_cards(df: pd.DataFrame, total_unfiltered: int) -> None:
    total = len(df)
    positive_pct = (df["AI_Sentiment"].eq("Positive").sum() / total * 100) if total else 0
    negative_pct = (df["AI_Sentiment"].eq("Negative").sum() / total * 100) if total else 0
    neutral_pct = (df["AI_Sentiment"].eq("Neutral").sum() / total * 100) if total else 0
    critical_issues = df[df["AI_Core_Issue"].str.lower() != "none"]["AI_Core_Issue"].nunique()

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Reviews Shown", f"{total:,}", help=f"Out of {total_unfiltered:,} total processed")
    col2.metric("Positive %", f"{positive_pct:.1f}%")
    col3.metric("Negative / Complaint %", f"{negative_pct:.1f}%")
    col4.metric("Neutral %", f"{neutral_pct:.1f}%")
    col5.metric("Distinct Issues Found", f"{critical_issues}")


def sentiment_pie(df: pd.DataFrame):
    counts = df["AI_Sentiment"].value_counts().reset_index()
    counts.columns = ["Sentiment", "Count"]
    fig = px.pie(
        counts,
        names="Sentiment",
        values="Count",
        title="Overall Sentiment Distribution",
        color="Sentiment",
        color_discrete_map={"Positive": "#2ecc71", "Negative": "#e74c3c", "Neutral": "#95a5a6"},
        hole=0.45,
    )
    fig.update_traces(textinfo="percent+label")
    fig.update_layout(legend_title_text="", title_font=dict(size=20))
    return fig


def top_issues_bar(df: pd.DataFrame):
    issues = df[df["AI_Core_Issue"].str.lower() != "none"]
    top5 = issues["AI_Core_Issue"].value_counts().head(5).reset_index()
    top5.columns = ["Core_Issue", "Count"]
    fig = px.bar(
        top5.sort_values("Count"),
        x="Count",
        y="Core_Issue",
        orientation="h",
        title="Top 5 Critical Product Issues",
        text="Count",
        color="Count",
        color_continuous_scale="Reds",
    )
    fig.update_layout(yaxis_title="", xaxis_title="Mentions", coloraxis_showscale=False, title_font=dict(size=20))
    return fig


def issue_sentiment_breakdown(df: pd.DataFrame):
    """Stacked bar: for each top issue, how sentiment splits (usually Negative-heavy)."""
    issues = df[df["AI_Core_Issue"].str.lower() != "none"]
    top_issue_names = issues["AI_Core_Issue"].value_counts().head(6).index.tolist()
    subset = issues[issues["AI_Core_Issue"].isin(top_issue_names)]
    grouped = subset.groupby(["AI_Core_Issue", "AI_Sentiment"]).size().reset_index(name="Count")
    fig = px.bar(
        grouped,
        x="Count",
        y="AI_Core_Issue",
        color="AI_Sentiment",
        orientation="h",
        title="Sentiment Split by Issue Type",
        color_discrete_map={"Positive": "#1D9E75", "Negative": "#D85A30", "Neutral": "#888780"},
    )
    fig.update_layout(
        yaxis_title="",
        xaxis_title="Mentions",
        legend_title_text="",
        title_font=dict(size=20),
    )
    return fig


def sentiment_by_version(df: pd.DataFrame):
    """Shows negative-review concentration per app version — helps spot
    which release introduced the most complaints."""
    if "App_Version" not in df.columns:
        return None
    data = df[df["App_Version"].str.lower() != "unknown"].copy()
    if data.empty:
        return None

    def shorten_version(v: str) -> str:
        # "26.22.0.100" -> "v26.22" — keep just the major.minor for readability
        parts = str(v).split(".")
        if len(parts) >= 2:
            return f"v{parts[0]}.{parts[1]}"
        return f"v{v}"

    data["Version_Short"] = data["App_Version"].apply(shorten_version)

    grouped = data.groupby(["Version_Short", "AI_Sentiment"]).size().reset_index(name="Count")
    top_versions = data["Version_Short"].value_counts().head(8).index.tolist()
    grouped = grouped[grouped["Version_Short"].isin(top_versions)]

    grouped["Version_Short"] = pd.Categorical(
        grouped["Version_Short"], categories=sorted(top_versions), ordered=True
    )
    grouped = grouped.sort_values("Version_Short")

    fig = px.bar(
        grouped,
        x="Version_Short",
        y="Count",
        color="AI_Sentiment",
        title="Sentiment by App Version",
        color_discrete_map={"Positive": "#5DCAA5", "Negative": "#E8776A", "Neutral": "#B4B2A9"},
        barmode="stack",
        text="Count",
    )
    fig.update_traces(
        textposition="inside",
        marker_line_width=0,
        texttemplate="%{text}",
    )
    fig.update_layout(
        xaxis_title="",
        yaxis_title="Reviews",
        legend_title_text="",
        bargap=0.35,
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(size=13),
        title_font=dict(size=20),
        xaxis=dict(tickangle=0, showgrid=False),
        yaxis=dict(showgrid=False),
        margin=dict(t=60, b=40),
    )
    return fig


def render_table(df: pd.DataFrame) -> str:
    """Builds a lightweight, styled HTML table (no pandas Styler / jinja2
    dependency needed) with color-coded sentiment badges."""
    has_version = "App_Version" in df.columns

    header_cells = "<th>Review ID</th><th>Review text</th><th>Sentiment</th><th>Core issue</th>"
    if has_version:
        header_cells += "<th>App version</th>"

    rows = []
    for _, row in df.iterrows():
        sentiment = str(row["AI_Sentiment"])
        bg, color = SENTIMENT_COLORS.get(sentiment, ("transparent", "inherit"))
        review_text = html.escape(str(row["Review_Text"]))[:180]
        core_issue = html.escape(str(row["AI_Core_Issue"]))
        review_id = html.escape(str(row["Review_ID"]))

        cells = (
            f"<td>{review_id}</td>"
            f"<td>{review_text}</td>"
            f"<td><span class='sentiment-badge' "
            f"style='background:{bg};color:{color};'>{html.escape(sentiment)}</span></td>"
            f"<td>{core_issue}</td>"
        )
        if has_version:
            cells += f"<td>{html.escape(str(row.get('App_Version', '')))}</td>"

        rows.append(f"<tr>{cells}</tr>")

    table_html = (
        "<div class='review-table-wrap'><table class='review-table'>"
        f"<thead><tr>{header_cells}</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table></div>"
    )
    return table_html


def sidebar_filters(df: pd.DataFrame):
    st.sidebar.header("🔧 Filters")

    sentiments = sorted(df["AI_Sentiment"].unique().tolist())
    selected_sentiments = st.sidebar.multiselect(
        "Sentiment", options=sentiments, default=sentiments
    )

    issues = sorted(
        [i for i in df["AI_Core_Issue"].unique().tolist() if i.lower() != "none"]
    )
    selected_issues = st.sidebar.multiselect(
        "Core issue (leave empty = all)", options=issues, default=[]
    )

    search = st.sidebar.text_input("Search review text")

    return selected_sentiments, selected_issues, search


def apply_filters(df, selected_sentiments, selected_issues, search):
    filtered = df.copy()
    if selected_sentiments:
        filtered = filtered[filtered["AI_Sentiment"].isin(selected_sentiments)]
    if selected_issues:
        filtered = filtered[filtered["AI_Core_Issue"].isin(selected_issues)]
    if search:
        mask = filtered.apply(
            lambda row: search.lower() in str(row.values).lower(), axis=1
        )
        filtered = filtered[mask]
    return filtered


def main():
    st.title("📊 AI-Driven Social Listening Dashboard")
    st.caption(
        "Turns raw customer reviews into instant, actionable product "
        "insights — no manual reading required."
    )

    if SHEET_CSV_URL.startswith("PASTE_"):
        st.warning(
            "Set SHEET_CSV_URL at the top of app.py to your published "
            "Google Sheet CSV link before this dashboard will show data."
        )
        st.stop()

    try:
        df = load_data(SHEET_CSV_URL)
    except Exception as e:
        st.error(f"Could not load data from the sheet: {e}")
        st.stop()

    if df.empty:
        st.info("No processed reviews yet — waiting for the n8n pipeline to fill in results.")
        st.stop()

    selected_sentiments, selected_issues, search = sidebar_filters(df)
    filtered_df = apply_filters(df, selected_sentiments, selected_issues, search)

    if filtered_df.empty:
        st.warning("No reviews match the current filters. Try widening your selection.")
        st.stop()

    kpi_cards(filtered_df, total_unfiltered=len(df))

    st.markdown("")
    col_left, col_right = st.columns(2)
    with col_left:
        st.plotly_chart(sentiment_pie(filtered_df), width="stretch")
    with col_right:
        st.plotly_chart(top_issues_bar(filtered_df), width="stretch")

    st.plotly_chart(issue_sentiment_breakdown(filtered_df), width="stretch")

    version_fig = sentiment_by_version(filtered_df)
    if version_fig is not None:
        st.plotly_chart(version_fig, width="stretch")

    st.subheader("🔎 Raw Review Logs")
    st.caption(f"Showing {len(filtered_df):,} of {len(df):,} processed reviews")

    st.markdown(render_table(filtered_df), unsafe_allow_html=True)


if __name__ == "__main__":
    main()