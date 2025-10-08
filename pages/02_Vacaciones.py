import streamlit as st
from google_sheets_client import connect_to_google_sheets
from ui_sections.vacaciones import seccion_vacaciones

def page():
    st.set_page_config(page_title="Vacaciones", page_icon="🌴")
    st.title("🌴 Vacaciones")

    client = connect_to_google_sheets()
    if client:
        personal_list = []
        if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
            personal_list = st.session_state.df_personal.iloc[:, 0].tolist()
        seccion_vacaciones(client, personal_list)

if __name__ == "__main__":
    page()
