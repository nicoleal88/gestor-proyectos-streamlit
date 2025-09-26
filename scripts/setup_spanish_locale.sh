#!/bin/bash
# Script para instalar y configurar locales de español en Linux
# Esto resuelve el warning "No se pudo configurar el locale en español"

echo "🌍 Configurando locales de español en el sistema..."
echo "=================================================="

# Verificar si estamos en un sistema basado en Debian/Ubuntu
if command -v apt-get &> /dev/null; then
    echo "📦 Sistema detectado: Debian/Ubuntu"

    # Actualizar lista de paquetes
    echo "🔄 Actualizando lista de paquetes..."
    sudo apt-get update

    # Instalar locales
    echo "📥 Instalando locales..."
    sudo apt-get install -y locales

    # Generar locales de español
    echo "⚙️ Generando locales de español..."
    sudo locale-gen es_ES.UTF-8
    sudo locale-gen es_AR.UTF-8
    sudo locale-gen es_CL.UTF-8
    sudo locale-gen es_MX.UTF-8

    # Configurar locale por defecto
    echo "🔧 Configurando locale por defecto..."
    sudo update-locale LANG=es_ES.UTF-8

    echo "✅ Locales instalados correctamente"

elif command -v yum &> /dev/null; then
    echo "📦 Sistema detectado: Red Hat/CentOS/Fedora"

    # Instalar glibc locales
    echo "📥 Instalando glibc locales..."
    sudo yum install -y glibc-locale-source glibc-langpack-es

    # Generar locales
    echo "⚙️ Generando locales de español..."
    sudo localedef -c -i es_ES -f UTF-8 es_ES.UTF-8
    sudo localedef -c -i es_AR -f UTF-8 es_AR.UTF-8

    echo "✅ Locales instalados correctamente"

elif command -v pacman &> /dev/null; then
    echo "📦 Sistema detectado: Arch Linux"

    # Instalar locales
    echo "📥 Instalando locales..."
    sudo pacman -S --noconfirm glibc-locales

    # Editar /etc/locale.gen para descomentar locales de español
    echo "⚙️ Habilitando locales de español..."
    sudo sed -i 's/#es_ES.UTF-8/es_ES.UTF-8/' /etc/locale.gen
    sudo sed -i 's/#es_AR.UTF-8/es_AR.UTF-8/' /etc/locale.gen

    # Generar locales
    sudo locale-gen

    echo "✅ Locales instalados correctamente"

else
    echo "❌ Sistema operativo no reconocido"
    echo "🔧 Instalación manual requerida:"
    echo "   1. Instalar el paquete de locales de tu distribución"
    echo "   2. Generar los locales: es_ES.UTF-8, es_AR.UTF-8"
    echo "   3. Configurar el locale por defecto"
    exit 1
fi

# Verificar que los locales se instalaron correctamente
echo ""
echo "🔍 Verificando instalación de locales..."
locale -a | grep -E "es_(ES|AR|CL|MX)" || echo "⚠️ No se encontraron locales de español"

# Mostrar locale actual
echo ""
echo "📋 Locale actual del sistema:"
echo "   LANG=$LANG"
echo "   LC_ALL=$LC_ALL"
echo "   LC_TIME=$LC_TIME"

echo ""
echo "🎉 Configuración completada!"
echo "💡 Para aplicar los cambios, reinicia la aplicación o ejecuta:"
echo "   export LANG=es_ES.UTF-8"
echo "   export LC_ALL=es_ES.UTF-8"
echo ""
echo "🔄 Reinicia la aplicación Streamlit para ver los cambios."
