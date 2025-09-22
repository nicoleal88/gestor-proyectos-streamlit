import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import warnings
import re
from datetime import datetime, timedelta
from datetime import datetime, timedelta

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
    Solo incluye compensatorios con horas de inicio y fin definidas.
    Devuelve un DataFrame con los compensatorios por fecha y empleado.
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
        
        # Filtrar solo compensatorios con horas de inicio y fin definidas
        compensados = compensados[
            compensados['Desde hora'].notna() &
            compensados['Hasta hora'].notna() &
            (compensados['Desde hora'] != '') &
            (compensados['Hasta hora'] != '')
        ]
        
        if compensados.empty:
            return pd.DataFrame()
            
        # Procesar cada registro de compensatorio
        registros = []
        for _, row in compensados.iterrows():
            try:
                # Obtener la duración en horas
                hora_inicio = pd.to_datetime(row['Desde hora']).time()
                hora_fin = pd.to_datetime(row['Hasta hora']).time()
                
                # Calcular duración en horas
                inicio_dt = datetime.combine(datetime.today(), hora_inicio)
                fin_dt = datetime.combine(datetime.today(), hora_fin)
                duracion = (fin_dt - inicio_dt).total_seconds() / 3600  # Convertir a horas
                
                # Obtener ID del empleado desde el nombre (asumiendo que está en el formato 'Apellido, Nombre')
                nombre_empleado = row['Apellido, Nombres']
                id_empleado = next((k for k, v in ID_NOMBRE_MAP.items() if v == nombre_empleado), None)
                
                if id_empleado:
                    registros.append({
                        'fecha': row['Desde fecha'],
                        'fecha_dt': pd.Timestamp(row['Desde fecha']),
                        'id_empleado': id_empleado,
                    'tipo': 'COMPENSATORIO',
                    'duracion_horas': duracion,
                    'fecha_formateada': row['Desde fecha'].strftime('%a %d-%b-%Y'),
                    'hora_inicio': hora_inicio.strftime('%H:%M'),
                    'hora_fin': hora_fin.strftime('%H:%M')
                })
            except Exception as e:
                st.warning(f"Error al procesar compensatorio para {row.get('Apellido, Nombres', 'empleado')}: {str(e)}")
                continue
                
        return pd.DataFrame(registros)
        
    except Exception as e:
        st.error(f"Error al procesar compensatorios: {str(e)}")
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
    '87': 'Villar, Sebastián'
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

