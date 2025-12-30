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
    sheets = ["Tareas", "Vacaciones", "Compensados", "Notas", "Recordatorios", "Personal", "Eventos", "Vehiculos", "Viajes", "ViajesUpdates", "Destinos", "Feriados_Manuales"]
    for sheet_name in sheets:
        if f"df_{sheet_name.lower()}" not in st.session_state:
            # Para Feriados_Manuales, si no existe no mostramos error crítico
            if sheet_name == "Feriados_Manuales":
                try:
                    st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data_silent(client, sheet_name)
                except:
                    st.session_state[f"df_{sheet_name.lower()}"] = pd.DataFrame()
            else:
                st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data(client, sheet_name)

def get_sheet_silent(client, sheet_name):
    """Versión silenciosa de get_sheet para hojas opcionales."""
    try:
        sheet = client.open("GestorProyectosStreamlit").worksheet(sheet_name)
        return sheet
    except:
        return None

def get_sheet_data_silent(client, sheet_name):
    """Versión silenciosa de get_sheet_data."""
    sheet = get_sheet_silent(client, sheet_name)
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except:
            return pd.DataFrame()
    return pd.DataFrame()

def get_sheet_data(client, sheet_name):
    """Obtiene los datos de una hoja y los devuelve como un DataFrame."""
    sheet = get_sheet(client, sheet_name)
    if sheet:
        try:
            df = pd.DataFrame(sheet.get_all_records())
            # Normalizar encabezados (espacios accidentales)
            df.columns = [str(c).strip() for c in df.columns]
            return df
        except Exception as e:
            st.error(f"Error al leer los registros de la hoja '{sheet_name}': {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def refresh_data(client, sheet_name):
    """Refresca los datos de una hoja específica en el estado de la sesión."""
    st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data(client, sheet_name)
    st.cache_data.clear()

def refresh_all_data(client):
    """Refresca todos los DataFrames del estado de la sesión."""
    sheets = ["Tareas", "Vacaciones", "Compensados", "Notas", "Recordatorios", "Personal", "Eventos", "Vehiculos", "Viajes", "ViajesUpdates", "Destinos", "Feriados_Manuales"]
    for sheet_name in sheets:
        if sheet_name == "Feriados_Manuales":
            st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data_silent(client, sheet_name)
        else:
            st.session_state[f"df_{sheet_name.lower()}"] = get_sheet_data(client, sheet_name)
    st.cache_data.clear()

def update_cell_by_id(client, sheet_name, id_to_find, column_name, new_value):
    """Actualiza una celda específica buscando por ID y nombre de columna."""
    sheet = get_sheet(client, sheet_name)
    if not sheet:
        return False
    try:
        df = get_sheet_data(client, sheet_name)
        if not df.empty:
            # Asegurar columnas normalizadas
            df.columns = [str(c).strip() for c in df.columns]
        if df.empty or 'ID' not in df.columns:
            st.error(f"La hoja '{sheet_name}' no tiene una columna 'ID' o está vacía.")
            return False

        # Asegurarse de que el tipo de dato del ID es consistente
        df['ID'] = df['ID'].astype(str).str.strip()
        id_to_find = str(id_to_find).strip()

        # Intento 1: búsqueda en DataFrame local
        row_index = df[df['ID'] == id_to_find].index

        headers_raw = sheet.row_values(1)
        headers = [str(h).strip() for h in headers_raw]
        if column_name not in headers:
            st.error(f"La columna '{column_name}' no existe en la hoja '{sheet_name}'.")
            return False
        
        col_to_update = headers.index(column_name) + 1

        # gspread usa índices basados en 1, y la primera fila es la cabecera
        if row_index.any():
            row_to_update = row_index[0] + 2
        else:
            # Intento 2: búsqueda directa en la hoja (fallback)
            try:
                id_col_idx = headers.index('ID') + 1 if 'ID' in headers else None
            except ValueError:
                id_col_idx = None

            if not id_col_idx:
                st.warning(f"No se encontró la columna 'ID' en los encabezados de '{sheet_name}'.")
                return False

            matches = sheet.findall(id_to_find)
            row_to_update = None
            for cell in matches:
                if cell.col == id_col_idx:
                    row_to_update = cell.row
                    break

            if not row_to_update:
                st.warning(f"No se encontró ninguna fila con ID '{id_to_find}' en '{sheet_name}'.")
                return False

        sheet.update_cell(row_to_update, col_to_update, new_value)
        return True
    except Exception as e:
        st.error(f"Error al actualizar la celda en Google Sheets: {e}")
        return False
