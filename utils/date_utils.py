import requests
import streamlit as st
import pandas as pd
from datetime import datetime

@st.cache_data(ttl=86400)  # Cache por 24 horas
def get_feriados_argentina(year):
    """Obtiene los feriados de Argentina desde la API de Argentina Datos."""
    try:
        url = f"https://api.argentinadatos.com/v1/feriados/{year}"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # Retornamos un diccionario {fecha: nombre}
        return {item['fecha']: item['nombre'] for item in data}
    except Exception as e:
        st.error(f"Error al obtener feriados para {year}: {e}")
        return {}

def calcular_dias_habiles_y_feriados(fecha_inicio, fecha_fin, extra_feriados_dict=None):
    """
    Calcula días de corrido, días hábiles (Lun-Vie) y detecta feriados intermedios.
    fecha_fin se interpreta como el último día de la licencia (inclusive).
    """
    if fecha_fin < fecha_inicio:
        return 0, 0, []

    # Generar rango de fechas
    rango_fechas = pd.date_range(start=fecha_inicio, end=fecha_fin)
    dias_corrido = len(rango_fechas)
    
    # Obtener feriados para los años involucrados
    years = set([d.year for d in rango_fechas])
    feriados_all = {}
    for year in years:
        feriados_all.update(get_feriados_argentina(year))
    
    # Sumar feriados manuales si existen
    if extra_feriados_dict:
        feriados_all.update(extra_feriados_dict)
    
    dias_habiles = 0
    feriados_encontrados = [] # Lista de tuplas (fecha, nombre)
    
    for fecha in rango_fechas:
        fecha_str = fecha.strftime('%Y-%m-%d')
        # Es día hábil si es de lunes a viernes (0-4) y NO es feriado
        if fecha.weekday() < 5:  # Lunes a Viernes
            if fecha_str in feriados_all:
                feriados_encontrados.append((fecha_str, feriados_all[fecha_str]))
            else:
                dias_habiles += 1
        elif fecha_str in feriados_all:
            # Aunque sea fin de semana, informamos que es feriado si está en la lista
            # pero no afecta al conteo de días hábiles ya que ya estaba excluido por ser finde
            feriados_encontrados.append((fecha_str, feriados_all[fecha_str]))
                
    return dias_corrido, dias_habiles, feriados_encontrados

def format_duracion_licencia(fecha_inicio, fecha_fin):
    """Formatea un mensaje con los detalles de la duración."""
    # Obtener feriados manuales del session_state como diccionario {fecha: motivo}
    manual_holidays_dict = {}
    df_manual = st.session_state.get("df_feriados_manuales", pd.DataFrame())
    if not df_manual.empty and 'Fecha' in df_manual.columns:
        # Normalizar nombres de columnas
        df_manual.columns = [str(c).strip() for c in df_manual.columns]
        motivo_col = 'Motivo (Opcional)' if 'Motivo (Opcional)' in df_manual.columns else ('Motivo' if 'Motivo' in df_manual.columns else None)
        
        for _, row in df_manual.iterrows():
            try:
                fecha_dt = pd.to_datetime(row['Fecha'], errors='coerce', dayfirst=True, format='mixed')
                if pd.notna(fecha_dt):
                    f_str = fecha_dt.strftime('%Y-%m-%d')
                    motivo = str(row[motivo_col]) if motivo_col and pd.notna(row[motivo_col]) else "Feriado/Asueto"
                    manual_holidays_dict[f_str] = motivo
            except:
                continue

    corrido, habiles, feriados = calcular_dias_habiles_y_feriados(fecha_inicio, fecha_fin, extra_feriados_dict=manual_holidays_dict)
    
    msg = f"**Duración:** {corrido} días de corrido | **{habiles} días hábiles**."
    if feriados:
        msg += f"\n\n⚠️ Se detectaron {len(feriados)} feriados:"
        for f_date, f_name in feriados:
            # Formatear fecha para el mensaje (DD/MM/YYYY)
            f_display = datetime.strptime(f_date, '%Y-%m-%d').strftime('%d/%m/%Y')
            msg += f"\n- {f_display} ({f_name})"
    
    return msg, corrido, habiles
