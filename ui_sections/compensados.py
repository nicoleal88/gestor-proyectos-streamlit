import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data

def seccion_compensados(client, personal_list):
    sheet_name = "Compensados"
    df_compensados = st.session_state.df_compensados
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_compensados.empty:
        df_compensados['Desde fecha'] = pd.to_datetime(df_compensados['Desde fecha'], errors='coerce')
        df_compensados['Hasta fecha'] = pd.to_datetime(df_compensados['Hasta fecha'], errors='coerce')
        today = pd.to_datetime(datetime.now().date())

        # Calcular métricas basadas en TODOS los registros (no filtrados)
        en_curso_total = ((df_compensados['Desde fecha'] <= today) & (df_compensados['Hasta fecha'] >= today)).sum()
        proximos_total = (df_compensados['Desde fecha'] > today).sum()
        transcurridos_total = (df_compensados['Hasta fecha'] < today).sum()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total de Registros", len(df_compensados))
        col2.metric("Compensatorios en Curso", en_curso_total)
        col3.metric("Próximos Compensatorios", proximos_total)
        col4.metric("Compensatorios Transcurridos", transcurridos_total)

    vista_general, agregar_compensatorio, modificar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar Compensatorio", "✏️ Modificar / Eliminar"])

    with vista_general:
        if not df_compensados.empty:
            # Filtro por estado de los compensatorios
            today = pd.to_datetime(datetime.now().date())

            # Crear opciones de filtro
            filter_options = ["Compensatorios en Curso", "Próximos Compensatorios", "Compensatorios Transcurridos", "Todos"]
            default_filter = "Compensatorios en Curso"

            selected_filter = st.selectbox(
                "Filtrar por Estado",
                options=filter_options,
                index=filter_options.index(default_filter)
            )

            # Aplicar filtro según la selección
            df_filtered = df_compensados.copy()

            if selected_filter == "Compensatorios en Curso":
                # Compensatorios que están actualmente en curso (desde <= hoy <= hasta)
                df_filtered = df_filtered[
                    (df_filtered['Desde fecha'] <= today) &
                    (df_filtered['Hasta fecha'] >= today)
                ]
            elif selected_filter == "Próximos Compensatorios":
                # Compensatorios que aún no han empezado (desde > hoy)
                df_filtered = df_filtered[df_filtered['Desde fecha'] > today]
            elif selected_filter == "Compensatorios Transcurridos":
                # Compensatorios que ya terminaron (hasta < hoy)
                df_filtered = df_filtered[df_filtered['Hasta fecha'] < today]
            # "Todos" no aplica ningún filtro adicional

            st.info(f"Mostrando: {selected_filter} ({len(df_filtered)} registros)")

        else:
            df_filtered = df_compensados.copy()

        df_display = df_filtered.sort_values(by='Desde fecha', ascending=False)
        if 'row_number' in df_display.columns:
            df_display = df_display.drop(columns=['row_number'])

        def style_status(row):
            today = pd.to_datetime(datetime.now().date()).date()
            start_date = pd.to_datetime(row['Desde fecha']).date()
            end_date = pd.to_datetime(row['Hasta fecha']).date()
            style = ''
            if start_date <= today and end_date >= today:
                style = 'background-color: #1E90FF'  # En curso (blue)
            elif end_date < today:
                style = 'background-color: #696969'  # Ya ocurridas (gray)
            elif start_date > today:
                style = 'background-color: #FF8C00'  # Próximas (orange)
            return [style] * len(row)

        st.dataframe(
            df_display.style.apply(style_status, axis=1),
            width='stretch',
            hide_index=True,
            column_config={
                'Desde fecha': st.column_config.DateColumn(format="DD/MM/YYYY"),
                'Hasta fecha': st.column_config.DateColumn(format="DD/MM/YYYY"),
                'Fecha Solicitud': st.column_config.DateColumn(format="DD/MM/YYYY")
            }
        )

    with agregar_compensatorio:
        tipo_compensatorio = st.radio("Tipo de compensatorio", ("Día completo", "Por horas"), key="tipo_compensatorio_radio")

        with st.form("compensados_form", clear_on_submit=True):
            nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list)
            fecha_solicitud = st.date_input("Fecha Solicitud", value=datetime.now())
            tipo = st.selectbox("Tipo", options=["Compensatorio"])
            
            if st.session_state.tipo_compensatorio_radio == "Día completo":
                col1, col2 = st.columns(2)
                desde_fecha = col1.date_input("Desde fecha")
                hasta_fecha = col2.date_input("Hasta fecha")
                desde_hora = None
                hasta_hora = None
            else: # Por horas
                col1, col2, col3 = st.columns(3)
                fecha = col1.date_input("Fecha")
                desde_hora = col2.time_input("Desde hora")
                hasta_hora = col3.time_input("Hasta hora")
                desde_fecha = fecha
                hasta_fecha = fecha

            if st.form_submit_button("Agregar Registro"):
                if nombre == "Seleccione persona...":
                    st.warning("Por favor, seleccione una persona.")
                else:
                    desde_hora_str = desde_hora.strftime('%H:%M') if desde_hora else ''
                    hasta_hora_str = hasta_hora.strftime('%H:%M') if hasta_hora else ''
                    new_row = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, desde_fecha.strftime('%Y-%m-%d'), desde_hora_str, hasta_fecha.strftime('%Y-%m-%d'), hasta_hora_str]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success("Registro de compensatorio agregado.")
                    st.rerun()

    with modificar_eliminar:
        if not df_compensados.empty:
            st.markdown("#### Modificar o Eliminar un registro")
            df_compensados['row_number'] = range(2, len(df_compensados) + 2)
            options = [f"Fila {row['row_number']}: {row['Apellido, Nombres']} - {row['Desde fecha'].strftime('%d/%m/%Y') if pd.notna(row['Desde fecha']) else ''} {row['Desde hora'] if not pd.isna(row['Desde hora']) else ''}" for _, row in df_compensados.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro para modificar o eliminar", options=[""] + options)

            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df_compensados[df_compensados['row_number'] == row_number_to_edit].iloc[0]

                es_dia_completo = pd.isna(record_data['Desde hora']) or record_data['Desde hora'] == ''
                tipo_compensatorio_key = f"tipo_compensatorio_radio_{row_number_to_edit}"
                tipo_compensatorio = st.radio("Tipo de compensatorio", ("Día completo", "Por horas"), index=0 if es_dia_completo else 1, key=tipo_compensatorio_key)

                with st.form(f"edit_compensados_form_{row_number_to_edit}"):
                    nombre = st.selectbox("Apellido, Nombres", options=["Seleccione persona..."] + personal_list, index=personal_list.index(record_data["Apellido, Nombres"]) + 1 if record_data["Apellido, Nombres"] in personal_list else 0)
                    fecha_solicitud = st.date_input("Fecha Solicitud", value=pd.to_datetime(record_data["Fecha Solicitud"]))
                    tipo = st.selectbox("Tipo", options=["Compensatorio"], index=0)

                    if st.session_state[tipo_compensatorio_key] == "Día completo":
                        col1, col2 = st.columns(2)
                        desde_fecha = col1.date_input("Desde fecha", value=pd.to_datetime(record_data["Desde fecha"]))
                        hasta_fecha = col2.date_input("Hasta fecha", value=pd.to_datetime(record_data["Hasta fecha"]))
                        desde_hora = None
                        hasta_hora = None
                    else: # Por horas
                        col1, col2, col3 = st.columns(3)
                        fecha = col1.date_input("Fecha", value=pd.to_datetime(record_data["Desde fecha"]))
                        desde_hora = col2.time_input("Desde hora", value=datetime.strptime(record_data["Desde hora"], '%H:%M').time() if not es_dia_completo and record_data["Desde hora"] and isinstance(record_data["Desde hora"], str) else None)
                        hasta_hora = col3.time_input("Hasta hora", value=datetime.strptime(record_data["Hasta hora"], '%H:%M').time() if not es_dia_completo and record_data["Hasta hora"] and isinstance(record_data["Hasta hora"], str) else None)
                        desde_fecha = fecha
                        hasta_fecha = fecha

                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if nombre == "Seleccione persona...":
                            st.warning("Por favor, seleccione una persona.")
                        else:
                            desde_hora_str = desde_hora.strftime('%H:%M') if desde_hora else ''
                            hasta_hora_str = hasta_hora.strftime('%H:%M') if hasta_hora else ''
                            update_values = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, desde_fecha.strftime('%Y-%m-%d'), desde_hora_str, hasta_fecha.strftime('%Y-%m-%d'), hasta_hora_str]
                            sheet.update(f'A{row_number_to_edit}:G{row_number_to_edit}', [update_values])
                            refresh_data(client, sheet_name)
                            st.success("¡Registro actualizado!")
                            st.rerun()

                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        refresh_data(client, sheet_name)
                        st.success("¡Registro eliminado!")
                        st.rerun()
