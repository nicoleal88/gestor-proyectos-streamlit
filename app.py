import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
from datetime import datetime

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


    comments_sheet = get_sheet(client, "Comentarios")
    if comments_sheet is None: return pd.DataFrame()

    all_comments = get_all_records(comments_sheet)
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
    return True

# --- SECCIÓN DE TAREAS (REFACTORIZADA) ---
def seccion_tareas(client, personal_list):
    st.subheader("Gestión de Tareas")
    sheet = get_sheet(client, "Tareas")
    if sheet is None: return

    df_tasks = get_all_records(sheet)

    # --- FILTROS ---
    if not df_tasks.empty:
        st.markdown("#### Filtros")
        col1, col2 = st.columns(2)

        # Opciones para los filtros
        status_options = df_tasks['Estado'].unique().tolist()
        responsable_options = df_tasks['Responsable'].unique().tolist()

        # Widgets de multiselección
        selected_statuses = col1.multiselect("Filtrar por Estado", options=status_options)
        selected_responsables = col2.multiselect("Filtrar por Responsable", options=responsable_options)

        # Aplicar filtros
        df_filtered = df_tasks.copy()
        if selected_statuses:
            df_filtered = df_filtered[df_filtered['Estado'].isin(selected_statuses)]
        if selected_responsables:
            df_filtered = df_filtered[df_filtered['Responsable'].isin(selected_responsables)]
    else:
        df_filtered = df_tasks.copy()

    st.markdown("---")

    # --- 1. VISTA GENERAL DE TAREAS ---
    if not df_filtered.empty:
        df_filtered['Fecha límite'] = pd.to_datetime(df_filtered['Fecha límite'], errors='coerce')
        df_filtered = df_filtered.sort_values(by="Fecha límite")

        df_display = df_filtered.copy()
        today = datetime.now().date()
        df_display['Título Tarea'] = df_display.apply(
            lambda row: f"🚨 {row['Título Tarea']}" if pd.notna(row['Fecha límite']) and row['Fecha límite'].date() < today and row['Estado'] != 'Finalizada' else row['Título Tarea'],
            axis=1
        )

        st.dataframe(df_display.style.apply(highlight_overdue, axis=1),
                     column_order=("ID", "Título Tarea", "Responsable", "Fecha límite", "Estado"),
                     width='stretch',
                     hide_index=True,
                     column_config={
                         'Fecha límite': st.column_config.DateColumn(format="DD/MM/YYYY")
                     })
    else:
        st.info("No hay tareas que coincidan con los filtros seleccionados." if not df_tasks.empty else "No hay tareas registradas.")

    st.markdown("---")

    # --- 2. AGREGAR NUEVA TAREA ---
    with st.expander("➕ Agregar Nueva Tarea"):
        with st.form("nueva_tarea_form", clear_on_submit=True):
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
                    st.success(f"¡Tarea ID {new_id} agregada!")
                    st.rerun()

    # --- 3. DETALLES, COMENTARIOS Y MODIFICACIÓN ---
    st.markdown("### 🔍 Ver Detalles, Comentarios y Modificar Tarea")
    if not df_filtered.empty:
        # Crear lista de opciones con ID y Título
        task_options = [f"{row['ID']} - {row['Título Tarea']}" for _, row in df_filtered.iterrows()]

        option_to_show = st.selectbox("Selecciona una tarea para ver detalles", options=[""] + task_options, key="view_select")

        if option_to_show:
            # Extraer el ID de la opción seleccionada
            id_to_show = option_to_show.split(' - ')[0]

            task_data = df_filtered[df_filtered["ID"] == int(id_to_show)].iloc[0]
            comments_df = get_comments_for_task(client, id_to_show)

            with st.container():
                st.write(f"**Título:** {task_data['Título Tarea']}")
                st.write(f"**Descripción:**")
                st.markdown(f"> {task_data['Tarea']}")
                st.write(f"**Responsable:** {task_data['Responsable']}")
                st.write(f"**Estado:** {task_data['Estado']}")

                with st.expander("📄 Ver Reporte en Markdown"):
                    reporte_md = generar_reporte_markdown(task_data, comments_df)
                    st.markdown(reporte_md)
                    st.download_button(
                        label="Descargar Reporte",
                        data=reporte_md,
                        file_name=f"reporte_tarea_{id_to_show}.md",
                        mime="text/markdown",
                    )

                st.markdown("#### Historial de Avances y Comentarios")
                if not comments_df.empty:
                    st.dataframe(comments_df, width='stretch', hide_index=True,
                                 column_config={
                                     'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                                 })
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

                with st.expander("✏️ Modificar / 🗑️ Eliminar Tarea Seleccionada"):
                    personal_options = ["Seleccione persona..."] + personal_list
                    try:
                        default_resp_idx = personal_options.index(task_data["Responsable"])
                    except ValueError:
                        default_resp_idx = 0

                    with st.form(f"edit_form_{id_to_show}"):
                        st.write(f"Modificando Tarea ID: {id_to_show}")
                        titulo_tarea = st.text_input("Título Tarea", value=task_data['Título Tarea'])
                        tarea = st.text_area("Descripción Completa", value=task_data['Tarea'])
                        responsable = st.selectbox("Responsable", options=personal_options, index=default_resp_idx)
                        fecha_limite = st.date_input("Fecha límite", value=pd.to_datetime(task_data["Fecha límite"]))
                        estado = st.selectbox("Estado", ["Pendiente", "En curso", "Finalizada"], index=["Pendiente", "En curso", "Finalizada"].index(task_data["Estado"]))

                        col_mod, col_del = st.columns(2)
                        if col_mod.form_submit_button("Guardar Cambios"):
                            if responsable == "Seleccione persona...":
                                st.warning("Por favor, seleccione un responsable.")
                            elif not all([titulo_tarea, tarea, responsable, fecha_limite, estado]):
                                st.warning("Todos los campos son obligatorios.")
                            else:
                                cell = sheet.find(id_to_show)
                                sheet.update_cell(cell.row, 2, titulo_tarea)
                                sheet.update_cell(cell.row, 3, tarea)
                                sheet.update_cell(cell.row, 4, responsable)
                                sheet.update_cell(cell.row, 5, fecha_limite.strftime('%Y-%m-%d'))
                                sheet.update_cell(cell.row, 6, estado)
                                st.success("¡Tarea actualizada!")
                                st.rerun()

                        if col_del.form_submit_button("Eliminar Tarea"):
                            cell = sheet.find(id_to_show)
                            sheet.delete_rows(cell.row)
                            st.success("¡Tarea eliminada!")
                            st.rerun()
    else:
        st.info("Agrega una tarea para poder ver sus detalles.")

# --- OTRAS SECCIONES (SIN CAMBIOS) ---
def seccion_vacaciones(client, personal_list):
    st.subheader("Registro de Licencias y Vacaciones")
    sheet = get_sheet(client, "Vacaciones")
    if sheet is None: return

    df = get_all_records(sheet)
    st.dataframe(df, width='stretch', hide_index=True,
                 column_config={
                     'Fecha solicitud': st.column_config.DateColumn(format="DD/MM/YYYY"),
                     'Fecha inicio': st.column_config.DateColumn(format="DD/MM/YYYY"),
                     'Fecha fin': st.column_config.DateColumn(format="DD/MM/YYYY")
                 })

    st.markdown("---")

    # --- AGREGAR NUEVO REGISTRO ---
    with st.expander("➕ Agregar Nuevo Registro de Licencia/Vacaciones"):
        with st.form("nueva_vacacion_form", clear_on_submit=True):
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
                    st.warning("Los campos 'Apellido, Nombres', 'Fecha de Solicitud', 'Tipo', 'Fecha de Inicio' y 'Fecha de Fin' son obligatorios.")
                else:
                    new_row = [
                        nombre,
                        fecha_solicitud.strftime('%Y-%m-%d'),
                        tipo,
                        fecha_inicio.strftime('%Y-%m-%d'),
                        fecha_fin.strftime('%Y-%m-%d'),
                        observaciones
                    ]
                    sheet.append_row(new_row)
                    st.success("Registro agregado exitosamente.")
                    st.rerun()

    # --- MODIFICAR / ELIMINAR REGISTRO ---
    st.markdown("### ✏️ Modificar / 🗑️ Eliminar Registro")
    if not df.empty:
        df['row_number'] = range(2, len(df) + 2)
        options = [f"Fila {row['row_number']}: {row['Apellido, Nombres']} ({row['Tipo']})" for _, row in df.iterrows()]

        option_to_edit = st.selectbox("Selecciona un registro para editar o eliminar", options=[""] + options, key="edit_vac_select")

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
                    elif not all([nombre, fecha_solicitud, tipo, fecha_inicio, fecha_fin]):
                        st.warning("Los campos obligatorios no pueden estar vacíos.")
                    else:
                        update_values = [
                            nombre,
                            fecha_solicitud.strftime('%Y-%m-%d'),
                            tipo,
                            fecha_inicio.strftime('%Y-%m-%d'),
                            fecha_fin.strftime('%Y-%m-%d'),
                            observaciones
                        ]
                        sheet.update(f'A{row_number_to_edit}:F{row_number_to_edit}', [update_values])
                        st.success("¡Registro actualizado!")
                        st.rerun()

                if col_del.form_submit_button("Eliminar Registro"):
                    sheet.delete_rows(row_number_to_edit)
                    st.success("¡Registro eliminado!")
                    st.rerun()
    else:
        st.info("No hay registros para modificar o eliminar.")

def seccion_notas(client, personal_list):
    st.subheader("Registro de Notas y Solicitudes")
    sheet = get_sheet(client, "Notas")
    if sheet is None: return

    df = get_all_records(sheet)

    # --- VISTA GENERAL DE NOTAS ---
    if not df.empty:
        # Forzar columnas a string para evitar errores de tipo en Arrow
        for col in ['DNI', 'Teléfono']:
            if col in df.columns:
                df[col] = df[col].astype(str).replace('nan', '')

        def style_estado(estado):
            if estado == 'Realizado':
                return 'color: green'
            elif estado == 'Rechazado':
                return 'color: red'
            elif estado == 'Pendiente':
                return 'color: orange'
            return ''

        st.dataframe(df.style.map(style_estado, subset=['Estado']),
                     width='stretch',
                     hide_index=True,
                     column_config={
                         'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                     })
    else:
        st.info("No hay notas o solicitudes registradas.")

    st.markdown("---")

    # --- AGREGAR NUEVA NOTA ---
    with st.expander("➕ Agregar Nueva Nota/Solicitud"):
        with st.form("nueva_nota_form", clear_on_submit=True):
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
                    new_row = [
                        fecha.strftime('%Y-%m-%d'),
                        remitente, dni, telefono, motivo, responsable, estado
                    ]
                    sheet.append_row(new_row)
                    st.success("Nota/Solicitud agregada exitosamente.")
                    st.rerun()

    # --- MODIFICAR / ELIMINAR NOTA ---
    st.markdown("### ✏️ Modificar / 🗑️ Eliminar Nota/Solicitud")
    if not df.empty:
        df['row_number'] = range(2, len(df) + 2)
        options = [f"Fila {row['row_number']}: {row['Motivo']} ({row['Remitente']})" for _, row in df.iterrows()]

        option_to_edit = st.selectbox("Selecciona un registro para editar o eliminar", options=[""] + options, key="edit_nota_select")

        if option_to_edit:
            row_number_to_edit = int(option_to_edit.split(':')[0].replace('Fila ', ''))
            record_data = df[df['row_number'] == row_number_to_edit].iloc[0]

            with st.form(f"edit_nota_form_{row_number_to_edit}"):
                st.write(f"**Modificando Registro de la Fila: {row_number_to_edit}**")

                # Preparar opciones y valores por defecto
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
                    elif not all([fecha, remitente, motivo, responsable, estado]):
                        st.warning("Los campos Fecha, Remitente, Motivo, Responsable y Estado son obligatorios.")
                    else:
                        update_values = [fecha.strftime('%Y-%m-%d'), remitente, dni, telefono, motivo, responsable, estado]
                        sheet.update(f'A{row_number_to_edit}:G{row_number_to_edit}', [update_values])
                        st.success("¡Registro actualizado!")
                        st.rerun()

                if col_del.form_submit_button("Eliminar Registro"):
                    sheet.delete_rows(row_number_to_edit)
                    st.success("¡Registro eliminado!")
                    st.rerun()
    else:
        st.info("No hay registros para modificar o eliminar.")

def seccion_recordatorios(client, personal_list):
    st.subheader("Recordatorios Importantes")
    sheet = get_sheet(client, "Recordatorios")
    if sheet is None: return

    df = get_all_records(sheet)
    st.dataframe(df, hide_index=True,
                 width='content',
                 column_config={
                     'Fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                 })

    with st.expander("➕ Agregar / 🗑️ Eliminar Recordatorio"):
        with st.form("recordatorios_form", clear_on_submit=True):
            personal_options = ["Seleccione persona..."] + personal_list
            st.write("**Agregar nuevo recordatorio**")
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
                    st.success("Recordatorio agregado.")
                    st.rerun()

        if not df.empty:
            st.write("**Eliminar un recordatorio**")
            options = [f"Fila {i+2}: {row['Mensaje']} ({row['Fecha']})" for i, row in df.iterrows()]
            row_to_delete_display = st.selectbox("Selecciona un recordatorio para eliminar", options=[""] + options, key="delete_reminder")

            if st.button("Eliminar Recordatorio Seleccionado"):
                if row_to_delete_display:
                    row_index = options.index(row_to_delete_display)
                    sheet.delete_rows(row_index + 2)
                    st.success("Recordatorio eliminado.")
                    st.rerun()
                else:
                    st.warning("Por favor, selecciona un recordatorio para eliminar.")

def seccion_compensados(client, personal_list):
    st.subheader("Registro de Compensatorios")
    sheet = get_sheet(client, "Compensados")
    if sheet is None: return

    df = get_all_records(sheet)
    st.dataframe(df, width='stretch', hide_index=True,
                 column_config={
                     'Fecha Solicitud': st.column_config.DateColumn(format="DD/MM/YYYY"),
                     'Desde fecha': st.column_config.DateColumn(format="DD/MM/YYYY"),
                     'Hasta fecha': st.column_config.DateColumn(format="DD/MM/YYYY")
                 })

    with st.expander("➕ Agregar / 🗑️ Eliminar Registro de Compensatorio"):
        # Formulario para agregar
        with st.form("compensados_form", clear_on_submit=True):
            st.write("**Agregar nuevo registro**")

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
                    new_row = [
                        nombre,
                        fecha_solicitud.strftime('%Y-%m-%d'),
                        tipo,
                        desde_fecha.strftime('%Y-%m-%d'),
                        desde_hora.strftime('%H:%M'),
                        hasta_fecha.strftime('%Y-%m-%d'),
                        hasta_hora.strftime('%H:%M')
                    ]
                    sheet.append_row(new_row)
                    st.success("Registro de compensatorio agregado.")
                    st.rerun()

        # Lógica para eliminar
        if not df.empty:
            st.write("**Eliminar un registro**")
            # Crear una representación de string única para cada fila
            options = [f"Fila {i+2}: {row['Apellido, Nombre']} - {row['Desde fecha']} {row['Desde hora']}" for i, row in df.iterrows()]
            row_to_delete_display = st.selectbox("Selecciona un registro para eliminar", options=[""] + options, key="delete_compensado")

            if st.button("Eliminar Registro de Compensatorio Seleccionado"):
                if row_to_delete_display:
                    # Encontrar el índice basado en la opción seleccionada
                    row_index = options.index(row_to_delete_display)
                    sheet.delete_rows(row_index + 2) # +2 porque las filas son 1-indexadas y hay una cabecera
                    st.success("Registro eliminado.")
                    st.rerun()
                else:
                    st.warning("Por favor, selecciona un registro para eliminar.")


# --- APP PRINCIPAL ---
def main():
    st.set_page_config(page_title="Gestor de Proyectos", layout="wide")
    st.title("📊 Gestor de Proyectos con Google Sheets")
    st.markdown("---")

    client = connect_to_google_sheets()

    if client:
        personal_list = get_personal_list(client)
        if not personal_list:
            st.warning("No se pudo cargar la lista de personal. Por favor, revisa la pestaña 'Personal' en tu Google Sheet.")

        st.sidebar.title("Navegación")
        secciones = ["Tareas", "Vacaciones", "Compensados", "Notas", "Recordatorios"]
        seccion = st.sidebar.radio("Ir a:", secciones)

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

if __name__ == "__main__":
    main()
