import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber

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

        df['id_empleado'] = df['id_empleado'].astype(str)
        df['fecha_hora'] = pd.to_datetime(df['fecha_hora'])
        df['fecha'] = df['fecha_hora'].dt.date
        df['hora'] = df['fecha_hora'].dt.hour

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
    with pdfplumber.open(path_pdf) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if table:
                for row in table[1:]:  # Salta encabezado
                    rows.append(row)
    # Ajusta los nombres de columna según el PDF
    df_pdf = pd.DataFrame(rows, columns=["Date", "ID Number", "Name", "Time", "Status", "Verification"])
    # Unifica formato con el DataFrame principal
    df_pdf['id_empleado'] = df_pdf['ID Number'].astype(str)
    df_pdf['fecha_hora'] = pd.to_datetime(df_pdf['Date'] + ' ' + df_pdf['Time'])
    df_pdf['fecha'] = pd.to_datetime(df_pdf['Date']).dt.date
    df_pdf['hora'] = pd.to_datetime(df_pdf['Time']).dt.hour
    # Puedes agregar columnas dummy para compatibilidad
    df_pdf['col_3'] = None
    df_pdf['col_4'] = None
    df_pdf['col_5'] = None
    return df_pdf[['id_empleado', 'fecha_hora', 'col_3', 'col_4', 'col_5', 'fecha', 'hora']]

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

def seccion_horarios(client, personal_list):
    """
    Sección de Streamlit para analizar y visualizar los horarios del personal.
    Permite cargar archivos de texto y PDF, procesar los datos y mostrar gráficos interactivos.
    """

    # --- Interfaz de Usuario (UI) ---
    st.subheader("📊 Analizador de Horarios del Personal")
    # st.markdown("Carga tus archivos de texto y PDF para visualizar tendencias y patrones de asistencia.")

    # Widgets para subir archivos
    col1, col2 = st.columns(2)
    archivo_subido = col1.file_uploader(
        "Registros de Estación Central (.txt, .csv)",
        type=['txt', 'csv']
    )
    archivo_pdf = col2.file_uploader(
        "Registros de SDECo (.pdf)",
        type=['pdf']
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

    if df_registros is not None and not df_registros.empty:
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

        jornada = (
            df_registros.groupby(['id_empleado', 'fecha'])['fecha_hora']
            .apply(sumar_intervalos)
            .reset_index(name='duracion_horas')
        )
        min_max = df_registros.groupby(['id_empleado', 'fecha'])['fecha_hora'].agg(['min', 'max']).reset_index()
        jornada = jornada.merge(min_max, on=['id_empleado', 'fecha'])
        jornada.rename(columns={'min': 'inicio_jornada', 'max': 'fin_jornada'}, inplace=True)
        jornada = jornada[jornada['duracion_horas'] > 0.25]

        # Añadir columna de nombre completo según ID
        df_registros['nombre'] = df_registros['id_empleado'].map(ID_NOMBRE_MAP).fillna(df_registros['id_empleado'])
        jornada['nombre'] = jornada['id_empleado'].map(ID_NOMBRE_MAP).fillna(jornada['id_empleado'])

        st.success("¡Archivos cargados y combinados con éxito!")


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
        # st.header("1. Análisis de Tendencias")
        st.subheader("Distribución de la Duración de la Jornada Laboral")
        # st.markdown("Este diagrama de caja muestra cómo varían las horas trabajadas por día. Es útil para ver la consistencia en las jornadas y detectar días con horas extra o jornadas inusualmente cortas.")
        fig_jornada = px.box(
            df_jornada_filtrada,
            x='nombre',
            y='duracion_horas',
            color='nombre',
            title='Duración de la Jornada Laboral por Empleado (en horas)',
            labels={'nombre': 'Empleado', 'duracion_horas': 'Horas Trabajadas'},
            template='plotly_white'
        )
        fig_jornada.add_shape(
            type='line',
            x0=-0.5, x1=len(df_jornada_filtrada['nombre'].unique())-0.5,
            y0=8, y1=8,
            line=dict(color='red', width=2, dash='dash'),
        )
        fig_jornada.add_annotation(
            xref="paper", x=1.01, y=8, yref="y",
            text="8 hs ideales",
            showarrow=False,
            font=dict(color="red")
        )
        st.plotly_chart(fig_jornada, use_container_width=True)

        if empleado_seleccionado != 'Todos':
            st.subheader(f"Historial de Jornadas para {ID_NOMBRE_MAP.get(empleado_seleccionado, empleado_seleccionado)}")
            # st.markdown("Visualiza la duración de la jornada de un empleado a lo largo del tiempo.")
            if not df_jornada_filtrada.empty:
                df_jornada_filtrada = df_jornada_filtrada.copy()
                df_jornada_filtrada['fecha'] = df_jornada_filtrada['fecha'].astype(str)
                fig_historial = px.bar(
                    df_jornada_filtrada,
                    x='fecha',
                    y='duracion_horas',
                    title=f'Horas trabajadas por día - {ID_NOMBRE_MAP.get(empleado_seleccionado, empleado_seleccionado)}',
                    labels={'fecha': 'Fecha', 'duracion_horas': 'Horas Trabajadas'},
                    template='plotly_white'
                )
                fig_historial.add_annotation(
                    xref="paper", x=1.01, y=8, yref="y",
                    text="8 hs ideales",
                    showarrow=False,
                    font=dict(color="red")
                )
                st.plotly_chart(fig_historial, use_container_width=True)
            else:
                st.info("No hay datos para mostrar en el historial de jornadas para este filtro.")
            
            st.subheader("Jornadas del empleado seleccionado")
            st.dataframe(df_jornada_filtrada)
        else:
            # --- Mostrar los DataFrames completos al final de la página ---
            st.header("Datos completos")
            st.subheader("Registros originales")
            st.dataframe(df_registros)
            st.subheader("Jornadas calculadas")
            st.dataframe(jornada)