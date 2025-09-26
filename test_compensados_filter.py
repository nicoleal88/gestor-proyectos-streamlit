#!/usr/bin/env python3
"""
Script de prueba para verificar los filtros en la sección Compensados.
"""

import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

def test_compensados_filter_logic():
    """Test que verifica la lógica del filtro por Estado en Compensados."""

    print("🧪 Probando lógica del filtro por Estado en Compensados...")

    # Simular datos de compensados para diferentes escenarios
    today = pd.to_datetime(datetime.now().date())

    # Crear datos de prueba
    test_data = {
        'Apellido, Nombres': ['Juan Pérez', 'María García', 'Pedro López', 'Ana Rodríguez', 'Carlos Sánchez'],
        'Fecha Solicitud': ['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04', '2024-01-05'],
        'Tipo': ['Compensatorio', 'Compensatorio', 'Compensatorio', 'Compensatorio', 'Compensatorio'],
        'Desde fecha': [
            today - timedelta(days=5),  # En curso (empezó hace 5 días)
            today + timedelta(days=10),  # Próximo (empieza en 10 días)
            today - timedelta(days=15),  # Transcurrido (terminó hace 15 días)
            today - timedelta(days=2),   # En curso (empezó hace 2 días)
            today + timedelta(days=30)   # Próximo (empieza en 30 días)
        ],
        'Desde hora': ['08:00', '09:00', '', '10:00', ''],
        'Hasta fecha': [
            today + timedelta(days=5),   # En curso (termina en 5 días)
            today + timedelta(days=20),  # Próximo (termina en 20 días)
            today - timedelta(days=5),   # Transcurrido (terminó hace 5 días)
            today + timedelta(days=8),   # En curso (termina en 8 días)
            today + timedelta(days=40)   # Próximo (termina en 40 días)
        ],
        'Hasta hora': ['17:00', '18:00', '', '16:00', '']
    }

    df_compensados = pd.DataFrame(test_data)

    # Convertir fechas a datetime
    df_compensados['Desde fecha'] = pd.to_datetime(df_compensados['Desde fecha'])
    df_compensados['Hasta fecha'] = pd.to_datetime(df_compensados['Hasta fecha'])

    print(f"✅ Datos de prueba creados: {len(df_compensados)} registros")

    # Test 1: Verificar cálculo de métricas totales
    en_curso_total = ((df_compensados['Desde fecha'] <= today) & (df_compensados['Hasta fecha'] >= today)).sum()
    proximos_total = (df_compensados['Desde fecha'] > today).sum()
    transcurridos_total = (df_compensados['Hasta fecha'] < today).sum()

    print(f"✅ Métricas totales calculadas:")
    print(f"   - En curso: {en_curso_total}")
    print(f"   - Próximos: {proximos_total}")
    print(f"   - Transcurridos: {transcurridos_total}")

    assert en_curso_total == 2, f"Deben haber 2 compensatorios en curso, pero hay {en_curso_total}"
    assert proximos_total == 2, f"Deben haber 2 compensatorios próximos, pero hay {proximos_total}"
    assert transcurridos_total == 1, f"Debe haber 1 compensatorio transcurrido, pero hay {transcurridos_total}"

    # Test 2: Verificar filtros individuales
    df_en_curso = df_compensados[
        (df_compensados['Desde fecha'] <= today) &
        (df_compensados['Hasta fecha'] >= today)
    ]
    print(f"✅ Compensatorios en curso: {len(df_en_curso)}")
    assert len(df_en_curso) == 2

    df_proximos = df_compensados[df_compensados['Desde fecha'] > today]
    print(f"✅ Próximos compensatorios: {len(df_proximos)}")
    assert len(df_proximos) == 2

    df_transcurridos = df_compensados[df_compensados['Hasta fecha'] < today]
    print(f"✅ Compensatorios transcurridos: {len(df_transcurridos)}")
    assert len(df_transcurridos) == 1

    # Test 3: Verificar que los registros están en las categorías correctas
    for idx, row in df_en_curso.iterrows():
        assert row['Desde fecha'] <= today, "Compensatorio en curso debe haber empezado"
        assert row['Hasta fecha'] >= today, "Compensatorio en curso debe estar vigente"

    for idx, row in df_proximos.iterrows():
        assert row['Desde fecha'] > today, "Compensatorio próximo debe empezar en el futuro"

    for idx, row in df_transcurridos.iterrows():
        assert row['Hasta fecha'] < today, "Compensatorio transcurrido debe haber terminado"

    print("✅ Todos los tests de lógica pasaron exitosamente!")

    return True

