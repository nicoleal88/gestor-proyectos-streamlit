import streamlit as st
from google_sheets_client import connect_to_google_sheets
from ui_sections.tareas import seccion_tareas

def page():
    st.set_page_config(page_title="Tareas", page_icon="📋")
    st.title("📋 Tareas")

    client = connect_to_google_sheets()
    if client:
        personal_list = []
        if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
            personal_list = st.session_state.df_personal.iloc[:, 0].tolist()
        seccion_tareas(client, personal_list)

if __name__ == "__main__":
    page()
