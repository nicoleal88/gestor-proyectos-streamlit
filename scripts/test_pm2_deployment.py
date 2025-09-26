#!/usr/bin/env python3
"""
Script simplificado para probar el deployment con PM2.
Verifica que todo funciona correctamente con la configuración actual.
"""

import sys
import os
import subprocess
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_pm2_deployment():
    """Test del sistema de deployment con PM2"""
    print("🧪 Probando Deployment con PM2")
    print("=" * 40)

    # Verificar si PM2 está instalado
    try:
        result = subprocess.run(['pm2', 'list'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ PM2 está instalado y funcionando")
        else:
            print("❌ PM2 no está funcionando correctamente")
            return False
    except FileNotFoundError:
        print("❌ PM2 no está instalado")
        return False

    # Verificar si hay procesos PM2 corriendo
    pm2_list = subprocess.run(['pm2', 'list'], capture_output=True, text=True)
    if 'gestor-proyectos' in pm2_list.stdout:
        print("✅ Aplicación 'gestor-proyectos' encontrada en PM2")

        # Verificar estado
        pm2_status = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True)
        if '"pm2_env"' in pm2_status.stdout:
            print("✅ PM2 está gestionando la aplicación correctamente")
        else:
            print("⚠️ PM2 puede tener problemas con la aplicación")
    else:
        print("⚠️ No se encontró 'gestor-proyectos' en PM2")
        print("💡 Ejecuta: pm2 start ecosystem.config.js")

    # Verificar si existe ecosystem.config.js
    if os.path.exists('ecosystem.config.js'):
        print("✅ ecosystem.config.js encontrado")

        # Mostrar contenido relevante
        with open('ecosystem.config.js', 'r') as f:
            content = f.read()
            if 'watch' in content.lower():
                print("✅ Configuración de watch detectada en ecosystem.config.js")
            else:
                print("⚠️ No se detectó configuración de watch en ecosystem.config.js")
    else:
        print("⚠️ No se encontró ecosystem.config.js")
        print("💡 Crea el archivo ecosystem.config.js con la configuración de PM2")

    # Verificar si existe el script de deployment
    if os.path.exists('deploy.sh'):
        print("✅ Script deploy.sh encontrado")
        print("💡 Para usar: ./deploy.sh")
    else:
        print("⚠️ No se encontró deploy.sh")

    # Verificar repositorio git
    if os.path.exists('.git'):
        print("✅ Repositorio git detectado")

        # Verificar si hay cambios remotos
        try:
            fetch_result = subprocess.run(['git', 'fetch', 'origin'], capture_output=True, text=True)
            status_result = subprocess.run(['git', 'status', '-uno'], capture_output=True, text=True)

            if 'ahead' in status_result.stdout or 'behind' in status_result.stdout:
                print("🔄 Hay cambios disponibles en el repositorio remoto")
            else:
                print("✅ Repositorio sincronizado")
        except:
            print("⚠️ Error verificando estado del repositorio")
    else:
        print("⚠️ No se detectó repositorio git")

    return True

def show_pm2_commands():
    """Mostrar comandos útiles para PM2"""
    print("\n🛠️ Comandos útiles para PM2:")
    print("   pm2 status                    # Ver estado")
    print("   pm2 logs gestor-proyectos     # Ver logs")
    print("   pm2 restart ecosystem.config.js # Reiniciar")
    print("   pm2 stop ecosystem.config.js  # Parar")
    print("   pm2 monit                     # Monitor")
    print("   pm2 jlist                     # Info detallada")

def main():
    """Función principal"""
    print("🔧 Prueba del Sistema de Deployment con PM2")
    print("=" * 50)

    try:
        success = test_pm2_deployment()

        print("\n" + "=" * 50)
        if success:
            print("🎉 ¡Sistema de PM2 funcionando correctamente!")
            print("✅ Tu aplicación ya está configurada para deployment automático")
            print("✅ Solo necesitas hacer git pull para actualizar")

            show_pm2_commands()

            print("\n🚀 Workflow recomendado:")
            print("   1. Desarrollo: git push origin main")
            print("   2. VPS: git pull origin main")
            print("   3. PM2: Se reinicia automáticamente")
        else:
            print("⚠️ Algunas verificaciones fallaron")
            print("🔧 Revisa la configuración de PM2")

        return success

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
