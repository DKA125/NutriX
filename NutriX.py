import datetime
from pathlib import Path

import bcrypt
import pandas as pd
import streamlit as st
from supabase import create_client


DATA_FILE = Path(__file__).parent / "food_metrics.csv"
MACRO_COLUMNS = ["calories", "protein", "carbohydrates", "fat"]

st.set_page_config(page_title="NutriX", page_icon="🍎", layout="wide")


@st.cache_data
def load_food_data():
    """Načte databázi jídel a převede výživové hodnoty na čísla."""
    df = pd.read_csv(DATA_FILE, sep=";", decimal=",")
    required_columns = {
        "Food", "Weight", "Calories", "Proteins", "Carbohydrates", "Fat"
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise ValueError(
            "V souboru food_metrics.csv chybí sloupce: "
            + ", ".join(sorted(missing_columns))
        )

    for col in ["Calories", "Proteins", "Carbohydrates", "Fat"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["Weight"] = pd.to_numeric(
        df["Weight"].astype(str).str.replace("g", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0.0)
    return df


@st.cache_resource
def get_database():
    """Vytvoří serverové připojení; klíč se nikdy nezobrazí uživateli."""
    try:
        return create_client(
            st.secrets["supabase"]["url"],
            st.secrets["supabase"]["secret_key"],
        )
    except (KeyError, FileNotFoundError):
        st.error("Chybí nastavení Supabase. Postup najdete v README.md.")
        st.stop()


def authenticate(username, password):
    """Ověří ručně vytvořený účet pomocí bcrypt hashe."""
    username = username.strip().lower()
    if not username or not password:
        return None

    result = (
        get_database()
        .table("nutrix_users")
        .select("id, username, password_hash")
        .eq("username", username)
        .execute()
    )
    if not result.data:
        return None

    user = result.data[0]
    try:
        valid_password = bcrypt.checkpw(
            password.encode("utf-8"), user["password_hash"].encode("utf-8")
        )
    except (TypeError, ValueError):
        return None
    return user if valid_password else None


def login_screen():
    st.title("🍎 NutriX")
    st.subheader("Přihlášení")
    with st.form("login_form"):
        username = st.text_input("Uživatelské jméno")
        password = st.text_input("Heslo", type="password")
        submitted = st.form_submit_button("Přihlásit", type="primary")

    if submitted:
        user = authenticate(username, password)
        if user:
            st.session_state.user = {
                "id": user["id"], "username": user["username"]}
            st.rerun()
        st.error("Nesprávné uživatelské jméno nebo heslo.")
    st.stop()


def load_memory(user_id):
    today = datetime.date.today().isoformat()
    result = (
        get_database()
        .table("daily_metrics")
        .select("calories, protein, carbohydrates, fat")
        .eq("user_id", user_id)
        .eq("date", today)
        .execute()
    )
    if result.data:
        values = result.data[0]
    else:
        values = {"calories": 0.0, "protein": 0.0,
                  "carbohydrates": 0.0, "fat": 0.0}
        get_database().table("daily_metrics").insert(
            {"user_id": user_id, "date": today, **values}
        ).execute()

    return {column: float(values[column]) for column in MACRO_COLUMNS}


def save_memory(user_id, memory):
    get_database().table("daily_metrics").upsert(
        {
            "user_id": user_id,
            "date": datetime.date.today().isoformat(),
            **memory,
        },
        on_conflict="user_id,date",
    ).execute()


try:
    food_df = load_food_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Databázi jídel se nepodařilo načíst: {error}")
    st.stop()

if "user" not in st.session_state:
    login_screen()

user = st.session_state.user
memory = load_memory(user["id"])

header_col, logout_col = st.columns([6, 1])
with header_col:
    st.title("🍎 NutriX")
    st.subheader(f"Denní sledování kalorií a makroživin · {user['username']}")
with logout_col:
    if st.button("Odhlásit"):
        del st.session_state.user
        st.rerun()

st.header("Přidat jídlo")
meal = st.selectbox(
    "Vyber jídlo",
    options=food_df["Food"].tolist(),
    index=None,
    placeholder="Začni psát a vyber jídlo...",
)
metrics = st.radio("Jednotka", options=["g", "porce"], horizontal=True)
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

        memory["calories"] += float(row["Calories"]) * factor
        memory["protein"] += float(row["Proteins"]) * factor
        memory["carbohydrates"] += float(row["Carbohydrates"]) * factor
        memory["fat"] += float(row["Fat"]) * factor
        save_memory(user["id"], memory)
        st.success("Jídlo bylo přidáno!")

st.header("Dnešní součet")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Kalorie", f"{memory['calories']:.0f} kcal")
col2.metric("Bílkoviny", f"{memory['protein']:.1f} g")
col3.metric("Sacharidy", f"{memory['carbohydrates']:.1f} g")
col4.metric("Tuky", f"{memory['fat']:.1f} g")
