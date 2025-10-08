import os
import sys
import streamlit as st
import pandas as pd

# Asegurar que podamos importar utilidades desde ui_sections/horarios.py
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    # Importamos las funciones existentes para evitar duplicar lógica
    from ui_sections.horarios import (
        cargar_y_procesar_datos,
        leer_pdf_query,
        leer_excel_horarios,
    )
    HAS_HELPERS = True
except Exception as e:
    HAS_HELPERS = False
    IMPORT_ERROR = e

st.set_page_config(page_title="Utilidades", page_icon="🧰")
st.title("🧰 Utilidades: Carga y Merge de Registros")

st.markdown(
    """
    Esta utilidad permite:
    - Cargar archivos individuales (txt/csv de Estación Central, PDF de SDECo, planilla Excel) y combinarlos.
    - Cargar uno o varios CSV exportados previamente y concatenarlos.
    """
)

if not HAS_HELPERS:
    st.error(
        "No fue posible importar las funciones desde `ui_sections/horarios.py`. "
        "Verifica que el proyecto tenga la carpeta `ui_sections/` accesible.\\n\\n"
        f"Detalle: {IMPORT_ERROR}"
    )
    st.stop()

# --- Widgets para subir archivos ---
st.markdown("### Cargar archivos individuales")
col1, col2, col3 = st.columns(3)
archivo_subido = col1.file_uploader(
    "Registros de Estación Central (.txt, .csv)",
    type=["txt", "csv"],
    key="util_estacion_central",
)
archivo_pdf = col2.file_uploader(
    "Registros de SDECo (.pdf)",
    type=["pdf"],
    key="util_sdeco_pdf",
)
archivo_excel = col3.file_uploader(
    "Registros de Planilla (.xlsx)",
    type=["xlsx"],
    key="util_planilla_excel",
)

# --- Carga y combinación de archivos ---
df_registros = None

# Primero manejamos los archivos individuales
if archivo_subido is not None or archivo_pdf is not None or archivo_excel is not None:
    if archivo_subido is not None:
        df_registros, _ = cargar_y_procesar_datos(archivo_subido)

    if archivo_pdf is not None:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo_pdf.read())
            tmp_path = tmp.name
        df_pdf = leer_pdf_query(tmp_path)
        if df_pdf is not None:
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

# Resultado y descarga
if df_registros is not None and not df_registros.empty:
    st.success("¡Archivos cargados y combinados con éxito!")

    # Preparar descarga
    df_descarga = df_registros.copy()
    if "fecha" in df_descarga.columns and not df_descarga["fecha"].isna().all():
        try:
            fecha_ejemplo = pd.to_datetime(df_descarga["fecha"].iloc[0])
            periodo = fecha_ejemplo.strftime("%Y-%m")
        except Exception:
            periodo = "sin_fecha"
    else:
        periodo = "sin_fecha"

    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    csv = df_descarga.to_csv(index=False, encoding="utf-8-sig")

    st.download_button(
        label="📥 Descargar datos combinados (CSV)",
        data=csv,
        file_name=f"datos_horarios_{periodo}_{timestamp}.csv",
        mime="text/csv",
        help="Descarga los datos combinados en formato CSV",
    )