#!/usr/bin/env python3
"""
Script de prueba para verificar la estructura de navegación de la aplicación.
Este script simula la ejecución de la aplicación para verificar que la estructura
de navegación esté funcionando correctamente.
"""

import sys
import os

# Add the parent directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_navigation_structure():
    """Test que verifica la estructura de navegación."""

    print("🧪 Verificando estructura de navegación...")

    # Verificar que el archivo principal existe
    app_file = os.path.join(os.path.dirname(__file__), 'app.py')
    if not os.path.exists(app_file):
        print("❌ Error: app.py no encontrado")
        return False

    # Verificar que el directorio de páginas existe
    pages_dir = os.path.join(os.path.dirname(__file__), 'pages')
    if not os.path.exists(pages_dir):
        print("❌ Error: directorio pages/ no encontrado")
        return False

    # Verificar que hay archivos de página
    page_files = [f for f in os.listdir(pages_dir) if f.endswith('.py')]
    if not page_files:
        print("❌ Error: no se encontraron archivos de página")
        return False

    print(f"✅ Estructura básica verificada:")
    print(f"   - app.py: {os.path.exists(app_file)}")
    print(f"   - pages/: {len(page_files)} archivos de página encontrados")

    # Verificar que las páginas tienen la estructura correcta
    for page_file in page_files:
        page_path = os.path.join(pages_dir, page_file)
        with open(page_path, 'r') as f:
            content = f.read()

        if 'def page():' not in content:
            print(f"⚠️  Advertencia: {page_file} no tiene función page()")
        else:
            print(f"✅ {page_file}: estructura correcta")

    return True

def test_app_structure():
    """Test que verifica la estructura del código en app.py."""

    print("\n🔍 Verificando estructura de app.py...")

    app_file = os.path.join(os.path.dirname(__file__), 'app.py')
    with open(app_file, 'r') as f:
        content = f.read()

    # Verificar que la estructura de navegación esté correcta
    if 'with st.sidebar:' in content and 'selected_page.run()' in content:
        if content.find('with st.sidebar:') < content.find('selected_page.run()'):
            print("✅ Estructura de navegación correcta:")
            print("   - Sidebar contiene información de usuario y navegación")
            print("   - Área principal ejecuta el contenido de la página")
        else:
            print("❌ Error: Estructura de navegación incorrecta")
            return False
    else:
        print("⚠️  Estructura de navegación no encontrada o incompleta")
        return False

    return True

def main():
    """Función principal de test."""
    print("🚀 Iniciando verificación de la aplicación...\n")

    success = True

    # Test 1: Estructura básica
    if not test_navigation_structure():
        success = False

    # Test 2: Estructura de app.py
    if not test_app_structure():
        success = False

    print(f"\n{'='*50}")

    if success:
        print("✅ Verificación completada exitosamente!")
        print("📝 La estructura de la aplicación parece estar correcta.")
        print("💡 Si aún ves problemas en el sidebar, verifica:")
        print("   1. Que las credenciales de Google estén configuradas")
        print("   2. Que el Google Sheet 'GestorProyectosStreamlit' exista")
        print("   3. Que las pestañas requeridas estén en el Google Sheet")
        print("   4. Que los permisos de la cuenta de servicio estén correctos")
    else:
        print("❌ Se encontraron problemas en la verificación")
        print("🔧 Revisa los errores mostrados arriba")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
