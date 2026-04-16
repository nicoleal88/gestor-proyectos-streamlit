import os
import sys
import streamlit as st
import pandas as pd
from datetime import datetime, time as datetime_time
import tempfile

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from ui_sections.horarios import (
        cargar_y_procesar_datos,
        leer_pdf_query,
        leer_excel_horarios,
        ID_NOMBRE_MAP,
    )
    HAS_HELPERS = True
except Exception as e:
    HAS_HELPERS = False
    IMPORT_ERROR = e


def get_nombre_empleado(id_empleado):
    """Convierte ID de empleado a nombre legible."""
    return ID_NOMBRE_MAP.get(str(id_empleado), f"ID: {id_empleado}")


def detectar_registros_impares(df):
    """Detecta días con número impar de registros por empleado."""
    if df is None or df.empty:
        return pd.DataFrame()

    cols_req = ['id_empleado', 'fecha_hora']
    if not all(col in df.columns for col in cols_req):
        return pd.DataFrame()

    df_work = df.copy()
    if 'fecha' not in df_work.columns:
        df_work['fecha'] = pd.to_datetime(df_work['fecha_hora']).dt.date

    conteo = df_work.groupby(['id_empleado', 'fecha']).size().reset_index(name='cant_registros')
    impares = conteo[conteo['cant_registros'] % 2 == 1].copy()
    impares = impares.sort_values(['id_empleado', 'fecha'])

    return impares


def sugerir_hora_faltante(registros_del_dia):
    """Sugiere la hora faltante basada en los registros existentes."""
    if registros_del_dia is None or len(registros_del_dia) == 0:
        return None, "Sin registros"

    horas = sorted(registros_del_dia['fecha_hora'].tolist())
    n = len(horas)

    h7 = datetime_time(7, 0)
    h9 = datetime_time(9, 0)
    h12 = datetime_time(12, 0)
    h13 = datetime_time(13, 0)
    h14 = datetime_time(14, 0)
    h15 = datetime_time(15, 0)
    h18 = datetime_time(18, 0)
    h19 = datetime_time(19, 0)

    if n == 1:
        hora = horas[0].time()
        if hora < h12:
            sugerencia = "Entrada mañana (7:00)"
            hora_sug = datetime_time(8, 0)
        elif hora < h14:
            sugerencia = "Salida mañana o Entrada tarde"
            if hora < h13:
                hora_sug = datetime_time(13, 0)
            else:
                hora_sug = datetime_time(14, 0)
        else:
            sugerencia = "Salida tarde (18:00)"
            hora_sug = datetime_time(18, 0)
        return hora_sug, sugerencia

    elif n == 3:
        primera = horas[0].time()
        ultima = horas[-1].time()
        if primera >= h7 and primera <= h9:
            if ultima < h14:
                return datetime_time(13, 0), "Salida mañana (13:00)"
            else:
                return datetime_time(14, 0), "Entrada tarde (14:00)"
        return datetime_time(8, 0), "Entrada mañana (8:00) - verificar"

    elif n == 5:
        return datetime_time(8, 0), "Entrada mañana (8:00) - verificar"

    elif n == 7:
        return datetime_time(14, 0), "Entrada tarde (14:0) - verificar"

    return None, "No se puede determinar"


def aplicar_correccion_olvido(df, id_empleado, fecha, hora_faltante, tipo_registro):
    """Agrega un registro de olvido al dataframe."""
    if df is None:
        return None

    fecha_dt = pd.to_datetime(fecha)
    fecha_hora_dt = datetime.combine(fecha_dt.date(), hora_faltante)

    nuevo_registro = pd.DataFrame([{
        'id_empleado': str(id_empleado),
        'fecha_hora': fecha_hora_dt,
        'col_3': None,
        'col_4': None,
        'col_5': None,
        'fecha': fecha_dt.date(),
        'hora': hora_faltante.hour,
        'tipo': 'OLVIDO'
    }])

    return pd.concat([df, nuevo_registro], ignore_index=True)


