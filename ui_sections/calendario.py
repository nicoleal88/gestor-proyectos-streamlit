import sys
import os
import requests
from icalendar import Calendar
from datetime import datetime, timedelta, timezone

# Add the parent directory to the path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
from streamlit_calendar import calendar

def get_google_calendar_events(ical_url, days_ahead=365):
    """Obtiene eventos de un calendario de Google a través de su URL iCal.
    
    Args:
        ical_url: URL del calendario iCal
        days_ahead: Número de días en el futuro para buscar eventos recurrentes
        
    Returns:
        Lista de eventos formateados para el calendario
    """
    try:
        import recurring_ical_events
        
        # Hacer la petición al calendario
        response = requests.get(ical_url)
        response.raise_for_status()
        
        # Parsear el calendario
        gcal = Calendar.from_ical(response.text)
        
        # Configurar el rango de fechas para eventos recurrentes
        today = datetime.now()
        max_date = today + timedelta(days=days_ahead)
        
        # Obtener la zona horaria local
        local_tz = today.astimezone().tzinfo
        
        # Obtener todos los eventos en el rango de fechas
        ical_events = recurring_ical_events.of(gcal).between(
            (today.year, today.month, today.day),
            (max_date.year, max_date.month, max_date.day)
        )
        
        events = []
        for event in ical_events:
            start = event.get('DTSTART').dt
            end = event.get('DTEND', event.get('DTSTART')).dt
            
            # Convertir a datetime con zona horaria si es necesario
            if isinstance(start, datetime):
                # Si no tiene zona horaria, asumir UTC
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                # Convertir a zona horaria local
                start = start.astimezone(local_tz)
                start_str = start.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                # Para eventos de todo el día, no necesitamos conversión de zona horaria
                start_str = start.strftime('%Y-%m-%d')
            
            if isinstance(end, datetime):
                # Si no tiene zona horaria, asumir UTC
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                # Convertir a zona horaria local
                end = end.astimezone(local_tz)
                end_str = end.strftime('%Y-%m-%dT%H:%M:%S')
            else:
                # Para eventos de todo el día, sumamos un día
                end_date = end if isinstance(end, datetime) else datetime.combine(end, datetime.min.time())
                end_str = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            event_data = {
                'title': str(event.get('SUMMARY', 'Evento sin título')),
                'start': start_str,
                'end': end_str,
                'color': '#FFA500',  # Naranja para los eventos de Google Calendar
                'allDay': not isinstance(start, datetime)  # True si es evento de todo el día
            }
            
            # Añadir descripción si existe
            description = event.get('DESCRIPTION')
            if description:
                event_data['description'] = str(description)
            
            # Añadir ubicación si existe
            location = event.get('LOCATION')
            if location:
                event_data['location'] = str(location)
            
            events.append(event_data)
            
        return events
    except Exception as e:
        st.error(f"Error al obtener eventos del calendario: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return []

def seccion_calendario(client):
    st.subheader("🗓️ Calendario Unificado")

    if "calendar_events" not in st.session_state:
        st.session_state.calendar_events = []
        
    # Obtener la URL del calendario de Google desde secrets.toml
    GOOGLE_CALENDAR_URL = st.secrets.get("google_calendar", {}).get("url")
    
    # Obtener eventos del calendario de Google si la URL está configurada
    google_events = []
    if GOOGLE_CALENDAR_URL:
        with st.spinner('Cargando eventos del calendario...'):
            google_events = get_google_calendar_events(GOOGLE_CALENDAR_URL)
    else:
        st.warning("No se ha configurado la URL del calendario de Google en secrets.toml")

    def update_calendar_events():
        events = []
        df_tasks = st.session_state.get("df_tareas", pd.DataFrame())
        if not df_tasks.empty:
            df_tasks['Fecha límite'] = pd.to_datetime(df_tasks['Fecha límite'], errors='coerce')
            # Filtrar para excluir tareas con estado "Finalizada"
            df_active_tasks = df_tasks[df_tasks['Estado'] != 'Finalizada']
            for _, row in df_active_tasks.iterrows():
                if pd.notna(row['Fecha límite']):
                    events.append({
                        "title": f"Tarea: {row['Título Tarea']}", 
                        "start": row['Fecha límite'].strftime('%Y-%m-%d'), 
                        "color": "#FF6347",
                        "extendedProps": {
                            "tipo": "tarea",
                            "estado": row.get('Estado', 'Pendiente'),
                            "responsable": row.get('Responsable', 'No asignado')
                        }
                    })
        
        df_vacations = st.session_state.get("df_vacaciones", pd.DataFrame())
        if not df_vacations.empty:
            df_vacations['Fecha inicio'] = pd.to_datetime(df_vacations['Fecha inicio'], errors='coerce')
            df_vacations['Fecha regreso'] = pd.to_datetime(df_vacations['Fecha regreso'], errors='coerce')
            for _, row in df_vacations.iterrows():
                if pd.notna(row['Fecha inicio']) and pd.notna(row['Fecha regreso']):
                    # Usar la fecha de fin directamente (sin sumar un día) ya que ya es el día de regreso
                    # y queremos que el evento termine el día anterior
                    end_date = row['Fecha regreso']
                    events.append({
                        "title": f"Licencia: {row['Apellido, Nombres']}", 
                        "start": row['Fecha inicio'].strftime('%Y-%m-%d'), 
                        "end": end_date.strftime('%Y-%m-%d'), 
                        "color": "#1E90FF",
                        "extendedProps": {
                            "tipo": "vacaciones",
                            "persona": row['Apellido, Nombres'],
                            "descripcion": f"Período de licencia de {row['Apellido, Nombres']} desde {row['Fecha inicio'].strftime('%d/%m/%Y')} hasta {end_date.strftime('%d/%m/%Y')}"
                        }
                    })
        
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

        # Añadir eventos de Google Calendar
        events.extend(google_events)
        
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
