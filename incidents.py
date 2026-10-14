
import streamlit as st
import pandas as pd
import altair as alt

# Page configuration
st.set_page_config(
    page_title="Nigeria Incidents Data",
    page_icon="📊",
    layout="wide"
)

# Load data function
@st.cache_data
def load_data():
    return pd.read_csv("incidents.csv")


# Display to the browser
try:
    df = load_data()

    st.title("Nigeria Incidents Data")
    st.write("Explore and analyze incident records.")

    # SIDEBAR
    st.sidebar.title("Incident Filters")

    # Search incidents
    search = st.sidebar.text_input("Search incidents")

    # Choose a column to filter
    column = st.sidebar.selectbox(
        "Choose a column to filter",
        df.columns
    )

    # Select values
    values = st.sidebar.multiselect(
        "Select values",
        options=sorted(
            df[column].dropna().astype(str).unique()
        )
    )

    # APPLY FILTERS
    filtered_df = df.copy()

    if search:
        mask = filtered_df.astype(str).apply(
            lambda col: col.str.contains(
                search, case=False, na=False
            )
        ).any(axis=1)

        filtered_df = filtered_df[mask]

    if values:
        filtered_df = filtered_df[
            filtered_df[column].astype(str).isin(values)
        ]

    # KPI METRICS
    col1, col2, col3 = st.columns(3)

    col1.metric("Total Records", f"{len(filtered_df):,}")
    col2.metric("Total Columns", len(filtered_df.columns))
    col3.metric(
        "Missing Values",
        f"{filtered_df.isnull().sum().sum():,}"
    )

    st.divider()

    # DISPLAY DATA
    st.subheader("Filtered Incident Records")
    st.dataframe(
        filtered_df,
        use_container_width=True,
        hide_index=True
    )

    # DOWNLOAD DATA
    st.download_button(
        label="Download Data as CSV",
        data=filtered_df.to_csv(index=False),
        file_name="nigeria_incidents.csv",
        mime="text/csv"
    )

except FileNotFoundError:
    st.error(
        "incidents.csv not found. Put it in the same "
        "folder as your Python file."
    )

except Exception as e:
    st.exception(e)
