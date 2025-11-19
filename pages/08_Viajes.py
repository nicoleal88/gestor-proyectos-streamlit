import streamlit as st
from google_sheets_client import connect_to_google_sheets
from ui_sections.viajes import seccion_viajes


def page():
    client = connect_to_google_sheets()
    if client:
        personal_list = []
        if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
            personal_list = st.session_state.df_personal.iloc[:, 0].tolist()
        seccion_viajes(client, personal_list)


if __name__ == "__main__":
    page()
