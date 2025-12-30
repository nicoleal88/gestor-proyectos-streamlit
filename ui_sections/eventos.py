import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data

def mostrar_seccion_eventos(client):
    st.subheader("📅 Eventos")
    sheet_name = "Eventos"
    df_eventos = st.session_state.df_eventos
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_eventos.empty:
        df_eventos['Desde fecha'] = pd.to_datetime(df_eventos['Desde fecha'], errors='coerce')
        df_eventos['Hasta fecha'] = pd.to_datetime(df_eventos['Hasta fecha'], errors='coerce')
        today = pd.to_datetime(datetime.now().date())
        en_curso = ((df_eventos['Desde fecha'] <= today) & (df_eventos['Hasta fecha'] >= today)).sum()
        proximos = (df_eventos['Desde fecha'] > today).sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Registros", len(df_eventos))
        col2.metric("Eventos en Curso", en_curso)
        col3.metric("Próximos Eventos", proximos)
    else:
        st.metric("Total de Registros", 0)
    st.markdown("---")

    vista_general, agregar_evento, modificar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar Evento", "✏️ Modificar / Eliminar"])

    with vista_general:
        df_display = df_eventos.copy()
        if 'row_number' in df_display.columns:
            df_display = df_display.drop(columns=['row_number'])
        df_display = df_display.sort_values(by='Desde fecha', ascending=False)

        def style_status(row):
            today = pd.to_datetime(datetime.now().date()).date()
            start_date = pd.to_datetime(row['Desde fecha']).date()
            end_date = pd.to_datetime(row['Hasta fecha']).date()
            style = ''
            if start_date <= today and end_date >= today:
                style = 'background-color: lightblue'  # En curso (blue)
            elif end_date < today:
                style = 'background-color: lightgray'  # Ya ocurridas (gray)
            elif start_date > today:
                style = 'background-color: orange'  # Próximas (orange)
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

    with agregar_evento:
        tipo_evento = st.radio("Tipo de evento", ("Día completo", "Por horas"), key="tipo_evento_radio")

        with st.form("eventos_form", clear_on_submit=True):
            nombre_evento = st.text_input("Nombre del Evento")
            fecha_solicitud = st.date_input("Fecha Solicitud", value=datetime.now(), format="DD/MM/YYYY")
            tipo = st.selectbox("Tipo", options=["Evento"])
            
            if st.session_state.tipo_evento_radio == "Día completo":
                col1, col2 = st.columns(2)
                desde_fecha = col1.date_input("Desde fecha", format="DD/MM/YYYY")
                hasta_fecha = col2.date_input("Hasta fecha", format="DD/MM/YYYY")
                desde_hora = None
                hasta_hora = None
            else: # Por horas
                col1, col2, col3 = st.columns(3)
                fecha = col1.date_input("Fecha", format="DD/MM/YYYY")
                desde_hora = col2.time_input("Desde hora")
                hasta_hora = col3.time_input("Hasta hora")
                desde_fecha = fecha
                hasta_fecha = fecha

            if st.form_submit_button("Agregar Registro"):
                if nombre_evento == "":
                    st.warning("Por favor, ingrese un nombre para el evento.")
                else:
                    desde_hora_str = desde_hora.strftime('%H:%M') if desde_hora else ''
                    hasta_hora_str = hasta_hora.strftime('%H:%M') if hasta_hora else ''
                    new_row = [nombre_evento, fecha_solicitud.strftime('%Y-%m-%d'), tipo, desde_fecha.strftime('%Y-%m-%d'), desde_hora_str, hasta_fecha.strftime('%Y-%m-%d'), hasta_hora_str]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success("Registro de evento agregado.")
                    st.rerun()

    with modificar_eliminar:
        if not df_eventos.empty:
            st.markdown("#### Modificar o Eliminar un registro")
            df_eventos['row_number'] = range(2, len(df_eventos) + 2)
            options = [f"Fila {row['row_number']}: {row['Nombre del Evento']} - {row['Desde fecha'].strftime('%d/%m/%Y') if pd.notna(row['Desde fecha']) else ''} {row['Desde hora'] if not pd.isna(row['Desde hora']) else ''}" for _, row in df_eventos.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro para modificar o eliminar", options=[""] + options)

            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df_eventos[df_eventos['row_number'] == row_number_to_edit].iloc[0]

                es_dia_completo = pd.isna(record_data['Desde hora']) or record_data['Desde hora'] == ''
                tipo_evento_key = f"tipo_evento_radio_{row_number_to_edit}"
                tipo_evento = st.radio("Tipo de evento", ("Día completo", "Por horas"), index=0 if es_dia_completo else 1, key=tipo_evento_key)

                with st.form(f"edit_eventos_form_{row_number_to_edit}"):
                    nombre_evento = st.text_input("Nombre del Evento", value=record_data["Nombre del Evento"])
                    fecha_solicitud = st.date_input("Fecha Solicitud", value=pd.to_datetime(record_data["Fecha Solicitud"]), format="DD/MM/YYYY")
                    tipo = st.selectbox("Tipo", options=["Evento"], index=0)

                    if st.session_state[tipo_evento_key] == "Día completo":
                        col1, col2 = st.columns(2)
                        desde_fecha = col1.date_input("Desde fecha", value=pd.to_datetime(record_data["Desde fecha"]), format="DD/MM/YYYY")
                        hasta_fecha = col2.date_input("Hasta fecha", value=pd.to_datetime(record_data["Hasta fecha"]), format="DD/MM/YYYY")
                        desde_hora = None
                        hasta_hora = None
                    else: # Por horas
                        col1, col2, col3 = st.columns(3)
                        fecha = col1.date_input("Fecha", value=pd.to_datetime(record_data["Desde fecha"]), format="DD/MM/YYYY")
                        desde_hora = col2.time_input("Desde hora", value=datetime.strptime(record_data["Desde hora"], '%H:%M').time() if not es_dia_completo and record_data["Desde hora"] and isinstance(record_data["Desde hora"], str) else None)
                        hasta_hora = col3.time_input("Hasta hora", value=datetime.strptime(record_data["Hasta hora"], '%H:%M').time() if not es_dia_completo and record_data["Hasta hora"] and isinstance(record_data["Hasta hora"], str) else None)
                        desde_fecha = fecha
                        hasta_fecha = fecha

                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if nombre_evento == "":
                            st.warning("Por favor, ingrese un nombre para el evento.")
                        else:
                            desde_hora_str = desde_hora.strftime('%H:%M') if desde_hora else ''
                            hasta_hora_str = hasta_hora.strftime('%H:%M') if hasta_hora else ''
                            update_values = [nombre_evento, fecha_solicitud.strftime('%Y-%m-%d'), tipo, desde_fecha.strftime('%Y-%m-%d'), desde_hora_str, hasta_fecha.strftime('%Y-%m-%d'), hasta_hora_str]
                            sheet.update(f'A{row_number_to_edit}:G{row_number_to_edit}', [update_values])
                            refresh_data(client, sheet_name)
                            st.success("¡Registro actualizado!")
                            st.rerun()

                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        refresh_data(client, sheet_name)
                        st.success("¡Registro eliminado!")
                        st.rerun()
