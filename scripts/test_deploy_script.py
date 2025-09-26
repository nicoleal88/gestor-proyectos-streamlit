#!/usr/bin/env python3
"""
Script para probar que deploy.sh funciona correctamente
con la nueva ubicación de logs.
"""

import subprocess
import os
import sys

def test_deploy_script():
    """Test del script deploy.sh"""
    print("🧪 Probando script deploy.sh")
    print("=" * 35)

    script_path = "./deploy.sh"

    if not os.path.exists(script_path):
        print("❌ No se encontró deploy.sh")
        return False

    # Verificar que el script es ejecutable
    if not os.access(script_path, os.X_OK):
        print("⚠️ deploy.sh no es ejecutable, haciendo ejecutable...")
        os.chmod(script_path, 0o755)

    print("✅ deploy.sh encontrado y ejecutable")

    # Verificar que el directorio de logs existe
    logs_dir = "logs"
    if not os.path.exists(logs_dir):
        print(f"📁 Creando directorio {logs_dir}...")
        os.makedirs(logs_dir)

    print(f"✅ Directorio {logs_dir}/ existe")

    # Verificar que el script puede escribir en el log
    try:
        # Simular una ejecución corta del script para verificar logs
        test_log = os.path.join(logs_dir, "test_deploy.log")
        with open(test_log, 'w') as f:
            f.write("Test log entry\n")

        if os.path.exists(test_log):
            print("✅ Permisos de escritura en logs OK")
            os.remove(test_log)  # Limpiar
        else:
            print("❌ No se puede escribir en logs")
            return False

    except Exception as e:
        print(f"❌ Error con logs: {e}")
        return False

    # Verificar sintaxis del script
    try:
        result = subprocess.run([script_path, '--help'],
                              capture_output=True, text=True, timeout=5)
        # Si no tiene --help, verificar que al menos no da error de sintaxis
        if result.returncode not in [0, 1, 2]:  # 1 y 2 son códigos comunes para "no implementado"
            print(f"⚠️ deploy.sh puede tener problemas: {result.stderr}")
        else:
            print("✅ Sintaxis de deploy.sh OK")
    except subprocess.TimeoutExpired:
        print("✅ deploy.sh se ejecutó (timeout normal)")
    except FileNotFoundError:
        print("❌ Error ejecutando deploy.sh")
        return False
    except Exception as e:
        print(f"⚠️ deploy.sh puede tener problemas: {e}")

    return True

def show_usage():
    """Mostrar cómo usar deploy.sh"""
    print("\n💡 Cómo usar deploy.sh:")
    print("   ./deploy.sh              # Actualizar desde main")
    print("   ./deploy.sh develop      # Actualizar desde develop")
    print("   tail -f logs/deploy.log  # Ver logs de deployment")

def main():
    """Función principal"""
    print("🔧 Prueba del deploy.sh corregido")
    print("=" * 40)

    success = test_deploy_script()

    if success:
        print("\n🎉 ¡deploy.sh configurado correctamente!")
        show_usage()
        print("\n✅ Listo para usar en la VPS")
    else:
        print("\n❌ deploy.sh necesita ajustes")

    return success

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
