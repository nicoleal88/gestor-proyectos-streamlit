import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data

def seccion_vacaciones(client, personal_list):
    st.subheader("📅 Registro de Licencias y Vacaciones")
    sheet_name = "Vacaciones"
    df_vacaciones = st.session_state.df_vacaciones
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_vacaciones.empty:
        df_vacaciones['Fecha inicio'] = pd.to_datetime(df_vacaciones['Fecha inicio'], errors='coerce')
        df_vacaciones['Fecha fin'] = pd.to_datetime(df_vacaciones['Fecha fin'], errors='coerce')
        # Ajustar la fecha fin para mostrar el último día de vacaciones (un día antes del regreso)
        df_vacaciones['Último día de vacaciones'] = df_vacaciones['Fecha fin'] - pd.Timedelta(days=1)
        
        today = pd.to_datetime(datetime.now().date())
        # Ajustar la lógica para usar el último día de vacaciones en lugar de la fecha de regreso
        en_curso = ((df_vacaciones['Fecha inicio'] <= today) & (df_vacaciones['Último día de vacaciones'] >= today)).sum()
        proximas = (df_vacaciones['Fecha inicio'] > today).sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", len(df_vacaciones))
        col2.metric("Licencias en Curso", en_curso)
        col3.metric("Próximas Licencias", proximas)

    st.markdown("---")
    vista_general, nueva_licencia, modificar_licencia = st.tabs(["📊 Vista General", "➕ Nueva Licencia", "✏️ Modificar / Eliminar"])

    with vista_general:
        df_display = df_vacaciones.sort_values(by='Fecha inicio', ascending=False)
        if 'row_number' in df_display.columns:
            df_display = df_display.drop(columns=['row_number'])

        def style_status(row):
            today = pd.to_datetime(datetime.now().date()).date()
            start_date = pd.to_datetime(row['Fecha inicio']).date()
            last_vacation_day = (pd.to_datetime(row['Fecha fin']) - pd.Timedelta(days=1)).date()
            style = ''
            if start_date <= today and last_vacation_day >= today:
                style = 'background-color: lightblue'  # En curso (blue)
            elif last_vacation_day < today:
                style = 'background-color: lightgray'  # Ya ocurridas (gray)
            elif start_date > today:
                style = 'background-color: #FFD580'  # Próximas (light orange)
            return [style] * len(row)

        # Crear una copia para mostrar, ajustando las fechas según lo necesario
        df_display_modified = df_display.copy()
        # Mostrar la fecha de fin como el último día de vacaciones
        df_display_modified['Fecha fin'] = df_display_modified['Fecha fin'] - pd.Timedelta(days=1)
        
        st.dataframe(
            df_display_modified.style.apply(style_status, axis=1),
            width='stretch',
            hide_index=True,
            column_config={
                'Fecha inicio': st.column_config.DateColumn(
                    format="DD/MM/YYYY",
                    help="Primer día de vacaciones"
                ),
                'Fecha fin': st.column_config.DateColumn(
                    format="DD/MM/YYYY",
                    help="Último día de vacaciones (el regreso al trabajo es al día siguiente)"
                ),
                'Fecha solicitud': st.column_config.DateColumn(format="DD/MM/YYYY")
            }
        )
        
        # Agregar nota aclaratoria
        st.caption("ℹ️ La 'Fecha fin' muestra el último día de vacaciones. El regreso al trabajo es al día siguiente.")

    with nueva_licencia:
        with st.form("nueva_vacacion_form", clear_on_submit=True):
            nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list)
            fecha_solicitud = st.date_input("Fecha de Solicitud", value=datetime.now())
            tipo = st.selectbox("Tipo", options=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025"])
            fecha_inicio = st.date_input("Fecha de Inicio")
            fecha_fin = st.date_input("Fecha de Fin")
            observaciones = st.text_area("Observaciones", value="Pendientes: ")

            if st.form_submit_button("Agregar Registro"):
                if nombre == "Seleccione persona...":
                    st.warning("Por favor, seleccione una persona.")
                elif fecha_inicio >= fecha_fin:
                    st.error("La fecha de inicio debe ser anterior a la fecha de regreso al trabajo.")
                else:
                    # Mostrar confirmación con la duración real de las vacaciones
                    duracion = (fecha_fin - fecha_inicio).days
                    st.info(f"Se registrarán {duracion} días de vacaciones desde {fecha_inicio.strftime('%d/%m/%Y')} hasta {(fecha_fin - pd.Timedelta(days=1)).strftime('%d/%m/%Y')} (inclusive).")
                    
                    # Guardar los datos con la fecha de fin como el día de regreso al trabajo
                    new_row = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), observaciones]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success("Registro agregado exitosamente.")
                    st.rerun()

    with modificar_licencia:
        if not df_vacaciones.empty:
            df_vacaciones['row_number'] = range(2, len(df_vacaciones) + 2)
            options = [f"Fila {row['row_number']}: {row['Apellido, Nombres']} ({row['Tipo']})" for _, row in df_vacaciones.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro", options=[""] + options)

            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df_vacaciones[df_vacaciones['row_number'] == row_number_to_edit].iloc[0]

                with st.form(f"edit_vac_form_{row_number_to_edit}"):
                    nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list, index=personal_list.index(record_data["Apellido, Nombres"]) + 1 if record_data["Apellido, Nombres"] in personal_list else 0)
                    fecha_solicitud = st.date_input("Fecha de Solicitud", value=pd.to_datetime(record_data["Fecha solicitud"]))
                    tipo = st.selectbox("Tipo", options=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025"], index=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025"].index(record_data["Tipo"]))
                    fecha_inicio = st.date_input("Fecha de Inicio", value=pd.to_datetime(record_data["Fecha inicio"]))
                    fecha_fin = st.date_input("Fecha de Fin", value=pd.to_datetime(record_data["Fecha fin"]))
                    observaciones = st.text_area("Observaciones", value=record_data["Observaciones"])

                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if nombre != "Seleccione persona...":
                            update_values = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), observaciones]
                            sheet.update(f'A{row_number_to_edit}:F{row_number_to_edit}', [update_values])
                            refresh_data(client, sheet_name)
                            st.success("¡Registro actualizado!")
                            st.rerun()
                        else:
                            st.warning("Seleccione una persona.")
                    
                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        refresh_data(client, sheet_name)
                        st.success("¡Registro eliminado!")
                        st.rerun()
        else:
            st.info("No hay registros para modificar.")
