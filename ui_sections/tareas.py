import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from google_sheets_client import get_sheet, refresh_data, get_sheet_data, update_cell_by_id

# --- FUNCIONES AUXILIARES ---
def highlight_overdue(row):
    deadline = pd.to_datetime(row['Fecha límite'], errors='coerce').date()
    today = datetime.now().date()
    return ['background-color: #8B0000'] * len(row) if pd.notna(deadline) and deadline < today and row['Estado'] != 'Finalizada' else [''] * len(row)

# --- FUNCIONES PARA COMENTARIOS Y REPORTES ---
def generar_reporte_markdown(task_data, comments_df):
    reporte = f"""
# Reporte de Tarea: {task_data['ID']} - {task_data['Título Tarea']}

## Detalles de la Tarea
- **ID:** {task_data['ID']}
- **Título:** {task_data['Título Tarea']}
- **Descripción Completa:** {task_data['Tarea']}
- **Responsable:** {task_data['Responsable']}
- **Fecha Límite:** {pd.to_datetime(task_data['Fecha límite']).strftime('%d/%m/%Y')}
- **Estado:** {task_data['Estado']}

---

## Historial de Avances
"""
    if not comments_df.empty:
        comments_df_sorted = comments_df.sort_values(by="Fecha", ascending=True)
        for _, comment in comments_df_sorted.iterrows():
            fecha_comentario = pd.to_datetime(comment['Fecha']).strftime('%d/%m/%Y')
            # Formatear cada línea del comentario con el prefijo '> '
            comentario_formateado = '\n> '.join(comment['Comentario'].split('\n'))
            reporte += f"""
**Fecha:** {fecha_comentario}
> {comentario_formateado}

"""
    else:
        reporte += """
_No hay avances registrados para esta tarea._"""
    return reporte

def get_comments_for_task(client, task_id):
    all_comments = get_sheet_data(client, "Comentarios")
    if all_comments.empty:
        return pd.DataFrame()
    all_comments['Fecha'] = pd.to_datetime(all_comments['Fecha'], errors='coerce')
    task_comments = all_comments[all_comments["ID_Tarea"].astype(str) == str(task_id)]
    return task_comments.sort_values(by="Fecha", ascending=False)

def add_comment_to_task(client, task_id, comment_text, comment_date):
    comments_sheet = get_sheet(client, "Comentarios")
    if comments_sheet is None: return False
    fecha_str = comment_date.strftime("%Y-%m-%d")
    comments_sheet.append_row([task_id, fecha_str, comment_text])
    return True

