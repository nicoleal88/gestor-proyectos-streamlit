import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_calendar import calendar

def seccion_calendario(client):
    st.subheader("🗓️ Calendario Unificado")

    if "calendar_events" not in st.session_state:
        st.session_state.calendar_events = []

    def update_calendar_events():
        events = []
        df_tasks = st.session_state.get("df_tareas", pd.DataFrame())
        if not df_tasks.empty:
            df_tasks['Fecha límite'] = pd.to_datetime(df_tasks['Fecha límite'], errors='coerce')
            for _, row in df_tasks.iterrows():
                if pd.notna(row['Fecha límite']):
                    events.append({"title": f"Tarea: {row['Título Tarea']}", "start": row['Fecha límite'].strftime('%Y-%m-%d'), "color": "#FF6347"})
        
        df_vacations = st.session_state.get("df_vacaciones", pd.DataFrame())
        if not df_vacations.empty:
            df_vacations['Fecha inicio'] = pd.to_datetime(df_vacations['Fecha inicio'], errors='coerce')
            df_vacations['Fecha fin'] = pd.to_datetime(df_vacations['Fecha fin'], errors='coerce')
            for _, row in df_vacations.iterrows():
                if pd.notna(row['Fecha inicio']) and pd.notna(row['Fecha fin']):
                    events.append({"title": f"Licencia: {row['Apellido, Nombres']}", "start": row['Fecha inicio'].strftime('%Y-%m-%d'), "end": (row['Fecha fin'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d'), "color": "#1E90FF"})
        
        df_compensados = st.session_state.get("df_compensados", pd.DataFrame())
        if not df_compensados.empty:
            df_compensados['Desde fecha'] = pd.to_datetime(df_compensados['Desde fecha'], errors='coerce')
            df_compensados['Hasta fecha'] = pd.to_datetime(df_compensados['Hasta fecha'], errors='coerce')
            for _, row in df_compensados.iterrows():
                if pd.notna(row['Desde fecha']) and pd.notna(row['Hasta fecha']):
                    # Check if time information is available and not empty
                    has_start_time = 'Desde hora' in row and pd.notna(row['Desde hora']) and str(row['Desde hora']).strip() != ''
                    has_end_time = 'Hasta hora' in row and pd.notna(row['Hasta hora']) and str(row['Hasta hora']).strip() != ''
                    if has_start_time and has_end_time:
                        # Format with time
                        start_time = row['Desde hora'].strftime('%H:%M:%S') if hasattr(row['Desde hora'], 'strftime') else str(row['Desde hora'])
                        end_time = row['Hasta hora'].strftime('%H:%M:%S') if hasattr(row['Hasta hora'], 'strftime') else str(row['Hasta hora'])
                        start_dt = f"{row['Desde fecha'].strftime('%Y-%m-%d')}T{start_time}"
                        end_dt = f"{row['Hasta fecha'].strftime('%Y-%m-%d')}T{end_time}"
                    else:
                        # Default to all-day event
                        start_dt = row['Desde fecha'].strftime('%Y-%m-%d')
                        end_dt = (row['Hasta fecha'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    events.append({
                        "title": f"Compensatorio: {row['Apellido, Nombres']}", 
                        "start": start_dt, 
                        "end": end_dt, 
                        "color": "#32CD32"
                    })

        df_eventos = st.session_state.get("df_eventos", pd.DataFrame())
        if not df_eventos.empty:
            df_eventos['Desde fecha'] = pd.to_datetime(df_eventos['Desde fecha'], errors='coerce')
            df_eventos['Hasta fecha'] = pd.to_datetime(df_eventos['Hasta fecha'], errors='coerce')
            for _, row in df_eventos.iterrows():
                if pd.notna(row['Desde fecha']) and pd.notna(row['Hasta fecha']):
                    # Check if time information is available and not empty
                    has_start_time = 'Desde hora' in row and pd.notna(row['Desde hora']) and str(row['Desde hora']).strip() != ''
                    has_end_time = 'Hasta hora' in row and pd.notna(row['Hasta hora']) and str(row['Hasta hora']).strip() != ''
                    if has_start_time and has_end_time:
                        # Format with time
                        start_time = row['Desde hora'].strftime('%H:%M:%S') if hasattr(row['Desde hora'], 'strftime') else str(row['Desde hora'])
                        end_time = row['Hasta hora'].strftime('%H:%M:%S') if hasattr(row['Hasta hora'], 'strftime') else str(row['Hasta hora'])
                        start_dt = f"{row['Desde fecha'].strftime('%Y-%m-%d')}T{start_time}"
                        end_dt = f"{row['Hasta fecha'].strftime('%Y-%m-%d')}T{end_time}"
                    else:
                        # Default to all-day event
                        start_dt = row['Desde fecha'].strftime('%Y-%m-%d')
                        end_dt = (row['Hasta fecha'] + pd.Timedelta(days=1)).strftime('%Y-%m-%d')
                    
                    events.append({
                        "title": f"Evento: {row['Nombre del Evento']}", 
                        "start": start_dt, 
                        "end": end_dt, 
                        "color": "#DDA0DD"
                    })
        df_reminders = st.session_state.get("df_recordatorios", pd.DataFrame())
        if not df_reminders.empty:
            df_reminders['Fecha'] = pd.to_datetime(df_reminders['Fecha'], errors='coerce')
            for _, row in df_reminders.iterrows():
                if pd.notna(row['Fecha']):
                    events.append({"title": f"Recordatorio: {row['Mensaje']}", "start": row['Fecha'].strftime('%Y-%m-%d'), "color": "#8A2BE2"})

        df_personal = st.session_state.get("df_personal", pd.DataFrame())
        if not df_personal.empty and 'Fecha de nacimiento' in df_personal.columns:
            df_personal['Fecha de nacimiento'] = pd.to_datetime(df_personal['Fecha de nacimiento'], errors='coerce', dayfirst=True)
            today = datetime.now()
            for _, row in df_personal.iterrows():
                if pd.notna(row['Fecha de nacimiento']):
                    cumple_actual = row['Fecha de nacimiento'].replace(year=today.year)
                    events.append({"title": f"🎂 Cumpleaños: {row['Apellido, Nombres']}", "start": cumple_actual.strftime('%Y-%m-%d'), "color": "#FFD700"})
                    if today.month == 12:
                        cumple_proximo = row['Fecha de nacimiento'].replace(year=today.year + 1)
                        events.append({"title": f"🎂 Cumpleaños: {row['Apellido, Nombres']}", "start": cumple_proximo.strftime('%Y-%m-%d'), "color": "#FFD700"})

        st.session_state.calendar_events = events

    if "last_section" not in st.session_state or st.session_state.last_section != "Calendario":
        update_calendar_events()
        st.session_state.last_section = "Calendario"

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay",
        },
        "initialView": "timeGridWeek",
        "locale": "es",
    }

    calendar(events=st.session_state.calendar_events, options=calendar_options, key="calendar")
