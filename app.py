import streamlit as st
from database import connect_to_database, init_session_state
from typing import Dict, List, Optional, Callable
import importlib
import os


# Mapeo de roles a permisos
ROLES_PERMISOS = {
    'admin': ['inicio', 'vacaciones', 'compensados', 'calendario', 'horarios', 'utilidades'],
    'empleado': ['inicio', 'vacaciones'],
    'secretaria': ['inicio', 'vacaciones', 'compensados', 'horarios'],
    'invitado': ['inicio']
}

# Mapeo de páginas a sus permisos requeridos
PAGE_PERMISSIONS = {
    '00_Inicio': 'inicio',
    '02_Vacaciones': 'vacaciones',
    '03_Compensados': 'compensados',
    '06_Calendario': 'calendario',
    '07_Horarios': 'horarios',
    '10_Utilidades_Carga_y_Merge': 'utilidades'
}

# Mapeo de páginas a sus emojis para el sidebar
PAGE_ICONS = {
    '00_Inicio': '🏠',
    '02_Vacaciones': '📅',
    '03_Compensados': '⏱️',
    '06_Calendario': '📆',
    '07_Horarios': '👥',
    '10_Utilidades_Carga_y_Merge': '🧰'
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
    secretaria_emails = st.secrets.get('roles', {}).get('secretaria_emails', [])
    
    # Verificar el rol del usuario
    if email in admin_emails:
        return 'admin'
    elif email in empleado_emails:
        return 'empleado'
    elif email in secretaria_emails:
        return 'secretaria'
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
    
    # Inicializar cliente de base de datos SQLite
    client = connect_to_database()
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
        # Ajuste de nombre visible: Compensados -> Ausencias
        if page_name == '03_Compensados':
            display_name = 'Ausencias'
        
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
        # 1. Logo e información del usuario (al principio del sidebar)
        with st.sidebar:
            st.image("data/Logo-Auger.png", width=100)
            st.markdown(f"## **Usuario:** {st.user.name}")
            st.markdown(f"**Rol:** {rol_usuario.capitalize()}")
            st.button("Cerrar sesión", on_click=st.logout)
            st.markdown("---")

        # 2. Navegación (el menú aparecerá debajo de lo anterior)
        selected_page = st.navigation(pages)


        # Área principal: Ejecutar la página seleccionada
        # Guardar la sección actual para que las páginas puedan detectar cambios de sección
        st.session_state.current_section = selected_page.title
        selected_page.run()
    else:
        st.error("No hay páginas disponibles para tu rol. Contacta al administrador.")

if __name__ == "__main__":
    main()