def eliminar_duplicados(df, tolerancia_minutos=1):
    """Elimina registros duplicados o casi duplicados (menos de X minutos de diferencia).
    Retorna: (df_limpio, df_pares_diferencia)
    """
    if df is None or df.empty:
        return df, pd.DataFrame()

    df_work = df.sort_values(['id_empleado', 'fecha_hora']).copy()
    mask = pd.Series(True, index=df_work.index)
    pares_diff = []

    for empleado in df_work['id_empleado'].unique():
        empleado_mask = df_work['id_empleado'] == empleado
        empleado_indices = df_work[empleado_mask].index.tolist()

        for i in range(1, len(empleado_indices)):
            idx_prev = empleado_indices[i-1]
            idx_curr = empleado_indices[i]

            tiempo_anterior = df_work.at[idx_prev, 'fecha_hora']
            tiempo_actual = df_work.at[idx_curr, 'fecha_hora']

            if (tiempo_actual - tiempo_anterior) < pd.Timedelta(minutes=tolerancia_minutos):
                mask.at[idx_curr] = False
                diff = (tiempo_actual - tiempo_anterior).total_seconds()
                nombre = get_nombre_empleado(empleado)
                fecha = tiempo_actual.date()
                pares_diff.append({
                    'nombre': nombre,
                    'fecha': fecha,
                    'hora_original': tiempo_anterior.strftime('%H:%M'),
                    'hora_duplicado': tiempo_actual.strftime('%H:%M'),
                    'diferencia_seg': diff
                })

    df_limpio = df_work[mask].copy()
    df_pares = pd.DataFrame(pares_diff) if pares_diff else pd.DataFrame()

    return df_limpio, df_pares


