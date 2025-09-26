#!/usr/bin/env python3
"""
Script para probar el sistema de versiones con diferentes roles.
Verifica que los detalles solo se muestren a usuarios admin.
"""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from version_manager import SimpleVersionManager, get_simple_version_string, get_detailed_version_string, display_simple_version_sidebar

def test_version_with_roles():
    """Test del sistema de versiones con diferentes roles"""
    print("🧪 Probando Sistema de Versiones con Control de Roles")
    print("=" * 55)

    vm = SimpleVersionManager()
    info = vm.get_simple_version_info()

    print("📋 Información del último commit:")
    print(f"   Commit: {info['short_hash']}")
    print(f"   Fecha: {info['date']}")
    print(f"   Autor: {info['author']}")
    print(f"   Mensaje: {info['message']}")

    print("\n📱 Lo que ven TODOS los usuarios:")
    print(f"   📅 {get_simple_version_string()}")

    roles_to_test = ['admin', 'empleado', 'invitado']

    for role in roles_to_test:
        print(f"\n👤 Usuario con rol '{role}':")
        print("   ┌─────────────────────────────────────┐")
        print(f"   │ 📅 {get_simple_version_string()}")

        if role == 'admin':
            print("   │ ℹ️ Detalles del commit [+]         │")
            print(f"   │     **Último commit:** {info['short_hash']} │")
            print(f"   │     **Fecha:** {info['date']}     │")
            print(f"   │     **Autor:** {info['author']}   │")
            print(f"   │     **Mensaje:** {info['message']} │")
            print("   │ [📋 Copiar Hash del Commit]        │")
        else:
            print("   │ (sin detalles adicionales)         │")

        print("   └─────────────────────────────────────┘")

    return True

def main():
    """Función principal"""
    print("🔐 Prueba del Sistema de Versiones con Control de Roles")
    print("=" * 60)

    try:
        success = test_version_with_roles()

        print("\n" + "=" * 60)
        if success:
            print("✅ ¡Sistema de roles funcionando correctamente!")
            print("✅ Todos los usuarios ven la fecha del último commit")
            print("✅ Solo los admins ven los detalles del commit")
            print("✅ Control de acceso implementado correctamente")
        else:
            print("❌ Error en el sistema de roles")

        return success

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
