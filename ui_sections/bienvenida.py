import streamlit as st
import requests
from datetime import datetime
import pytz
import pandas as pd
import os
import locale
import plotly.graph_objects as go
from typing import Dict, Optional
from ui_sections.pronostico import obtener_pronostico_extendido, mostrar_grafico_pronostico

# Configurar locale en español
spanish_locales = [
    'es_ES.UTF-8', 'es_ES.utf8', 'es_ES', 'es-ES',
    'es_AR.UTF-8', 'es_AR.utf8', 'es_AR', 'es-AR',
    'es_CL.UTF-8', 'es_CL.utf8', 'es_CL', 'es-CL',
    'es_MX.UTF-8', 'es_MX.utf8', 'es_MX', 'es-MX',
    'es_ES', 'es', 'esp', 'spanish'
]

locale_configured = False
for loc in spanish_locales:
    try:
        locale.setlocale(locale.LC_TIME, loc)
        locale_configured = True
        break
    except locale.Error:
        continue

if not locale_configured:
    st.warning("No se pudo configurar el locale en español. Las fechas se mostrarán en inglés.")

@st.cache_data(ttl=3600)  # Cache por 1 hora
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
            pronostico = data.get('daily', [])[:5]  # Solo los próximos 5 días
            # Agregar timestamp a cada día para debug
            for dia in pronostico:
                dia['_cached_at'] = datetime.now().timestamp()
            return pronostico
    except Exception as e:
        st.error(f"Error al obtener el pronóstico: {e}")
    return None

@st.cache_data(ttl=3600)  # Cache por 1 hora
def get_weather(lat=-35.4755, lon=-69.5843):
    """Obtener el clima actual desde OpenWeatherMap"""
    api_key = st.secrets.get('api_keys', {}).get('openweather')
    if not api_key:
        st.warning("No se encontró la clave de OpenWeather API en secrets.toml")
        return None

    try:
        response = requests.get(
            f'https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric&lang=es'
        )
        data = response.json()
        
        if response.status_code == 200:
            return {
                'temperature': data['main']['temp'],
                'feels_like': data['main']['feels_like'],
                'humidity': data['main']['humidity'],
                'pressure': data['main']['pressure'],
                'wind_speed': data['wind']['speed'] * 3.6,  # Convertir a km/h
                'description': data['weather'][0]['description'].capitalize(),
                'visibility': data.get('visibility', 10000),  # En metros
                'timestamp': datetime.now().timestamp()  # Agregar timestamp para debug
            }
    except Exception as e:
        st.error(f"Error al obtener el clima: {e}")
    return None

def get_exchange_rates(base_currency='USD', target_currencies=['ARS', 'EUR', 'BRL']):
    """Obtener tasas de cambio usando la API de exchangerate-api.com"""
    api_key = st.secrets.get('api_keys', {}).get('exchangerate')
    if not api_key:
        st.warning("No se encontró la clave de ExchangeRate API en secrets.toml")
        return None
        
    try:
        response = requests.get(f'https://v6.exchangerate-api.com/v6/{api_key}/latest/{base_currency}')
        data = response.json()
        
        if response.status_code == 200 and data['result'] == 'success':
            rates = data['conversion_rates']
            return {currency: rates.get(currency, 'N/A') for currency in target_currencies}
    except Exception as e:
        st.error(f"Error al obtener tasas de cambio: {e}")
    return None

@st.cache_data(ttl=600)  # Cache por 10 minutos
def obtener_tipo_cambio() -> Optional[Dict[str, Dict[str, float]]]:
    """Obtiene los tipos de cambio de DolarAPI"""
    try:
        # Obtener datos del dólar oficial y blue
        response = requests.get("https://dolarapi.com/v1/dolares/oficial")
        oficial = response.json()
        
        response = requests.get("https://dolarapi.com/v1/dolares/blue")
        blue = response.json()
        
        response = requests.get("https://dolarapi.com/v1/cotizaciones/eur")
        euro = response.json()
        
        return {
            'oficial': {
                'compra': oficial.get('compra', 0),
                'venta': oficial.get('venta', 0),
                'timestamp': datetime.now().timestamp()
            },
            'blue': {
                'compra': blue.get('compra', 0),
                'venta': blue.get('venta', 0),
                'timestamp': datetime.now().timestamp()
            },
            'euro': {
                'compra': euro.get('compra', 0),
                'venta': euro.get('venta', 0),
                'timestamp': datetime.now().timestamp()
            }
        }
    except Exception as e:
        st.error(f"Error al obtener los tipos de cambio: {e}")
        return None

