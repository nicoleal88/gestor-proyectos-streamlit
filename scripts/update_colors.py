#!/usr/bin/env python3
"""
Script para mejorar los colores de la aplicación para modo oscuro.
Este script analiza y actualiza los colores de fondo en los dataframes
para mejorar el contraste cuando se usa tema oscuro.
"""

import re

def is_dark_mode():
    """
    Detecta si la aplicación está en modo oscuro.
    Esta es una función simplificada - en una implementación real,
    se podría detectar el tema de Streamlit o del sistema.
    """
    # Por ahora, asumimos que si se está ejecutando en un entorno
    # donde el usuario menciona tema oscuro, aplicamos colores para dark mode
    return True  # Cambiar a False para modo claro

def get_improved_colors():
    """
    Retorna los colores mejorados para modo oscuro.
    """
    if is_dark_mode():
        return {
            # Tareas - colores más intensos para dark mode
            'tarea_vencida': '#8B0000',  # Rojo oscuro intenso
            'tarea_en_curso': '#0066CC',  # Azul más intenso
            'tarea_pendiente': '#FF8C00',  # Naranja más intenso

            # Vacaciones - colores más intensos para dark mode
            'vacaciones_en_curso': '#1E90FF',  # Azul más intenso
            'vacaciones_transcurridas': '#696969',  # Gris más oscuro
            'vacaciones_proximas': '#FF8C00',  # Naranja más intenso

            # Compensados - colores más intensos para dark mode
            'compensados_en_curso': '#1E90FF',  # Azul más intenso
            'compensados_transcurridos': '#696969',  # Gris más oscuro
            'compensados_proximos': '#FF8C00',  # Naranja más intenso

            # Notas - colores de texto mejorados
            'nota_realizada': '#32CD32',  # Verde lima
            'nota_rechazada': '#FF6347',  # Rojo tomate
            'nota_pendiente': '#FFD700',  # Oro
        }
    else:
        return {
            # Modo claro - colores originales
            'tarea_vencida': '#ffcccc',
            'tarea_en_curso': 'lightblue',
            'tarea_pendiente': '#FFD580',

            'vacaciones_en_curso': 'lightblue',
            'vacaciones_transcurridas': 'lightgray',
            'vacaciones_proximas': '#FFD580',

            'compensados_en_curso': 'lightblue',
            'compensados_transcurridos': 'lightgray',
            'compensados_proximos': 'orange',

            'nota_realizada': 'green',
            'nota_rechazada': 'red',
            'nota_pendiente': 'orange',
        }

def update_tareas_colors():
    """Actualiza los colores en ui_sections/tareas.py"""
    colors = get_improved_colors()

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/tareas.py', 'r') as f:
        content = f.read()

    # Actualizar color de tareas vencidas
    old_color = "background-color: #ffcccc"
    new_color = f"background-color: {colors['tarea_vencida']}"
    content = content.replace(old_color, new_color)

    # Actualizar colores de estado (texto)
    content = content.replace("color: green", f"color: {colors['nota_realizada']}")
    content = content.replace("color: blue", f"color: {colors['tarea_en_curso']}")
    content = content.replace("color: orange", f"color: {colors['tarea_pendiente']}")

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/tareas.py', 'w') as f:
        f.write(content)

    print("✅ Colores de tareas actualizados")

def update_vacaciones_colors():
    """Actualiza los colores en ui_sections/vacaciones.py"""
    colors = get_improved_colors()

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/vacaciones.py', 'r') as f:
        content = f.read()

    # Actualizar colores de vacaciones
    content = content.replace("background-color: lightblue", f"background-color: {colors['vacaciones_en_curso']}")
    content = content.replace("background-color: lightgray", f"background-color: {colors['vacaciones_transcurridas']}")
    content = content.replace("background-color: #FFD580", f"background-color: {colors['vacaciones_proximas']}")

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/vacaciones.py', 'w') as f:
        f.write(content)

    print("✅ Colores de vacaciones actualizados")

def update_compensados_colors():
    """Actualiza los colores en ui_sections/compensados.py"""
    colors = get_improved_colors()

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/compensados.py', 'r') as f:
        content = f.read()

    # Actualizar colores de compensados
    content = content.replace("background-color: lightblue", f"background-color: {colors['compensados_en_curso']}")
    content = content.replace("background-color: lightgray", f"background-color: {colors['compensados_transcurridos']}")
    content = content.replace("background-color: orange", f"background-color: {colors['compensados_proximos']}")

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/compensados.py', 'w') as f:
        f.write(content)

    print("✅ Colores de compensados actualizados")

def update_notas_colors():
    """Actualiza los colores en ui_sections/notas.py"""
    colors = get_improved_colors()

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/notas.py', 'r') as f:
        content = f.read()

    # Actualizar colores de notas
    content = content.replace("color: green", f"color: {colors['nota_realizada']}")
    content = content.replace("color: red", f"color: {colors['nota_rechazada']}")
    content = content.replace("color: orange", f"color: {colors['nota_pendiente']}")

    with open('/home/nleal/gestor_proyectos_streamlit/ui_sections/notas.py', 'w') as f:
        f.write(content)

    print("✅ Colores de notas actualizados")

def main():
    """Función principal para actualizar todos los colores"""
    print("🎨 Actualizando colores para mejorar contraste en modo oscuro...\n")

    colors = get_improved_colors()

    print("📋 Colores que se aplicarán:")
    print(f"   • Tareas vencidas: {colors['tarea_vencida']}")
    print(f"   • Tareas en curso: {colors['tarea_en_curso']}")
    print(f"   • Tareas pendientes: {colors['tarea_pendiente']}")
    print(f"   • Vacaciones en curso: {colors['vacaciones_en_curso']}")
    print(f"   • Vacaciones transcurridas: {colors['vacaciones_transcurridas']}")
    print(f"   • Vacaciones próximas: {colors['vacaciones_proximas']}")
    print(f"   • Compensados en curso: {colors['compensados_en_curso']}")
    print(f"   • Compensados transcurridos: {colors['compensados_transcurridos']}")
    print(f"   • Compensados próximos: {colors['compensados_proximos']}")
    print(f"   • Notas realizadas: {colors['nota_realizada']}")
    print(f"   • Notas rechazadas: {colors['nota_rechazada']}")
    print(f"   • Notas pendientes: {colors['nota_pendiente']}")
    print()

    # Actualizar todos los archivos
    update_tareas_colors()
    update_vacaciones_colors()
    update_compensados_colors()
    update_notas_colors()

    print("\n✅ ¡Todos los colores han sido actualizados!")
    print("🎯 Mejoras implementadas:")
    print("   • Colores más intensos para mejor contraste")
    print("   • Mejor legibilidad en modo oscuro")
    print("   • Mantenida la estética y significado de cada color")
    print("   • Colores optimizados para texto blanco")

    print("\n🔄 Para aplicar los cambios:")
    print("   1. Reinicia la aplicación de Streamlit")
    print("   2. Los nuevos colores se aplicarán automáticamente")
    print("   3. Verifica que el contraste sea adecuado")

if __name__ == "__main__":
    main()
