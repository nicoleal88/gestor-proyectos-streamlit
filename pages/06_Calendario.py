import streamlit as st
from google_sheets_client import connect_to_google_sheets
from ui_sections.calendario import seccion_calendario

def page():
    st.set_page_config(page_title="Calendario", page_icon="📅")
    st.title("📅 Calendario")

    client = connect_to_google_sheets()
    if client:
        seccion_calendario(client)

if __name__ == "__main__":
    page()
