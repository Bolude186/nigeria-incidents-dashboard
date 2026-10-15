

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Nigeria Incidents Data", page_icon="📊", layout="wide")

BASE = Path(__file__).parent


@st.cache_data
def load_data():
    for p in (BASE / "incidents.csv", BASE / "data" / "incidents.csv"):
        if p.exists():
            df = pd.read_csv(p)
            df.columns = df.columns.str.strip()
            return df.drop_duplicates()
    raise FileNotFoundError


def find_col(df, candidates):
    """Case-insensitive column lookup ('Start date' matches 'Start Date')."""
    lookup = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand.lower() in lookup:
            return lookup[cand.lower()]
    return None


try:
    df = load_data()

    #  Find the key columns 
    start_col = find_col(df, ["Start date"])
    end_col = find_col(df, ["End date"])
    deaths_col = find_col(df, ["Number of deaths", "Deaths", "Fatalities", "Killed"])
    title_col = find_col(df, ["Title", "Incident", "Event", "Description"])

    # Prepare data (same steps as the notebook) 
    data = df.copy()
    if start_col:
        data[start_col] = pd.to_datetime(data[start_col], errors="coerce")
        data["Year"] = data[start_col].dt.year
        data["Month"] = data[start_col].dt.month
    if end_col:
        data[end_col] = pd.to_datetime(data[end_col], errors="coerce")
    if start_col and end_col:
        data["Incident Duration"] = (data[end_col] - data[start_col]).dt.days
        data.loc[data["Incident Duration"] < 0, "Incident Duration"] = np.nan
    if deaths_col:
        data[deaths_col] = pd.to_numeric(
            data[deaths_col].astype(str).str.replace(",", "", regex=False), errors="coerce"
        )

    st.title("Nigeria Incidents Data")
    st.write("Explore and analyze incident records.")

    #  Sidebar filters 
    st.sidebar.title("Incident Filters")

    if "Year" in data.columns and data["Year"].notna().any():
        y_min, y_max = int(data["Year"].min()), int(data["Year"].max())
        if y_min < y_max:
            year_range = st.sidebar.slider("Year range", y_min, y_max, (y_min, y_max))
            data = data[data["Year"].between(year_range[0], year_range[1])]

    search = st.sidebar.text_input("Search incidents")
    column = st.sidebar.selectbox("Choose a column to filter", df.columns)
    values = st.sidebar.multiselect(
        "Select values", options=sorted(data[column].dropna().astype(str).unique())
    )

    filtered_df = data.copy()
    if search:
        mask = filtered_df.astype(str).apply(
            lambda col: col.str.contains(search, case=False, na=False)
        ).any(axis=1)
        filtered_df = filtered_df[mask]
    if values:
        filtered_df = filtered_df[filtered_df[column].astype(str).isin(values)]

    #  KPIs 
    st.subheader("Dashboard Overview")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Records", f"{len(filtered_df):,}")
    if deaths_col:
        k2.metric("Total Deaths", f"{int(filtered_df[deaths_col].sum()):,}")
        k3.metric("Avg Deaths / Incident", f"{filtered_df[deaths_col].mean():.1f}" if len(filtered_df) else "0")
    k4.metric("Missing Values", f"{filtered_df.isnull().sum().sum():,}")
    st.divider()

    if filtered_df.empty:
        st.warning("No records match the current filters.")
    else:
        #  Chart 1: incidents by year 
        st.subheader("Number of Reported Incidents by Year")
        if "Year" in filtered_df.columns:
            yearly = (
                filtered_df["Year"].dropna().astype(int).value_counts().sort_index()
                .rename_axis("Year").reset_index(name="Number of Incidents")
            )
            if not yearly.empty:
                st.altair_chart(
                    alt.Chart(yearly).mark_line(point=True).encode(
                        x=alt.X("Year:O", title="Year"),
                        y=alt.Y("Number of Incidents:Q", title="Number of Incidents"),
                        tooltip=["Year", "Number of Incidents"],
                    ).properties(height=350),
                    use_container_width=True,
                )
        else:
            st.warning(f"Start date column not found. Columns: {list(df.columns)}")
        st.divider()

        #  Chart 2: top 10 incidents by deaths 
        st.subheader("Top 10 Incidents by Number of Deaths")
        if title_col and deaths_col:
            top_10 = filtered_df[[title_col, deaths_col]].dropna().nlargest(10, deaths_col)
            st.altair_chart(
                alt.Chart(top_10).mark_bar().encode(
                    x=alt.X(f"{deaths_col}:Q", title="Number of Deaths"),
                    y=alt.Y(f"{title_col}:N", title="Incident", sort="-x"),
                    tooltip=[title_col, deaths_col],
                ).properties(height=400),
                use_container_width=True,
            )
        else:
            st.warning(f"Title or deaths column not found. Columns: {list(df.columns)}")
        st.divider()

        #  Chart 3 and 4: distribution + duration vs deaths 
        left, right = st.columns(2)

        with left:
            st.subheader("Distribution of Deaths per Incident")
            if deaths_col:
                st.altair_chart(
                    alt.Chart(filtered_df[[deaths_col]].dropna()).mark_bar().encode(
                        x=alt.X(f"{deaths_col}:Q", bin=alt.Bin(maxbins=30), title="Number of Deaths"),
                        y=alt.Y("count()", title="Number of Incidents"),
                    ).properties(height=350),
                    use_container_width=True,
                )

        with right:
            st.subheader("Incident Duration vs Number of Deaths")
            if deaths_col and "Incident Duration" in filtered_df.columns:
                scatter = filtered_df[["Incident Duration", deaths_col]].dropna()
                if not scatter.empty:
                    st.altair_chart(
                        alt.Chart(scatter).mark_circle(opacity=0.5).encode(
                            x=alt.X("Incident Duration:Q", title="Incident Duration (Days)"),
                            y=alt.Y(f"{deaths_col}:Q", title="Number of Deaths"),
                            tooltip=["Incident Duration", deaths_col],
                        ).properties(height=350),
                        use_container_width=True,
                    )
                    if len(scatter) > 1:
                        st.caption(f"Correlation: {scatter['Incident Duration'].corr(scatter[deaths_col]):.3f}")
        st.divider()

        #  Chart 5: incidents by month 
        st.subheader("Number of Reported Incidents by Month")
        if "Month" in filtered_df.columns:
            monthly = (
                filtered_df["Month"].dropna().astype(int).value_counts().sort_index()
                .rename_axis("Month").reset_index(name="Number of Incidents")
            )
            st.altair_chart(
                alt.Chart(monthly).mark_bar().encode(
                    x=alt.X("Month:O", title="Month"),
                    y=alt.Y("Number of Incidents:Q", title="Number of Incidents"),
                    tooltip=["Month", "Number of Incidents"],
                ).properties(height=350),
                use_container_width=True,
            )
        st.divider()

    # Table download
    st.subheader("Filtered Incident Records")
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    st.download_button(
        "Download Data as CSV",
        filtered_df.to_csv(index=False),
        "nigeria_incidents.csv",
        "text/csv",
    )

except FileNotFoundError:
    st.error("incidents.csv not found. Put it next to incidents.py or in a data/ folder.")
except Exception as e:
    st.exception(e)
