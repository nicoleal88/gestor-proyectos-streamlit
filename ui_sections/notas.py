import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data

def seccion_notas(client, personal_list):
    st.subheader("📝 Registro de Notas y Solicitudes")
    sheet_name = "Notas"
    df_notas = st.session_state.df_notas
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_notas.empty:
        try:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Notas", len(df_notas))
            col2.metric("Pendientes", (df_notas['Estado'] == "Pendiente").sum())
            col3.metric("Realizadas", (df_notas['Estado'] == "Realizado").sum())
            col4.metric("Rechazadas", (df_notas['Estado'] == "Rechazado").sum())
        except KeyError:
            st.error("La columna 'Estado' no se encontró. No se pueden mostrar las métricas.")

    st.markdown("---")
    vista_general, nueva_nota, modificar_nota = st.tabs(["📊 Vista General", "➕ Nueva Nota", "✏️ Modificar / Eliminar"])

    with vista_general:
        if not df_notas.empty:
            # Agregar número de fila para poder actualizar Google Sheets
            df_with_row = df_notas.copy()
            df_with_row.loc[:, 'row_number'] = range(2, len(df_with_row) + 2)

            status_options = df_with_row['Estado'].unique().tolist()
            # Establecer "Pendiente" como valor por defecto si existe
            default_status = ["Pendiente"] if "Pendiente" in status_options else status_options[:1] if status_options else []
            selected_statuses = st.multiselect(
                "Filtrar por Estado",
                options=status_options,
                default=default_status
            )
            if selected_statuses:
                df_filtered = df_with_row[df_with_row['Estado'].isin(selected_statuses)]
            else:
                df_filtered = df_with_row.copy()
        else:
            df_filtered = df_notas.copy()

        if not df_filtered.empty:
            # Limpiar tipos y valores nulos visibles
            for col in ['DNI', 'Teléfono']:
                if col in df_filtered.columns:
                    df_filtered.loc[:, col] = df_filtered[col].astype(str).replace('nan', '')

            # Editor de datos con edición sólo del Estado
            df_display = df_filtered.copy()
            st.session_state['df_notas_display'] = df_display.copy()

            column_order = [c for c in df_display.columns if c != 'row_number']
            edited_df = st.data_editor(
                df_display,
                key="data_editor_notas",
                width='stretch',
                hide_index=True,
                column_order=column_order,
                column_config={
                    'Fecha': st.column_config.Column(disabled=True),
                    'Remitente': st.column_config.Column(disabled=True),
                    'DNI': st.column_config.Column(disabled=True),
                    'Teléfono': st.column_config.Column(disabled=True),
                    'Motivo': st.column_config.Column(disabled=True),
                    'Responsable': st.column_config.Column(disabled=True),
                    'Estado': st.column_config.SelectboxColumn(
                        options=["Pendiente", "Realizado", "Rechazado"],
                        required=True,
                    ),
                    'row_number': st.column_config.Column(disabled=True),
                }
            )

            # Detectar cambios y actualizar sólo el Estado en Google Sheets
            try:
                if not edited_df.equals(st.session_state['df_notas_display']):
                    comparison_df = st.session_state['df_notas_display'].compare(edited_df)
                    if not comparison_df.empty:
                        changes_made = False
                        for idx, row in comparison_df.iterrows():
                            if ('Estado', 'other') in row:
                                new_status = row[('Estado', 'other')]
                                if pd.notna(new_status):
                                    row_number = int(st.session_state['df_notas_display'].loc[idx, 'row_number'])
                                    # Columna G = 7 -> Estado
                                    sheet.update_cell(row_number, 7, new_status)
                                    st.toast(f"Estado de la fila {row_number} actualizado a '{new_status}'.")
                                    changes_made = True
                        if changes_made:
                            refresh_data(client, sheet_name)
                            st.rerun()
            except Exception as e:
                st.error(f"Ocurrió un error al procesar los cambios: {e}")
        else:
            st.info("No hay notas registradas.")

    with nueva_nota:
        with st.form("nueva_nota_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", value=datetime.now())
            remitente = st.text_area("Remitente(s)")
            dni = st.text_input("DNI(s)")
            telefono = st.text_input("Teléfono(s)")
            motivo = st.text_area("Motivo")
            responsable = st.selectbox("Responsable", options=["Seleccione persona..."] + personal_list)
            estado = st.selectbox("Estado", options=["Pendiente", "Realizado", "Rechazado"])
            if st.form_submit_button("Agregar Nota"):
                if responsable == "Seleccione persona...":
                    st.warning("Por favor, seleccione un responsable.")
                else:
                    new_row = [fecha.strftime('%Y-%m-%d'), remitente, dni, telefono, motivo, responsable, estado]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success("Nota/Solicitud agregada exitosamente.")
                    st.rerun()

    with modificar_nota:
        if not df_notas.empty:
            # Usar .loc para evitar SettingWithCopyWarning
            df_notas.loc[:, 'row_number'] = range(2, len(df_notas) + 2)
            options = [f"Fila {row['row_number']}: {row['Motivo']} ({row['Remitente']})" for _, row in df_notas.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro", options=[""] + options)
            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df_notas[df_notas['row_number'] == row_number_to_edit].iloc[0]
                with st.form(f"edit_nota_form_{row_number_to_edit}"):
                    estados_options = ["Pendiente", "Realizado", "Rechazado"]
                    default_estado_idx = estados_options.index(record_data["Estado"]) if record_data["Estado"] in estados_options else 0
                    personal_options = ["Seleccione persona..."] + personal_list
                    try:
                        default_resp_idx = personal_options.index(record_data["Responsable"])
                    except (ValueError, KeyError):
                        default_resp_idx = 0
                    fecha = st.date_input("Fecha", value=pd.to_datetime(record_data["Fecha"]))
                    remitente = st.text_area("Remitente(s)", value=record_data["Remitente"])
                    dni = st.text_input("DNI(s)", value=str(record_data.get("DNI", "")))
                    telefono = st.text_input("Teléfono(s)", value=str(record_data.get("Teléfono", "")))
                    motivo = st.text_area("Motivo", value=record_data["Motivo"])
                    responsable = st.selectbox("Responsable", options=personal_options, index=default_resp_idx)
                    estado = st.selectbox("Estado", options=estados_options, index=default_estado_idx)
                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if responsable == "Seleccione persona...":
                            st.warning("Por favor, seleccione un responsable.")
                        else:
                            update_values = [fecha.strftime('%Y-%m-%d'), remitente, dni, telefono, motivo, responsable, estado]
                            sheet.update(f'A{row_number_to_edit}:G{row_number_to_edit}', [update_values])
                            refresh_data(client, sheet_name)
                            st.success("¡Registro actualizado!")
                            st.rerun()
                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        refresh_data(client, sheet_name)
                        st.success("¡Registro eliminado!")
                        st.rerun()
        else:
            st.info("No hay registros para modificar o eliminar.")
