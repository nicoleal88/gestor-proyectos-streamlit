import streamlit as st
from streamlit_option_menu import option_menu
from google_sheets_client import connect_to_google_sheets, init_session_state
from ui_sections.tareas import seccion_tareas
from ui_sections.vacaciones import seccion_vacaciones
from ui_sections.compensados import seccion_compensados
from ui_sections.notas import seccion_notas
from ui_sections.recordatorios import seccion_recordatorios
from ui_sections.calendario import seccion_calendario
from ui_sections.horarios import seccion_horarios
from ui_sections.eventos import mostrar_seccion_eventos
from ui_sections.bienvenida import mostrar_seccion_bienvenida

# --- FUNCIONES AUXILIARES ---
def get_personal_list():
    if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
        return st.session_state.df_personal.iloc[:, 0].tolist()
    return []

# --- APP PRINCIPAL ---
def main():
    st.set_page_config(page_title="Gestor de Proyectos", layout="wide")
    # st.markdown("<h1 style='text-align:center'>📊 Gestor de Proyectos</h1>", unsafe_allow_html=True)

    client = connect_to_google_sheets()

    if client:
        init_session_state(client)
        personal_list = get_personal_list()

        with st.sidebar:
            seccion = option_menu(
                "Menú Principal",
                ["Inicio", "Tareas", "Vacaciones", "Compensados", "Eventos", "Notas", "Recordatorios", "Calendario", "Horarios"],
                icons=['house', 'list-check', 'calendar-check', 'clock-history', 'calendar-event', 'sticky', 'bell', 'calendar', 'people'],
                menu_icon="cast",
                default_index=0
            )

        st.sidebar.markdown("---")
        # st.sidebar.info("Esta app utiliza Google Sheets como backend.")

        if seccion == "Inicio":
            mostrar_seccion_bienvenida()
        elif seccion == "Tareas":
            seccion_tareas(client, personal_list)
        elif seccion == "Vacaciones":
            seccion_vacaciones(client, personal_list)
        elif seccion == "Compensados":
            seccion_compensados(client, personal_list)
        elif seccion == "Notas":
            seccion_notas(client, personal_list)
        elif seccion == "Recordatorios":
            seccion_recordatorios(client, personal_list)
        elif seccion == "Eventos":
            mostrar_seccion_eventos(client)
        elif seccion == "Calendario":
            seccion_calendario(client)
        elif seccion == "Horarios":
            seccion_horarios(client, personal_list)


if __name__ == "__main__":
    main()