def mostrar_seccion_bienvenida():
    st.title("Bienvenido al Gestor de Proyectos")
    
    # Obtener fecha y hora actual
    now = datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
    
    # Diccionario de traducción para los meses y días
    meses = {
        'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo',
        'April': 'Abril', 'May': 'Mayo', 'June': 'Junio',
        'July': 'Julio', 'August': 'Agosto', 'September': 'Septiembre',
        'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
    }
    
    dias = {
        'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
        'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado',
        'Sunday': 'Domingo'
    }
    
    if locale_configured:
        # Si el locale está configurado, usamos strftime
        fecha = now.strftime('%A, %d de %B de %Y')
    else:
        # Si no, usamos el diccionario de traducción
        dia_semana = dias.get(now.strftime('%A'), now.strftime('%A'))
        mes = meses.get(now.strftime('%B'), now.strftime('%B'))
        fecha = f"{dia_semana}, {now.day} de {mes} de {now.year}"
    
    st.subheader(f"📅 {fecha}")
    st.markdown("---")

    # Obtener el clima actual
    weather = get_weather()
    pronostico = obtener_pronostico_extendido()
    tipos_cambio = obtener_tipo_cambio()
    
    # Mostrar información del clima en 3 columnas
    col1, col2, col3 = st.columns([3, 4, 4])
    
    with col1:
        st.markdown("### 🌤️ Clima en Malargüe")
        if weather:
            st.metric("Temperatura", f"{weather['temperature']:.1f}°C")
            st.caption(f"Sensación térmica: {weather['feels_like']:.1f}°C")
            st.caption(f"{weather['description']}")
            st.caption(f"💧 Humedad: {weather['humidity']:.1f}%")
            st.caption(f"💨 Viento: {weather['wind_speed']:.1f} km/h")
            st.caption(f"🪟 Presión: {weather['pressure']:.1f} hPa")
            if weather.get('visibility'):
                st.caption(f"👁️ Visibilidad: {weather['visibility']/1000:.1f} km")
        else:
            st.warning("No se pudo cargar la información del clima")
    
    with col2:
        st.markdown("### 📈 Pronóstico de Temperaturas")
        if pronostico:
            # Mostrar solo el gráfico de temperaturas
            fig_temp = go.Figure()
            
            # Preparar datos
            fechas = [datetime.fromtimestamp(dia.get('dt', 0)).strftime('%a %d/%m') for dia in pronostico]
            temps_min = [dia.get('temp', {}).get('min') for dia in pronostico]
            temps_max = [dia.get('temp', {}).get('max') for dia in pronostico]
            
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
            
            # Configuración del layout
            fig_temp.update_layout(
                yaxis_title='Temperatura (°C)',
                showlegend=False,
                hovermode='x unified',
                height=300,
                margin=dict(l=0, r=0, t=0, b=0)
            )
            
            st.plotly_chart(fig_temp, use_container_width=True)
        else:
            st.warning("No se pudo cargar el pronóstico de temperaturas")
    
    with col3:
        st.markdown("### 🌧️ Lluvia y Viento")
        if pronostico and len(pronostico) > 0:
            # Crear gráfico combinado de lluvia y viento
            dias = [datetime.fromtimestamp(dia.get('dt', 0)).strftime('%a %d/%m') for dia in pronostico]
            lluvia = [dia.get('pop', 0) * 100 for dia in pronostico]  # Probabilidad de lluvia en %
            viento = [dia.get('wind_speed', 0) for dia in pronostico]  # Velocidad del viento en m/s
            
            fig_lluvia_viento = go.Figure()
            
            # Agregar barras de lluvia
            fig_lluvia_viento.add_trace(go.Bar(
                x=dias,
                y=lluvia,
                name='Prob. lluvia',
                marker_color='rgba(54, 162, 235, 0.6)',
                yaxis='y1'
            ))
            
            # Agregar línea de viento
            fig_lluvia_viento.add_trace(go.Scatter(
                x=dias,
                y=viento,
                name='Viento (km/h)',
                line=dict(color='orange', width=2),
                yaxis='y2'
            ))
            
            # Configurar el diseño del gráfico
            fig_lluvia_viento.update_layout(
                yaxis=dict(
                    title='Prob. lluvia (%)',
                    title_font=dict(color='rgba(54, 162, 235, 1)'),
                    tickfont=dict(color='rgba(54, 162, 235, 1)'),
                    range=[0, 100],
                    showgrid=False
                ),
                yaxis2=dict(
                    title='Viento (km/h)',
                    title_font=dict(color='orange'),
                    tickfont=dict(color='orange'),
                    anchor='x',
                    overlaying='y',
                    side='right',
                    showgrid=False
                ),
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
                hovermode='x',
                height=300,
                margin=dict(l=0, r=0, t=0, b=0),
                xaxis=dict(showgrid=False)
            )
            
            st.plotly_chart(fig_lluvia_viento, use_container_width=True)
        else:
            st.warning("No se pudo cargar el pronóstico de lluvia y viento")
    
    # Mostrar tipos de cambio en una fila separada
    st.markdown("---")
    st.markdown("### 💰 Cotizaciones")
    
    if tipos_cambio:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### **Dólar Oficial**")
            st.metric(label="Compra", value=f"${tipos_cambio['oficial']['compra']:,.2f}")
            st.metric(label="Venta", value=f"${tipos_cambio['oficial']['venta']:,.2f}")
        
        # with col2:
        #     st.markdown("#### **Dólar Blue**")
        #     st.metric(label="Compra", value=f"${tipos_cambio['blue']['compra']:,.2f}")
        #     st.metric(label="Venta", value=f"${tipos_cambio['blue']['venta']:,.2f}")
        
        with col2:
            st.markdown("#### **Euro Oficial**")
            st.metric(label="Compra", value=f"${tipos_cambio['euro']['compra']:,.2f}")
            st.metric(label="Venta", value=f"${tipos_cambio['euro']['venta']:,.2f}")
        
        # with col3:
            
        
        # Mostrar última actualización
        st.markdown(f"<div style='text-align: center;'><small>Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}</small></div>", unsafe_allow_html=True)
    else:
        st.warning("No se pudieron cargar los tipos de cambio")
    
if __name__ == "__main__":
    mostrar_seccion_bienvenida()
