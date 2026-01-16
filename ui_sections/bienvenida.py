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

# Configurar locale en español con fallback robusto
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
        print(f"✅ Locale configurado correctamente: {loc}")
        break
    except locale.Error:
        continue

# Si no se pudo configurar el locale, usar implementación alternativa
if not locale_configured:
    print("ℹ️ Usando traducciones manuales para fechas en español")

def formatear_fecha_espanol(datetime_obj, formato='completo'):
    """
    Formatear fecha en español sin depender del locale del sistema.

    Args:
        datetime_obj: objeto datetime
        formato: 'completo' para fecha completa, 'corto' para fecha corta
    """
    # Diccionarios de traducción
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

    # Obtener componentes de fecha en inglés
    dia_semana_ingles = datetime_obj.strftime('%A')
    mes_ingles = datetime_obj.strftime('%B')

    # Traducir a español
    dia_semana = dias.get(dia_semana_ingles, dia_semana_ingles)
    mes = meses.get(mes_ingles, mes_ingles)
    dia = datetime_obj.day
    anio = datetime_obj.year

    if formato == 'completo':
        return f"{dia_semana}, {dia} de {mes} de {anio}"
    elif formato == 'corto':
        return f"{dia:02d}/{datetime_obj.month:02d}/{anio}"
    elif formato == 'dia_semana':
        return dia_semana
    else:
        return f"{dia_semana}, {dia} de {mes} de {anio}"

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
def obtener_tipo_cambio(day_key: str) -> Optional[Dict[str, Dict[str, float]]]:
    """Obtiene los tipos de cambio de ArgentinaDatos API y DolarAPI (para el euro)"""
    try:
        # Obtener datos actuales (últimos 7 días)
        end_date = datetime.now()
        start_date = end_date - pd.Timedelta(days=7)
        
        # Formatear fechas para la API
        def format_date(dt):
            return dt.strftime('%Y/%m/%d')
        
        # Obtener datos para cada tipo de cambio
        def obtener_datos(casa):
            try:
                # Obtener datos para hoy
                hoy = format_date(end_date)
                response = requests.get(
                    f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}/{hoy}",
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    # Verificar si la respuesta es una lista y tiene datos
                    if isinstance(data, list) and len(data) > 0:
                        return data[0]  # Devolver el primer elemento de la lista
                    elif isinstance(data, dict):
                        return data  # Si es un diccionario, devolverlo directamente
                    else:
                        st.warning(f"Formato de datos inesperado para {casa}")
                else:
                    st.warning(f"Error al obtener datos para {casa}: HTTP {response.status_code}")
                return None
            except requests.exceptions.RequestException as e:
                st.error(f"Error de conexión al obtener datos para {casa}: {str(e)}")
            except Exception as e:
                st.error(f"Error inesperado al obtener datos para {casa}: {str(e)}")
            return None
        
        # Obtener datos históricos para calcular variación
        def obtener_historico(casa, dias=7):
            historico = []
            for i in range(dias):
                try:
                    fecha = end_date - pd.Timedelta(days=i)
                    fecha_str = format_date(fecha)
                    response = requests.get(
                        f"https://api.argentinadatos.com/v1/cotizaciones/dolares/{casa}/{fecha_str}",
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        if isinstance(data, list) and len(data) > 0:
                            # Asegurarse de que el dato tenga la fecha
                            dato = data[0]
                            if 'fecha' not in dato:
                                dato['fecha'] = fecha_str
                            historico.append(dato)
                        elif isinstance(data, dict):
                            if 'fecha' not in data:
                                data['fecha'] = fecha_str
                            historico.append(data)
                except requests.exceptions.RequestException as e:
                    st.warning(f"No se pudo obtener histórico para {casa} ({fecha_str}): {str(e)}")
                except Exception as e:
                    st.warning(f"Error procesando histórico para {casa} ({fecha_str}): {str(e)}")
            
            # Ordenar por fecha (más antigua primero)
            historico_ordenado = sorted(historico, key=lambda x: x.get('fecha', ''))
            return historico_ordenado
        
        # Obtener datos actuales desde dolarapi.com
        def obtener_dolarapi(casa):
            try:
                response = requests.get(f"https://dolarapi.com/v1/dolares/{casa}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Asegurarse de que el dato tenga la fecha
                    if 'fecha' not in data:
                        data['fecha'] = format_date(datetime.now())
                    return data
                return None
            except Exception as e:
                st.warning(f"No se pudo obtener datos actuales para {casa} desde dolarapi.com: {str(e)}")
                return None
        
        # Obtener datos actuales
        oficial = obtener_dolarapi('oficial')
        blue = obtener_dolarapi('blue')
        
        # Obtener histórico desde ArgentinaDatos (excluyendo el día actual)
        hist_oficial = obtener_historico('oficial')
        hist_blue = obtener_historico('blue')
        
        # Agregar datos actuales al histórico si están disponibles
        if oficial and hist_oficial:
            # Verificar que no esté ya en el histórico
            hoy = format_date(datetime.now())
            if not any(d.get('fecha', '').startswith(hoy.split('T')[0]) for d in hist_oficial):
                hist_oficial.append(oficial)
        
        if blue and hist_blue:
            hoy = format_date(datetime.now())
            if not any(d.get('fecha', '').startswith(hoy.split('T')[0]) for d in hist_blue):
                hist_blue.append(blue)
        
        # Obtener datos del euro desde dolarapi.com
        def obtener_euro():
            try:
                response = requests.get("https://dolarapi.com/v1/cotizaciones/eur", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    # Asegurarse de que el dato tenga la fecha
                    if 'fecha' not in data:
                        data['fecha'] = format_date(datetime.now())
                    return data
                return None
            except Exception as e:
                st.error(f"Error al obtener datos del euro: {str(e)}")
                return None
        
        euro_data = obtener_euro()
        
        # Función auxiliar para calcular variación
        def calcular_variacion(historico):
            if len(historico) < 2:
                return 0.0
            
            # Ordenar por fecha (más reciente primero)
            historico_ordenado = sorted(historico, key=lambda x: x.get('fecha', ''), reverse=True)
            
            # Obtener el valor de hoy y ayer
            valor_actual = historico_ordenado[0].get('venta', 0) if historico_ordenado else 0
            valor_anterior = historico_ordenado[1].get('venta', 0) if len(historico_ordenado) > 1 else 0
            
            if valor_anterior == 0:
                return 0.0
                
            return ((valor_actual - valor_anterior) / valor_anterior) * 100
        
        # Helper para normalizar fechas a ISO (YYYY-MM-DD)
        def _norm_fecha(fecha_val):
            try:
                return pd.to_datetime(str(fecha_val)).date().isoformat()
            except Exception:
                return None

        return {
            'oficial': {
                'compra': oficial.get('compra', 0) if oficial else 0,
                'venta': oficial.get('venta', 0) if oficial else 0,
                'variacion': calcular_variacion(hist_oficial) if hist_oficial else 0,
                'historico_compra': [d.get('compra', 0) for d in hist_oficial if 'compra' in d],
                'historico_venta': [d.get('venta', 0) for d in hist_oficial if 'venta' in d],
                'fechas': [f for f in (_norm_fecha(d.get('fecha')) for d in hist_oficial) if f],
                'timestamp': datetime.now().timestamp()
            },
            'blue': {
                'compra': blue.get('compra', 0) if blue else 0,
                'venta': blue.get('venta', 0) if blue else 0,
                'variacion': calcular_variacion(hist_blue) if hist_blue else 0,
                'historico_compra': [d.get('compra', 0) for d in hist_blue if 'compra' in d],
                'historico_venta': [d.get('venta', 0) for d in hist_blue if 'venta' in d],
                'fechas': [f for f in (_norm_fecha(d.get('fecha')) for d in hist_blue) if f],
                'timestamp': datetime.now().timestamp()
            },
            'euro': {
                'compra': euro_data.get('compra', 0) if euro_data else 0,
                'venta': euro_data.get('venta', 0) if euro_data else 0,
                'variacion': 0,  # No mostramos variación para el euro
                'historico_compra': [],
                'historico_venta': [],
                'fechas': [],
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
    
    if locale_configured:
        # Si el locale está configurado, usamos strftime
        fecha = now.strftime('%A, %d de %B de %Y')
    else:
        # Si no, usamos la función de formateo manual
        fecha = formatear_fecha_espanol(now, formato='completo')
    
    st.subheader(f"📅 {fecha}")
    
    # --- ALERTAS DE PERSONAL (Cumpleaños y Aniversarios) ---
    df_personal = st.session_state.get('df_personal', pd.DataFrame())
    if not df_personal.empty:
        today_date = now.date()
        lookahead = today_date + pd.Timedelta(days=7)
        personal_alerts = []

        for _, row in df_personal.iterrows():
            nombre_completo = row.get('Apellido, Nombres', row.get('Nombre', ''))
            if not nombre_completo: continue
            
            # Obtener nombre a mostrar (Nombre + Inicial Apellido)
            nombre_str = str(nombre_completo)
            if ',' in nombre_str:
                partes = nombre_str.split(',')
                apellido = partes[0].strip()
                nombres = partes[1].strip() if len(partes) > 1 else ""
                # Primer nombre
                nombre_pila = nombres.split(' ')[0] if nombres else apellido
                # Inicial del apellido
                inicial_apellido = apellido[0].upper() if apellido else ""
                nombre_mostrar = f"{nombre_pila} {inicial_apellido}." if inicial_apellido else nombre_pila
            else:
                partes = nombre_str.split(' ')
                nombre_pila = partes[0]
                inicial_apellido = partes[1][0].upper() if len(partes) > 1 else ""
                nombre_mostrar = f"{nombre_pila} {inicial_apellido}." if inicial_apellido else nombre_pila

            # 🎂 Cumpleaños
            col_nac = 'Fecha de nacimiento'
            if col_nac in row and pd.notna(row[col_nac]):
                try:
                    dob = pd.to_datetime(row[col_nac], dayfirst=True, format='mixed').date()
                    for anio in [today_date.year, today_date.year + 1]:
                        try:
                            bday = dob.replace(year=anio)
                        except ValueError: # Feb 29
                            bday = dob.replace(year=anio, month=3, day=1)
                        
                        if today_date <= bday <= lookahead:
                            edad = anio - dob.year
                            dia_sem = formatear_fecha_espanol(bday, formato='dia_semana').lower()
                            if bday == today_date:
                                personal_alerts.append(f"🎂 **{nombre_mostrar}** cumple **{edad} años** ¡HOY!")
                            else:
                                personal_alerts.append(f"🎂 **{nombre_mostrar}** cumple **{edad} años** el próximo {dia_sem} ({bday.strftime('%d/%m')})")
                except: pass

            # 🎖️ Aniversarios de Trabajo (múltiplos de 5)
            col_pao = 'Fecha ingreso PAO'
            if col_pao in row and pd.notna(row[col_pao]):
                try:
                    ingreso = pd.to_datetime(row[col_pao], dayfirst=True, format='mixed').date()
                    for anio in [today_date.year, today_date.year + 1]:
                        try:
                            anniv = ingreso.replace(year=anio)
                        except ValueError:
                            anniv = ingreso.replace(year=anio, month=3, day=1)
                        
                        if today_date <= anniv <= lookahead:
                            anios_serv = anio - ingreso.year
                            if anios_serv > 0 and anios_serv % 5 == 0:
                                if anniv == today_date:
                                    personal_alerts.append(f"🎖️ **{nombre_mostrar}** cumple **{anios_serv} años** de trabajo ¡HOY!")
                                else:
                                    personal_alerts.append(f"🎖️ **{nombre_mostrar}** cumple **{anios_serv} años** de trabajo el {formatear_fecha_espanol(anniv, formato='corto')}")
                except: pass

        if personal_alerts:
            # Mostrar alertas en un contenedor destacado
            with st.container():
                for alert in personal_alerts:
                    st.toast(alert, icon="🎊") # Opcional: toast para llamar la atención
                    st.info(alert)
    
    st.markdown("---")

    # --- RESUMEN DE PERSONAL EN CURSO ---
    df_vacaciones = st.session_state.get('df_vacaciones', pd.DataFrame())
    df_compensados = st.session_state.get('df_compensados', pd.DataFrame())
    
    today = pd.to_datetime(datetime.now().date())
    
    # Vacaciones en curso (Inicio <= Hoy < Regreso)
    vac_en_curso = pd.DataFrame()
    if not df_vacaciones.empty and 'Fecha inicio' in df_vacaciones.columns:
        df_vac_tmp = df_vacaciones.copy()
        df_vac_tmp['Fecha inicio'] = pd.to_datetime(df_vac_tmp['Fecha inicio'], errors='coerce', dayfirst=True, format='mixed')
        df_vac_tmp['Fecha regreso'] = pd.to_datetime(df_vac_tmp['Fecha regreso'], errors='coerce', dayfirst=True, format='mixed')
        
        vac_en_curso = df_vac_tmp[
            (df_vac_tmp['Fecha inicio'] <= today) & 
            (df_vac_tmp['Fecha regreso'] > today)
        ].copy()
        
        if not vac_en_curso.empty:
            vac_en_curso = vac_en_curso[['Apellido, Nombres', 'Fecha inicio', 'Fecha regreso']]
            vac_en_curso.columns = ['Personal', 'Inicio', 'Regreso']
            vac_en_curso['Inicio'] = vac_en_curso['Inicio'].dt.strftime('%d/%m/%Y')
            vac_en_curso['Regreso'] = vac_en_curso['Regreso'].dt.strftime('%d/%m/%Y')

    # Ausencias en curso (Desde <= Hoy <= Hasta)
    comp_en_curso = pd.DataFrame()
    if not df_compensados.empty and 'Desde fecha' in df_compensados.columns:
        df_comp_tmp = df_compensados.copy()
        df_comp_tmp['Desde fecha'] = pd.to_datetime(df_comp_tmp['Desde fecha'], errors='coerce', dayfirst=True, format='mixed')
        df_comp_tmp['Hasta fecha'] = pd.to_datetime(df_comp_tmp['Hasta fecha'], errors='coerce', dayfirst=True, format='mixed')
        
        comp_en_curso = df_comp_tmp[
            (df_comp_tmp['Desde fecha'] <= today) & 
            (df_comp_tmp['Hasta fecha'] >= today)
        ].copy()
        
        if not comp_en_curso.empty:
            comp_en_curso = comp_en_curso[['Apellido, Nombres', 'Desde fecha', 'Hasta fecha']]
            comp_en_curso.columns = ['Personal', 'Desde', 'Hasta']
            comp_en_curso['Desde'] = comp_en_curso['Desde'].dt.strftime('%d/%m/%Y')
            comp_en_curso['Hasta'] = comp_en_curso['Hasta'].dt.strftime('%d/%m/%Y')

    # Mostrar sección solo si hay datos para mostrar
    if not vac_en_curso.empty or not comp_en_curso.empty:
        col_vac, col_comp = st.columns(2)
        
        with col_vac:
            st.markdown("#### 📅 Vacaciones en curso")
            if not vac_en_curso.empty:
                st.dataframe(vac_en_curso, hide_index=True, width='stretch')
            else:
                st.info("No hay vacaciones en curso")
                
        with col_comp:
            st.markdown("#### ⏱️ Ausencias en curso")
            if not comp_en_curso.empty:
                st.dataframe(comp_en_curso, hide_index=True, width='stretch')
            else:
                st.info("No hay ausencias en curso")
        st.markdown("---")

    # Obtener el clima actual
    weather = get_weather()
    pronostico = obtener_pronostico_extendido()
    # Pasar clave diaria para invalidar cache cada día
    tipos_cambio = obtener_tipo_cambio(day_key=datetime.now().strftime('%Y-%m-%d'))
    
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
            
            st.plotly_chart(fig_temp, width='stretch')
        else:
            st.warning("No se pudo cargar el pronóstico de temperaturas")
    
    with col3:
        st.markdown("### 🌧️ Lluvia y Viento")
        if pronostico and len(pronostico) > 0:
            # Crear gráfico combinado de lluvia y viento
            dias = [datetime.fromtimestamp(dia.get('dt', 0)).strftime('%a %d/%m') for dia in pronostico]
            lluvia = [dia.get('pop', 0) * 100 for dia in pronostico]  # Probabilidad de lluvia en %
            # Obtener ráfagas de viento y convertir de m/s a km/h
            viento = [dia.get('wind_gust', dia.get('wind_speed', 0)) * 3.6 for dia in pronostico]
            
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
                name='Ráfagas (km/h)',
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
                    title='Ráfagas de viento (km/h)',
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
            
            st.plotly_chart(fig_lluvia_viento, width='stretch')
        else:
            st.warning("No se pudo cargar el pronóstico de lluvia y viento")
    
    # Mostrar tipos de cambio en una fila separada
    st.markdown("---")
    st.markdown("### 💰 Cotizaciones")
    
    if tipos_cambio:
        col1, col2, col3 = st.columns([1, 1, 2])
        
        # Función auxiliar para mostrar una tarjeta de cotización
        def mostrar_cotizacion(moneda, nombre, historico_key):
            variacion = tipos_cambio[historico_key]['variacion']
            color = 'red' if variacion > 0 else 'green' if variacion < 0 else 'gray'
            
                # No mostramos el gráfico pequeño aquí, lo haremos más abajo
            
            # Mostrar métricas con variación
            st.metric(
                label=f"**{nombre} - Compra**",
                value=f"${tipos_cambio[historico_key]['compra']:,.2f}",
                delta=f"{variacion:+.2f}%" if variacion != 0 else None,
                delta_color="normal"
            )
            
            st.metric(
                label=f"**{nombre} - Venta**",
                value=f"${tipos_cambio[historico_key]['venta']:,.2f}",
                delta=None
            )
        
        with col1:
            mostrar_cotizacion("USD", "Dólar Oficial", "oficial")
        
        with col2:
            mostrar_cotizacion("EUR", "Euro Oficial", "euro")
        
        # Gráfico de tendencia más grande en la tercera columna
        with col3:
            st.markdown("#### Tendencias (últimos 7 días)")
            # Renderizar si hay al menos 1 dato histórico (hoy se agrega si falta)
            if any(len(tipos_cambio[key].get('historico_compra', [])) >= 1 for key in ['oficial', 'blue']):
                fig_tendencia = go.Figure()
                
                # Agregar líneas para cada tipo de cambio
                for key, color, name in [
                    ('oficial', '#ff7f0e', 'Dólar Oficial'),  # Naranja para el oficial
                    ('blue', '#1f77b4', 'Dólar Blue')         # Azul para el blue
                ]:
                    # Preparar series locales y garantizar que incluimos el día actual si falta
                    historico_compra = list(tipos_cambio[key].get('historico_compra', []))
                    historico_venta = list(tipos_cambio[key].get('historico_venta', []))
                    fechas_series = list(tipos_cambio[key].get('fechas', []))

                    # Fecha de hoy en formato ISO para comparaciones consistentes
                    hoy_str = datetime.now().date().isoformat()

                    # Si falta el día actual y tenemos valores actuales, agregarlos al final
                    valor_actual_compra = tipos_cambio[key].get('compra')
                    valor_actual_venta = tipos_cambio[key].get('venta')
                    if hoy_str not in {str(f).split('T')[0] for f in fechas_series} and \
                       valor_actual_compra is not None and valor_actual_venta is not None and \
                       valor_actual_compra != 0 and valor_actual_venta != 0:
                        fechas_series.append(hoy_str)
                        historico_compra.append(valor_actual_compra)
                        historico_venta.append(valor_actual_venta)

                    # Convertir fechas a datetime para que el eje X formatee ticks como fechas
                    try:
                        fechas_dt = pd.to_datetime([f.split('T')[0] for f in fechas_series], errors='coerce')
                    except Exception:
                        fechas_dt = fechas_series  # fallback a strings si algo falla

                    # Verificar que tengamos datos históricos de compra y venta
                    if (len(historico_compra) > 1 and len(historico_venta) > 1 and len(fechas_series) > 1):
                        # Línea de compra
                        fig_tendencia.add_trace(go.Scatter(
                            x=fechas_dt,
                            y=historico_compra,
                            name=f'{name} - Compra',
                            line=dict(
        color=color, 
        width=2.5, 
        dash='dash',
        shape='spline',
        smoothing=1.3
    ),
    mode='lines+markers',
    marker=dict(
        size=5, 
        symbol='circle',
        line=dict(width=1.5, color='white'),
        opacity=0.9
    )
                        ))
                        
                        # Línea de venta
                        fig_tendencia.add_trace(go.Scatter(
                            x=fechas_dt,
                            y=historico_venta,
                            name=f'{name} - Venta',
                            line=dict(
        color=color, 
        width=2.5,
        shape='spline',
        smoothing=1.3
    ),
    mode='lines+markers',
    marker=dict(
        size=5, 
        symbol='circle',
        line=dict(width=1.5, color='white'),
        opacity=0.9
    )
                        ))

                        # Nota: evitamos agregar trazas adicionales para el día de hoy
                        # para no duplicar puntos (el punto de hoy ya está incluido en la serie)
                
                # Obtener el rango de valores para el eje Y con un margen del 5%
                all_values = []
                for key in ['oficial', 'blue']:
                    compras = list(tipos_cambio[key].get('historico_compra', []))
                    ventas = list(tipos_cambio[key].get('historico_venta', []))
                    fechas_series = list(tipos_cambio[key].get('fechas', []))
                    hoy_str = datetime.now().date().isoformat()
                    if hoy_str not in {str(f).split('T')[0] for f in fechas_series}:
                        # incluir los valores actuales en el cálculo del rango
                        comp = tipos_cambio[key].get('compra')
                        ven = tipos_cambio[key].get('venta')
                        if comp:
                            compras.append(comp)
                        if ven:
                            ventas.append(ven)
                    if len(compras) > 0:
                        all_values.extend(compras)
                    if len(ventas) > 0:
                        all_values.extend(ventas)
                
                if all_values:
                    min_val = min(all_values)
                    max_val = max(all_values)
                    margin = (max_val - min_val) * 0.05  # 5% de margen
                    y_range = [max(0, min_val - margin), max_val + margin]
                else:
                    y_range = None
                
                # Configuración del diseño del gráfico
                fig_tendencia.update_layout(
                    height=300,
                    margin=dict(l=60, r=30, t=50, b=50) ,
                    legend=dict(
                        orientation='h',
                        yanchor='bottom',
                        y=1.02,
                        xanchor='center',
                        x=0.5,
                        font=dict(size=10)
                    ),
                    xaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(200, 200, 200, 0.15)' ,
                        tickangle=-45,
                        tickformat='%a %d/%m',  # Formato: Mar 08/10
                        type='date',
                        title='',
                        title_font=dict(size=12),
                        showline=True,
                        linecolor='rgba(0,0,0,0.1)',
                        tickfont=dict(size=10)
                    ),
                    yaxis=dict(
                        showgrid=True,
                        gridcolor='rgba(200, 200, 200, 0.15)' ,
                        title='Precio (ARS)',
                        title_font=dict(size=12),
                        tickprefix='$',
                        tickformat=',.0f',
                        range=y_range,  # Usar el rango calculado
                        showline=True,
                        linecolor='rgba(0,0,0,0.1)',
                        tickfont=dict(size=10)
                    ),
                    hovermode='x unified',
                    plot_bgcolor='rgba(15, 15, 15, 0.9)' ,
                    paper_bgcolor='rgba(0,0,0,0)',
                    showlegend=True,
                    hoverlabel=dict(
                        bgcolor='rgba(255, 255, 255, 0.95)',
                        font_size=12,
                        font_family='Arial'
                    )
                )
                
                # Configurar tooltips con estilo consistente
                fig_tendencia.update_traces(
                    hovertemplate='<span style="font-size: 13px; font-weight: bold;">%{x|%A %d/%m}</span><br>' +
                                '<span style="font-size: 12px;">Precio: <b>$%{y:,.2f} ARS</b></span><br>' +
                                '<extra></extra>'
                )
                
                # Asegurar que el fondo del tooltip sea oscuro y el texto claro
                fig_tendencia.update_layout(
                    hoverlabel=dict(
                        bgcolor='rgba(30, 30, 30, 0.9)',
                        font_size=12,
                        font_family='Arial',
                        bordercolor='rgba(150, 150, 150, 0.5)',
                        font_color='white',
                        align='left'
                    )
                )
                
                st.plotly_chart(fig_tendencia, width='stretch', config={'displayModeBar': True})
        
        # Mostrar última actualización
        st.markdown(
            f"<div style='text-align: right; font-size: 0.8em; color: #666; margin-top: -10px;'>"
            f"Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            "</div>",
            unsafe_allow_html=True
        )
    else:
        st.warning("No se pudieron cargar los tipos de cambio")
    
if __name__ == "__main__":
    mostrar_seccion_bienvenida()
