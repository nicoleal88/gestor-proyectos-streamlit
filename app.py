import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime, timedelta
from streamlit_option_menu import option_menu
from streamlit_calendar import calendar

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
@st.cache_resource
def connect_to_google_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name("credenciales.json", scope)
        client = gspread.authorize(creds)
        return client
    except FileNotFoundError:
        st.error("Error: El archivo 'credenciales.json' no se encontró.")
        st.info("Por favor, sigue las instrucciones en el README.md para configurar tus credenciales de Google Cloud.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error al conectar con Google Sheets: {e}")
        return None

def get_sheet(client, sheet_name):
    try:
        sheet = client.open("GestorProyectosStreamlit").worksheet(sheet_name)
        return sheet
    except gspread.exceptions.SpreadsheetNotFound:
        st.error("Error: La hoja de cálculo 'GestorProyectosStreamlit' no fue encontrada.")
        st.info("Asegúrate de haber creado el Google Sheet con ese nombre exacto.")
        return None
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: La pestaña '{sheet_name}' no fue encontrada en el Google Sheet.")
        st.info(f"Asegúrate de que la pestaña '{sheet_name}' existe.")
        return None
    except Exception as e:
        st.error(f"Ocurrió un error inesperado al acceder a la hoja: {e}")
        return None

# --- FUNCIONES AUXILIARES ---
@st.cache_data(ttl=600)
def get_personal_list(_client):
    sheet = get_sheet(_client, "Personal")
    if sheet:
        try:
            personal = sheet.col_values(1)[1:]
            return [name for name in personal if name]
        except Exception as e:
            st.error(f"No se pudo leer la lista de personal: {e}")
            return []
    return []

@st.cache_data(ttl=600)
def get_cached_sheet_data(_client, sheet_name):
    '''Fetches all records from a sheet and caches the result.'''
    sheet = get_sheet(_client, sheet_name)
    if sheet is None:
        return pd.DataFrame()
    try:
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error al leer los registros de la hoja '{sheet_name}': {e}")
        return pd.DataFrame()

def get_all_records(sheet):
    if sheet is None:
        return pd.DataFrame()
    try:
        return pd.DataFrame(sheet.get_all_records())
    except Exception as e:
        st.error(f"Error al leer los registros de la hoja: {e}")
        return pd.DataFrame()

def highlight_overdue(row):
    deadline = pd.to_datetime(row['Fecha límite'], errors='coerce').date()
    today = datetime.now().date()
    return ['background-color: #ffcccc'] * len(row) if pd.notna(deadline) and deadline < today and row['Estado'] != 'Finalizada' else [''] * len(row)

# --- FUNCIONES PARA COMENTARIOS Y REPORTES ---
def generar_reporte_markdown(task_data, comments_df):
    '''Genera un reporte de tarea en formato Markdown.'''
    reporte = f'''
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
'''
    if not comments_df.empty:
        # Ordenar comentarios por fecha ascendente para el reporte
        comments_df_sorted = comments_df.sort_values(by="Fecha", ascending=True)
        for _, comment in comments_df_sorted.iterrows():
            fecha_comentario = pd.to_datetime(comment['Fecha']).strftime('%d/%m/%Y')
            reporte += f'''
**Fecha:** {fecha_comentario}
> {comment['Comentario']}

'''
    else:
        reporte += "\n_No hay avances registrados para esta tarea._"

    return reporte



def get_comments_for_task(client, task_id):
    all_comments = get_cached_sheet_data(client, "Comentarios")
    if all_comments.empty:
        return pd.DataFrame()

    # Asegurar que la columna de fecha sea datetime para ordenar correctamente
    all_comments['Fecha'] = pd.to_datetime(all_comments['Fecha'], errors='coerce')
    task_comments = all_comments[all_comments["ID_Tarea"].astype(str) == str(task_id)]
    return task_comments.sort_values(by="Fecha", ascending=False)

