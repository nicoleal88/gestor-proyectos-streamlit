import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import warnings
import re
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO
import os
from utils.date_utils import get_feriados_argentina

# Imports opcionales para Google Drive (no rompen si no están instalados)
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    HAS_GOOGLE_DRIVE = True
except Exception:
    HAS_GOOGLE_DRIVE = False

warnings.filterwarnings("ignore", message=".*FontBBox.*")

# --- Configuración de la Página ---
st.set_page_config(
    page_title="Análisis de Asistencia",
    page_icon="🕒",
    layout="wide"
)

# --- Funciones de Procesamiento ---

def cargar_y_procesar_datos(archivo_subido):
    """
    Carga los datos desde el archivo subido, los procesa y calcula
    métricas clave como la jornada laboral sumando intervalos de pares de registros.
    """
    if archivo_subido is None:
        return None, None

    try:
        df = pd.read_csv(
            archivo_subido,
            header=None,
            sep=r'\s+|\t+',
            engine='python'
        )

        if df.shape[1] == 6:
            df.columns = ['id_empleado', 'fecha', 'hora', 'col_3', 'col_4', 'col_5']
            df['fecha_hora'] = df['fecha'] + ' ' + df['hora']
            df = df[['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5']]
        else:
            df.columns = ['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5']

        # Procesamiento común
        df['id_empleado'] = df['id_empleado'].astype(str)
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
        df['fecha'] = df['fecha_hora'].dt.date
        df['hora'] = df['fecha_hora'].dt.hour
        df['tipo'] = 'RELOJ'  # Marcar como datos de reloj

        # --- NUEVO: Calcular suma de intervalos por día y empleado ---
        def sumar_intervalos(fechas):
            fechas = fechas.sort_values()
            tiempos = fechas.tolist()
            total = pd.Timedelta(0)
            for i in range(0, len(tiempos)-1, 2):
                total += tiempos[i+1] - tiempos[i]
            return total.total_seconds() / 3600  # en horas

        jornada = (
            df.groupby(['id_empleado', 'fecha'])['fecha_hora']
            .apply(sumar_intervalos)
            .reset_index(name='duracion_horas')
        )

        # Para mostrar inicio y fin de jornada (opcional)
        min_max = df.groupby(['id_empleado', 'fecha'])['fecha_hora'].agg(['min', 'max']).reset_index()
        jornada = jornada.merge(min_max, on=['id_empleado', 'fecha'])
        jornada.rename(columns={'min': 'inicio_jornada', 'max': 'fin_jornada'}, inplace=True)
        jornada = jornada[jornada['duracion_horas'] > 0.25]

        return df, jornada

    except Exception as e:
        st.error(f"Error al procesar el archivo: {e}")
        st.warning("Asegúrate de que el archivo tenga el formato esperado: ID_Empleado Fecha_Hora Col3 Col4 Col5.")
        return None, None

def leer_pdf_query(path_pdf):
    """Lee el PDF de query y devuelve un DataFrame compatible."""
    rows = []
    try:
        with pdfplumber.open(path_pdf) as pdf:
            for i, page in enumerate(pdf.pages):
                table = page.extract_table()
                if table:
                    # Solo saltar el encabezado en la primera página
                    start_idx = 1 if i == 0 else 0
                    for row in table[start_idx:]:
                        # Solo agregar filas que tengan datos
                        if any(cell is not None for cell in row):
                            rows.append(row)
        
        if not rows:
            st.warning("No se encontraron datos en el PDF.")
            return None
        
        # Ajusta los nombres de columna según el PDF
        try:
            df_pdf = pd.DataFrame(rows, columns=["Date", "ID Number", "Name", "Time", "Status", "Verification"])
            
            # Limpiar y convertir fechas y horas
            df_pdf = df_pdf.dropna(subset=['Date', 'Time'])
            
            # Unificar formato con el DataFrame principal
            df_pdf['id_empleado'] = df_pdf['ID Number'].astype(str).str.strip()
            
            # Intentar diferentes formatos de fecha/hora
            date_formats = [
                '%d/%m/%Y %H:%M:%S',  # 31/12/2023 23:59:59
                '%Y-%m-%d %H:%M:%S',  # 2023-12-31 23:59:59
                '%d/%m/%Y %H:%M',      # 31/12/2023 23:59
                '%Y-%m-%d %H:%M'       # 2023-12-31 23:59
            ]
            
            df_pdf['fecha_hora'] = pd.NaT
            for fmt in date_formats:
                mask = df_pdf['fecha_hora'].isna()
                if mask.any():
                    df_pdf.loc[mask, 'fecha_hora'] = pd.to_datetime(
                        df_pdf.loc[mask, 'Date'] + ' ' + df_pdf.loc[mask, 'Time'],
                        format=fmt,
                        errors='coerce'
                    )
            
            # Verificar si se pudieron convertir las fechas
            if df_pdf['fecha_hora'].isna().all():
                st.error("Error: No se pudo interpretar el formato de fecha/hora del PDF.")
                return None
            
            # Eliminar filas con fechas/horas inválidas
            df_pdf = df_pdf.dropna(subset=['fecha_hora'])
            
            if df_pdf.empty:
                st.error("Error: No se encontraron registros válidos en el PDF.")
                return None
            
            # Extraer fecha y hora
            df_pdf['fecha'] = df_pdf['fecha_hora'].dt.date
            df_pdf['hora'] = df_pdf['fecha_hora'].dt.hour
            
            # Columnas dummy para compatibilidad
            df_pdf['col_3'] = None
            df_pdf['col_4'] = None
            df_pdf['col_5'] = None
            df_pdf['tipo'] = 'RELOJ'  # Marcar como datos de reloj
            
            return df_pdf[['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5', 'fecha', 'hora', 'tipo']]
            
        except Exception as e:
            st.error(f"Error al procesar el archivo PDF: {str(e)}")
            return None
    
    except Exception as e:
        st.error(f"Error al abrir el archivo PDF: {str(e)}")
        return None

# --- Integración con Google Drive (Service Account) ---
@st.cache_resource
def build_drive_client():
    """
    Construye un cliente de Google Drive v3 usando el archivo credenciales.json
    ya utilizado por gspread. Requiere que las dependencias de Google estén instaladas.
    """
    if not HAS_GOOGLE_DRIVE:
        return None
    try:
        # Buscar credenciales.json en la raíz del proyecto (un nivel arriba de ui_sections/)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(current_dir)
        creds_path = os.path.join(root_dir, "credenciales.json")
        
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
        )
        service = build("drive", "v3", credentials=creds, cache_discovery=False)
        return service
    except FileNotFoundError:
        st.warning("No se encontró 'credenciales.json' para Google Drive.")
        return None
    except Exception as e:
        st.error(f"No fue posible inicializar el cliente de Google Drive: {e}")
        return None