def page():
    st.subheader("🧰 Utilidades: Carga y Merge de Registros")

    st.markdown(
        """
        Esta utilidad permite:
        - Cargar archivos de horarios (txt/csv, PDF, Excel) y combinarlos.
        - Detectar y corregir registros faltantes (olvidos).
        - Eliminar registros duplicados.
        """
    )

    if not HAS_HELPERS:
        st.error(
            "No fue posible importar las funciones desde `ui_sections/horarios.py`. "
            f"Detalle: {IMPORT_ERROR}"
        )
        st.stop()

    if 'df_registros_temp' not in st.session_state:
        st.session_state.df_registros_temp = None

    tab1, tab2, tab3, tab4 = st.tabs([
        "📂 Cargar archivos",
        "🧹 Duplicados",
        "🔧 Corrección olvidos",
        "📥 Descargar datos"
    ])

    with tab1:
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

        if st.button("📥 Cargar todos los archivos"):
            df_registros = None

            if archivo_subido is not None:
                df_registros, _ = cargar_y_procesar_datos(archivo_subido)

            if archivo_pdf is not None:
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

            if df_registros is not None and not df_registros.empty:
                st.session_state.df_registros_temp = df_registros
                st.success(f"✅ Datos cargados: {len(st.session_state.df_registros_temp)} registros")
                st.rerun()
            else:
                st.warning("No se cargaron archivos")

        if st.session_state.df_registros_temp is not None and not st.session_state.df_registros_temp.empty:
            st.markdown("---")
            st.markdown("### 📊 Resumen de datos cargados")
            st.info(f"Total de registros en memoria: **{len(st.session_state.df_registros_temp)}**")
            st.info(f"Tipos de registro: {st.session_state.df_registros_temp['tipo'].value_counts().to_dict()}")

    with tab2:
        st.markdown("### 🧹 Eliminación de duplicados")
        
        if st.session_state.df_registros_temp is None or st.session_state.df_registros_temp.empty:
            st.info("Carga archivos primero en la pestaña 'Cargar archivos'")
        else:
            st.info(f"Registros actuales: {len(st.session_state.df_registros_temp)}")
            
            tol = st.slider(
                "Tolerancia (minutos)",
                min_value=1,
                max_value=5,
                value=1,
                help="Registros con diferencia menor a esta tolerancia serán considerados duplicados"
            )
            
            df_limpio, df_pares = eliminar_duplicados(st.session_state.df_registros_temp, tol)
            
            if df_pares.empty:
                st.success("✅ No se encontraron duplicados")
            else:
                st.warning(f"Se encontraron {len(df_pares)} pares de registros duplicados")
                
                with st.expander("Ver duplicados (pares de horarios)"):
                    st.dataframe(df_pares[['nombre', 'fecha', 'hora_original', 'hora_duplicado', 'diferencia_seg']])
                
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    if st.button("✅ Eliminar duplicados"):
                        st.session_state.df_registros_temp = df_limpio
                        st.success(f"✅ Se eliminaron {len(df_pares)} duplicados. Total: {len(df_limpio)} registros")
                        st.rerun()
                with col_d2:
                    st.caption(f"Sin cambios: {len(st.session_state.df_registros_temp)} registros")

    with tab3:
        st.markdown("### 🔧 Corrección de olvidos")

        if st.session_state.df_registros_temp is None or st.session_state.df_registros_temp.empty:
            st.info("Carga archivos primero en la pestaña 'Cargar archivos'")
        else:
            impares = detectar_registros_impares(st.session_state.df_registros_temp)

            if impares.empty:
                st.success("✅ No se detectaron días con registros impares")
            else:
                st.markdown(f"**Días con registros impares:** {len(impares)}")

                idx_seleccion = st.selectbox(
                    "Seleccionar registro a corregir:",
                    range(len(impares)),
                    format_func=lambda i: f"{get_nombre_empleado(impares.iloc[i]['id_empleado'])} - {impares.iloc[i]['fecha']} ({impares.iloc[i]['cant_registros']} registros)"
                )

                if idx_seleccion is not None:
                    emp = impares.iloc[idx_seleccion]['id_empleado']
                    fecha_sel = impares.iloc[idx_seleccion]['fecha']

                    df_dia = st.session_state.df_registros_temp[
                        (st.session_state.df_registros_temp['id_empleado'] == emp) &
                        (st.session_state.df_registros_temp['fecha'] == fecha_sel)
                    ].sort_values('fecha_hora')

                    nombre_emp = get_nombre_empleado(emp)
                    st.markdown(f"**Registros del día para {nombre_emp} ({fecha_sel}):**")
                    for _, row in df_dia.iterrows():
                        st.write(f"  - {row['fecha_hora'].strftime('%H:%M')} ({row.get('tipo', 'RELOJ')})")

                    hora_sug, sugerencia = sugerir_hora_faltante(df_dia)

                    col_h1, col_h2 = st.columns(2)
                    hora_input = col_h1.time_input(
                        "Hora del registro faltante",
                        value=hora_sug if hora_sug else datetime_time(8, 0),
                        key="hora_olvido_manual"
                    )
                    st.caption(f"Sugerencia: {sugerencia}")

                    if st.button("✅ Agregar registro de olvido", key="btn_agregar_olvido"):
                        st.session_state.df_registros_temp = aplicar_correccion_olvido(
                            st.session_state.df_registros_temp,
                            emp,
                            fecha_sel,
                            hora_input,
                            "OLVIDO"
                        )
                        st.success(f"Registro agregado para {nombre_emp} en {fecha_sel}")
                        st.rerun()

    with tab4:
        st.markdown("### 📥 Descargar datos combinados")

        if st.session_state.df_registros_temp is None or st.session_state.df_registros_temp.empty:
            st.info("Carga archivos primero en la pestaña 'Cargar archivos'")
        else:
            df_descarga = st.session_state.df_registros_temp.copy()
            
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

            col_dl1, col_dl2 = st.columns(2)
            with col_dl1:
                st.download_button(
                    label="📥 Descargar CSV",
                    data=csv,
                    file_name=f"datos_horarios_{periodo}_{timestamp}.csv",
                    mime="text/csv",
                    help="Descarga los datos combinados en formato CSV",
                )
            with col_dl2:
                st.metric("Registros totales", len(df_descarga))

            with st.expander("Ver datos finales"):
                df_descarga['nombre'] = df_descarga['id_empleado'].apply(get_nombre_empleado)
                st.dataframe(df_descarga[['nombre', 'fecha_hora', 'tipo', 'fecha', 'hora']])