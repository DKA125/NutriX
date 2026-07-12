import streamlit as st
import pandas as pd
import datetime
import os

# -----------------------------
# CONFIG
# -----------------------------
st.set_page_config(page_title="FoodKalučka", page_icon="🍎", layout="wide")

DATA_FILE = "food_metrics.csv"
MEMORY_FILE = "memory.xlsx"

# -----------------------------
# LOAD FOOD DATABASE
# -----------------------------


@st.cache_data
def load_food_data():
    # TVŮJ CSV používá středníky a české desetinné čárky
    return pd.read_csv(DATA_FILE, sep=";", decimal=",")


food_df = load_food_data()

# -----------------------------
# LOAD OR INIT MEMORY
# -----------------------------


def init_memory():
    if not os.path.exists(MEMORY_FILE):
        df = pd.DataFrame([{
            "date": datetime.date.today().isoformat(),
            "calories": 0,
            "protein": 0,
            "carbohydrates": 0,
            "fat": 0
        }])
        df.to_excel(MEMORY_FILE, index=False)
        return df

    df = pd.read_excel(MEMORY_FILE)

    saved_date = str(df.loc[0, "date"])
    today = datetime.date.today().isoformat()

    if saved_date != today:
        df = pd.DataFrame([{
            "date": today,
            "calories": 0,
            "protein": 0,
            "carbohydrates": 0,
            "fat": 0
        }])
        df.to_excel(MEMORY_FILE, index=False)

    return df


memory = init_memory()

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.title("🍎 FoodKalučka")
st.subheader("Denní sledování kalorií a makroživin")

# -----------------------------
# ADD MEAL FORM
# -----------------------------
st.header("Přidat jídlo")

meal = st.text_input("Co jste snědli?")
metrics = st.selectbox("Měření", ["g", "ks"])
amount = st.number_input("Kolik?", min_value=0.0)

if st.button("Přidat jídlo"):
    if meal in food_df["Food"].values:
        row = food_df[food_df["Food"] == meal].iloc[0]

        # výpočet množství
        factor = amount / 100 if metrics == "g" else amount

        memory.loc[0, "calories"] += row["Calories"] * factor
        memory.loc[0, "protein"] += row["Proteins"] * factor
        memory.loc[0, "carbohydrates"] += row["Carbohydrates"] * factor
        memory.loc[0, "fat"] += row["Fat"] * factor

        memory.to_excel(MEMORY_FILE, index=False)
        st.success("Jídlo bylo přidáno!")
    else:
        st.error("Jídlo nebylo nalezeno v databázi.")

# -----------------------------
# DAILY SUMMARY
# -----------------------------
st.header("Dnešní součet")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Kalorie", f"{memory.loc[0, 'calories']:.0f} kcal")
col2.metric("Bílkoviny", f"{memory.loc[0, 'protein']:.1f} g")
col3.metric("Sacharidy", f"{memory.loc[0, 'carbohydrates']:.1f} g")
col4.metric("Tuky", f"{memory.loc[0, 'fat']:.1f} g")