@st.cache_data(ttl=600, show_spinner=False)
def list_csvs_in_folder(folder_id: str):
    """
    Lista archivos CSV en una carpeta de Drive por su Folder ID.
    Devuelve lista de dicts: [{id, name, size, modifiedTime, mimeType}]
    """
    service = build_drive_client()
    if service is None:
        return []
    try:
        files = []
        page_token = None
        query = (
            f"'{folder_id}' in parents and trashed = false and "
            "(mimeType = 'text/csv' or name contains '.csv')"
        )
        while True:
            resp = service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, size, modifiedTime, mimeType)",
                pageToken=page_token,
                orderBy="modifiedTime desc",
            ).execute()
            files.extend(resp.get("files", []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return files
    except Exception as e:
        st.error(f"Error al listar archivos de Drive: {e}")
        return []

@st.cache_data(show_spinner=False)
def download_csv_file(file_id: str) -> bytes:
    """
    Descarga el contenido de un archivo CSV de Drive por file_id y devuelve bytes.
    """
    service = build_drive_client()
    if service is None:
        return b""
    try:
        request = service.files().get_media(fileId=file_id)
        buf = BytesIO()
        downloader = MediaIoBaseDownload(buf, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        return buf.getvalue()
    except Exception as e:
        st.error(f"Error al descargar archivo de Drive ({file_id}): {e}")
        return b""

def read_csv_bytes(content: bytes) -> pd.DataFrame:
    """Lee bytes de CSV de manera robusta intentando distintos encodings."""
    if not content:
        return pd.DataFrame()
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            df = pd.read_csv(BytesIO(content), encoding=enc)
            return df
        except Exception:
            continue
    return pd.DataFrame()

def limpiar_nombre_empleado(nombre):
    """
    Limpia el nombre del empleado eliminando números iniciales y espacios adicionales.
    Ejemplos:
    - "10 PEREZ" -> "PEREZ"
    - "2PACHECO" -> "PACHECO"
    - " 5  GOMEZ  " -> "GOMEZ"
    """
    if not isinstance(nombre, str):
        return nombre
    # Eliminar números iniciales y cualquier espacio que los siga
    nombre_limpio = re.sub(r'^\d+\s*', '', nombre.strip())
    # Eliminar espacios múltiples internos
    nombre_limpio = re.sub(r'\s+', ' ', nombre_limpio)
    return nombre_limpio

def leer_excel_horarios(archivo_excel):
    """
    Lee un archivo Excel con hojas por empleado (formato planilla de horarios).
    El nombre del archivo debe estar en formato YYYY-MM.xlsx (ej: 2025-07.xlsx).
    Acepta tanto un objeto UploadedFile de Streamlit como una ruta de archivo.
    Devuelve un DataFrame con columnas compatibles con df_registros.
    """
    import os
    import tempfile
    from datetime import datetime
    
    # Manejar tanto UploadedFile como rutas de archivo
    if hasattr(archivo_excel, 'name'):  # Es un UploadedFile
        filename = archivo_excel.name
        # Crear un archivo temporal para leer con pandas
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            tmp.write(archivo_excel.getvalue())
            temp_path = tmp.name
        try:
            xls = pd.ExcelFile(temp_path)
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {str(e)}")
            return pd.DataFrame(columns=['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5', 'fecha', 'hora'])
        finally:
            # Asegurarse de que el archivo temporal se elimine
            try:
                os.unlink(temp_path)
            except:
                pass
    else:  # Es una ruta de archivo
        filename = os.path.basename(archivo_excel)
        try:
            xls = pd.ExcelFile(archivo_excel)
        except Exception as e:
            st.error(f"Error al leer el archivo Excel: {str(e)}")
            return pd.DataFrame(columns=['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5', 'fecha', 'hora'])
    
    # Extraer mes y año del nombre del archivo (ej: '2025-07.xlsx' -> '2025-07')
    try:
        # Extraer la parte antes de .xlsx y validar el formato
        date_part = os.path.splitext(filename)[0]
        mes_dt = datetime.strptime(date_part, '%Y-%m')
        mes_num = mes_dt.strftime('%Y-%m')
    except (ValueError, IndexError):
        st.error(f"El archivo debe tener el formato YYYY-MM.xlsx (ej: 2025-07.xlsx). Se encontró: {filename}")
        return pd.DataFrame(columns=['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5', 'fecha', 'hora', 'tipo'])
    
    registros = []

    for hoja in xls.sheet_names:
        df = pd.read_excel(xls, hoja, header=None)

        # recorrer filas de días (aprox 12 a 42)
        for i in range(10, 42):
            dia = df.iloc[i, 0]  # columna A
            if pd.isna(dia):
                continue
            try:
                fecha = f"{mes_num}-{int(dia):02d}"
            except Exception:
                continue

            # columnas de horas/minutos (C:D, E:F, G:H, I:J → índices 2:3, 4:5, 6:7, 8:9)
            pares = [(2, 3), (4, 5), (6, 7), (8, 9)]
            for col_h, col_m in pares:
                hora = df.iloc[i, col_h]
                minuto = df.iloc[i, col_m]
                if pd.notna(hora) and pd.notna(minuto):
                    try:
                        dt = pd.to_datetime(
                            f"{fecha} {int(hora)}:{int(minuto)}",
                            errors="coerce"
                        )
                        if pd.notna(dt):
                            # Limpiar el nombre de la hoja (eliminar números iniciales y espacios) y convertir a mayúsculas
                            nombre_hoja_limpio = limpiar_nombre_empleado(hoja).upper()
                            
                            # Buscar el ID en el mapa de planilla
                            id_match = MAPA_PLANILLA_ID.get(nombre_hoja_limpio, None)
                            
                            # Si no se encuentra, mostrar advertencia y usar el nombre como fallback
                            if id_match is None:
                                st.warning(f"No se encontró ID para la hoja '{hoja}' (limpio: '{nombre_hoja_limpio}'), usando nombre como fallback")
                                id_match = nombre_hoja_limpio

                            registros.append({
                                "id_empleado": id_match if id_match else nombre_hoja,
                                "fecha_hora": dt,
                                "col_3": None,
                                "col_4": None,
                                "col_5": None,
                                "fecha": dt.date(),
                                "hora": dt.hour,
                                "tipo": 'LIBRO'  # Marcar como datos del libro de horarios
                            })
                    except Exception:
                        continue

    df_planilla = pd.DataFrame(registros)
    if not df_planilla.empty:
        df_planilla['fecha'] = df_planilla['fecha_hora'].dt.date
        df_planilla['hora'] = df_planilla['fecha_hora'].dt.hour
    return df_planilla


def obtener_compensatorios_por_fecha():
    """
    Obtiene los compensatorios activos del session_state y los procesa para el análisis de horarios.
    Incluye:
    - Ausencias "por horas" (usa horas de inicio y fin)
    - Ausencias de "día completo" (expande cada día con 8 horas)
    Devuelve un DataFrame con los registros por fecha y empleado.
    """
    if 'df_compensados' not in st.session_state or st.session_state.df_compensados.empty:
        return pd.DataFrame()
    
    try:
        # Obtener datos de compensatorios
        compensados = st.session_state.df_compensados.copy()
        
        # Verificar si las columnas necesarias existen
        required_columns = ['Apellido, Nombres', 'Desde fecha', 'Hasta fecha', 'Desde hora', 'Hasta hora']
        if not all(col in compensados.columns for col in required_columns):
            st.warning("El formato de la hoja de compensatorios no es el esperado")
            return pd.DataFrame()
        
        # Convertir fechas y horas
        compensados['Desde fecha'] = pd.to_datetime(compensados['Desde fecha']).dt.date
        compensados['Hasta fecha'] = pd.to_datetime(compensados['Hasta fecha']).dt.date
        
        # Subconjuntos: por horas vs día completo
        mask_con_horas = (
            compensados['Desde hora'].notna() &
            compensados['Hasta hora'].notna() &
            (compensados['Desde hora'] != '') &
            (compensados['Hasta hora'] != '')
        )
        df_con_horas = compensados[mask_con_horas].copy()
        df_dia_completo = compensados[~mask_con_horas].copy()

        registros = []

        # Procesar ausencias por horas
        for _, row in df_con_horas.iterrows():
            try:
                hora_inicio = pd.to_datetime(row['Desde hora']).time()
                hora_fin = pd.to_datetime(row['Hasta hora']).time()

                inicio_dt = datetime.combine(datetime.today(), hora_inicio)
                fin_dt = datetime.combine(datetime.today(), hora_fin)
                duracion = (fin_dt - inicio_dt).total_seconds() / 3600

                nombre_empleado = row['Apellido, Nombres']
                id_empleado = next((k for k, v in ID_NOMBRE_MAP.items() if v == nombre_empleado), None)

                if id_empleado:
                    # Extraer detalle exclusivamente desde la columna 'Tipo'
                    detalle = ''
                    if 'Tipo' in compensados.columns and pd.notna(row.get('Tipo', '')):
                        detalle = str(row.get('Tipo', '')).strip()
                    registros.append({
                        'fecha': row['Desde fecha'],
                        'fecha_dt': pd.Timestamp(row['Desde fecha']),
                        'id_empleado': id_empleado,
                        'tipo': 'AUSENCIAS',
                        'tipo_detalle': detalle,
                        'duracion_horas': duracion,
                        'fecha_formateada': pd.Timestamp(row['Desde fecha']).strftime('%d/%m/%Y'),
                        'hora_inicio': hora_inicio.strftime('%H:%M'),
                        'hora_fin': hora_fin.strftime('%H:%M')
                    })
            except Exception as e:
                st.warning(f"Error al procesar ausencia por horas para {row.get('Apellido, Nombres', 'empleado')}: {str(e)}")
                continue

        # Procesar ausencias de día completo: expandir cada día con 8 horas
        for _, row in df_dia_completo.iterrows():
            try:
                nombre_empleado = row['Apellido, Nombres']
                id_empleado = next((k for k, v in ID_NOMBRE_MAP.items() if v == nombre_empleado), None)
                if not id_empleado:
                    continue

                inicio = pd.Timestamp(row['Desde fecha'])
                fin = pd.Timestamp(row['Hasta fecha'])
                if pd.isna(inicio) or pd.isna(fin) or fin < inicio:
                    continue

                fechas = pd.date_range(start=inicio, end=fin, freq='D')
                for f in fechas:
                    # Extraer detalle exclusivamente desde la columna 'Tipo'
                    detalle = ''
                    if 'Tipo' in compensados.columns and pd.notna(row.get('Tipo', '')):
                        detalle = str(row.get('Tipo', '')).strip()
                    registros.append({
                        'fecha': f.date(),
                        'fecha_dt': f,
                        'id_empleado': id_empleado,
                        'tipo': 'AUSENCIAS',
                        'tipo_detalle': detalle,
                        'duracion_horas': 8.0,
                        'fecha_formateada': f.strftime('%d/%m/%Y'),
                        'hora_inicio': '',
                        'hora_fin': ''
                    })
            except Exception as e:
                st.warning(f"Error al procesar ausencia de día completo para {row.get('Apellido, Nombres', 'empleado')}: {str(e)}")
                continue

        return pd.DataFrame(registros)
        
    except Exception as e:
        st.error(f"Error al procesar compensatorios: {str(e)}")
        return pd.DataFrame()

def obtener_vacaciones_por_fecha():
    """
    Convierte las licencias/vacaciones del session_state en registros diarios de 8h por empleado.
    Devuelve columnas compatibles con el pipeline de Horarios.
    """
    df_vac = st.session_state.get('df_vacaciones', pd.DataFrame())
    if df_vac is None or df_vac.empty:
        return pd.DataFrame()

    # Columnas esperadas: 'Apellido, Nombres', 'Fecha inicio', 'Fecha regreso'
    required = ['Apellido, Nombres', 'Fecha inicio', 'Fecha regreso']
    if not all(col in df_vac.columns for col in required):
        return pd.DataFrame()

    try:
        vac = df_vac.copy()
        vac['Fecha inicio'] = pd.to_datetime(vac['Fecha inicio'], errors='coerce').dt.date
        vac['Fecha regreso'] = pd.to_datetime(vac['Fecha regreso'], errors='coerce').dt.date

        registros = []
        for _, row in vac.iterrows():
            try:
                inicio = pd.Timestamp(row['Fecha inicio'])
                fin = pd.Timestamp(row['Fecha regreso'])
                # No incluir el día de regreso: fin es no-inclusivo
                if pd.isna(inicio) or pd.isna(fin) or fin <= inicio:
                    continue

                nombre = row['Apellido, Nombres']
                id_emp = next((k for k, v in ID_NOMBRE_MAP.items() if v == nombre), None)
                # Fallback: si no hay ID mapeado, usar el nombre como identificador para no perder la barra
                if not id_emp:
                    id_emp = nombre

                # Expandir diariamente SIN incluir el día de regreso (fin no inclusivo)
                for f in pd.date_range(start=inicio, end=fin - pd.Timedelta(days=1), freq='D'):
                    # Extraer subtipo de vacaciones exclusivamente desde 'Tipo'
                    vac_detalle = ''
                    if 'Tipo' in vac.columns and pd.notna(row.get('Tipo', '')):
                        vac_detalle = str(row.get('Tipo', '')).strip()
                    registros.append({
                        'fecha': f.date(),
                        'fecha_dt': f,
                        'id_empleado': id_emp,
                        'tipo': 'VACACIONES',
                        'tipo_detalle': vac_detalle,
                        'duracion_horas': 8.0,
                        'fecha_formateada': f.strftime('%d/%m/%Y'),
                        'hora_inicio': '',
                        'hora_fin': ''
                    })
            except Exception:
                continue
        return pd.DataFrame(registros)
    except Exception:
        return pd.DataFrame()

# --- Relación ID <-> Apellido y Nombre ---
ID_NOMBRE_MAP = {
    '37': 'Alcalde, Eduardo Jorge',
    '67': 'Arroyo, Ivana',
    '89': 'Balibrea, Yosel de Jesús',
    '88': 'Behler, Juan Pablo',
    '32': 'Blanco, Juan Carlos',
    '73': 'Castro, Neiber',
    '91': 'Cogo, Marcela',
    '61': 'Díaz, Lucas Gabriel',
    '69': 'Domínguez, Tania',
    '19': 'Escalona, José Luis',
    '18': 'Farías, María Isabel',
    '39': 'Gajardo, Mauro Luis',
    '7': 'Giménez, Yamila Gisela',
    '27': 'Gómez, Leandro Marcelo',
    '53': 'González, Marta Mary',
    '77': 'Guerra, Yan Carlos',
    '55': 'Morales , Claudio Gabriel',
    '11': 'Morales , Ignacio Agustín',
    '34': 'Muñoz, Iván Marcelo',
    '16': 'Pacheco, Rosa Inés',
    '79': 'Parasécoli, Matías',
    '15': 'Pérez, Ricardo Rubén',
    '4': 'Rodríguez, Alexis Damián',
    '10001': 'Rojas, José Fernando',
    '76': 'Rojas, Matías',
    '35': 'Sáez, Oscar Antonio',
    '3': 'Salinas, Adolfo Javier',
    '5': 'Salvadores, Miguel Angel',
    '82': 'Sepúlveda, Nicolás',
    '65': 'Torres, Luciana',
    '54': 'Travaini, Andrés Esteban',
    '10000': 'Velázquez, Jesica Lorena',
    '22': 'Vidal, Raúl Eduardo',
    '8': 'Villalovos, Fabián Darío',
    '87': 'Villar, Sebastián',
    'GOBBI': 'Gobbi, Fabián Jesús',
    'GONGORA': 'Gongora, Juan Pablo',
    'RODRIGUEZ, JORGE': 'Rodriguez, Jorge',
    'VITALE': 'Vitale, Primo',
    'SATO': 'Sato, Ricardo',
    'CERDA': 'Cerda, Marcos',
    'LEAL': 'Leal, Nicolás',
    'RIOS': 'Rios, Gustavo'
}

MAPA_PLANILLA_ID = {
    "GIMENEZ": "7",                # Giménez, Yamila Gisela
    "PACHECO": "16",               # Pacheco, Rosa Inés
    "ESCALONA": "19",              # Escalona, José Luis
    "GÓMEZ L.": "27",              # Gómez, Leandro Marcelo
    "ALCALDE": "37",               # Alcalde, Eduardo Jorge
    "BLANCO": "32",                # Blanco, Juan Carlos
    "FARIAS": "18",                # Farías, María Isabel
    "GONZALEZ": "53",              # González, Marta Mary
    "MUÑOZ": "34",                 # Muñoz, Iván Marcelo
    "PEREZ": "15",                 # Pérez, Ricardo Rubén
    "RODRIGUEZ A": "4",            # Rodríguez, Alexis Damián
    "SALINAS": "3",                # Salinas, Adolfo Javier
    "ROJAS JOSE": "10001",         # Rojas, José Fernando
    "GAJARDO": "39",               # Gajardo, Mauro Luis
    "SÁEZ": "35",                  # Sáez, Oscar Antonio
    "SALVADORES": "5",             # Salvadores, Miguel Angel
    "VELAZQUEZ": "10000",          # Velázquez, Jesica Lorena
    "VIDAL": "22",                 # Vidal, Raúl Eduardo
    "TRAVAINI": "54",              # Travaini, Andrés Esteban
    "VILLALOVOS": "8",             # Villalovos, Fabián Darío
    "GUERRA": "77",                # Guerra, Yan Carlos
    "BEHLER": "88",                # Behler, Juan Pablo
    "BALIBREA": "89",              # Balibrea, Yosel de Jesús
    "GABRIEL MORALES": "55",       # Morales, Claudio Gabriel
    "AGUSTIN MORALES": "11",       # Morales, Ignacio Agustín
    "TORRES": "65",                # Torres, Luciana
    "SEPULVEDA": "82",             # Sepúlveda, Nicolás
    "DÍAZ": "61",                  # Díaz, Lucas Gabriel
    "ROJAS MATÍAS": "76",          # Rojas, Matías
    "CASTRO": "73",                # Castro, Neiber
    "PARASECOLI": "79",            # Parasécoli, Matías
    "VILLAR": "87",                # Villar, Sebastián
    "DOMINGUEZ": "69",             # Domínguez, Tania
    "COGO": "91",                  # Cogo, Marcela
    "ARROYO": "67",                # Arroyo, Ivana
    # --- Hojas sin ID en tu ID_NOMBRE_MAP ---
    "VITALE": None,
    "RODRIGUEZ, JORGE": None,
    "GONGORA": None,
    "SATO": None,
    "CERDA": None,
    "GOBBI": None,
    "LEAL": None,
    "RIOS": None
}

def get_employee_display(id_empleado, incognito_mode):
    """Devuelve el nombre o ID del empleado según el modo incógnito"""
    if incognito_mode:
        return f"ID: {id_empleado}"
    return ID_NOMBRE_MAP.get(id_empleado, f"ID: {id_empleado}")

def seccion_horarios(client, personal_list):
    """
    Sección de Streamlit para analizar y visualizar los horarios del personal.
    Permite cargar archivos de texto y PDF, procesar los datos y mostrar gráficos interactivos.
    """

    # --- Interfaz de Usuario (UI) ---
    st.subheader("📊 Analizador de Horarios del Personal")
    
    # Toggle para modo incógnito
    incognito_mode = st.checkbox("Modo incógnito (mostrar IDs en lugar de nombres)", 
                               value=st.session_state.get('incognito_mode', False),
                               key='incognito_mode')

    # Fuente única: Google Drive (carpeta fija)
    st.markdown("### Archivos mensuales - Reloj + Libro")
    if not HAS_GOOGLE_DRIVE:
        st.info("Para usar esta opción instala: google-api-python-client, google-auth, google-auth-httplib2, google-auth-oauthlib")
        return
        
    DEFAULT_FOLDER_ID = "1mN0l4IOrsawz1p4p0K0OeHMm1dMe8RWS"

    # Botón para refrescar lista de archivos desde Google Drive
    if st.button("🔄 Actualizar lista"):
        try:
            st.cache_data.clear()
        except Exception:
            pass
        # Limpiar estados relacionados para forzar recarga
        st.session_state.pop('drive_csv_files', None)
        st.session_state.pop('df_registros_horarios', None)
        st.session_state.pop('drive_processed_ids', None)
        st.session_state.pop('jornada_horarios', None)
        st.rerun()

    # Limpiar caché al cargar la página
    if 'drive_csv_files' not in st.session_state or 'df_registros_horarios' not in st.session_state:
        st.session_state['drive_processed_ids'] = None
        st.session_state['df_registros_horarios'] = None
        st.session_state['jornada_horarios'] = None
    
    # Obtener lista de archivos del Drive (usando caché)
    files_list_all = list_csvs_in_folder(DEFAULT_FOLDER_ID)
    st.session_state['drive_csv_files'] = files_list_all
    
    # Ordenar por nombre descendente (YYYY-MM) para asegurar los periodos más recientes cronológicamente
    files_list_all.sort(key=lambda x: x.get('name', ''), reverse=True)
    
    files_list = files_list_all[:6]  # Tomar solo los 6 más recientes por nombre de archivo
    
    if not files_list_all:
        st.warning("No se encontraron archivos en la carpeta de Google Drive.")
        return
    
    # Extraer período (YYYY-MM) del nombre del archivo
    def extract_period(filename):
        """Extrae el período YYYY-MM del nombre del archivo si existe."""
        import re
        match = re.search(r'(\d{4}-\d{2})', filename)
        return match.group(1) if match else filename.rsplit('.', 1)[0] if '.' in filename else filename

    # Mapeo de periodos a IDs de archivos
    period_to_id = {extract_period(f["name"]): f["id"] for f in files_list_all}
    available_periods = sorted(period_to_id.keys(), reverse=True)
    
    # Periodos seleccionados por defecto (los 6 más recientes)
    default_periods = available_periods[:6]
    
    # Inicializar el estado si no existe para el widget con key
    if 'last_selected_periods' not in st.session_state:
        st.session_state['last_selected_periods'] = default_periods
    
    # Multiselector para elegir periodos
    selected_periods = st.multiselect(
        "Selecciona los periodos a analizar:",
        options=available_periods,
        key='last_selected_periods',
        help="Los archivos seleccionados se descargarán y procesarán para el análisis."
    )
    
    # Obtener IDs de los periodos seleccionados (asegurando que sea una lista)
    file_ids_to_load = [period_to_id[p] for p in (selected_periods or []) if p in period_to_id]
    
    # Verificar si necesitamos cargar datos (asegurando que sea una lista)
    raw_processed_ids = st.session_state.get('drive_processed_ids')
    processed_ids = list(raw_processed_ids) if isinstance(raw_processed_ids, (list, tuple, set)) else []
    
    # Comparar selecciones
    needs_reload = sorted(file_ids_to_load) != sorted(processed_ids)
    
    if needs_reload:
        if st.button("🚀 Procesar periodos seleccionados", type="primary"):
            st.session_state['drive_to_load_ids'] = file_ids_to_load
            # Limpiar datos previos para forzar recarga en el siguiente bloque
            st.session_state['df_registros_horarios'] = None
            st.session_state['drive_processed_ids'] = None
            st.rerun()
        
        # Si NO hay una carga en progreso (drive_to_load_ids vacío o ya procesado)
        # y no hay datos cargados, entonces pedimos al usuario que inicie la carga.
        if not st.session_state.get('drive_to_load_ids') or st.session_state.get('drive_processed_ids') is not None:
            if not processed_ids:
                st.info("Selecciona los meses que deseas analizar y haz clic en 'Procesar periodos seleccionados'.")
                return
            else:
                st.warning("La selección ha cambiado. Haz clic en el botón para actualizar los datos con los nuevos meses.")

    # Mostrar mensaje con los meses actualmente cargados
    if processed_ids:
        loaded_periods = [p for p, fid in period_to_id.items() if fid in processed_ids]
        st.success(f"Datos cargados para {len(loaded_periods)} períodos: {', '.join(sorted(loaded_periods))}")
    
    # Traer datos previos si existen
    df_registros = st.session_state.get('df_registros_horarios')
    jornada_cached = st.session_state.get('jornada_horarios')

    # --- Carga y combinación de archivos ---
    # Verificar si ya tenemos datos cargados y procesados
    if 'drive_processed_ids' not in st.session_state or st.session_state.get('df_registros_horarios') is None:
        # Procesar archivos de Google Drive
        dfs_csv = []
        file_ids = st.session_state.get('drive_to_load_ids', [])
        
        with st.spinner('Cargando datos de Google Drive...'):
            for i, fid in enumerate(file_ids):
                try:
                    content = download_csv_file(fid)
                    df_temp = read_csv_bytes(content)
                    if not df_temp.empty:
                        columnas_requeridas = ['id_empleado', 'fecha_hora', 'tipo']
                        if all(col in df_temp.columns for col in columnas_requeridas):
                            if not pd.api.types.is_datetime64_any_dtype(df_temp['fecha_hora']):
                                df_temp['fecha_hora'] = pd.to_datetime(df_temp['fecha_hora'], errors='coerce')
                            df_temp = df_temp.dropna(subset=['fecha_hora'])
                            df_temp['id_empleado'] = df_temp['id_empleado'].astype(str)
                            if 'fecha' not in df_temp.columns:
                                df_temp['fecha'] = pd.to_datetime(df_temp['fecha_hora']).dt.date
                            dfs_csv.append(df_temp)
                except Exception as e:
                    st.warning(f"Error al procesar un archivo: {str(e)}")
            
            if dfs_csv:
                df_registros = pd.concat(dfs_csv, ignore_index=True)
                st.session_state['csv_loaded'] = {
                    'count': len(dfs_csv),
                    'total_records': len(df_registros)
                }
                # Persistir en session_state
                st.session_state['df_registros_horarios'] = df_registros
                st.session_state['drive_processed_ids'] = sorted(file_ids)
            else:
                st.error("No se pudieron cargar datos de los archivos.")
                return
    
    # Obtener datos del session_state
    df_registros = st.session_state.get('df_registros_horarios')
    if df_registros is None or df_registros.empty:
        st.warning("No hay datos disponibles para mostrar. Por favor, verifica los archivos en Google Drive.")
        return

    if df_registros is not None and not df_registros.empty:
        # Separar los DataFrames por tipo
        df_reloj = df_registros[df_registros['tipo'] == 'RELOJ'].copy()
        df_libro = df_registros[df_registros['tipo'] == 'LIBRO'].copy()
        
        # --- Eliminar registros duplicados o casi duplicados (menos de 1 minuto de diferencia) solo para RELOJ ---
        if not df_reloj.empty:
            df_reloj = df_reloj.sort_values(['id_empleado', 'fecha_hora'])
            
            # Crear una máscara para identificar registros a mantener
            mask = pd.Series(True, index=df_reloj.index)
            
            # Para cada empleado, verificar duplicados consecutivos
            for empleado in df_reloj['id_empleado'].unique():
                empleado_mask = df_reloj['id_empleado'] == empleado
                empleado_indices = df_reloj[empleado_mask].index
                
                # Calcular diferencias de tiempo entre registros consecutivos
                for i in range(1, len(empleado_indices)):
                    idx_prev = empleado_indices[i-1]
                    idx_curr = empleado_indices[i]
                    
                    tiempo_anterior = df_reloj.at[idx_prev, 'fecha_hora']
                    tiempo_actual = df_reloj.at[idx_curr, 'fecha_hora']
                    
                    # Si la diferencia es menor a 1 minuto, marcar como duplicado
                    if (tiempo_actual - tiempo_anterior) < pd.Timedelta(minutes=1):
                        mask.at[idx_curr] = False
            
            # Filtrar los registros duplicados
            duplicados = df_reloj[~mask]
            df_reloj = df_reloj[mask]
            
            # Mostrar información de depuración
            # if not duplicados.empty:
            #     st.warning(f"Se encontraron {len(duplicados)} registros de RELOJ duplicados o casi duplicados (diferencia < 1 minuto):")
            #     st.dataframe(duplicados[['id_empleado', 'fecha_hora']].sort_values(['id_empleado', 'fecha_hora']))
        
        # Volver a combinar los DataFrames
        df_registros = pd.concat([df_reloj, df_libro], ignore_index=True)
        
        # --- Procesamiento y análisis sobre el DataFrame combinado ---
        
        # --- Procesamiento y análisis sobre el DataFrame combinado ---
        # Recalcula la jornada laboral sobre el DataFrame combinado
        def sumar_intervalos(fechas):
            fechas = fechas.sort_values()
            tiempos = fechas.tolist()
            total = pd.Timedelta(0)
            for i in range(0, len(tiempos)-1, 2):
                total += tiempos[i+1] - tiempos[i]
            return total.total_seconds() / 3600  # en horas

        df_registros['fecha'] = pd.to_datetime(df_registros['fecha_hora']).dt.date
        df_registros['hora'] = pd.to_datetime(df_registros['fecha_hora']).dt.hour

        # Agrupar por empleado, fecha y tipo para mantener la información del tipo (LIBRO/RELOJ)
        jornada = (
            df_registros.groupby(['id_empleado', 'fecha', 'tipo'])['fecha_hora']
            .apply(sumar_intervalos)
            .reset_index(name='duracion_horas')
        )
        
        # Obtener el primer tipo para cada empleado y fecha (en caso de que haya múltiples tipos)
        tipo_por_dia = df_registros.groupby(['id_empleado', 'fecha'])['tipo'].first().reset_index()
        
        # Obtener min y max por empleado y fecha
        min_max = df_registros.groupby(['id_empleado', 'fecha'])['fecha_hora'].agg(['min', 'max']).reset_index()
        
        # Combinar todo en un solo DataFrame
        jornada = jornada.merge(min_max, on=['id_empleado', 'fecha'])
        jornada = jornada.merge(tipo_por_dia, on=['id_empleado', 'fecha'])
        
        jornada.rename(columns={'min': 'inicio_jornada', 'max': 'fin_jornada'}, inplace=True)
        jornada = jornada[jornada['duracion_horas'] > 0.25]

        # Guardar en session_state para persistencia entre reruns
        st.session_state['jornada_horarios'] = jornada

        # Añadir columna de nombre completo según ID
        df_registros['nombre'] = df_registros['id_empleado'].apply(
            lambda x: get_employee_display(x, st.session_state.get('incognito_mode', False))
        )
        jornada['nombre'] = jornada['id_empleado'].apply(
            lambda x: get_employee_display(x, st.session_state.get('incognito_mode', False))
        )

        # Mostrar mensaje de éxito y botón de descarga
        # col1, col2 = st.columns([1, 2])
        # with col1:
        #     st.success("¡Archivos cargados y combinados con éxito!")
        # with col2:
        #     # Crear un dataframe para la descarga (copiamos para no modificar el original)
        #     df_descarga = df_registros.copy()
        #     # Obtener el mes y año de los datos (usamos el primer registro como referencia)
        #     if not df_descarga.empty and 'fecha' in df_descarga.columns:
        #         fecha_ejemplo = pd.to_datetime(df_descarga['fecha'].iloc[0])
        #         periodo = fecha_ejemplo.strftime('%Y-%m')
        #     else:
        #         periodo = 'sin_fecha'
            
        #     # Generar timestamp actual
        #     timestamp = pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')
            
        #     # Convertir a CSV
        #     csv = df_descarga.to_csv(index=False, encoding='utf-8-sig')
            
        #     # Crear botón de descarga
        #     st.download_button(
        #         label="📥 Descargar datos completos (CSV)",
        #         data=csv,
        #         file_name=f"datos_horarios_{periodo}_{timestamp}.csv",
        #         mime='text/csv',
        #         help="Descarga los datos completos de horarios en formato CSV"
        #     )

        # # --- Comparación de Horarios Libro vs Reloj ---
        # if 'tipo' in df_registros.columns and len(df_registros['tipo'].unique()) > 1:
        #     st.header("🔍 Comparación: Horarios Libro vs Reloj")
            
        #     # Separar DataFrames por tipo
        #     df_reloj = df_registros[df_registros['tipo'] == 'RELOJ'].copy()
        #     df_libro = df_registros[df_registros['tipo'] == 'LIBRO'].copy()
            
        #     # Obtener lista de empleados con datos en ambos conjuntos
        #     empleados_comunes = list(set(df_reloj['id_empleado'].unique()) & set(df_libro['id_empleado'].unique()))
            
        #     if empleados_comunes:
        #         # Selector de empleado para la comparación
        #         empleado_comp = st.selectbox(
        #             "Selecciona un empleado para comparar:",
        #             options=empleados_comunes,
        #             format_func=lambda x: f"{ID_NOMBRE_MAP.get(x, x)} (ID: {x})"
        #         )
                
        #         # Filtrar datos para el empleado seleccionado
        #         reloj_empleado = df_reloj[df_reloj['id_empleado'] == empleado_comp].sort_values('fecha_hora')
        #         libro_empleado = df_libro[df_libro['id_empleado'] == empleado_comp].sort_values('fecha_hora')
                
        #         # Mostrar resumen
        #         col1, col2 = st.columns(2)
        #         with col1:
        #             st.metric("Registros de Reloj", len(reloj_empleado))
        #         with col2:
        #             st.metric("Registros de Libro", len(libro_empleado))
                
        #         # Mostrar tabla comparativa
        #         st.subheader("Registros Detallados")
                
        #         # Crear DataFrames con columnas consistentes para la comparación
        #         reloj_display = reloj_empleado[['fecha_hora', 'tipo']].copy()
        #         reloj_display['Origen'] = 'Reloj'
                
        #         libro_display = libro_empleado[['fecha_hora', 'tipo']].copy()
        #         libro_display['Origen'] = 'Libro'
                
        #         # Combinar y ordenar por fecha
        #         comparacion = pd.concat([reloj_display, libro_display]).sort_values('fecha_hora')
                
        #         # Resaltar diferencias
        #         def highlight_diff(row):
        #             if row['Origen'] == 'Reloj':
        #                 return ['background-color: #0000ff'] * len(row)
        #             return [''] * len(row)
                
        #         st.dataframe(
        #             comparacion.style.apply(highlight_diff, axis=1),
        #             column_config={
        #                 'fecha_hora': 'Fecha y Hora',
        #                 'tipo': 'Tipo',
        #                 'Origen': 'Origen'
        #             },
        #             use_container_width=True,
        #             height=min(400, 50 + len(comparacion) * 35)
        #         )
                
            #     # Análisis de diferencias
            #     st.subheader("Análisis de Diferencias")
                
            #     # Agrupar por fecha para comparar días completos
            #     reloj_por_dia = reloj_empleado.groupby('fecha').size().reset_index(name='conteo_reloj')
            #     libro_por_dia = libro_empleado.groupby('fecha').size().reset_index(name='conteo_libro')
                
            #     # Combinar datos
            #     comparacion_dias = pd.merge(
            #         libro_por_dia, 
            #         reloj_por_dia, 
            #         on='fecha', 
            #         how='outer'
            #     ).fillna(0)
                
            #     # Calcular diferencias
            #     comparacion_dias['diferencia'] = comparacion_dias['conteo_libro'] - comparacion_dias['conteo_reloj']
                
            #     # Mostrar días con diferencias
            #     st.write("Días con diferencias en la cantidad de registros:")
            #     st.dataframe(
            #         comparacion_dias[comparacion_dias['diferencia'] != 0]
            #         .sort_values('fecha')
            #         .style.bar(subset=['diferencia'], align='mid', color=['#d65f5f', '#5fba7d']),
            #         use_container_width=True
            #     )
                
            # else:
            #     st.warning("No se encontraron empleados con datos en ambos conjuntos (Libro y Reloj)")
        
        # --- Filtros para el Análisis ---
        st.header("Filtros de Visualización")

        col3, col4 = st.columns(2)

        lista_empleados = ['Todos'] + sorted(df_registros['id_empleado'].unique().tolist(), key=lambda x: ID_NOMBRE_MAP.get(x, x))
        empleado_seleccionado = col3.selectbox(
            "Selecciona un Empleado:",
            options=lista_empleados,
            format_func=lambda x: (
                f"{get_employee_display(x, st.session_state.get('incognito_mode', False))}" 
                if x != 'Todos' else x
            )
        )

        df_registros['año_mes'] = pd.to_datetime(df_registros['fecha_hora']).dt.to_period('M')
        meses_disponibles = sorted(df_registros['año_mes'].unique().astype(str).tolist())
        mes_seleccionado = col4.selectbox(
            "Selecciona un Mes:",
            options=['Todos'] + meses_disponibles
        )

        # Filtrar los dataframes según la selección
        df_filtrado = df_registros.copy()
        if empleado_seleccionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['id_empleado'] == empleado_seleccionado]
        if mes_seleccionado != 'Todos':
            df_filtrado = df_filtrado[df_filtrado['año_mes'] == mes_seleccionado]

        df_jornada_filtrada = jornada.copy()
        if empleado_seleccionado != 'Todos':
            df_jornada_filtrada = df_jornada_filtrada[df_jornada_filtrada['id_empleado'] == empleado_seleccionado]
        if mes_seleccionado != 'Todos':
            df_jornada_filtrada = df_jornada_filtrada[
                pd.to_datetime(df_jornada_filtrada['inicio_jornada']).dt.to_period('M').astype(str) == mes_seleccionado
            ]

        # --- Análisis y Gráficos ---
        st.subheader("Análisis de Horas Trabajadas")

        if empleado_seleccionado == 'Todos':
            # --- Vista general para todos los empleados ---
            st.subheader("Resumen General del Personal")
            
            # Calcular métricas generales
            total_empleados = len(df_jornada_filtrada['id_empleado'].unique())
            total_dias = len(df_jornada_filtrada['fecha'].unique())
            horas_promedio = df_jornada_filtrada['duracion_horas'].mean()
            
            # Mostrar métricas generales
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Empleados", total_empleados)
            with col2:
                st.metric("Días analizados", total_dias)
            with col3:
                st.metric("Horas promedio por día", f"{horas_promedio:.1f} hs")
            
            # --- Tabla resumen por empleado ---
            st.subheader("Resumen por Empleado")
            
            # Calcular métricas por empleado
            resumen_empleados = df_jornada_filtrada.groupby(['id_empleado', 'nombre']).agg(
                dias_trabajados=('fecha', 'nunique'),
                horas_totales=('duracion_horas', 'sum'),
                horas_promedio=('duracion_horas', 'mean'),
                jornada_mas_larga=('duracion_horas', 'max'),
                jornada_mas_corta=('duracion_horas', 'min')
            ).reset_index()
            
            # Ordenar por nombre de empleado
            resumen_empleados = resumen_empleados.sort_values('nombre')
            
            # Formatear las columnas
            resumen_empleados['horas_promedio'] = resumen_empleados['horas_promedio'].round(2)
            resumen_empleados['horas_totales'] = resumen_empleados['horas_totales'].round(2)
            
            # Mostrar la tabla con estilos condicionales
            def color_jornada(val):
                if val < 7.5:
                    return 'color: #e74c3c'  # Rojo para menos de 7.5 horas
                elif val > 8.5:
                    return 'color: #f39c12'   # Naranja para más de 8.5 horas
                else:
                    return 'color: #2ecc71'   # Verde para entre 7.5 y 8.5 horas
            
            # Aplicar estilos a la tabla
            styled_df = resumen_empleados.style.map(
                color_jornada, 
                subset=['horas_promedio', 'jornada_mas_larga', 'jornada_mas_corta']
            ).format({
                'horas_promedio': '{:.2f} hs',
                'horas_totales': '{:.2f} hs',
                'jornada_mas_larga': '{:.2f} hs',
                'jornada_mas_corta': '{:.2f} hs',
            })
            
            # Mostrar la tabla con scroll
            st.dataframe(
                styled_df,
                column_config={
                    'id_empleado': 'ID',
                    'nombre': 'Empleado',
                    'dias_trabajados': 'Días Trabajados',
                    'horas_totales': 'Horas Totales',
                    'horas_promedio': 'Horas Promedio',
                    'jornada_mas_larga': 'Jornada Más Larga',
                    'jornada_mas_corta': 'Jornada Más Corta'
                },
                width='stretch',
                height=min(400, 100 + len(resumen_empleados) * 35)
            )
            
            # --- Gráfico de distribución de horas ---
            st.subheader("Distribución de Horas por Día")
            
            # Crear gráfico de cajas por empleado
            fig_distribucion = px.box(
                df_jornada_filtrada,
                x='nombre',
                y='duracion_horas',
                color='nombre',
                labels={'duracion_horas': 'Horas trabajadas', 'nombre': 'Empleado'},
                title=f"Distribución de horas trabajadas por empleado ({pd.to_datetime(mes_seleccionado).strftime('%B %Y').title()})" if mes_seleccionado != 'Todos' else 'Distribución de horas trabajadas por empleado',
                template='plotly_white',
                range_y=[0, 16]  # Establecer rango del eje Y entre 0 y 16 horas
            )
            
            # Añadir línea de referencia de 8 horas
            fig_distribucion.add_hline(
                y=8,
                line_dash="dash",
                line_color="red",
                annotation_text="8 hs ideales",
                annotation_position="top right"
            )
            
            # Ajustar diseño del gráfico
            fig_distribucion.update_layout(
                showlegend=True,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=-0.6,  # Posición vertical de la leyenda (negativo para moverla abajo)
                    xanchor="center",
                    x=0.5,   # Centrar la leyenda horizontalmente
                    title=None,
                    font=dict(size=10)  # Tamaño de fuente más pequeño para la leyenda
                ),
                xaxis_title=None,
                yaxis_title='Horas trabajadas',
                height=600,  # Aumentar la altura para acomodar la leyenda
                margin=dict(l=20, r=20, t=40, b=100),  # Aumentar margen inferior para la leyenda
                boxmode='group',
                boxgap=0.2,
                boxgroupgap=0.3
            )
            
            # Configurar para mostrar solo los boxplots sin puntos y con mejor ancho
            fig_distribucion.update_traces(
                boxpoints=False,  # No mostrar puntos individuales
                showlegend=True,
                width=0.6,       # Ancho de los boxplots
                line=dict(width=1.5)  # Grosor del borde de los boxplots
            )
            
            # Asegurar que el gráfico sea interactivo
            fig_distribucion.update_layout(
                hovermode='closest',
                clickmode='event+select'
            )
            
            st.plotly_chart(fig_distribucion, width='stretch')
            
        else:
            display_name = get_employee_display(empleado_seleccionado, st.session_state.get('incognito_mode', False))
            st.subheader(f"Horas trabajadas por día - {display_name}")
            
            if not df_jornada_filtrada.empty:
                # Crear una copia para no modificar el DataFrame original
                df_plot = df_jornada_filtrada.copy()
                
                # Asegurarse de que la columna 'fecha' sea datetime
                df_plot['fecha_dt'] = pd.to_datetime(df_plot['fecha'])
                
                # Ordenar por fecha
                df_plot = df_plot.sort_values('fecha_dt')
                
                # Formatear la fecha para incluir el día de la semana en español
                dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                df_plot['fecha_formateada'] = df_plot['fecha_dt'].apply(
                    lambda x: f"{dias_semana[x.weekday()]} {x.strftime('%d/%m/%Y')}"
                )
                
                # Obtener datos de ausencias y vacaciones y filtrar por mes/empleado
                df_compensatorios = obtener_compensatorios_por_fecha()
                df_vacaciones_plot = obtener_vacaciones_por_fecha()
                if not df_compensatorios.empty:
                    # Filtrar por empleado si está seleccionado (tolerante a ID o Nombre)
                    if empleado_seleccionado != 'Todos':
                        allowed_ids = {empleado_seleccionado}
                        nombre_emp = ID_NOMBRE_MAP.get(empleado_seleccionado)
                        if nombre_emp:
                            allowed_ids.add(nombre_emp)
                        df_compensatorios = df_compensatorios[df_compensatorios['id_empleado'].isin(allowed_ids)]
                    
                    # Filtrar por mes seleccionado
                    if mes_seleccionado != 'Todos':
                        # Convertir el mes seleccionado a datetime para comparación
                        mes_seleccionado_dt = pd.to_datetime(mes_seleccionado)
                        # Filtrar compensatorios que caigan en el mes seleccionado
                        df_compensatorios = df_compensatorios[
                            (df_compensatorios['fecha_dt'].dt.month == mes_seleccionado_dt.month) &
                            (df_compensatorios['fecha_dt'].dt.year == mes_seleccionado_dt.year)
                        ]
                if df_vacaciones_plot is not None and not df_vacaciones_plot.empty:
                    if empleado_seleccionado != 'Todos':
                        allowed_ids_v = {empleado_seleccionado}
                        nombre_emp_v = ID_NOMBRE_MAP.get(empleado_seleccionado)
                        if nombre_emp_v:
                            allowed_ids_v.add(nombre_emp_v)
                        df_vacaciones_plot = df_vacaciones_plot[df_vacaciones_plot['id_empleado'].isin(allowed_ids_v)]
                    if mes_seleccionado != 'Todos':
                        mes_seleccionado_dt = pd.to_datetime(mes_seleccionado)
                        df_vacaciones_plot = df_vacaciones_plot[
                            (df_vacaciones_plot['fecha_dt'].dt.month == mes_seleccionado_dt.month) &
                            (df_vacaciones_plot['fecha_dt'].dt.year == mes_seleccionado_dt.year)
                        ]
                    # if df_vacaciones_plot.empty:
                    #     st.info("No hay vacaciones para mostrar según los filtros seleccionados.")
                
                # Asegurarse de que tenemos la columna 'tipo' correcta (puede ser 'tipo_x' o 'tipo_y')
                tipo_col = 'tipo_x' if 'tipo_x' in df_plot.columns else 'tipo_y' if 'tipo_y' in df_plot.columns else 'tipo'
                
                # Asegurarse de que los tipos sean consistentes
                df_plot[tipo_col] = df_plot[tipo_col].replace({'LIBRO': 'LIBRO', 'RELOJ': 'RELOJ'})
                
                # Asegurarse de que tenemos datos para todos los tipos (LIBRO, RELOJ y COMPENSATORIO) para cada fecha
                from itertools import product
                # Generar rango completo de fechas para mostrar días sin datos (fines de semana, etc.)
                if mes_seleccionado != 'Todos':
                    try:
                        mes_dt = pd.to_datetime(mes_seleccionado)
                        start_date = mes_dt.replace(day=1).date()
                        # Obtener el último día del mes
                        if hasattr(mes_dt, 'days_in_month'):
                            end_date = mes_dt.replace(day=mes_dt.days_in_month).date()
                        else:
                            import calendar
                            last_day = calendar.monthrange(mes_dt.year, mes_dt.month)[1]
                            end_date = mes_dt.replace(day=last_day).date()
                        fechas_unicas = pd.date_range(start=start_date, end=end_date).date
                    except Exception:
                        fechas_unicas = df_plot['fecha'].unique() if not df_plot.empty else []
                elif not df_plot.empty:
                    # Usar el rango de fechas presentes en df_plot (que ya está filtrado por los periodos subidos)
                    all_fechas = df_plot['fecha'].tolist()
                    min_date = min(all_fechas)
                    max_date = max(all_fechas)
                    fechas_unicas = pd.date_range(start=min_date, end=max_date).date
                else:
                    fechas_unicas = df_plot['fecha'].unique() if not df_plot.empty else []
                
                # Asegurar que sean fechas únicas y ordenadas
                fechas_unicas = sorted(list(set(fechas_unicas)))
                
                # Definir los tipos de registro
                tipos = ['LIBRO', 'RELOJ']
                
                # Crear un DataFrame con todas las combinaciones posibles
                combinaciones = pd.DataFrame(list(product(fechas_unicas, tipos)), 
                                          columns=['fecha', 'tipo_combinado'])
                
                # Hacer merge con los datos existentes
                df_completo = pd.merge(combinaciones, df_plot, 
                                     left_on=['fecha', 'tipo_combinado'], 
                                     right_on=['fecha', tipo_col], 
                                     how='left')
                
                # Rellenar valores faltantes con 0
                df_completo['duracion_horas'] = df_completo['duracion_horas'].fillna(0)
                
                # Combinar datos de horarios y compensatorios
                if not df_compensatorios.empty:
                    # Preparar datos de compensatorios para el merge
                    if 'tipo_detalle' not in df_compensatorios.columns:
                        df_compensatorios['tipo_detalle'] = ''
                    df_compensatorios_plot = df_compensatorios.rename(columns={
                        'tipo': 'tipo_combinado',
                        'fecha_dt': 'fecha_dt',
                        'fecha_formateada': 'fecha_formateada'
                    })
                    
                    # Añadir columnas faltantes
                    for col in ['inicio_jornada', 'fin_jornada', 'minutos_trabajados', 'hora_entrada', 'hora_salida']:
                        if col not in df_compensatorios_plot.columns:
                            df_compensatorios_plot[col] = None
                    
                    # Asegurar columna 'tipo_detalle' en df_completo antes de concatenar
                    if 'tipo_detalle' not in df_completo.columns:
                        df_completo['tipo_detalle'] = ''
                    # Preparar frame a agregar con mismas columnas y orden que df_completo
                    to_add = df_compensatorios_plot.reindex(columns=df_completo.columns)
                    # Evitar concat con frames vacíos o totalmente NA para prevenir FutureWarning
                    if not to_add.empty and not to_add.isna().all(axis=None):
                        df_completo = pd.concat([df_completo, to_add], ignore_index=True)
                if df_vacaciones_plot is not None and not df_vacaciones_plot.empty:
                    df_vacaciones_plot = df_vacaciones_plot.rename(columns={
                        'tipo': 'tipo_combinado',
                        'fecha_dt': 'fecha_dt',
                        'fecha_formateada': 'fecha_formateada'
                    })
                    for col in ['inicio_jornada', 'fin_jornada', 'minutos_trabajados', 'hora_entrada', 'hora_salida']:
                        if col not in df_vacaciones_plot.columns:
                            df_vacaciones_plot[col] = None
                    if 'tipo_detalle' not in df_vacaciones_plot.columns:
                        df_vacaciones_plot['tipo_detalle'] = ''
                    # Preparar frame a agregar con mismas columnas y orden que df_completo
                    to_add_vac = df_vacaciones_plot.reindex(columns=df_completo.columns)
                    # Evitar concat con frames vacíos o totalmente NA para prevenir FutureWarning
                    if not to_add_vac.empty and not to_add_vac.isna().all(axis=None):
                        df_completo = pd.concat([df_completo, to_add_vac], ignore_index=True)

                # --- Agregar Feriados ---
                try:
                    years_in_plot = pd.to_datetime(list(fechas_unicas)).year.unique()
                    feriados_dict = {}
                    for y in years_in_plot:
                        feriados_dict.update(get_feriados_argentina(y))
                    
                    df_manual = st.session_state.get("df_feriados_manuales", pd.DataFrame())
                    if not df_manual.empty and 'Fecha' in df_manual.columns:
                        for _, row in df_manual.iterrows():
                            try:
                                f_dt = pd.to_datetime(row['Fecha'], errors='coerce', dayfirst=True, format='mixed')
                                if pd.notna(f_dt):
                                    f_str = f_dt.strftime('%Y-%m-%d')
                                    label = row.get('Motivo (Opcional)') or row.get('Motivo') or 'Feriado/Asueto'
                                    feriados_dict[f_str] = label
                            except: continue

                    rows_feriados = []
                    for f_str, f_name in feriados_dict.items():
                        f_date = datetime.strptime(f_str, '%Y-%m-%d').date()
                        if f_date in fechas_unicas:
                            rows_feriados.append({
                                'fecha': f_date,
                                'fecha_dt': pd.to_datetime(f_date),
                                'duracion_horas': 8.0,
                                'tipo_combinado': 'FERIADOS',
                                'tipo_detalle': f_name,
                                'es_salida_campo': False
                            })
                    
                    if rows_feriados:
                        df_feriados_plot = pd.DataFrame(rows_feriados)
                        to_add_fer = df_feriados_plot.reindex(columns=df_completo.columns)
                        if not to_add_fer.empty and not to_add_fer.isna().all(axis=None):
                            df_completo = pd.concat([df_completo, to_add_fer], ignore_index=True)
                except Exception as e:
                    st.warning(f"No se pudieron cargar los feriados para el gráfico: {e}")

                # Ordenar por fecha y tipo
                df_completo = df_completo.sort_values(['fecha', 'tipo_combinado'])
                
                # Identificar días con salida a campo (2 registros de reloj y más de 6 horas trabajadas)
                if empleado_seleccionado != 'Todos':
                    # Crear un DataFrame con los registros de reloj del empleado seleccionado
                    df_reloj_empleado = df_registros[
                        (df_registros['id_empleado'] == empleado_seleccionado) & 
                        (df_registros['tipo'] == 'RELOJ')
                    ].copy()
                    
                    # Contar registros por fecha
                    registros_por_dia = df_reloj_empleado.groupby('fecha').size()
                    
                    # Obtener horas trabajadas por día desde df_jornada_filtrada
                    horas_por_dia = df_jornada_filtrada[['fecha', 'duracion_horas']].drop_duplicates()
                    
                    # Identificar días con salida a campo
                    dias_salida_campo = []
                    for fecha, conteo in registros_por_dia.items():
                        if conteo == 2:  # Solo considerar días con exactamente 2 registros
                            # Obtener las horas trabajadas para este día
                            horas_dia = horas_por_dia[horas_por_dia['fecha'] == fecha]['duracion_horas']
                            if not horas_dia.empty and float(horas_dia.iloc[0]) > 7:  # Más de 7 horas trabajadas
                                dias_salida_campo.append(fecha)
                    
                    # Añadir columna para resaltar en el gráfico
                    df_completo['es_salida_campo'] = df_completo['fecha'].isin(dias_salida_campo)
                else:
                    df_completo['es_salida_campo'] = False
                
                df_plot = df_completo.copy()
                # Asegurar que todas las filas tengan datos de fecha procesados para el gráfico (incluyendo días vacíos)
                df_plot['fecha_dt'] = pd.to_datetime(df_plot['fecha'])
                dias_semana = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']
                df_plot['fecha_formateada'] = df_plot['fecha_dt'].apply(
                    lambda x: f"{dias_semana[x.weekday()]} {x.strftime('%d/%m/%Y')}"
                )
                
                # Asegurar columna para detalles de ausencias
                if 'tipo_detalle' not in df_plot.columns:
                    df_plot['tipo_detalle'] = ''
                # Calcular detalle final para AUSENCIAS con fallback (por horas o día completo)
                def _calc_detalle_final(row):
                    if row.get('tipo_combinado') == 'AUSENCIAS':
                        det = (row.get('tipo_detalle') or '').strip()
                        h_ini = row.get('hora_inicio') or ''
                        h_fin = row.get('hora_fin') or ''
                        if det:
                            return det
                        if h_ini and h_fin:
                            return f"Por horas ({h_ini}-{h_fin})"
                        return "Día completo"
                    if row.get('tipo_combinado') in ['VACACIONES', 'FERIADOS']:
                        return (row.get('tipo_detalle') or '').strip()
                    return ''
                df_plot['tipo_detalle_final'] = df_plot.apply(_calc_detalle_final, axis=1)

                # --- Cálculo de Base para Apilamiento (Stacking Manual) --- 
                # Apilamos en Cluster de "Registros": RELOJ -> AUSENCIAS -> VACACIONES -> FERIADOS
                # El LIBRO siempre tiene base 0 y estará en su propia columna lateral
                df_plot['base_horas'] = 0.0
                df_plot['duracion_horas'] = df_plot['duracion_horas'].fillna(0.0)
                
                for fecha in df_plot['fecha'].unique():
                    mask_day = df_plot['fecha'] == fecha
                    day_data = df_plot[mask_day]
                    
                    
                    val_reloj = day_data[day_data['tipo_combinado'] == 'RELOJ']['duracion_horas'].sum()
                    current_base = val_reloj
                    # Apilar solo AUSENCIAS y VACACIONES sobre RELOJ
                    for t in ['AUSENCIAS', 'VACACIONES']:
                        mask_type = mask_day & (df_plot['tipo_combinado'] == t)
                        if mask_type.any():
                            df_plot.loc[mask_type, 'base_horas'] = current_base
                            current_base += df_plot.loc[mask_type, 'duracion_horas'].sum()
                    # FERIADOS y LIBRO mantienen base_horas = 0.0 (inicializado arriba)

                # -------- Gráfico integrado: LIBRO / RELOJ / AUSENCIAS / VACACIONES --------
                fechas_unicas = sorted(df_plot['fecha'].unique()) if not df_plot.empty else []
                n_fechas = len(fechas_unicas)

                if n_fechas > 30:
                    step = max(1, n_fechas // 15)
                    tick_vals = fechas_unicas[::step]
                    tick_text = [f"{pd.to_datetime(d).strftime('%d/%m')}" for d in tick_vals]
                else:
                    tick_vals = fechas_unicas
                    tick_text = [f"{pd.to_datetime(d).strftime('%d/%m')}" for d in tick_vals]

                fig_historial = px.bar(
                    df_plot,
                    x='fecha',
                    y='duracion_horas',
                    color='tipo_combinado',
                    barmode='group',
                    title='Horas trabajadas, ausencias y vacaciones por día',
                    labels={'fecha': 'Fecha', 'duracion_horas': 'Horas', 'tipo_combinado': 'Tipo'},
                    color_discrete_map={
                        'LIBRO': '#1f77b4',
                        'RELOJ': '#ff7f0e',
                        'AUSENCIAS': '#9b59b6',
                        'VACACIONES': '#16a085',
                        'FERIADOS': '#f1c40f'
                    },
                    category_orders={'fecha': fechas_unicas, 'tipo_combinado': ["FERIADOS", "LIBRO", "RELOJ", "AUSENCIAS", "VACACIONES"]},
                    template='plotly_white',
                    custom_data=['fecha_formateada', 'tipo_combinado', 'es_salida_campo', 'tipo_detalle_final'],
                    base='base_horas'
                )

                # Ajustar posiciones (offset) y anchos para solapamiento descentrado
                # FERIADOS un poco a la izquierda, LIBRO un poco a la derecha, RELOJ al centro/frente
                for tr in fig_historial.data:
                    t_name = getattr(tr, 'name', '')
                    if t_name == 'FERIADOS':
                        tr.width = 0.6
                        tr.offset = -0.15  # Se extiende de -0.15 a 0.45
                        tr.opacity = 0.4
                    elif t_name == 'LIBRO':
                        tr.width = 0.6
                        tr.offset = -0.1  # Se extiende de -0.1 a 0.5
                        tr.opacity = 1
                    elif t_name in ['RELOJ', 'AUSENCIAS', 'VACACIONES']:
                        tr.width = 0.4
                        tr.offset = -0.2  # Se extiende de -0.2 a 0.2 (CENTRO)
                        tr.opacity = 1.0
                        
                        # Resaltar RELOJ de fines de semana (Sáb/Dom) con naranja rojizo
                        if t_name == 'RELOJ':
                            colors = []
                            for date_val in tr.x:
                                d_dt = pd.to_datetime(date_val)
                                # Lunes=0, Domingo=6 -> Sáb(5), Dom(6)
                                if d_dt.weekday() >= 5:
                                    colors.append('#d35400') # Naranja rojizo
                                else:
                                    colors.append('#ff7f0e') # Naranja normal
                            tr.marker.color = colors
                
                # Configurar el diseño del gráfico
                fig_historial.update_layout(
                    xaxis={
                        'type': 'category',
                        'categoryorder': 'array',
                        'categoryarray': fechas_unicas,
                        'tickangle': -45,
                        'tickmode': 'array',
                        'tickvals': tick_vals,
                        'ticktext': tick_text,
                        'tickfont': {'size': 10}  # Reducir tamaño de fuente
                    },
                    margin=dict(l=20, r=20, t=40, b=100),  # Ajustar márgenes para consistencia
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='lightgray',
                        gridwidth=0.5,
                        title_text='Horas Trabajadas',
                        fixedrange=False
                    ),
                    plot_bgcolor='rgba(0,0,0,0)',
                    legend_title='Tipo de Registro',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                # Configurar los bordes de las barras
                for trace in fig_historial.data:
                    # Asegurar que el marcador y la línea estén inicializados
                    if not hasattr(trace, 'marker'):
                        trace.marker = {}
                    if 'line' not in trace.marker:
                        trace.marker.line = {}
                    
                    # Inicializar listas para los bordes
                    line_widths = [1] * len(trace.x)
                    line_colors = ['rgba(0,0,0,0)'] * len(trace.x)
                    
                    # Verificar si hay datos personalizados
                    if hasattr(trace, 'customdata') and trace.customdata is not None:
                        for i, custom_data in enumerate(trace.customdata):
                            if i < len(line_widths) and len(custom_data) > 2 and custom_data[2]:  # es_salida_campo es True
                                pass
                    
                    # Aplicar los bordes
                    trace.marker.line.width = line_widths
                    trace.marker.line.color = line_colors
                
                # Asegurar que las barras se posicionen correctamente
                fig_historial.update_layout(
                    xaxis={
                        'type': 'category',
                        'categoryorder': 'array',
                        'categoryarray': sorted(df_plot['fecha'].unique()) if not df_plot.empty else []
                    }
                )
                
                # Actualizar los textos de hover para mostrar información detallada
                for trace in fig_historial.data:
                    hover_texts = []
                    
                    if hasattr(trace, 'customdata') and trace.customdata is not None:
                        for i, custom_data in enumerate(trace.customdata):
                            if i < len(trace.y):
                                fecha_texto = custom_data[0] if len(custom_data) > 0 else str(trace.x[i])
                                tipo = custom_data[1] if len(custom_data) > 1 else 'DESCONOCIDO'
                                horas = trace.y[i]
                                detalle = custom_data[3] if len(custom_data) > 3 else ''
                                
                                if len(custom_data) > 2 and custom_data[2]:  # es_salida_campo es True
                                    hover_text = (
                                        f'<b>{fecha_texto}</b><br>' +
                                        (f'Tipo: {detalle} ({tipo})<br>' if (tipo in ['AUSENCIAS','VACACIONES']) and detalle else f'Tipo: {tipo}<br>') +
                                        f'Horas: {horas:.2f}<br>' +
                                        '<b>Posible salida al campo</b><br>'
                                    )
                                else:
                                    if tipo in ['AUSENCIAS','VACACIONES', 'FERIADOS']:
                                        label = detalle if detalle else tipo
                                        hover_text = f'<b>{fecha_texto}</b><br>Tipo: {label} ({tipo})<br>Horas: {horas:.2f}'
                                    else:
                                        hover_text = f'<b>{fecha_texto}</b><br>Tipo: {tipo}<br>Horas: {horas:.2f}'
                                
                                hover_texts.append(hover_text)
                    
                    # Aplicar los textos de hover si hay datos
                    if hover_texts:
                        trace.hovertemplate = '%{customdata[0]}<extra></extra>'
                        trace.customdata = [[ht] for ht in hover_texts]
                    
                    # Ajustar el ancho de las barras para mejor visualización
                    trace.width = 0.4
                    
                    # Asegurar que todas las barras tengan un borde por defecto
                    if not hasattr(trace, 'showlegend') or trace.showlegend is not False:
                        # Solo aplicar bordes a las barras, no a los ítems de la leyenda
                        if not hasattr(trace.marker, 'line'):
                            trace.marker.line = dict(width=1, color='DarkSlateGrey')
                        elif isinstance(trace.marker.line, dict):
                            if 'width' not in trace.marker.line:
                                trace.marker.line['width'] = 1
                            if 'color' not in trace.marker.line:
                                trace.marker.line['color'] = 'DarkSlateGrey'
                
                
                # Añadir línea horizontal en 8 horas
                fig_historial.add_hline(
                    y=8,
                    line_dash="dash",
                    line_color="red",
                    annotation_text="8 hs ideales",
                    annotation_position="top right",
                    annotation_font_size=12,
                    annotation_font_color="red",
                    opacity=0.7
                )
                
                st.plotly_chart(fig_historial, width='stretch')
                
                # --- Gráfico de diferencias ---
                st.subheader("Diferencia diaria (LIBRO - RELOJ)")
                
                # Crear un DataFrame con las diferencias
                df_diferencias = df_completo.pivot(
                    index='fecha', 
                    columns='tipo_combinado', 
                    values='duracion_horas'
                ).reset_index()
                
                # Calcular la diferencia LIBRO - RELOJ solo si ambos valores existen y son mayores a cero
                if 'LIBRO' in df_diferencias.columns and 'RELOJ' in df_diferencias.columns:
                    # Inicializar la columna de diferencia como NaN
                    df_diferencias['diferencia'] = float('nan')
                    
                    # Calcular la diferencia solo para filas donde ambos valores son positivos
                    mask = (df_diferencias['LIBRO'] > 0) & (df_diferencias['RELOJ'] > 0)
                    df_diferencias.loc[mask, 'diferencia'] = df_diferencias.loc[mask, 'LIBRO'] - df_diferencias.loc[mask, 'RELOJ']
                    
                    # Contar cuántas diferencias válidas hay
                    diferencias_validas = mask.sum()
                    
                    # Verificar si hay registros impares para cada fecha
                    df_diferencias['tiene_impares'] = False
                    
                    # Obtener los conteos de registros por fecha y tipo
                    if empleado_seleccionado != 'Todos':
                        # Contar registros por fecha y tipo para el empleado seleccionado
                        conteo_registros = df_registros[df_registros['id_empleado'] == empleado_seleccionado].groupby(
                            ['fecha', 'tipo']
                        ).size().unstack(fill_value=0)
                        
                        # Verificar si hay algún tipo con conteo impar para cada fecha
                        for fecha in df_diferencias['fecha']:
                            if fecha in conteo_registros.index:
                                # Verificar si hay algún tipo con conteo impar
                                if any(conteo_registros.loc[fecha] % 2 != 0):
                                    df_diferencias.loc[df_diferencias['fecha'] == fecha, 'tiene_impares'] = True
                    
                    # Si no hay diferencias válidas, mostrar mensaje pero continuar con el resto del código
                    if diferencias_validas == 0:
                        st.warning("No hay días con ambos valores de LIBRO y RELOJ mayores a cero para calcular diferencias.")
                        sin_diferencias_validas = True
                    else:
                        st.success(f"Se calcularon diferencias para {diferencias_validas} días con ambos valores de LIBRO y RELOJ.")
                        sin_diferencias_validas = False
                    
                    # Solo mostrar el gráfico y métricas si hay diferencias válidas
                    if not sin_diferencias_validas:
                        # Crear la columna para el color basado en la diferencia y si hay impares
                        def get_color(row):
                            if row['tiene_impares']:
                                return 'Registros impares'
                            elif row['diferencia'] > 0:
                                return 'Positiva'
                            elif row['diferencia'] < 0:
                                return 'Negativa'
                            else:
                                return 'Cero'
                        
                        df_diferencias['tipo_diferencia'] = df_diferencias.apply(get_color, axis=1)
                        
                        # Filtrar días sin registros impares para las estadísticas
                        df_sin_impares = df_diferencias[~df_diferencias['tiene_impares']]
                        total_dias = len(df_diferencias)
                        dias_con_impares = df_diferencias['tiene_impares'].sum()
                        
                        # Crear el gráfico de barras para las diferencias
                        fig_diferencias = px.bar(
                            df_diferencias,
                            x='fecha',
                            y='diferencia',
                            color='tipo_diferencia',
                            title='Diferencia entre horas LIBRO y RELOJ (LIBRO - RELOJ)',
                            labels={
                                'fecha': 'Fecha',
                                'diferencia': 'Diferencia (horas)',
                                'tipo_diferencia': 'Tipo de Diferencia'
                            },
                            color_discrete_map={
                                'Positiva': '#2ecc71',
                                'Negativa': '#e74c3c',
                                'Cero': '#7f8c8d',
                                'Registros impares': '#f39c12'
                            },
                            category_orders={
                                'fecha': sorted(df_diferencias['fecha'].unique())
                            },
                            template='plotly_white'
                        )
                        
                        # Configurar el diseño del gráfico
                        # Calcular el espaciado de ticks basado en el número de fechas
                        fechas_unicas = sorted(df_diferencias['fecha'].unique())
                        n_fechas = len(fechas_unicas)
                        
                        # Mostrar una etiqueta cada cierta cantidad de días dependiendo de cuántas fechas hay
                        if n_fechas > 30:  # Si hay muchas fechas, mostrar una cada 7 días
                            step = max(1, n_fechas // 15)  # Asegurar al menos 1 y aproximadamente 15 etiquetas
                            tick_vals = fechas_unicas[::step]
                            tick_text = [f"{pd.to_datetime(d).strftime('%d/%m')}" for d in tick_vals]
                        else:
                            tick_vals = fechas_unicas
                            tick_text = [f"{pd.to_datetime(d).strftime('%d/%m')}" for d in tick_vals]
                        
                        fig_diferencias.update_layout(
                            xaxis={
                                'type': 'category',
                                'categoryorder': 'array',
                                'categoryarray': fechas_unicas,
                                'tickangle': -45,
                                'tickmode': 'array',
                                'tickvals': tick_vals,
                                'ticktext': tick_text,
                                'tickfont': {'size': 10}  # Reducir tamaño de fuente
                            },
                            margin=dict(l=20, r=20, t=40, b=100),  # Margen aumentado para las etiquetas
                            yaxis=dict(
                                showgrid=True,
                                gridcolor='lightgray',
                                gridwidth=0.5,
                                title_text='Diferencia (horas)',
                                range=[-1, 1],
                                fixedrange=False
                            ),
                            legend_title='Tipo de Diferencia',
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            ),
                            plot_bgcolor='rgba(0,0,0,0)',
                            paper_bgcolor='rgba(0,0,0,0)',
                            height=400,
                            showlegend=True
                        )
                        
                        # Configurar el hover
                        fig_diferencias.update_traces(
                            hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Diferencia: %{y:.2f} horas<extra></extra>',
                            width=0.4,
                            marker=dict(
                                line=dict(
                                    width=1,
                                    color='DarkSlateGrey'
                                )
                            )
                        )
                        
                        # Añadir línea horizontal en 0
                        fig_diferencias.add_hline(
                            y=0,
                            line_dash="solid",
                            line_color="black",
                            opacity=0.7
                        )
                        
                        # Mostrar el gráfico
                        st.plotly_chart(fig_diferencias, width='stretch')
                        
                        # Mostrar métricas
                        col1, col2, col3, col4, col5 = st.columns(5)
                        
                        # Filtrar solo las diferencias válidas (no nulas)
                        diferencias_validas_metricas = df_sin_impares['diferencia'].dropna()
                        
                        with col1:
                            if not diferencias_validas_metricas.empty:
                                promedio = diferencias_validas_metricas.mean()
                                st.metric("Diferencia promedio", f"{promedio:+.2f} horas")
                            else:
                                st.metric("Diferencia promedio", "-")
                                
                        with col5:
                            if not diferencias_validas_metricas.empty:
                                suma_acumulada = diferencias_validas_metricas.sum()
                                st.metric("Diferencia acumulada", f"{suma_acumulada:+.2f} horas")
                            else:
                                st.metric("Diferencia acumulada", "-")
                                
                        with col2:
                            if not diferencias_validas_metricas.empty:
                                st.metric("Máx. diferencia positiva", f"{diferencias_validas_metricas.max():.2f} horas")
                            else:
                                st.metric("Máx. diferencia positiva", "-")
                                
                        with col3:
                            if not diferencias_validas_metricas.empty:
                                st.metric("Máx. diferencia negativa", f"{diferencias_validas_metricas.min():.2f} horas")
                            else:
                                st.metric("Máx. diferencia negativa", "-")
                                
                        with col4:
                            st.metric("Días con registros impares", f"{dias_con_impares} de {total_dias}", 
                                   delta=None, delta_color="inverse" if dias_con_impares > 0 else "normal")
                # --- Boxplots de distribución por tipo de registro ---
                st.subheader("Distribución de horas por tipo de registro")
                
                # Crear dos columnas para los boxplots
                col1, col2 = st.columns(2)
                
                with col1:
                    # Boxplot para LIBRO - excluyendo días con 0 horas
                    df_libro = df_completo[(df_completo['tipo_combinado'] == 'LIBRO') & 
                                         (df_completo['duracion_horas'] > 0)]
                    if not df_libro.empty:
                        fig_box_libro = px.box(
                            df_libro,
                            y='duracion_horas',
                            title='Distribución de horas - LIBRO',
                            labels={'duracion_horas': 'Horas trabajadas'},
                            color_discrete_sequence=['#1f77b4'],
                            template='plotly_white'
                        )
                        fig_box_libro.update_layout(
                            showlegend=False,
                            yaxis_title='Horas',
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        # Añadir línea en 8 horas
                        fig_box_libro.add_hline(
                            y=8,
                            line_dash="dash",
                            line_color="red",
                            annotation_text="8 hs ideales",
                            annotation_position="top right"
                        )
                        st.plotly_chart(fig_box_libro, width='stretch')
                    else:
                        st.warning("No hay datos de LIBRO para mostrar")
                
                with col2:
                    # Boxplot para RELOJ (excluyendo horas trabajadas = 0)
                    df_reloj = df_completo[(df_completo['tipo_combinado'] == 'RELOJ') & 
                                         (df_completo['duracion_horas'] > 0)]
                    if not df_reloj.empty:
                        fig_box_reloj = px.box(
                            df_reloj,
                            y='duracion_horas',
                            title='Distribución de horas - RELOJ',
                            labels={'duracion_horas': 'Horas trabajadas'},
                            color_discrete_sequence=['#ff7f0e'],
                            template='plotly_white'
                        )
                        fig_box_reloj.update_layout(
                            showlegend=False,
                            yaxis_title='Horas',
                            height=400,
                            margin=dict(l=20, r=20, t=40, b=20)
                        )
                        # Añadir línea en 8 horas
                        fig_box_reloj.add_hline(
                            y=8,
                            line_dash="dash",
                            line_color="red",
                            annotation_text="8 hs ideales",
                            annotation_position="top right"
                        )
                        st.plotly_chart(fig_box_reloj, width='stretch')
                    else:
                        st.warning("No hay datos de RELOJ para mostrar")
            else:
                st.info("No hay datos para mostrar en el historial de jornadas para este filtro.")

            st.subheader("Jornadas del empleado seleccionado")
            
            # Mostrar todos los registros del empleado seleccionado
            if empleado_seleccionado != 'Todos':
                # Filtrar registros del empleado seleccionado (acepta ID o Nombre)
                allowed_ids = {empleado_seleccionado}
                nombre_emp_det = ID_NOMBRE_MAP.get(empleado_seleccionado)
                if nombre_emp_det:
                    allowed_ids.add(nombre_emp_det)
                registros_empleado = df_registros[df_registros['id_empleado'].isin(allowed_ids)].copy()
                
                # Agregar columnas de fecha y año_mes para agrupar/filtrar
                registros_empleado['fecha'] = pd.to_datetime(registros_empleado['fecha_hora']).dt.date
                registros_empleado['año_mes'] = pd.to_datetime(registros_empleado['fecha_hora']).dt.to_period('M').astype(str)
                if mes_seleccionado != 'Todos':
                    registros_empleado = registros_empleado[registros_empleado['año_mes'] == mes_seleccionado]
                
                # Ordenar por fecha y hora
                registros_empleado = registros_empleado.sort_values('fecha_hora')
                
                # Mostrar los registros agrupados por fecha
                st.subheader("Registros diarios")
                
                # Ordenar por fecha y hora (primero) y luego por tipo
                registros_empleado = registros_empleado.sort_values(['fecha_hora', 'tipo'])
                
                # Agrupar por fecha manteniendo el orden
                for fecha, grupo in registros_empleado.groupby('fecha'):
                    # Asegurar que el grupo también esté ordenado por fecha y hora
                    grupo = grupo.sort_values('fecha_hora')
                    num_registros = len(grupo)
                    # Contar registros por tipo
                    conteo_tipos = grupo['tipo'].value_counts().to_dict()
                    conteo_texto = ", ".join([f"{k}: {v}" for k, v in conteo_tipos.items()])
                    
                    # Determinar si hay número impar de registros
                    es_impar = any(v % 2 != 0 for v in conteo_tipos.values())
                    
                    # # Mostrar advertencia si hay número impar de registros en algún tipo
                    # if es_impar:
                    #     st.markdown(
                    #         f"""
                    #         <div style='background-color: #1e1e1e; border-left: 5px solid #f44336; 
                    #                     padding: 0.5em; margin: 0.5em 0; border-radius: 0.3em;'>
                    #             ⚠️ <strong>¡Atención!</strong> Número impar de registros: {conteo_texto}
                    #         </div>
                    #         """,
                    #         unsafe_allow_html=True
                    #     )
                    
                    # Mostrar el expander con el contador de registros
                    with st.expander(f"📅 {fecha.strftime('%d/%m/%Y')} - Total: {num_registros} ({conteo_texto}){' ⚠️' if es_impar else ''}"):
                        # Mostrar resumen de la jornada si existe
                        jornada_dia = df_jornada_filtrada[df_jornada_filtrada['fecha'] == pd.Timestamp(fecha)]
                        if not jornada_dia.empty:
                            st.write(f"⏱️ **Duración total:** {jornada_dia['duracion_horas'].iloc[0]:.2f} horas")
                            st.write(f"🕒 **Inicio:** {jornada_dia['inicio_jornada'].iloc[0].strftime('%H:%M')}")
                            st.write(f"🏁 **Fin:** {jornada_dia['fin_jornada'].iloc[0].strftime('%H:%M')}")
                        
                        # Ordenar registros por fecha y hora antes de mostrar
                        registros_ordenados = grupo.sort_values('fecha_hora')
                        
                        # Función para aplicar formato a los registros
                        def formatear_registro(fila):
                            if fila['tipo'] == 'LIBRO':
                                return f"📘 {fila['fecha_hora'].strftime('%d/%m/%Y %H:%M')}"
                            else:
                                return f"⏱️ {fila['fecha_hora'].strftime('%d/%m/%Y %H:%M')}"
                        
                        # Crear una copia para no modificar el original
                        df_mostrar = registros_ordenados.copy()
                        df_mostrar['Registro'] = df_mostrar.apply(formatear_registro, axis=1)
                        
                        # Mostrar los registros con formato
                        for _, fila in df_mostrar.iterrows():
                            if fila['tipo'] == 'LIBRO':
                                st.markdown(
                                    f"<div style='background-color: #1a3a5e; padding: 0.5em; margin: 0.2em 0; border-radius: 0.3em; color: white; border-left: 4px solid #4a90e2;'>"
                                    f"📘 <strong>LIBRO</strong> - {fila['fecha_hora'].strftime('%d/%m/%Y %H:%M')}"
                                    "</div>",
                                    unsafe_allow_html=True
                                )
                            else:
                                st.markdown(
                                    f"<div style='background-color: #5c3d1a; padding: 0.5em; margin: 0.2em 0; border-radius: 0.3em; color: white; border-left: 4px solid #e6a23c;'>"
                                    f"⏱️ <strong>RELOJ</strong> - {fila['fecha_hora'].strftime('%d/%m/%Y %H:%M')}"
                                    "</div>",
                                    unsafe_allow_html=True
                                )
            # --- Mostrar los DataFrames completos al final de la página (solo en modo desarrollador) ---
            # if st.checkbox("Mostrar datos completos (modo desarrollador)"):
            #     st.header("Datos completos")
            #     st.subheader("Registros originales")
            #     st.dataframe(df_registros)
            #     st.subheader("Jornadas calculadas")
            #     st.dataframe(jornada)