def seccion_horarios(client, personal_list):
    """
    Sección de Streamlit para analizar y visualizar los horarios del personal.
    Permite cargar archivos de texto y PDF, procesar los datos y mostrar gráficos interactivos.
    """

    # --- Interfaz de Usuario (UI) ---
    st.subheader("📊 Analizador de Horarios del Personal")
    # st.markdown("Carga tus archivos de texto y PDF para visualizar tendencias y patrones de asistencia.")

    # Widgets para subir archivos
    col1, col2 ,col3 = st.columns(3)
    archivo_subido = col1.file_uploader(
        "Registros de Estación Central (.txt, .csv)",
        type=['txt', 'csv']
    )
    archivo_pdf = col2.file_uploader(
        "Registros de SDECo (.pdf)",
        type=['pdf']
    )
    archivo_excel = col3.file_uploader(
        "Registros de Planilla (.xlsx)",
        type=['xlsx']
    )
    df_registros = None

    # --- Carga y combinación de archivos ---
    if archivo_subido is not None:
        df_registros, _ = cargar_y_procesar_datos(archivo_subido)

    if archivo_pdf is not None:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo_pdf.read())
            tmp_path = tmp.name
        df_pdf = leer_pdf_query(tmp_path)
        if df_registros is not None:
            df_registros = pd.concat([df_registros, df_pdf], ignore_index=True)
        else:
            df_registros = df_pdf

    if archivo_excel is not None:
        df_excel = leer_excel_horarios(archivo_excel)
        if df_registros is not None:
            df_registros = pd.concat([df_registros, df_excel], ignore_index=True)
        else:
            df_registros = df_excel

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

        # Añadir columna de nombre completo según ID
        df_registros['nombre'] = df_registros['id_empleado'].map(ID_NOMBRE_MAP).fillna(df_registros['id_empleado'])
        jornada['nombre'] = jornada['id_empleado'].map(ID_NOMBRE_MAP).fillna(jornada['id_empleado'])

        st.success("¡Archivos cargados y combinados con éxito!")

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
            format_func=lambda x: f"{ID_NOMBRE_MAP[x]} (ID: {x})" if x in ID_NOMBRE_MAP else (x if x == 'Todos' else f"ID: {x}")
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
            styled_df = resumen_empleados.style.applymap(
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
                use_container_width=True,
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
                title='Distribución de horas trabajadas por empleado',
                template='plotly_white'
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
            
            st.plotly_chart(fig_distribucion, use_container_width=True)
            
        else:
            st.subheader(f"Horas trabajadas por día - {ID_NOMBRE_MAP.get(empleado_seleccionado, empleado_seleccionado)}")
            
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
                    lambda x: f"{dias_semana[x.weekday()]} {x.strftime('%d-%b-%Y')}"
                )
                
                # Obtener datos de compensatorios para el empleado
                df_compensatorios = obtener_compensatorios_por_fecha()
                if not df_compensatorios.empty and empleado_seleccionado != 'Todos':
                    df_compensatorios = df_compensatorios[df_compensatorios['id_empleado'] == empleado_seleccionado]
                
                # Asegurarse de que tenemos la columna 'tipo' correcta (puede ser 'tipo_x' o 'tipo_y')
                tipo_col = 'tipo_x' if 'tipo_x' in df_plot.columns else 'tipo_y' if 'tipo_y' in df_plot.columns else 'tipo'
                
                # Asegurarse de que los tipos sean consistentes
                df_plot[tipo_col] = df_plot[tipo_col].replace({'LIBRO': 'LIBRO', 'RELOJ': 'RELOJ'})
                
                # Asegurarse de que tenemos datos para todos los tipos (LIBRO, RELOJ y COMPENSATORIO) para cada fecha
                from itertools import product
                fechas_unicas = df_plot['fecha'].unique()
                
                # Si hay compensatorios, añadir sus fechas únicas
                if not df_compensatorios.empty:
                    fechas_compensatorios = df_compensatorios['fecha'].unique()
                    fechas_unicas = pd.unique(list(fechas_unicas) + list(fechas_compensatorios))
                
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
                    df_compensatorios_plot = df_compensatorios.rename(columns={
                        'tipo': 'tipo_combinado',
                        'fecha_dt': 'fecha_dt',
                        'fecha_formateada': 'fecha_formateada'
                    })
                    
                    # Añadir columnas faltantes
                    for col in ['inicio_jornada', 'fin_jornada', 'minutos_trabajados', 'hora_entrada', 'hora_salida']:
                        if col not in df_compensatorios_plot.columns:
                            df_compensatorios_plot[col] = None
                    
                    # Combinar con datos existentes
                    df_completo = pd.concat([
                        df_completo,
                        df_compensatorios_plot[df_completo.columns.intersection(df_compensatorios_plot.columns)]
                    ], ignore_index=True)
                
                # Ordenar por fecha y tipo
                df_completo = df_completo.sort_values(['fecha', 'tipo_combinado'])
                
                # Crear el gráfico de barras agrupado
                fig_historial = px.bar(
                    df_completo,
                    x='fecha',
                    y='duracion_horas',
                    color='tipo_combinado',
                    barmode='group',  # Esto coloca las barras una al lado de la otra
                    title=f'Comparación de horas trabajadas por día',
                    labels={
                        'fecha': 'Fecha', 
                        'duracion_horas': 'Horas Trabajadas',
                        'tipo_combinado': 'Tipo de Registro'
                    },
                    color_discrete_map={
                        'LIBRO': '#1f77b4',  # Azul para LIBRO
                        'RELOJ': '#ff7f0e',  # Naranja para RELOJ
                        'COMPENSATORIO': '#2ecc71'  # Verde para COMPENSATORIO
                    },
                    category_orders={
                        'fecha': sorted(df_completo['fecha'].unique()),
                        'tipo_combinado': ["LIBRO", "RELOJ", "COMPENSATORIO"]
                    },
                    template='plotly_white',
                    custom_data=['fecha_formateada', 'tipo_combinado']
                )
                
                # Asegurar que las barras se agrupen correctamente
                fig_historial.update_layout(
                    xaxis={
                        'type': 'category',
                        'categoryorder': 'array',
                        'categoryarray': sorted(df_plot['fecha'].unique())
                    },
                    # Mejorar el espaciado entre grupos de barras
                    bargap=0.15,
                    bargroupgap=0.1
                )
                
                # Actualizar el formato del hover
                fig_historial.update_traces(
                    hovertemplate='<b>%{customdata[0]}</b><br>Tipo: %{customdata[1]}<br>Horas: %{y:.2f}<extra></extra>',
                    # Aumentar el ancho de las barras para mejor visualización
                    width=0.4,
                    # Añadir borde a las barras para mejor contraste
                    marker=dict(
                        line=dict(
                            width=1,
                            color='DarkSlateGrey'
                        )
                    )
                )
                
                # Ajustar el diseño del gráfico
                fig_historial.update_layout(
                    xaxis_tickangle=-45,
                    xaxis_title=None,
                    legend_title='Tipo de Registro',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1,
                        title_font=dict(size=12),
                        font=dict(size=11)
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    xaxis=dict(
                        showgrid=False,
                        tickmode='array',
                        tickvals=df_plot['fecha'].unique(),
                        ticktext=[f"{d.strftime('%d/%m')}" for d in pd.to_datetime(df_plot['fecha'].unique())]
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='lightgray',
                        gridwidth=0.5,
                        title_text='Horas Trabajadas'
                    ),
                    height=400
                )
                
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
                
                st.plotly_chart(fig_historial, use_container_width=True)
                
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
                    if diferencias_validas == 0:
                        st.warning("No hay días con ambos valores de LIBRO y RELOJ mayores a cero para calcular diferencias.")
                    else:
                        st.success(f"Se calcularon diferencias para {diferencias_validas} días con ambos valores de LIBRO y RELOJ.")
                    
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
                    fig_diferencias.update_layout(
                        xaxis={
                            'type': 'category',
                            'categoryorder': 'array',
                            'categoryarray': sorted(df_diferencias['fecha'].unique()),
                            'tickangle': -45,
                            'tickmode': 'array',
                            'tickvals': df_diferencias['fecha'].unique(),
                            'ticktext': [f"{d.strftime('%d/%m')}" for d in pd.to_datetime(df_diferencias['fecha'].unique())]
                        },
                        yaxis=dict(
                            showgrid=True,
                            gridcolor='lightgray',
                            gridwidth=0.5,
                            title_text='Diferencia (horas)',
                            range=[-1, 1],  # Establecer rango fijo de -1 a 1
                            fixedrange=False  # Evitar zoom/desplazamiento
                        ),
                        legend_title='Tipo de Diferencia',
                        legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=1
                        ),
                        margin=dict(l=20, r=20, t=40, b=20),
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
                    st.plotly_chart(fig_diferencias, use_container_width=True)
                    
                    # Mostrar métricas
                    col1, col2, col3, col4, col5 = st.columns(5)
                    
                    # Filtrar solo las diferencias válidas (no nulas)
                    diferencias_validas = df_sin_impares['diferencia'].dropna()
                    
                    with col1:
                        if not diferencias_validas.empty:
                            # Calcular promedio solo con diferencias válidas
                            promedio = diferencias_validas.mean()
                            st.metric("Diferencia promedio", f"{promedio:+.2f} horas")
                        else:
                            st.metric("Diferencia promedio", "N/A")
                            
                    with col5:
                        if not diferencias_validas.empty:
                            # Calcular suma acumulada de diferencias
                            suma_acumulada = diferencias_validas.sum()
                            st.metric("Diferencia acumulada", f"{suma_acumulada:+.2f} horas")
                        else:
                            st.metric("Diferencia acumulada", "N/A")
                    with col2:
                        if not df_sin_impares.empty:
                            st.metric("Máx. diferencia positiva", f"{df_sin_impares['diferencia'].max():.2f} horas")
                        else:
                            st.metric("Máx. diferencia positiva", "N/A")
                    with col3:
                        if not df_sin_impares.empty:
                            st.metric("Máx. diferencia negativa", f"{df_sin_impares['diferencia'].min():.2f} horas")
                        else:
                            st.metric("Máx. diferencia negativa", "N/A")
                    with col4:
                        st.metric("Días con registros impares", f"{dias_con_impares} de {total_dias}", 
                               delta=None, delta_color="inverse" if dias_con_impares > 0 else "normal")
            else:
                st.info("No hay datos para mostrar en el historial de jornadas para este filtro.")
            
            # --- Boxplots de distribución por tipo de registro ---
            st.subheader("Distribución de horas por tipo de registro")
            
            # Crear dos columnas para los boxplots
            col1, col2 = st.columns(2)
            
            with col1:
                # Boxplot para LIBRO
                df_libro = df_completo[df_completo['tipo_combinado'] == 'LIBRO']
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
                    st.plotly_chart(fig_box_libro, use_container_width=True)
                else:
                    st.warning("No hay datos de LIBRO para mostrar")
            
            with col2:
                # Boxplot para RELOJ
                df_reloj = df_completo[df_completo['tipo_combinado'] == 'RELOJ']
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
                    st.plotly_chart(fig_box_reloj, use_container_width=True)
                else:
                    st.warning("No hay datos de RELOJ para mostrar")

            st.subheader("Jornadas del empleado seleccionado")
            
            # Mostrar todos los registros del empleado seleccionado
            if empleado_seleccionado != 'Todos':
                # Filtrar registros del empleado seleccionado
                registros_empleado = df_registros[df_registros['id_empleado'] == empleado_seleccionado].copy()
                
                # Agregar columna de fecha para agrupar
                registros_empleado['fecha'] = pd.to_datetime(registros_empleado['fecha_hora']).dt.date
                
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
            if st.checkbox("Mostrar datos completos (modo desarrollador)"):
                st.header("Datos completos")
                st.subheader("Registros originales")
                st.dataframe(df_registros)
                st.subheader("Jornadas calculadas")
                st.dataframe(jornada)