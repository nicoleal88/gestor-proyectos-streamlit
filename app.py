import streamlit as st
from streamlit_option_menu import option_menu
from google_sheets_client import connect_to_google_sheets, init_session_state
from typing import Dict, List, Optional
from ui_sections.tareas import seccion_tareas
from ui_sections.vacaciones import seccion_vacaciones
from ui_sections.compensados import seccion_compensados
from ui_sections.notas import seccion_notas
from ui_sections.recordatorios import seccion_recordatorios
from ui_sections.calendario import seccion_calendario
from ui_sections.horarios import seccion_horarios
from ui_sections.eventos import mostrar_seccion_eventos
from ui_sections.bienvenida import mostrar_seccion_bienvenida

# Mapeo de roles a permisos
ROLES_PERMISOS = {
    'admin': ['inicio', 'tareas', 'vacaciones', 'compensados', 'eventos', 'notas', 'recordatorios', 'calendario', 'horarios'],
    'empleado': ['inicio', 'tareas', 'vacaciones'],
    'invitado': ['inicio']
}

def obtener_rol_usuario(email: str) -> str:
    """
    Determina el rol del usuario basado en su email.
    Los roles se definen en el archivo .streamlit/secrets.toml
    """
    if not email:
        return 'invitado'
    
    # Obtener listas de emails de los secrets
    admin_emails = st.secrets.get('roles', {}).get('admin_emails', [])
    empleado_emails = st.secrets.get('roles', {}).get('empleado_emails', [])
    
    # Verificar el rol del usuario
    if email in admin_emails:
        return 'admin'
    elif email in empleado_emails:
        return 'empleado'
    else:
        return 'invitado'

def tiene_permiso(rol: str, seccion: str) -> bool:
    """Verifica si un rol tiene permiso para acceder a una sección"""
    return rol in ROLES_PERMISOS and seccion.lower() in ROLES_PERMISOS[rol]

def login_screen():
    st.header("Gestor de Proyectos - Acceso Restringido")
    st.subheader("Por favor inicia sesión para continuar")
    st.button("Iniciar sesión con Google", on_click=st.login)

# --- FUNCIONES AUXILIARES ---
def get_personal_list():
    if "df_personal" in st.session_state and not st.session_state.df_personal.empty:
        return st.session_state.df_personal.iloc[:, 0].tolist()
    return []

# --- APP PRINCIPAL ---
def main():
    st.set_page_config(page_title="Gestor de Proyectos", layout="wide")
    
    # Verificar si el usuario ha iniciado sesión
    if not st.user.is_logged_in:
        login_screen()
        return
        
    # Obtener rol del usuario
    rol_usuario = obtener_rol_usuario(st.user.email)
    
    # Mostrar información del usuario en el sidebar
    st.sidebar.markdown(f"## **Usuario:** {st.user.name}")
    st.sidebar.markdown(f"**Rol:** {rol_usuario.capitalize()}")
    st.sidebar.button("Cerrar sesión", on_click=st.logout)
    st.sidebar.markdown("---")

    # st.markdown(f"<h1 style='text-align:center'>📊 Gestor de Proyectos</h1>", unsafe_allow_html=True)

    client = connect_to_google_sheets()

    if client:
        init_session_state(client)
        personal_list = get_personal_list()

        # Filtrar opciones del menú según los permisos del usuario
        opciones_menu = []
        iconos_menu = []
        
        # Mapeo de secciones a nombres para mostrar y sus íconos
        secciones_disponibles = {
            "Inicio": ('house', 'inicio'),
            "Tareas": ('list-check', 'tareas'),
            "Vacaciones": ('calendar-check', 'vacaciones'),
            "Compensados": ('clock-history', 'compensados'),
            "Eventos": ('calendar-event', 'eventos'),
            "Notas": ('sticky', 'notas'),
            "Recordatorios": ('bell', 'recordatorios'),
            "Calendario": ('calendar', 'calendario'),
            "Horarios": ('people', 'horarios')
        }
        
        # Filtrar secciones según permisos
        for seccion, (icono, permiso) in secciones_disponibles.items():
            if tiene_permiso(rol_usuario, permiso):
                opciones_menu.append(seccion)
                iconos_menu.append(icono)
        
        with st.sidebar:
            seccion = option_menu(
                "Menú Principal",
                opciones_menu,
                icons=iconos_menu,
                menu_icon="cast",
                default_index=0
            )

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