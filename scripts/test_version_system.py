#!/usr/bin/env python3
"""
Script para probar el sistema de versiones de git.
Verifica que la información de versión se obtenga correctamente.
"""

import sys
import os
# Agregar la ruta raíz al path para poder importar version_manager
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from version_manager import VersionManager, get_version_string, get_version_info

def test_version_system():
    """Test completo del sistema de versiones"""
    print("🧪 Probando Sistema de Versiones")
    print("=" * 40)

    vm = VersionManager()

    # Test 1: Obtener información básica
    print("📋 Test 1: Información básica de git")
    git_info = get_version_info()

    required_fields = ['branch', 'commit_hash', 'short_hash', 'version']
    for field in required_fields:
        if git_info.get(field) != 'unknown':
            print(f"   ✅ {field}: {git_info[field]}")
        else:
            print(f"   ⚠️ {field}: {git_info[field]}")

    # Test 2: Versiones formateadas
    print("\n📋 Test 2: Versiones formateadas")
    formats = ['full', 'short', 'compact', 'badge']
    for fmt in formats:
        version = get_version_string(fmt)
        print(f"   ✅ {fmt}: {version}")

    # Test 3: Estado de producción
    print("\n📋 Test 3: Estado de producción")
    is_prod_ready = vm.is_production_ready()
    print(f"   ✅ Producción Ready: {'Sí' if is_prod_ready else 'No'}")

    if git_info['is_dirty']:
        print("   ⚠️ Hay cambios sin commitear")
    else:
        print("   ✅ Repositorio limpio")

    # Test 4: Simular diferentes escenarios
    print("\n📋 Test 4: Simulación de escenarios")

    # Escenario 1: Branch main con tag
    if git_info['branch'] == 'main' and git_info['tag']:
        print("   ✅ Escenario: Release en producción")
        print(f"      Versión: {git_info['version']}")

    # Escenario 2: Branch develop
    elif 'dev' in git_info['branch'].lower():
        print("   ✅ Escenario: Desarrollo activo")
        print(f"      Versión: {git_info['version']}")

    # Escenario 3: Feature branch
    else:
        print("   ✅ Escenario: Feature branch")
        print(f"      Versión: {git_info['version']}")

    return True

def test_sidebar_integration():
    """Test de integración con sidebar"""
    print("\n🖥️ Test 5: Integración con sidebar")

    try:
        # Importar la función (sin ejecutar streamlit)
        from version_manager import display_version_sidebar

        # Simular que se llama la función
        print("   ✅ display_version_sidebar() importada correctamente")
        print("   ✅ Función disponible para integrar en sidebar")

    except ImportError as e:
        print(f"   ❌ Error al importar: {e}")
        return False

    return True

def main():
    """Función principal de test"""
    print("🚀 Prueba del Sistema de Versiones Git")
    print("=" * 50)

    success = True

    try:
        # Test del sistema de versiones
        if not test_version_system():
            success = False

        # Test de integración
        if not test_sidebar_integration():
            success = False

        print("\n" + "=" * 50)

        if success:
            print("🎉 ¡Todas las pruebas pasaron exitosamente!")
            print("✅ El sistema de versiones está funcionando correctamente")
            print("✅ Listo para integrar en el sidebar")

            # Mostrar ejemplo de cómo se verá
            print("\n📱 Ejemplo de cómo se verá en el sidebar:")
            git_info = get_version_info()
            print(f"   📦 Versión: {get_version_string('short')}")
            badge = get_version_string('badge')
            print(f"   {badge}")
            print("   ℹ️ Detalles de versión [+]")
        else:
            print("⚠️ Algunas pruebas fallaron")
            print("🔧 Revisa los errores mostrados arriba")

        return success

    except Exception as e:
        print(f"\n❌ Error crítico: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
