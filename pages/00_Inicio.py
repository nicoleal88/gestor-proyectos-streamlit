import streamlit as st
from ui_sections.bienvenida import mostrar_seccion_bienvenida

def page():
    st.set_page_config(page_title="Gestor de Proyectos", page_icon="🏠")
    st.title("🏠 Inicio")
    mostrar_seccion_bienvenida()

if __name__ == "__main__":
    page()
