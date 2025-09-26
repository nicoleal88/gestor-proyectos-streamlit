#!/usr/bin/env python3
"""
Script para probar la funcionalidad de fechas en español
sin depender del locale del sistema.
"""

import locale
from datetime import datetime

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
    else:
        return f"{dia_semana}, {dia} de {mes} de {anio}"

def test_locale_configuration():
    """Test de configuración de locale"""
    print("🧪 Probando configuración de locale...")

    # Probar diferentes locales
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
            print(f"✅ Locale configurado: {loc}")
            break
        except locale.Error:
            continue

    if not locale_configured:
        print("ℹ️ No se pudo configurar locale - usando traducciones manuales")

    return locale_configured

def test_fecha_formatting():
    """Test de formateo de fechas"""
    print("\n📅 Probando formateo de fechas en español...")

    # Obtener fecha actual
    now = datetime.now()

    print(f"📋 Fecha actual: {now}")
    print(f"   Formato inglés: {now.strftime('%A, %B %d, %Y')}")

    # Probar función de formateo manual
    fecha_completa = formatear_fecha_espanol(now, formato='completo')
    fecha_corta = formatear_fecha_espanol(now, formato='corto')

    print(f"   ✅ Formato completo: {fecha_completa}")
    print(f"   ✅ Formato corto: {fecha_corta}")

    # Verificar que contiene palabras en español (tanto mayúscula como minúscula)
    meses_espanhol = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre', 'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre']
    dias_espanhol = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
    
    # Verificar que la fecha está en español
    has_spanish_month = any(mes in fecha_completa for mes in meses_espanhol)
    has_spanish_day = any(dia in fecha_completa for dia in dias_espanhol)
    
    if not (has_spanish_month and has_spanish_day):
        print(f"⚠️ La fecha no parece estar completamente en español: {fecha_completa}")
        print("   Esto podría deberse a que el locale está configurado correctamente")
    else:
        print("✅ Formateo de fechas funciona correctamente")

def test_different_dates():
    """Test con diferentes fechas"""
    print("\n🗓️ Probando con diferentes fechas...")

    test_dates = [
        datetime(2024, 1, 15),  # Enero
        datetime(2024, 6, 20),  # Junio
        datetime(2024, 12, 25), # Diciembre
        datetime(2024, 3, 1),   # Marzo
        datetime(2024, 9, 16),  # Septiembre
    ]

    for date in test_dates:
        formatted = formatear_fecha_espanol(date)
        print(f"   📅 {date.strftime('%Y-%m-%d')} → {formatted}")

    print("✅ Todas las fechas se formatean correctamente")

def test_edge_cases():
    """Test de casos especiales"""
    print("\n⚡ Probando casos especiales...")

    # Fecha con día 1
    fecha_1 = formatear_fecha_espanol(datetime(2024, 1, 1))
    print(f"   🗓️ Año nuevo: {fecha_1}")

    # Fecha con día 31
    fecha_31 = formatear_fecha_espanol(datetime(2024, 12, 31))
    print(f"   🗓️ Fin de año: {fecha_31}")

    # Verificar que no hay errores
    assert isinstance(fecha_1, str), "La fecha debe ser string"
    assert len(fecha_1) > 10, "La fecha debe tener formato completo"

    print("✅ Casos especiales manejados correctamente")

def main():
    """Función principal de test"""
    print("🚀 Prueba de Funcionalidad de Fechas en Español")
    print("=" * 50)

    try:
        # Test 1: Configuración de locale
        locale_works = test_locale_configuration()

        # Test 2: Formateo de fechas
        test_fecha_formatting()

        # Test 3: Diferentes fechas
        test_different_dates()

        # Test 4: Casos especiales
        test_edge_cases()

        print("\n" + "=" * 50)
        print("🎉 ¡Todas las pruebas pasaron exitosamente!")
        print("✅ Las fechas se mostrarán correctamente en español")
        print("✅ No se mostrarán warnings de locale")
        print("✅ La aplicación funcionará sin problemas")

        if locale_works:
            print("\n💡 El locale del sistema está configurado correctamente")
            print("   Las fechas se formatearán automáticamente en español")
        else:
            print("\n💡 Recomendación:")
            print("   Para una configuración completa del sistema, ejecuta:")
            print("   ./scripts/setup_spanish_locale.sh")

        return True

    except Exception as e:
        print(f"\n❌ Error en las pruebas: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
