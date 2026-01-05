import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

def obtener_pronostico_extendido(lat=-35.4755, lon=-69.5843):
    """Obtener pronóstico extendido de OpenWeatherMap API"""
    api_key = st.secrets.get('api_keys', {}).get('openweather')
    if not api_key:
        st.warning("No se encontró la clave de OpenWeather API en secrets.toml")
        return None

    try:
        base_url = "https://api.openweathermap.org/data/3.0/onecall"
        params = {
            'lat': lat,
            'lon': lon,
            'exclude': 'current,minutely,hourly,alerts',
            'appid': api_key,
            'units': 'metric',
            'lang': 'es'
        }
        
        response = requests.get(base_url, params=params)
        data = response.json()
        
        if response.status_code == 200:
            return data.get('daily', [])[:5]  # Solo los próximos 5 días
    except Exception as e:
        st.error(f"Error al obtener el pronóstico: {e}")
    return None

def mostrar_grafico_pronostico(datos_pronostico):
    """Mostrar gráfico con el pronóstico extendido"""
    if not datos_pronostico:
        return
    
    # Preparar datos para el gráfico
    fechas = []
    temps_min = []
    temps_max = []
    lluvia = []
    viento = []
    descripciones = []
    
    for dia in datos_pronostico:
        fecha = datetime.fromtimestamp(dia.get('dt', 0)).strftime('%a %d/%m')
        fechas.append(fecha)
        temps_min.append(dia.get('temp', {}).get('min'))
        temps_max.append(dia.get('temp', {}).get('max'))
        lluvia.append(dia.get('pop', 0) * 100)  # Convertir a porcentaje
        viento.append(dia.get('wind_speed', 0))
        descripciones.append(dia.get('weather', [{}])[0].get('description', '').capitalize())
    
    # Crear gráfico de temperatura
    fig_temp = go.Figure()
    
    # Agregar barras de rango de temperatura
    fig_temp.add_trace(go.Bar(
        x=fechas,
        y=[t_max - t_min for t_min, t_max in zip(temps_min, temps_max)],
        base=temps_min,
        name='Rango de temperatura',
        marker_color='rgba(255, 200, 200, 0.5)',
        hoverinfo='skip',
        showlegend=False
    ))
    
    # Agregar línea de temperatura máxima
    fig_temp.add_trace(go.Scatter(
        x=fechas,
        y=temps_max,
        mode='lines+markers+text',
        name='Máx',
        line=dict(color='red', width=2),
        text=[f"{t:.0f}°C" for t in temps_max],
        textposition='top center',
        textfont=dict(color='red')
    ))
    
    # Agregar línea de temperatura mínima
    fig_temp.add_trace(go.Scatter(
        x=fechas,
        y=temps_min,
        mode='lines+markers+text',
        name='Mín',
        line=dict(color='blue', width=2),
        text=[f"{t:.0f}°C" for t in temps_min],
        textposition='bottom center',
        textfont=dict(color='blue')
    ))
    
    # Configuración del layout de temperatura
    fig_temp.update_layout(
        title='Pronóstico de Temperaturas - Próximos 5 días',
        yaxis_title='Temperatura (°C)',
        xaxis_title='Día',
        showlegend=True,
        hovermode='x unified',
        height=400
    )
    
    # Crear gráfico de precipitación y viento
    fig_lluvia_viento = go.Figure()
    
    # Agregar barras de probabilidad de lluvia
    fig_lluvia_viento.add_trace(go.Bar(
        x=fechas,
        y=lluvia,
        name='Prob. lluvia',
        marker_color='rgba(100, 149, 237, 0.7)',
        text=[f"{p:.0f}%" for p in lluvia],
        textposition='auto',
        yaxis='y'
    ))
    
    # Agregar línea de velocidad del viento
    fig_lluvia_viento.add_trace(go.Scatter(
        x=fechas,
        y=viento,
        mode='lines+markers',
        name='Viento (km/h)',
        line=dict(color='green', width=2),
        text=[f"{v} km/h" for v in viento],
        yaxis='y2'
    ))
    
    # Configuración del layout de lluvia/viento
    fig_lluvia_viento.update_layout(
        title='Probabilidad de Lluvia y Velocidad del Viento',
        xaxis_title='Día',
        yaxis=dict(
            title='Prob. Lluvia (%)',
            range=[0, 100],
            side='left',
            showgrid=False
        ),
        yaxis2=dict(
            title='Viento (km/h)',
            range=[0, max(viento) * 1.5 if viento else 20],
            side='right',
            overlaying='y',
            showgrid=False
        ),
        showlegend=True,
        hovermode='x',
        height=400
    )
    
    # Mostrar gráficos
    st.plotly_chart(fig_temp, width='stretch')
    st.plotly_chart(fig_lluvia_viento, width='stretch')
    
    # Mostrar resumen de cada día
    st.markdown("### Detalle por día")
    for i, (fecha, t_min, t_max, prob_lluvia, viento_dia, desc) in enumerate(zip(
        fechas, temps_min, temps_max, lluvia, viento, descripciones
    )):
        with st.expander(f"{fecha}: {desc}"):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Máxima", f"{t_max:.0f}°C")
            with col2:
                st.metric("Mínima", f"{t_min:.0f}°C")
            with col3:
                st.metric("Lluvia", f"{prob_lluvia:.0f}%")
            with col4:
                st.metric("Viento", f"{viento_dia:.1f} km/h")
