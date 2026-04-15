import streamlit as st
from database import connect_to_database, init_session_state
from ui_sections.tareas import seccion_tareas

def page():
    client = connect_to_database()
    if client:
        if "df_personal" not in st.session_state or st.session_state.df_personal.empty:
            init_session_state(client)
        
        personal_list = []
        if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
            personal_list = st.session_state.df_personal.iloc[:, 0].tolist()
        seccion_tareas(client, personal_list)

if __name__ == "__main__":
    page()