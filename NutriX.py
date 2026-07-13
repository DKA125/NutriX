import datetime
import os

import pandas as pd
import streamlit as st


DATA_FILE = "food_metrics.csv"
MEMORY_FILE = "memory.xlsx"

st.set_page_config(page_title="NutriX", page_icon="🍎", layout="wide")


@st.cache_data
def load_food_data():
    """Načte databázi jídel a převede výživové hodnoty na čísla."""
    df = pd.read_csv(DATA_FILE, sep=";", decimal=",")

    required_columns = {
        "Food",
        "Weight",
        "Calories",
        "Proteins",
        "Carbohydrates",
        "Fat",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            "V souboru food_metrics.csv chybí sloupce: "
            + ", ".join(sorted(missing_columns))
        )

    numeric_cols = ["Calories", "Proteins", "Carbohydrates", "Fat"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Weight může být například "100 g" nebo samotné číslo.
    df["Weight"] = pd.to_numeric(
        df["Weight"].astype(str).str.replace("g", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)

    return df


def empty_memory(today):
    return pd.DataFrame(
        [{
            "date": today,
            "calories": 0.0,
            "protein": 0.0,
            "carbohydrates": 0.0,
            "fat": 0.0,
        }]
    )


def init_memory():
    today = datetime.date.today().isoformat()

    if not os.path.exists(MEMORY_FILE):
        df = empty_memory(today)
        df.to_excel(MEMORY_FILE, index=False)
        return df

    df = pd.read_excel(MEMORY_FILE)
    required_columns = {"date", "calories", "protein", "carbohydrates", "fat"}
    if df.empty or not required_columns.issubset(df.columns):
        df = empty_memory(today)
    else:
        saved_date = pd.to_datetime(df.loc[0, "date"], errors="coerce")
        if pd.isna(saved_date) or saved_date.date().isoformat() != today:
            df = empty_memory(today)
        else:
            df = df.loc[[0], list(required_columns)].copy()
            df["date"] = today
            for col in ["calories", "protein", "carbohydrates", "fat"]:
                df[col] = pd.to_numeric(
                    df[col], errors="coerce").fillna(0.0).astype(float)

    df.to_excel(MEMORY_FILE, index=False)
    return df


try:
    food_df = load_food_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Databázi jídel se nepodařilo načíst: {error}")
    st.stop()

memory = init_memory()
macro_columns = ["calories", "protein", "carbohydrates", "fat"]
memory[macro_columns] = memory[macro_columns].astype(float)

st.title("🍎 NutriX")
st.subheader("Denní sledování kalorií a makroživin")

st.header("Přidat jídlo")
meal = st.selectbox(
    "Vyber jídlo",
    options=food_df["Food"].tolist(),
    index=None,
    placeholder="Začni psát a vyber jídlo...",
)

# Vestavěný přepínač je spolehlivější než CSS, které Streamlit tlačítka nepodporuje.
metrics = st.radio("Jednotka", options=["g", "ks"], horizontal=True)
amount = st.number_input("Kolik?", min_value=0.0, step=1.0)

if st.button("Přidat jídlo", type="primary"):
    if meal is None:
        st.error("Nejdříve vyberte jídlo.")
    elif amount <= 0:
        st.error("Zadejte množství větší než nula.")
    else:
        row = food_df.loc[food_df["Food"] == meal].iloc[0]
        weight = float(row["Weight"])

        if metrics == "g":
            if weight <= 0:
                st.error("U vybraného jídla chybí platná hmotnost porce.")
                st.stop()
            factor = amount / weight
        else:
            factor = amount

        memory.at[0, "calories"] += float(row["Calories"]) * factor
        memory.at[0, "protein"] += float(row["Proteins"]) * factor
        memory.at[0, "carbohydrates"] += float(row["Carbohydrates"]) * factor
        memory.at[0, "fat"] += float(row["Fat"]) * factor
        memory.to_excel(MEMORY_FILE, index=False)
        st.success("Jídlo bylo přidáno!")

st.header("Dnešní součet")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kalorie", f"{memory.loc[0, 'calories']:.0f} kcal")
col2.metric("Bílkoviny", f"{memory.loc[0, 'protein']:.1f} g")
col3.metric("Sacharidy", f"{memory.loc[0, 'carbohydrates']:.1f} g")
col4.metric("Tuky", f"{memory.loc[0, 'fat']:.1f} g")