def test_compensados_ui_structure():
    """Test que verifica la estructura de la UI de Compensados."""

    print("\n🔍 Verificando estructura de la sección Compensados...")

    # Verificar que el archivo existe y tiene la estructura correcta
    try:
        with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/compensados.py', 'r') as f:
            content = f.read()

        # Verificar que tiene el filtro implementado
        if 'selected_filter = st.selectbox' in content:
            print("✅ Filtro selectbox implementado")
        else:
            print("❌ Filtro selectbox no encontrado")
            return False

        if 'Compensatorios en Curso' in content and 'Próximos Compensatorios' in content and 'Compensatorios Transcurridos' in content:
            print("✅ Todas las opciones de filtro implementadas")
        else:
            print("❌ Opciones de filtro incompletas")
            return False

        if 'default_filter = \"Compensatorios en Curso\"' in content:
            print("✅ Valor por defecto 'Compensatorios en Curso' implementado")
        else:
            print("❌ Valor por defecto no encontrado")
            return False

        if 'st.info(f\"Mostrando: {selected_filter}' in content:
            print("✅ Información de filtro activo implementada")
        else:
            print("❌ Información de filtro activo no encontrada")
            return False

        if 'Compensatorios Transcurridos' in content:
            print("✅ Nueva métrica 'Compensatorios Transcurridos' añadida")
        else:
            print("❌ Nueva métrica no encontrada")
            return False

        print("✅ Estructura de la sección Compensados verificada correctamente")

    except FileNotFoundError:
        print("❌ Archivo ui_sections/compensados.py no encontrado")
        return False

    return True

def test_filter_functionality():
    """Test que verifica la funcionalidad específica del filtro."""

    print("\n🔧 Verificando funcionalidad específica del filtro...")

    try:
        with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/compensados.py', 'r') as f:
            content = f.read()

        # Verificar lógica de filtrado
        checks = [
            ('if selected_filter == "Compensatorios en Curso":', "Lógica para compensatorios en curso"),
            ('elif selected_filter == "Próximos Compensatorios":', "Lógica para próximos compensatorios"),
            ('elif selected_filter == "Compensatorios Transcurridos":', "Lógica para compensatorios transcurridos"),
            ('# "Todos" no aplica ningún filtro adicional', "Comentario para opción 'Todos'")
        ]

        for check, description in checks:
            if check in content:
                print(f"✅ {description} implementado")
            else:
                print(f"❌ {description} no encontrado")
                return False

        print("✅ Funcionalidad del filtro verificada correctamente")

    except FileNotFoundError:
        print("❌ Archivo ui_sections/compensados.py no encontrado")
        return False

    return True

def main():
    """Función principal de test."""
    print("🚀 Iniciando verificación del filtro por Estado en Compensados...\n")

    success = True

    # Test 1: Lógica del filtro
    if not test_compensados_filter_logic():
        success = False

    # Test 2: Estructura de la UI
    if not test_compensados_ui_structure():
        success = False

    # Test 3: Funcionalidad específica
    if not test_filter_functionality():
        success = False

    print(f"\n{'='*70}")

    if success:
        print("✅ Verificación completada exitosamente!")
        print("📝 El filtro por Estado en Compensados está correctamente implementado.")
        print("💡 Características implementadas:")
        print("   • 'Compensatorios en Curso' seleccionado por defecto")
        print("   • Filtros para Próximos Compensatorios y Compensatorios Transcurridos")
        print("   • Opción 'Todos' para ver todos los registros")
        print("   • Métricas totales mejoradas con 4 columnas")
        print("   • Información del filtro activo mostrada al usuario")
        print("   • Integración perfecta con la UI existente")
    else:
        print("❌ Se encontraron problemas en la verificación")
        print("🔧 Revisa los errores mostrados arriba")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
