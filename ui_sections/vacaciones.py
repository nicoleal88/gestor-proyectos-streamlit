import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data
from utils.date_utils import format_duracion_licencia

def seccion_vacaciones(client, personal_list):
    st.subheader("📅 Registro de Vacaciones")
    sheet_name = "Vacaciones"
    df_vacaciones = st.session_state.df_vacaciones
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_vacaciones.empty:
        df_vacaciones['Fecha inicio'] = pd.to_datetime(df_vacaciones['Fecha inicio'], errors='coerce')
        df_vacaciones['Fecha regreso'] = pd.to_datetime(df_vacaciones['Fecha regreso'], errors='coerce')
        # Ajustar la fecha fin para mostrar el último día de vacaciones (un día antes del regreso)
        df_vacaciones['Último día de vacaciones'] = df_vacaciones['Fecha regreso'] - pd.Timedelta(days=1)

        today = pd.to_datetime(datetime.now().date())

        # Calcular métricas basadas en TODOS los registros (no filtrados)
        en_curso_total = ((df_vacaciones['Fecha inicio'] <= today) & (df_vacaciones['Último día de vacaciones'] >= today)).sum()
        proximas_total = (df_vacaciones['Fecha inicio'] > today).sum()
        transcurridas_total = (df_vacaciones['Último día de vacaciones'] < today).sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Registros", len(df_vacaciones))
        col2.metric("Vacaciones en Curso", en_curso_total)
        col3.metric("Próximas Vacaciones", proximas_total)
        col4.metric("Vacaciones Transcurridas", transcurridas_total)

        st.markdown("---")

    vista_general, agregar_vacaciones, modificar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar Vacaciones", "✏️ Modificar / Eliminar"])

    with vista_general:
        if not df_vacaciones.empty:
            # Filtro por estado de las vacaciones
            today = pd.to_datetime(datetime.now().date())

            # Crear opciones de filtro
            filter_options = ["Vacaciones en Curso", "Próximas Vacaciones", "Vacaciones Transcurridas", "Todos"]
            default_filter = "Vacaciones en Curso"

            selected_filter = st.selectbox(
                "Filtrar por Estado",
                options=filter_options,
                index=filter_options.index(default_filter)
            )

            # Aplicar filtro según la selección
            df_filtered = df_vacaciones.copy()

            if selected_filter == "Vacaciones en Curso":
                # Vacaciones que están actualmente en curso (inicio <= hoy <= último día)
                df_filtered = df_filtered[
                    (df_filtered['Fecha inicio'] <= today) &
                    (df_filtered['Último día de vacaciones'] >= today)
                ]
            elif selected_filter == "Próximas Vacaciones":
                # Vacaciones que aún no han empezado (inicio > hoy)
                df_filtered = df_filtered[df_filtered['Fecha inicio'] > today]
            elif selected_filter == "Vacaciones Transcurridas":
                # Vacaciones que ya terminaron (último día < hoy)
                df_filtered = df_filtered[df_filtered['Último día de vacaciones'] < today]
            # "Todos" no aplica ningún filtro adicional

            st.info(f"Mostrando: {selected_filter} ({len(df_filtered)} registros)")

        else:
            df_filtered = df_vacaciones.copy()

        df_display = df_filtered.sort_values(by='Fecha inicio', ascending=False)
        if 'row_number' in df_display.columns:
            df_display = df_display.drop(columns=['row_number'])

        # Eliminar columna auxiliar de la visualización
        if 'Último día de vacaciones' in df_display.columns:
            df_display = df_display.drop(columns=['Último día de vacaciones'])

        def style_status(row):
            today = pd.to_datetime(datetime.now().date()).date()
            start_date = pd.to_datetime(row['Fecha inicio']).date()
            # La fecha regresa es el día que vuelve al trabajo, el último día es uno antes
            last_vacation_day = (pd.to_datetime(row['Fecha regreso']) - pd.Timedelta(days=1)).date()
            style = ''
            if start_date <= today and last_vacation_day >= today:
                style = 'background-color: #1E90FF'  # En curso (blue)
            elif last_vacation_day < today:
                style = 'background-color: #696969'  # Ya ocurridas (gray)
            elif start_date > today:
                style = 'background-color: #FF8C00'  # Próximas (orange)
            return [style] * len(row)

        st.dataframe(
            df_display.style.apply(style_status, axis=1),
            width='stretch',
            hide_index=True,
            column_config={
                'Fecha inicio': st.column_config.DateColumn(format="DD/MM/YYYY", help="Primer día de vacaciones"),
                'Fecha regreso': st.column_config.DateColumn(format="DD/MM/YYYY", help="Día de regreso al trabajo"),
                'Fecha solicitud': st.column_config.DateColumn(format="DD/MM/YYYY")
            }
        )

    with agregar_vacaciones:
        st.info("Complete las fechas para ver la duración del período.")
        col1, col2 = st.columns(2)
        fecha_inicio_live = col1.date_input("Fecha inicio", key="vac_fecha_inicio", value=datetime.now().date())
        fecha_regreso_live = col2.date_input("Fecha regreso al trabajo", key="vac_fecha_regreso", value=datetime.now().date() + pd.Timedelta(days=1))

        # Cálculo en vivo de días con API de feriados
        if fecha_regreso_live <= fecha_inicio_live:
            st.warning("La fecha de regreso debe ser posterior a la de inicio.")
            msg_duracion, dias_corrido, dias_habiles = "", 0, 0
        else:
            # El último día de vacaciones es el día anterior al regreso
            ultimo_dia = fecha_regreso_live - pd.Timedelta(days=1)
            msg_duracion, dias_corrido, dias_habiles = format_duracion_licencia(fecha_inicio_live, ultimo_dia)
            st.markdown(msg_duracion)
            st.success(f"Período confirmado: {dias_corrido} días de corrido ({dias_habiles} hábiles).")

        with st.form("vacaciones_form", clear_on_submit=True):
            nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list)
            fecha_solicitud = st.date_input("Fecha Solicitud", value=datetime.now())
            tipo = st.selectbox("Tipo", options=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025", "Otros"])
            observaciones = st.text_area("Observaciones", placeholder="Detalles adicionales...")

            if st.form_submit_button("Agregar Registro"):
                if nombre == "Seleccione persona...":
                    st.warning("Por favor, seleccione una persona.")
                elif fecha_inicio_live >= fecha_regreso_live:
                    st.error("La fecha de inicio debe ser anterior a la de regreso.")
                else:
                    new_row = [
                        nombre,
                        fecha_solicitud.strftime('%Y-%m-%d'),
                        tipo,
                        fecha_inicio_live.strftime('%Y-%m-%d'),
                        fecha_regreso_live.strftime('%Y-%m-%d'),
                        observaciones
                    ]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success(f"Registro agregado para {nombre}.")
                    st.rerun()

    with modificar_eliminar:
        if not df_vacaciones.empty:
            st.markdown("#### Modificar o Eliminar un registro")
            df_vacaciones['row_number'] = range(2, len(df_vacaciones) + 2)
            options = [f"Fila {row['row_number']}: {row['Apellido, Nombres']} - {row['Fecha inicio'].strftime('%d/%m/%Y') if pd.notna(row['Fecha inicio']) else ''} ({row['Tipo']})" for _, row in df_vacaciones.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro para modificar o eliminar", options=[""] + options, key="select_edit_vac")

            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df_vacaciones[df_vacaciones['row_number'] == row_number_to_edit].iloc[0]

                # Entradas en vivo para la edición
                st.markdown("---")
                col1, col2 = st.columns(2)
                edit_inicio = col1.date_input("Modificar inicio", value=pd.to_datetime(record_data["Fecha inicio"]), key=f"edit_vac_ini_{row_number_to_edit}")
                edit_regreso = col2.date_input("Modificar regreso", value=pd.to_datetime(record_data["Fecha regreso"]), key=f"edit_vac_reg_{row_number_to_edit}")

                if edit_regreso > edit_inicio:
                    ultimo_dia_edit = edit_regreso - pd.Timedelta(days=1)
                    msg_edit, dias_c_edit, dias_h_edit = format_duracion_licencia(edit_inicio, ultimo_dia_edit)
                    st.info(msg_edit)
                else:
                    st.warning("La fecha de regreso debe ser posterior a la de inicio.")

                with st.form(f"edit_vac_form_{row_number_to_edit}"):
                    nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list, index=personal_list.index(record_data["Apellido, Nombres"]) + 1 if record_data["Apellido, Nombres"] in personal_list else 0)
                    fecha_solicitud = st.date_input("Fecha Solicitud", value=pd.to_datetime(record_data["Fecha solicitud"]))
                    tipo = st.selectbox("Tipo", options=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025", "Otros"], index=["Licencia Ordinaria 2024", "Licencia Ordinaria 2025", "Otros"].index(record_data["Tipo"]) if record_data["Tipo"] in ["Licencia Ordinaria 2024", "Licencia Ordinaria 2025", "Otros"] else 0)
                    observaciones = st.text_area("Observaciones", value=record_data["Observaciones"])

                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if nombre == "Seleccione persona...":
                            st.warning("Por favor, seleccione una persona.")
                        elif edit_inicio >= edit_regreso:
                            st.error("No se pueden guardar cambios: Fecha inicio >= Fecha regreso.")
                        else:
                            update_values = [
                                nombre, 
                                fecha_solicitud.strftime('%Y-%m-%d'), 
                                tipo, 
                                edit_inicio.strftime('%Y-%m-%d'), 
                                edit_regreso.strftime('%Y-%m-%d'), 
                                observaciones
                            ]
                            sheet.update(f'A{row_number_to_edit}:F{row_number_to_edit}', [update_values])
                            refresh_data(client, sheet_name)
                            st.success("¡Registro actualizado!")
                            st.rerun()

                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        refresh_data(client, sheet_name)
                        st.success("¡Registro eliminado!")
                        st.rerun()
        else:
            st.info("No hay registros de vacaciones.")
