import streamlit as st
from database import connect_to_database, init_session_state
from ui_sections.calendario import seccion_calendario

def page():
    client = connect_to_database()
    if client:
        if "df_personal" not in st.session_state or st.session_state.df_personal.empty:
            init_session_state(client)
        seccion_calendario(client)

if __name__ == "__main__":
    page()