def add_comment_to_task(client, task_id, comment_text, comment_date):
    comments_sheet = get_sheet(client, "Comentarios")
    if comments_sheet is None: return False

    # Usar la fecha provista y formatearla como string
    fecha_str = comment_date.strftime("%Y-%m-%d")
    comments_sheet.append_row([task_id, fecha_str, comment_text])
    st.cache_data.clear()
    return True

# --- SECCIÓN DE TAREAS (REFACTORIZADA) ---
def seccion_tareas(client, personal_list):
    st.subheader("📋 Gestión de Tareas")
    df_tasks = get_cached_sheet_data(client, "Tareas")
    sheet = get_sheet(client, "Tareas") # Necesario para escribir

    if sheet is None: return

    # --- MÉTRICAS ---
    if not df_tasks.empty:
        try:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Tareas", len(df_tasks))
            col2.metric("Pendientes", (df_tasks['Estado'] == "Pendiente").sum())
            col3.metric("En curso", (df_tasks['Estado'] == "En curso").sum())
            col4.metric("Finalizadas", (df_tasks['Estado'] == "Finalizada").sum())
        except KeyError:
            st.error("La columna 'Estado' no se encontró en la hoja de Tareas. No se pueden mostrar las métricas.")

    st.markdown("---")

    # --- PESTAÑAS ---
    vista_general, nueva_tarea, detalles = st.tabs(["📊 Vista General", "➕ Nueva Tarea", "🔍 Detalles y Comentarios"])

    with vista_general:
        # --- FILTROS ---
        if not df_tasks.empty:
            st.markdown("#### Filtros")
            col1, col2 = st.columns(2)
            status_options = df_tasks['Estado'].unique().tolist()
            responsable_options = df_tasks['Responsable'].unique().tolist()
            selected_statuses = col1.multiselect("Filtrar por Estado", options=status_options)
            selected_responsables = col2.multiselect("Filtrar por Responsable", options=responsable_options)

            df_filtered = df_tasks.copy()
            if selected_statuses:
                df_filtered = df_filtered[df_filtered['Estado'].isin(selected_statuses)]
            if selected_responsables:
                df_filtered = df_filtered[df_filtered['Responsable'].isin(selected_responsables)]
        else:
            df_filtered = df_tasks.copy()

        # --- VISTA DE TABLA ---
        if not df_filtered.empty:
            df_filtered['Fecha límite'] = pd.to_datetime(df_filtered['Fecha límite'], errors='coerce')
            df_display = df_filtered.sort_values(by="Fecha límite").copy()
            today = datetime.now().date()
            df_display['Título Tarea'] = df_display.apply(
                lambda row: f"🚨 {row['Título Tarea']}" if pd.notna(row['Fecha límite']) and row['Fecha límite'].date() < today and row['Estado'] != 'Finalizada' else row['Título Tarea'],
                axis=1
            )
            st.dataframe(df_display.style.apply(highlight_overdue, axis=1),
                         column_order=("ID", "Título Tarea", "Responsable", "Fecha límite", "Estado"),
                         width='stretch', hide_index=True,
                         column_config={'Fecha límite': st.column_config.DateColumn(format="DD/MM/YYYY")})
        else:
            st.info("No hay tareas que coincidan con los filtros." if not df_tasks.empty else "No hay tareas registradas.")

    with nueva_tarea:
        with st.form("nueva_tarea_form", clear_on_submit=True):
            st.markdown("#### Ingresar datos de la nueva tarea")
            personal_options = ["Seleccione persona..."] + personal_list
            titulo_tarea = st.text_input("Título Tarea")
            tarea = st.text_area("Descripción Completa de la Tarea")
            responsable = st.selectbox("Responsable", options=personal_options, key="add_resp", index=0)
            fecha_limite = st.date_input("Fecha límite")
            estado = st.selectbox("Estado", ["Pendiente", "En curso", "Finalizada"], key="add_estado")

            if st.form_submit_button("Agregar Tarea"):
                if responsable == "Seleccione persona...":
                    st.warning("Por favor, seleccione un responsable.")
                elif not all([titulo_tarea, tarea, responsable, fecha_limite, estado]):
                    st.warning("Todos los campos son obligatorios.")
                else:
                    new_id = (max(df_tasks['ID'].astype(int)) + 1) if not df_tasks.empty else 1
                    sheet.append_row([new_id, titulo_tarea, tarea, responsable, fecha_limite.strftime('%Y-%m-%d'), estado])
                    st.cache_data.clear()
                    st.success(f"¡Tarea ID {new_id} agregada!")
                    st.rerun()

    with detalles:
        if not df_tasks.empty:
            # Usar el dataframe original (df_tasks) para el selector, para poder ver detalles incluso si está filtrado
            task_options = [f"{row['ID']} - {row['Título Tarea']}" for _, row in df_tasks.iterrows()]
            option_to_show = st.selectbox("Selecciona una tarea para ver sus detalles", options=[""] + task_options, key="view_select_details")

            if option_to_show:
                id_to_show = option_to_show.split(' - ')[0]
                task_data = df_tasks[df_tasks["ID"] == int(id_to_show)].iloc[0]
                comments_df = get_comments_for_task(client, id_to_show)

                st.markdown(f"#### Detalles de la Tarea: {task_data['Título Tarea']}")
                # Contenedor para los detalles
                with st.container():
                    st.write(f"**Descripción:**")
                    st.markdown(f"> {task_data['Tarea']}")
                    st.write(f"**Responsable:** {task_data['Responsable']}")
                    st.write(f"**Estado:** {task_data['Estado']}")

                # Expander para el reporte
                with st.expander("📄 Ver Reporte en Markdown"):
                    reporte_md = generar_reporte_markdown(task_data, comments_df)
                    st.markdown(reporte_md)
                    st.download_button(
                        label="Descargar Reporte",
                        data=reporte_md,
                        file_name=f"reporte_tarea_{id_to_show}.md",
                        mime="text/markdown",
                    )

                st.markdown("--- ")
                # Lógica de comentarios
                st.markdown("#### Historial de Avances y Comentarios")
                if not comments_df.empty:
                    st.dataframe(comments_df, width='stretch', hide_index=True,
                                 column_config={'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")})
                else:
                    st.info("Esta tarea aún no tiene comentarios.")

                with st.form(f"comment_form_{id_to_show}", clear_on_submit=True):
                    comment_date = st.date_input("Fecha del comentario", value=datetime.now())
                    new_comment = st.text_area("Añadir nuevo comentario o avance")
                    if st.form_submit_button("Guardar Comentario"):
                        if new_comment and comment_date:
                            if add_comment_to_task(client, id_to_show, new_comment, comment_date):
                                st.success("Comentario añadido.")
                                st.rerun()
                        else:
                            st.warning("El comentario no puede estar vacío.")

                st.markdown("---")
                # Lógica de modificación
                with st.expander("✏️ Modificar / 🗑️ Eliminar Tarea Seleccionada"):
                    personal_options = ["Seleccione persona..."] + personal_list
                    try:
                        default_resp_idx = personal_options.index(task_data["Responsable"])
                    except ValueError:
                        default_resp_idx = 0

                    with st.form(f"edit_form_{id_to_show}"):
                        st.write(f"**Modificando Tarea ID: {id_to_show}**")
                        titulo_tarea = st.text_input("Título Tarea", value=task_data['Título Tarea'])
                        tarea = st.text_area("Descripción Completa", value=task_data['Tarea'])
                        responsable = st.selectbox("Responsable", options=personal_options, index=default_resp_idx)
                        fecha_limite = st.date_input("Fecha límite", value=pd.to_datetime(task_data["Fecha límite"]))
                        estado = st.selectbox("Estado", ["Pendiente", "En curso", "Finalizada"], index=["Pendiente", "En curso", "Finalizada"].index(task_data["Estado"]))

                        col_mod, col_del = st.columns(2)
                        if col_mod.form_submit_button("Guardar Cambios"):
                            if responsable == "Seleccione persona...":
                                st.warning("Por favor, seleccione un responsable.")
                            else:
                                sheet.update_cell(task_data.name + 2, 2, titulo_tarea)
                                sheet.update_cell(task_data.name + 2, 3, tarea)
                                sheet.update_cell(task_data.name + 2, 4, responsable)
                                sheet.update_cell(task_data.name + 2, 5, fecha_limite.strftime('%Y-%m-%d'))
                                sheet.update_cell(task_data.name + 2, 6, estado)
                                st.cache_data.clear()
                                st.success("¡Tarea actualizada!")
                                st.rerun()

                        if col_del.form_submit_button("Eliminar Tarea"):
                            sheet.delete_rows(task_data.name + 2)
                            st.cache_data.clear()
                            st.success("¡Tarea eliminada!")
                            st.rerun()
        else:
            st.info("No hay tareas para mostrar detalles.")

# --- OTRAS SECCIONES (SIN CAMBIOS) ---
def seccion_vacaciones(client, personal_list):
    st.subheader("📅 Registro de Licencias y Vacaciones")
    df = get_cached_sheet_data(client, "Vacaciones")
    sheet = get_sheet(client, "Vacaciones") # Necesario para escribir
    if sheet is None: return

    # --- MÉTRICAS ---
    if not df.empty:
        # Asegurarse que las columnas de fecha son datetime
        df['Fecha inicio'] = pd.to_datetime(df['Fecha inicio'], errors='coerce')
        df['Fecha fin'] = pd.to_datetime(df['Fecha fin'], errors='coerce')
        today = pd.to_datetime(datetime.now().date())

        en_curso = ((df['Fecha inicio'] <= today) & (df['Fecha fin'] >= today)).sum()
        proximas = (df['Fecha inicio'] > today).sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Registros", len(df))
        col2.metric("Licencias en Curso", en_curso)
        col3.metric("Próximas Licencias", proximas)

    st.markdown("---")

    # --- PESTAÑAS ---
    vista_general, nueva_licencia, modificar_licencia = st.tabs(["📊 Vista General", "➕ Nueva Licencia", "✏️ Modificar / Eliminar"])

    with vista_general:
        st.dataframe(df, width='stretch', hide_index=True,
                     column_config={
                         'Fecha solicitud': st.column_config.DateColumn(format="DD/MM/YYYY"),
                         'Fecha inicio': st.column_config.DateColumn(format="DD/MM/YYYY"),
                         'Fecha fin': st.column_config.DateColumn(format="DD/MM/YYYY")
                     })

    with nueva_licencia:
        with st.form("nueva_vacacion_form", clear_on_submit=True):
            st.markdown("#### Ingresar datos de la nueva licencia")
            tipo_options = ["Licencia Ordinaria 2024", "Licencia Ordinaria 2025"]
            personal_options = ["Seleccione persona..."] + personal_list

            nombre = st.selectbox("Apellido, Nombres", options=personal_options, key="add_vac_nombre", index=0)
            fecha_solicitud = st.date_input("Fecha de Solicitud", value=datetime.now())
            tipo = st.selectbox("Tipo", options=tipo_options, index=0)
            fecha_inicio = st.date_input("Fecha de Inicio")
            fecha_fin = st.date_input("Fecha de Fin")
            observaciones = st.text_area("Observaciones")

            if st.form_submit_button("Agregar Registro"):
                if nombre == "Seleccione persona...":
                    st.warning("Por favor, seleccione una persona.")
                elif not all([nombre, fecha_solicitud, tipo, fecha_inicio, fecha_fin]):
                    st.warning("Todos los campos obligatorios no pueden estar vacíos.")
                else:
                    new_row = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), observaciones]
                    sheet.append_row(new_row)
                    st.cache_data.clear()
                    st.success("Registro agregado exitosamente.")
                    st.rerun()

    with modificar_licencia:
        if not df.empty:
            df['row_number'] = range(2, len(df) + 2)
            options = [f"Fila {row['row_number']}: {row['Apellido, Nombres']} ({row['Tipo']})" for _, row in df.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro", options=[""] + options, key="edit_vac_select")

            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df[df['row_number'] == row_number_to_edit].iloc[0]

                with st.form(f"edit_vac_form_{row_number_to_edit}"):
                    st.write(f"**Modificando Registro de la Fila: {row_number_to_edit}**")
                    personal_options = ["Seleccione persona..."] + personal_list
                    tipo_options = ["Licencia Ordinaria 2024", "Licencia Ordinaria 2025"]
                    try:
                        default_nombre_idx = personal_options.index(record_data["Apellido, Nombres"])
                    except ValueError:
                        default_nombre_idx = 0
                    try:
                        default_tipo_idx = tipo_options.index(record_data["Tipo"])
                    except ValueError:
                        default_tipo_idx = 0

                    nombre = st.selectbox("Apellido, Nombres", options=personal_options, index=default_nombre_idx)
                    fecha_solicitud = st.date_input("Fecha de Solicitud", value=pd.to_datetime(record_data["Fecha solicitud"]))
                    tipo = st.selectbox("Tipo", options=tipo_options, index=default_tipo_idx)
                    fecha_inicio = st.date_input("Fecha de Inicio", value=pd.to_datetime(record_data["Fecha inicio"]))
                    fecha_fin = st.date_input("Fecha de Fin", value=pd.to_datetime(record_data["Fecha fin"]))
                    observaciones = st.text_area("Observaciones", value=record_data["Observaciones"])

                    col_mod, col_del = st.columns(2)
                    if col_mod.form_submit_button("Guardar Cambios"):
                        if nombre == "Seleccione persona...":
                            st.warning("Por favor, seleccione una persona.")
                        else:
                            update_values = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'), observaciones]
                            sheet.update(f'A{row_number_to_edit}:F{row_number_to_edit}', [update_values])
                            st.cache_data.clear()
                            st.success("¡Registro actualizado!")
                            st.rerun()

                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        st.cache_data.clear()
                        st.success("¡Registro eliminado!")
                        st.rerun()
        else:
            st.info("No hay registros para modificar o eliminar.")

def seccion_notas(client, personal_list):
    st.subheader("📝 Registro de Notas y Solicitudes")
    df = get_cached_sheet_data(client, "Notas")
    sheet = get_sheet(client, "Notas") # Necesario para escribir
    if sheet is None: return

    # --- MÉTRICAS ---
    if not df.empty:
        try:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total de Notas", len(df))
            col2.metric("Pendientes", (df['Estado'] == "Pendiente").sum())
            col3.metric("Realizadas", (df['Estado'] == "Realizado").sum())
            col4.metric("Rechazadas", (df['Estado'] == "Rechazado").sum())
        except KeyError:
            st.error("La columna 'Estado' no se encontró en la hoja de Notas. No se pueden mostrar las métricas.")

    st.markdown("---")

    # --- PESTAÑAS ---
    vista_general, nueva_nota, modificar_nota = st.tabs(["📊 Vista General", "➕ Nueva Nota", "✏️ Modificar / Eliminar"])

    with vista_general:
        # --- FILTROS ---
        if not df.empty:
            status_options = df['Estado'].unique().tolist()
            selected_statuses = st.multiselect("Filtrar por Estado", options=status_options, key="filtro_notas_estado")
            if selected_statuses:
                df_filtered = df[df['Estado'].isin(selected_statuses)]
            else:
                df_filtered = df.copy()
        else:
            df_filtered = df.copy()

        # --- VISTA DE TABLA ---
        if not df_filtered.empty:
            for col in ['DNI', 'Teléfono']:
                if col in df_filtered.columns:
                    df_filtered[col] = df_filtered[col].astype(str).replace('nan', '')
            def style_estado(estado):
                if estado == 'Realizado': return 'color: green'
                elif estado == 'Rechazado': return 'color: red'
                elif estado == 'Pendiente': return 'color: orange'
                return ''
            st.dataframe(df_filtered.style.map(style_estado, subset=['Estado']), width='stretch', hide_index=True,
                         column_config={'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")})
        else:
            st.info("No hay notas que coincidan con el filtro." if not df.empty else "No hay notas registradas.")

    with nueva_nota:
        with st.form("nueva_nota_form", clear_on_submit=True):
            st.markdown("#### Ingresar datos de la nueva nota/solicitud")
            estados_options = ["Pendiente", "Realizado", "Rechazado"]
            personal_options = ["Seleccione persona..."] + personal_list
            fecha = st.date_input("Fecha", value=datetime.now())
            remitente = st.text_area("Remitente(s)")
            dni = st.text_input("DNI(s)")
            telefono = st.text_input("Teléfono(s)")
            motivo = st.text_area("Motivo")
            responsable = st.selectbox("Responsable", options=personal_options, index=0)
            estado = st.selectbox("Estado", options=estados_options, index=0)
            if st.form_submit_button("Agregar Nota"):
                if responsable == "Seleccione persona...":
                    st.warning("Por favor, seleccione un responsable.")
                elif not all([fecha, remitente, motivo, responsable, estado]):
                    st.warning("Los campos Fecha, Remitente, Motivo, Responsable y Estado son obligatorios.")
                else:
                    new_row = [fecha.strftime('%Y-%m-%d'), remitente, dni, telefono, motivo, responsable, estado]
                    sheet.append_row(new_row)
                    st.cache_data.clear()
                    st.success("Nota/Solicitud agregada exitosamente.")
                    st.rerun()

    with modificar_nota:
        if not df.empty:
            df['row_number'] = range(2, len(df) + 2)
            options = [f"Fila {row['row_number']}: {row['Motivo']} ({row['Remitente']})" for _, row in df.iterrows()]
            option_to_edit = st.selectbox("Selecciona un registro", options=[""] + options, key="edit_nota_select")
            if option_to_edit:
                row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
                record_data = df[df['row_number'] == row_number_to_edit].iloc[0]
                with st.form(f"edit_nota_form_{row_number_to_edit}"):
                    st.write(f"**Modificando Registro de la Fila: {row_number_to_edit}**")
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
                            st.cache_data.clear()
                            st.success("¡Registro actualizado!")
                            st.rerun()
                    if col_del.form_submit_button("Eliminar Registro"):
                        sheet.delete_rows(row_number_to_edit)
                        st.cache_data.clear()
                        st.success("¡Registro eliminado!")
                        st.rerun()
        else:
            st.info("No hay registros para modificar o eliminar.")

def seccion_recordatorios(client, personal_list):
    st.subheader("🔔 Recordatorios Importantes")
    df = get_cached_sheet_data(client, "Recordatorios")
    sheet = get_sheet(client, "Recordatorios") # Necesario para escribir
    if sheet is None: return

    # --- MÉTRICAS ---
    st.metric("Total de Recordatorios", len(df))
    st.markdown("---")

    # --- PESTAÑAS ---
    vista_general, agregar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar / 🗑️ Eliminar"])

    with vista_general:
        st.dataframe(df, hide_index=True, width='content',
                     column_config={
                         'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                     })

    with agregar_eliminar:
        with st.form("recordatorios_form", clear_on_submit=True):
            st.markdown("#### Agregar nuevo recordatorio")
            personal_options = ["Seleccione persona..."] + personal_list
            fecha = st.date_input("Fecha del recordatorio")
            mensaje = st.text_area("Mensaje")
            responsable = st.selectbox("Responsable", options=personal_options, index=0)

            if st.form_submit_button("Agregar Recordatorio"):
                if responsable == "Seleccione persona...":
                    st.warning("Por favor, seleccione un responsable.")
                elif not all([fecha, mensaje, responsable]):
                    st.warning("Todos los campos son obligatorios.")
                else:
                    sheet.append_row([fecha.strftime('%Y-%m-%d'), mensaje, responsable])
                    st.cache_data.clear()
                    st.success("Recordatorio agregado.")
                    st.rerun()

        st.markdown("---")

        if not df.empty:
            st.markdown("#### Eliminar un recordatorio")
            df['row_number'] = range(2, len(df) + 2)
            options = [f"Fila {row['row_number']}: {row['Mensaje']} ({row['Fecha']})" for _, row in df.iterrows()]
            row_to_delete_display = st.selectbox("Selecciona un recordatorio para eliminar", options=[""] + options, key="delete_reminder")

            if st.button("Eliminar Recordatorio Seleccionado"):
                if row_to_delete_display:
                    row_index = int(row_to_delete_display.split(':')[0].replace('Fila ', ''))
                    sheet.delete_rows(row_index)
                    st.cache_data.clear()
                    st.success("Recordatorio eliminado.")
                    st.rerun()
                else:
                    st.warning("Por favor, selecciona un recordatorio para eliminar.")

def seccion_compensados(client, personal_list):
    st.subheader("⏱️ Registro de Compensatorios")
    df = get_cached_sheet_data(client, "Compensados")
    sheet = get_sheet(client, "Compensados") # Necesario para escribir
    if sheet is None: return

    # --- MÉTRICAS ---
    st.metric("Total de Registros", len(df))
    st.markdown("---")

    # --- PESTAÑAS ---
    vista_general, agregar_eliminar = st.tabs(["📊 Vista General", "➕ Agregar / 🗑️ Eliminar"])

    with vista_general:
        st.dataframe(df, width='stretch', hide_index=True,
                     column_config={
                         'Fecha Solicitud': st.column_config.DateColumn(format="DD/MM/YYYY"),
                         'Desde fecha': st.column_config.DateColumn(format="DD/MM/YYYY"),
                         'Hasta fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                     })

    with agregar_eliminar:
        # Formulario para agregar
        with st.form("compensados_form", clear_on_submit=True):
            st.markdown("#### Agregar nuevo registro")
            personal_options = ["Seleccione persona..."] + personal_list
            tipo_options = ["Compensatorio"]

            nombre = st.selectbox("Apellido, Nombre", options=personal_options, index=0)
            fecha_solicitud = st.date_input("Fecha Solicitud", value=datetime.now())
            tipo = st.selectbox("Tipo", options=tipo_options, index=0)

            col1, col2 = st.columns(2)
            desde_fecha = col1.date_input("Desde fecha")
            desde_hora = col2.time_input("Desde hora")
            hasta_fecha = col1.date_input("Hasta fecha")
            hasta_hora = col2.time_input("Hasta hora")

            if st.form_submit_button("Agregar Registro"):
                if nombre == "Seleccione persona...":
                    st.warning("Por favor, seleccione una persona.")
                elif not all([nombre, fecha_solicitud, tipo, desde_fecha, desde_hora, hasta_fecha, hasta_hora]):
                    st.warning("Todos los campos son obligatorios.")
                else:
                    new_row = [nombre, fecha_solicitud.strftime('%Y-%m-%d'), tipo, desde_fecha.strftime('%Y-%m-%d'), desde_hora.strftime('%H:%M'), hasta_fecha.strftime('%Y-%m-%d'), hasta_hora.strftime('%H:%M')]
                    sheet.append_row(new_row)
                    st.cache_data.clear()
                    st.success("Registro de compensatorio agregado.")
                    st.rerun()

        st.markdown("---")

        # Lógica para eliminar
        if not df.empty:
            st.markdown("#### Eliminar un registro")
            df['row_number'] = range(2, len(df) + 2)
            options = [f"Fila {row['row_number']}: {row['Apellido, Nombre']} - {row['Desde fecha']} {row['Desde hora']}" for _, row in df.iterrows()]
            row_to_delete_display = st.selectbox("Selecciona un registro para eliminar", options=[""] + options, key="delete_compensado")

            if st.button("Eliminar Registro Seleccionado"):
                if row_to_delete_display:
                    row_index = int(row_to_delete_display.split(':')[0].replace('Fila ', ''))
                    sheet.delete_rows(row_index)
                    st.cache_data.clear()
                    st.success("Registro eliminado.")
                    st.rerun()
                else:
                    st.warning("Por favor, selecciona un registro para eliminar.")

def seccion_calendario(client):
    st.subheader("🗓️ Calendario Unificado")

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "initialView": "dayGridMonth",
        "editable": False,
        "selectable": True,
    }

    calendar_events = []

    # Cargar Tareas
    df_tasks = get_cached_sheet_data(client, "Tareas")
    if not df_tasks.empty:
        df_tasks['Fecha límite'] = pd.to_datetime(df_tasks['Fecha límite'], errors='coerce')
        for _, row in df_tasks.iterrows():
            if pd.notna(row['Fecha límite']):
                calendar_events.append({
                    "title": f"Tarea: {row['Título Tarea']}",
                    "start": row['Fecha límite'].strftime('%Y-%m-%d'),
                    "end": row['Fecha límite'].strftime('%Y-%m-%d'),
                    "color": "#FF6347",  # Rojo Tomate
                })

    # Cargar Vacaciones
    df_vacations = get_cached_sheet_data(client, "Vacaciones")
    if not df_vacations.empty:
        df_vacations['Fecha inicio'] = pd.to_datetime(df_vacations['Fecha inicio'], errors='coerce')
        df_vacations['Fecha fin'] = pd.to_datetime(df_vacations['Fecha fin'], errors='coerce')
        for _, row in df_vacations.iterrows():
            if pd.notna(row['Fecha inicio']) and pd.notna(row['Fecha fin']):
                calendar_events.append({
                    "title": f"Licencia: {row['Apellido, Nombres']}",
                    "start": row['Fecha inicio'].strftime('%Y-%m-%d'),
                    "end": (row['Fecha fin'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), # +1 para incluir el día final
                    "color": "#1E90FF",  # Azul Dodger
                })

    # Cargar Compensatorios
    df_compensados = get_cached_sheet_data(client, "Compensados")
    if not df_compensados.empty:
        df_compensados['Desde fecha'] = pd.to_datetime(df_compensados['Desde fecha'], errors='coerce')
        df_compensados['Hasta fecha'] = pd.to_datetime(df_compensados['Hasta fecha'], errors='coerce')
        for _, row in df_compensados.iterrows():
            if pd.notna(row['Desde fecha']) and pd.notna(row['Hasta fecha']):
                calendar_events.append({
                    "title": f"Compensatorio: {row['Apellido, Nombre']}",
                    "start": row['Desde fecha'].strftime('%Y-%m-%d'),
                    "end": (row['Hasta fecha'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), # +1 para incluir el día final
                    "color": "#32CD32", # Verde Lima
                })

    calendar(events=calendar_events, options=calendar_options)


# --- APP PRINCIPAL ---
def main():
    st.set_page_config(page_title="Gestor de Proyectos", layout="wide")
    st.markdown("<h1 style='text-align:center'>📊 Gestor de Proyectos</h1>", unsafe_allow_html=True)

    # Estilos personalizados
    st.markdown("""
    <style>
    .block-container {padding-top:2rem; padding-bottom:2rem;}
    .stDataFrame {border-radius: 10px; overflow: hidden;}
    </style>
    """, unsafe_allow_html=True)

    client = connect_to_google_sheets()

    if client:
        personal_list = get_personal_list(client)
        if not personal_list:
            st.warning("No se pudo cargar la lista de personal. Por favor, revisa la pestaña 'Personal' en tu Google Sheet.")

        with st.sidebar:
            seccion = option_menu(
                "Menú Principal",
                ["Tareas", "Vacaciones", "Compensados", "Notas", "Recordatorios", "Calendario"],
                icons=['list-check', 'calendar-check', 'clock-history', 'sticky', 'bell', 'calendar'],
                menu_icon="cast",
                default_index=0
            )

        st.sidebar.markdown("---")
        st.sidebar.info("Esta app utiliza Google Sheets como backend.")

        if seccion == "Tareas":
            seccion_tareas(client, personal_list)
        elif seccion == "Vacaciones":
            seccion_vacaciones(client, personal_list)
        elif seccion == "Compensados":
            seccion_compensados(client, personal_list)
        elif seccion == "Notas":
            seccion_notas(client, personal_list)
        elif seccion == "Recordatorios":
            seccion_recordatorios(client, personal_list)
        elif seccion == "Calendario":
            seccion_calendario(client)

if __name__ == "__main__":
    main()
