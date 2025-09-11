import streamlit as st
import gspread
import pandas as pd

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def connect_to_google_sheets():
    try:
        client = gspread.service_account("credenciales.json")
        return client
    except FileNotFoundError:
        st.error("Error: El archivo 'credenciales.json' no se encontró.")
        st.info("Por favor, sigue las instrucciones en el README.md para configurar tus credenciales de Google Cloud.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al conectar con Google Sheets: {e}")
        return None

def get_sheet(client, sheet_name):
    try:
        sheet = client.open("GestorProyectosStreamlit").worksheet(sheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Error: La hoja de cálculo 'GestorProyectosStreamlit' no fue encontrada.")
        st.info("Asegúrate de haber creado el Google Sheet con ese nombre exacto.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: La pestaña '{sheet_name}' no fue encontrada en el Google Sheet.")
        st.info(f"Asegúrate de que la pestaña '{sheet_name}' existe.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al acceder a la hoja: {e}")
        return None

# --- FUNCIONES DE DATOS ---
def init_session_state(client):
    """Inicializa el estado de la sesión para cada hoja de cálculo."""
    sheets = ["Tareas", "Vacaciones", "Compensados", "Notas", "Recordatorios", "Personal", "Eventos"]
    for sheet_name in sheets:
        if f"df_{sheet_name.lower()}" not in st.session_state:
            st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data(client, sheet_name)

def get_sheet_data(client, sheet_name):
    """Obtiene los datos de una hoja y los devuelve como un DataFrame."""
    sheet = get_sheet(client, sheet_name)
    if sheet:
        try:
            return pd.DataFrame(sheet.get_all_records())
        except Exception as e:
            st.error(f"Error al leer los registros de la hoja '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def refresh_data(client, sheet_name):
    """Refresca los datos de una hoja específica en el estado de la sesión."""
    st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data(client, sheet_name)
    st.cache_data.clear()