# --- SECCION DE TAREAS ---
def seccion_tareas(client, personal_list):
    st.subheader("📋 Gestión de Tareas")
    sheet_name = "Tareas"
    df_tasks = st.session_state.df_tareas
    sheet = get_sheet(client, sheet_name)
    if sheet is None: return

    if not df_tasks.empty:
        try:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Tareas", len(df_tasks))
            col2.metric("Pendientes", (df_tasks['Estado'] == "Pendiente").sum())
            col3.metric("En curso", (df_tasks['Estado'] == "En curso").sum())
            col4.metric("Finalizadas", (df_tasks['Estado'] == "Finalizada").sum())
        except KeyError:
            st.error("La columna 'Estado' no se encontró. No se pueden mostrar las métricas.")

    st.markdown("---")
    vista_general, nueva_tarea, detalles = st.tabs(["📊 Vista General", "➕ Nueva Tarea", "🔍 Detalles y Comentarios"])

    with vista_general:
        if not df_tasks.empty:
            def style_estado(estado):
                if estado == 'Finalizada':
                    return 'color: #32CD32'
                elif estado == 'En curso':
                    return 'color: #0066CC'
                elif estado == 'Pendiente':
                    return 'color: #FF8C00'
                return ''
            col1, col2 = st.columns(2)
            status_options = df_tasks['Estado'].unique().tolist()
            responsable_options = df_tasks['Responsable'].unique().tolist()
            selected_statuses = col1.multiselect(
                "Filtrar por Estado", 
                options=status_options,
                default=["En curso", "Pendiente"]  # Valores por defecto
            )
            selected_responsables = col2.multiselect("Filtrar por Responsable", options=responsable_options)

            df_filtered = df_tasks.copy()
            if selected_statuses:
                df_filtered = df_filtered[df_filtered['Estado'].isin(selected_statuses)]
            if selected_responsables:
                df_filtered = df_filtered[df_filtered['Responsable'].isin(selected_responsables)]
            
            df_filtered['Fecha límite'] = pd.to_datetime(df_filtered['Fecha límite'], errors='coerce')
            df_display = df_filtered.sort_values(by="Fecha límite").copy()
            today = datetime.now().date()
            # Aplicar formato al título de la tarea
            df_display['Título Tarea'] = df_display.apply(
                lambda row: f"🚨 {row['Título Tarea']}" if pd.notna(row['Fecha límite']) and row['Fecha límite'].date() < today and row['Estado'] != 'Finalizada' else row['Título Tarea'],
                axis=1
            )
            
            # Obtener todos los comentarios de una sola vez
            all_comments = get_sheet_data(client, "Comentarios")
            if not all_comments.empty and 'ID_Tarea' in all_comments.columns:
                all_comments['ID_Tarea'] = all_comments['ID_Tarea'].astype(str)
                # Agrupar comentarios por ID de tarea
                comments_by_task = {}
                for task_id, group in all_comments.groupby('ID_Tarea'):
                    comments = []
                    for _, row in group.iterrows():
                        date_str = pd.to_datetime(row['Fecha']).strftime('%d/%m/%Y')
                        comments.append(f"{date_str}: {row['Comentario']}")
                    comments_by_task[task_id] = "\n---\n".join(comments)
                
                # Mapear comentarios a las tareas
                df_display['Comentarios'] = df_display['ID'].astype(str).map(comments_by_task).fillna('')
            else:
                df_display['Comentarios'] = ''
            
            # Guardar el dataframe original en el estado de la sesión para comparar cambios
            st.session_state['df_tasks_display'] = df_display.copy()

            edited_df = st.data_editor(
                df_display,
                key="data_editor_tasks",
                width='stretch',
                hide_index=True,
                column_config={
                    'ID': st.column_config.Column(disabled=True),
                    'Título Tarea': st.column_config.Column(disabled=True),
                    'Tarea': st.column_config.Column(disabled=True),
                    'Responsable': st.column_config.Column(disabled=True),
                    'Fecha límite': st.column_config.DateColumn(format="DD/MM/YYYY", disabled=False),
                    'Estado': st.column_config.SelectboxColumn(
                        options=["Pendiente", "En curso", "Finalizada"],
                        required=True,
                    ),
                    'Comentarios': st.column_config.TextColumn(width='large', disabled=True)
                }
            )

            # Detectar cambios y actualizar la hoja de cálculo
            if not edited_df.equals(st.session_state['df_tasks_display']):
                try:
                    comparison_df = st.session_state['df_tasks_display'].compare(edited_df)
                    if not comparison_df.empty:
                        for index, row in comparison_df.iterrows():
                            task_id = st.session_state['df_tasks_display'].loc[index, 'ID']
                            changes_made = False

                            # Verificar cambio de estado
                            if ('Estado', 'other') in row:
                                new_status = row[('Estado', 'other')]
                                if pd.notna(new_status):
                                    success = update_cell_by_id(client, sheet_name, task_id, 'Estado', new_status)
                                    if success:
                                        st.toast(f"Estado de la tarea {task_id} actualizado a '{new_status}'.")
                                        changes_made = True
                                    else:
                                        st.error(f"No se pudo actualizar el estado de la tarea {task_id}.")
                            
                            # Verificar cambio de fecha límite
                            if ('Fecha límite', 'other') in row:
                                new_date = row[('Fecha límite', 'other')]
                                # gspread espera un string, no un objeto de fecha
                                new_date_str = pd.to_datetime(new_date).strftime('%Y-%m-%d') if pd.notna(new_date) else ""
                                success = update_cell_by_id(client, sheet_name, task_id, 'Fecha límite', new_date_str)
                                if success:
                                    st.toast(f"Fecha límite de la tarea {task_id} actualizada.")
                                    changes_made = True
                                else:
                                    st.error(f"No se pudo actualizar la fecha límite de la tarea {task_id}.")

                        if changes_made:
                            refresh_data(client, sheet_name)
                            st.rerun()
                except Exception as e:
                    st.error(f"Ocurrió un error al procesar los cambios: {e}")
        else:
            st.info("No hay tareas registradas.")

    with nueva_tarea:
        with st.form("nueva_tarea_form", clear_on_submit=True):
            titulo_tarea = st.text_input("Título Tarea")
            tarea = st.text_area("Descripción Completa de la Tarea")
            responsable = st.selectbox("Responsable", options=["Seleccione persona..."] + personal_list)
            fecha_limite = st.date_input("Fecha límite", value=None, format="DD/MM/YYYY")
            estado = st.selectbox("Estado", ["Pendiente", "En curso", "Finalizada"])

            if st.form_submit_button("Agregar Tarea"):
                if responsable == "Seleccione persona..." or not all([titulo_tarea, tarea]):
                    st.warning("Por favor, complete todos los campos obligatorios.")
                else:
                    new_id = (max(df_tasks['ID'].astype(int)) + 1) if not df_tasks.empty else 1
                    fecha_limite_str = fecha_limite.strftime('%Y-%m-%d') if fecha_limite else ""
                    new_row = [new_id, titulo_tarea, tarea, responsable, fecha_limite_str, estado]
                    sheet.append_row(new_row)
                    refresh_data(client, sheet_name)
                    st.success(f"¡Tarea ID {new_id} agregada!")
                    st.rerun()

    with detalles:
        if not df_tasks.empty:
            task_options = [f"{row['ID']} - {row['Título Tarea']}" for _, row in df_tasks.iterrows()]
            option_to_show = st.selectbox("Selecciona una tarea", options=[""] + task_options)

            if option_to_show:
                id_to_show = int(option_to_show.split(' - ')[0])
                task_data = df_tasks[df_tasks["ID"] == id_to_show].iloc[0]
                comments_df = get_comments_for_task(client, id_to_show)

                st.markdown(f"#### Detalles de la Tarea: {task_data['Título Tarea']}")
                st.write(f"**Descripción:** {task_data['Tarea']}")
                st.write(f"**Responsable:** {task_data['Responsable']}")
                st.write(f"**Estado:** {task_data['Estado']}")

                with st.expander("📄 Ver Reporte en Markdown"):
                    reporte_md = generar_reporte_markdown(task_data, comments_df)
                    st.markdown(reporte_md)
                    st.download_button("Descargar Reporte", reporte_md, f"reporte_tarea_{id_to_show}.md", "text/markdown")

                st.markdown("#### Historial de Avances")
                if not comments_df.empty:
                    st.dataframe(
                        comments_df, 
                        width='stretch', 
                        hide_index=True,
                        column_config={
                            "Fecha": st.column_config.DateColumn(format="DD/MM/YYYY")
                        }
                    )
                else:
                    st.info("No hay comentarios.")

                with st.form(f"comment_form_{id_to_show}", clear_on_submit=True):
                    comment_date = st.date_input("Fecha del comentario", value=datetime.now(), format="DD/MM/YYYY")
                    new_comment = st.text_area("Añadir nuevo comentario")
                    if st.form_submit_button("Guardar Comentario"):
                        if new_comment:
                            add_comment_to_task(client, id_to_show, new_comment, comment_date)
                            st.success("Comentario añadido.")
                            st.rerun()
                        else:
                            st.warning("El comentario no puede estar vacío.")
                
                with st.expander("✏️ Modificar / 🗑️ Eliminar Tarea"):
                    with st.form(f"edit_form_{id_to_show}"):
                        titulo_tarea = st.text_input("Título Tarea", value=task_data['Título Tarea'])
                        tarea = st.text_area("Descripción Completa", value=task_data['Tarea'])
                        responsable = st.selectbox("Responsable", options=["Seleccione persona..."] + personal_list, index=personal_list.index(task_data["Responsable"]) + 1 if task_data["Responsable"] in personal_list else 0)
                        fecha_limite = st.date_input("Fecha límite", value=pd.to_datetime(task_data["Fecha límite"]), format="DD/MM/YYYY")
                        estado = st.selectbox("Estado", ["Pendiente", "En curso", "Finalizada"], index=["Pendiente", "En curso", "Finalizada"].index(task_data["Estado"]))
                        
                        col_mod, col_del = st.columns(2)
                        if col_mod.form_submit_button("Guardar Cambios"):
                            if responsable != "Seleccione persona...":
                                sheet.update_cell(task_data.name + 2, 2, titulo_tarea)
                                sheet.update_cell(task_data.name + 2, 3, tarea)
                                sheet.update_cell(task_data.name + 2, 4, responsable)
                                sheet.update_cell(task_data.name + 2, 5, fecha_limite.strftime('%Y-%m-%d'))
                                sheet.update_cell(task_data.name + 2, 6, estado)
                                refresh_data(client, sheet_name)
                                st.success("¡Tarea actualizada!")
                                st.rerun()
                            else:
                                st.warning("Seleccione un responsable.")

                        if col_del.form_submit_button("Eliminar Tarea"):
                            sheet.delete_rows(task_data.name + 2)
                            refresh_data(client, sheet_name)
                            st.success("¡Tarea eliminada!")
                            st.rerun()
        else:
            st.info("No hay tareas para mostrar detalles.")
