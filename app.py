import streamlit as st
from google_sheets_client import connect_to_google_sheets, init_session_state
from typing import Dict, List, Optional, Callable
import importlib
import os
from version_manager import display_version_sidebar

# Mapeo de roles a permisos
ROLES_PERMISOS = {
    'admin': ['inicio', 'tareas', 'vacaciones', 'compensados', 'eventos', 'notas', 'recordatorios', 'calendario', 'horarios'],
    'empleado': ['inicio', 'tareas', 'vacaciones'],
    'invitado': ['inicio']
}

# Mapeo de páginas a sus permisos requeridos
PAGE_PERMISSIONS = {
    '00_Inicio': 'inicio',
    '01_Tareas': 'tareas',
    '02_Vacaciones': 'vacaciones',
    '03_Compensados': 'compensados',
    '04_Notas': 'notas',
    '05_Recordatorios': 'recordatorios',
    '06_Calendario': 'calendario',
    '07_Horarios': 'horarios'
}

# Mapeo de páginas a sus emojis para el sidebar
PAGE_ICONS = {
    '00_Inicio': '🏠',
    '01_Tareas': '✅',
    '02_Vacaciones': '📅',
    '03_Compensados': '⏱️',
    '04_Notas': '📝',
    '05_Recordatorios': '🔔',
    '06_Calendario': '📆',
    '07_Horarios': '👥'
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

def get_available_pages(rol: str) -> List[str]:
    """Obtiene la lista de páginas disponibles según el rol del usuario"""
    available_pages = []
    pages_dir = os.path.join(os.path.dirname(__file__), 'pages')
    
    if not os.path.exists(pages_dir):
        return available_pages
        
    for filename in sorted(os.listdir(pages_dir)):
        if filename.endswith('.py') and not filename.startswith('.'):
            page_name = os.path.splitext(filename)[0]
            # Obtener el permiso requerido para esta página
            permission_required = PAGE_PERMISSIONS.get(page_name, '').lower()
            
            # Si la página no está en el mapeo de permisos, se asume que requiere permiso de admin
            if not permission_required:
                permission_required = 'admin'
                
            # Verificar si el rol tiene permiso para acceder a esta página
            if tiene_permiso(rol, permission_required):
                available_pages.append(filename)
    
    return available_pages

def load_page(page_file: str):
    """Carga dinámicamente una página y devuelve su función page()"""
    module_name = f"pages.{os.path.splitext(page_file)[0]}"
    try:
        module = importlib.import_module(module_name)
        return module.page
    except (ImportError, AttributeError) as e:
        st.error(f"Error al cargar la página {page_file}: {e}")
        return None

def main():
    st.set_page_config(
        page_title="Gestor de Proyectos",
        layout="wide",
        page_icon="📊"
    )
    
    # Verificar si el usuario ha iniciado sesión
    if not st.user.is_logged_in:
        login_screen()
        return
    
    # Obtener rol del usuario
    rol_usuario = obtener_rol_usuario(st.user.email)
    
    # Inicializar cliente de Google Sheets
    client = connect_to_google_sheets()
    if client:
        init_session_state(client)
    
    # Obtener páginas disponibles para este rol
    available_pages = get_available_pages(rol_usuario)
    
    # Crear páginas
    pages = []
    for page_file in available_pages:
        page_name = os.path.splitext(page_file)[0]
        # Extraer el nombre legible del nombre del archivo (después del primer _)
        display_name = ' '.join(page_name.split('_')[1:])
        
        # Crear la página
        page_func = load_page(page_file)
        if page_func:
            pages.append(st.Page(
                page_func,
                title=display_name,
                icon=PAGE_ICONS.get(page_name, None),
                url_path=page_name.lower().replace('_', '-')
            ))
    
    # Mostrar navegación y ejecutar la página seleccionada
    if pages:
        # Sidebar: Información del usuario y navegación
        with st.sidebar:
            st.markdown(f"## **Usuario:** {st.user.name}")
            st.markdown(f"**Rol:** {rol_usuario.capitalize()}")
            st.button("Cerrar sesión", on_click=st.logout)
            st.markdown("---")

            # Mostrar información de versión
            display_version_sidebar()

            st.markdown("---")

            # Mostrar navegación en el sidebar
            selected_page = st.navigation(pages)

        # Área principal: Ejecutar la página seleccionada
        selected_page.run()
    else:
        st.error("No hay páginas disponibles para tu rol. Contacta al administrador.")

if __name__ == "__main__":
    main()