#!/usr/bin/env python3
"""
Script simplificado para probar el sistema de versiones.
Solo muestra fecha y hora del último commit.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from version_manager import SimpleVersionManager, get_simple_version_string, get_detailed_version_string

def test_simple_version():
    """Test del sistema simplificado de versiones"""
    print("🧪 Probando Sistema Simplificado de Versiones")
    print("=" * 50)

    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    print("📋 Información del último commit:")
    print(f"   Commit: {info['short_hash']}")
    print(f"   Fecha: {info['date']}")
    print(f"   Autor: {info['author']}")
    print(f"   Mensaje: {info['message']}")

    print("\n📱 Lo que se muestra en el sidebar:")
    print(f"   📅 {get_simple_version_string()}")

    print("\n📋 Detalles expandidos:")
    print(f"   {get_detailed_version_string().replace(chr(10), chr(10) + '   ')}")

    return True

def main():
    """Función principal"""
    print("📅 Prueba del Sistema Simplificado de Versiones")
    print("=" * 55)

    try:
        success = test_simple_version()

        print("\n" + "=" * 55)
        if success:
            print("✅ ¡Sistema simplificado funcionando correctamente!")
            print("✅ No se necesitan scripts complejos")
            print("✅ Solo muestra fecha y hora del último commit")
            print("✅ Fácil de mantener y entender")
        else:
            print("❌ Error en el sistema")

        return success

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
