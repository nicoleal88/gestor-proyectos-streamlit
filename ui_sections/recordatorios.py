import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data

def seccion_recordatorios(client, personal_list):
    st.subheader("🔔 Recordatorios Importantes")
    sheet_name = "Recordatorios"
    df_recordatorios = st.session_state.df_recordatorios
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    st.metric("Total de Recordatorios", len(df_recordatorios))
    st.markdown("---")

    vista_general, agregar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar / 🗑️ Eliminar"])

    with vista_general:
        st.dataframe(
            df_recordatorios, 
            hide_index=True, 
            width='content',
            column_config={
                "Fecha": st.column_config.DateColumn(format="DD/MM/YYYY")
            }
        )

    with agregar_eliminar:
        with st.form("recordatorios_form", clear_on_submit=True):
            fecha = st.date_input("Fecha del recordatorio", format="DD/MM/YYYY")
            mensaje = st.text_area("Mensaje")
            responsable = st.selectbox("Responsable", options=["Seleccione persona..."] + personal_list)

            if st.form_submit_button("Agregar Recordatorio"):
                if responsable == "Seleccione persona...":
                    st.warning("Por favor, seleccione un responsable.")
                else:
                    sheet.append_row([fecha.strftime('%Y-%m-%d'), mensaje, responsable])
                    refresh_data(client, sheet_name)
                    st.success("Recordatorio agregado.")
                    st.rerun()

        if not df_recordatorios.empty:
            st.markdown("#### Eliminar un recordatorio")
            df_recordatorios['row_number'] = range(2, len(df_recordatorios) + 2)
            # Formatear fecha para el selector
            def format_row_display(row):
                try:
                    f = pd.to_datetime(row['Fecha']).strftime('%d/%m/%Y')
                except:
                    f = row['Fecha']
                return f"Fila {row['row_number']}: {row['Mensaje']} ({f})"

            options = [format_row_display(row) for _, row in df_recordatorios.iterrows()]
            row_to_delete_display = st.selectbox("Selecciona un recordatorio para eliminar", options=[""] + options)

            if st.button("Eliminar Recordatorio Seleccionado"):
                if row_to_delete_display:
                    row_index = int(row_to_delete_display.split(':')[0].replace('Fila ', ''))
                    sheet.delete_rows(row_index)
                    refresh_data(client, sheet_name)
                    st.success("Recordatorio eliminado.")
                    st.rerun()
                else:
                    st.warning("Por favor, selecciona un recordatorio para eliminar.")
