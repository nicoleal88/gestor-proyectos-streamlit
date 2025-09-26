#!/usr/bin/env python3
"""
Script para alternar entre colores de modo claro y modo oscuro.
Permite cambiar fácilmente la paleta de colores según el tema deseado.
"""

import sys

def set_dark_mode_colors():
    """Aplica colores optimizados para modo oscuro"""
    colors = {
        # Tareas
        'tarea_vencida': '#8B0000',  # Rojo oscuro intenso
        'tarea_en_curso': '#0066CC',  # Azul intenso
        'tarea_pendiente': '#FF8C00',  # Naranja intenso

        # Vacaciones
        'vacaciones_en_curso': '#1E90FF',  # Azul intenso
        'vacaciones_transcurridas': '#696969',  # Gris oscuro
        'vacaciones_proximas': '#FF8C00',  # Naranja intenso

        # Compensados
        'compensados_en_curso': '#1E90FF',  # Azul intenso
        'compensados_transcurridos': '#696969',  # Gris oscuro
        'compensados_proximos': '#FF8C00',  # Naranja intenso

        # Notas
        'nota_realizada': '#32CD32',  # Verde lima
        'nota_rechazada': '#FF6347',  # Rojo tomate
        'nota_pendiente': '#FFD700',  # Oro
    }

    update_all_colors(colors, "Modo Oscuro")
    return colors

def set_light_mode_colors():
    """Aplica colores optimizados para modo claro"""
    colors = {
        # Tareas
        'tarea_vencida': '#ffcccc',  # Rojo claro
        'tarea_en_curso': 'lightblue',  # Azul claro
        'tarea_pendiente': '#FFD580',  # Naranja claro

        # Vacaciones
        'vacaciones_en_curso': 'lightblue',  # Azul claro
        'vacaciones_transcurridas': 'lightgray',  # Gris claro
        'vacaciones_proximas': '#FFD580',  # Naranja claro

        # Compensados
        'compensados_en_curso': 'lightblue',  # Azul claro
        'compensados_transcurridos': 'lightgray',  # Gris claro
        'compensados_proximos': 'orange',  # Naranja

        # Notas
        'nota_realizada': 'green',  # Verde
        'nota_rechazada': 'red',  # Rojo
        'nota_pendiente': 'orange',  # Naranja
    }

    update_all_colors(colors, "Modo Claro")
    return colors

def update_all_colors(colors, mode_name):
    """Actualiza todos los archivos con los colores especificados"""
    files_to_update = [
        '/home/nleal/gestor_proyectos_streamlit/ui_sections/tareas.py',
        '/home/nleal/gestor_proyectos_streamlit/ui_sections/vacaciones.py',
        '/home/nleal/gestor_proyectos_streamlit/ui_sections/compensados.py',
        '/home/nleal/gestor_proyectos_streamlit/ui_sections/notas.py'
    ]

    for file_path in files_to_update:
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Actualizar cada color
            for color_name, color_value in colors.items():
                if color_name == 'tarea_vencida':
                    old_value = r"background-color: #[0-9a-fA-F]{6}|background-color: #[0-9a-fA-F]{3}"
                    content = re.sub(old_value, f"background-color: {color_value}", content, count=1, flags=re.IGNORECASE)
                elif color_name.endswith('_en_curso'):
                    content = content.replace("background-color: lightblue", f"background-color: {color_value}")
                    content = content.replace("color: blue", f"color: {color_value}")
                elif color_name.endswith('_transcurridas') or color_name.endswith('_transcurridos'):
                    content = content.replace("background-color: lightgray", f"background-color: {color_value}")
                elif color_name.endswith('_proximas') or color_name.endswith('_proximos'):
                    content = content.replace("background-color: orange", f"background-color: {color_value}")
                    content = content.replace("background-color: #FFD580", f"background-color: {color_value}")
                elif color_name.endswith('_pendiente'):
                    content = content.replace("color: orange", f"color: {color_value}")
                elif color_name.endswith('_realizada'):
                    content = content.replace("color: green", f"color: {color_value}")
                elif color_name.endswith('_rechazada'):
                    content = content.replace("color: red", f"color: {color_value}")

            with open(file_path, 'w') as f:
                f.write(content)

            print(f"✅ {file_path.split('/')[-1]} actualizado para {mode_name}")

        except FileNotFoundError:
            print(f"❌ Archivo {file_path} no encontrado")

    print(f"\n🎨 ¡Colores actualizados para {mode_name}!")
    print("🔄 Reinicia la aplicación para ver los cambios.")

def show_color_preview(colors, mode_name):
    """Muestra una vista previa de los colores"""
    print(f"\n📋 Vista previa de colores para {mode_name}:")
    print("=" * 50)

    print("🔴 Tareas vencidas:" + " " * 20 + f"{colors['tarea_vencida']}")
    print("🔵 Tareas en curso:" + " " * 20 + f"{colors['tarea_en_curso']}")
    print("🟠 Tareas pendientes:" + " " * 18 + f"{colors['tarea_pendiente']}")
    print()
    print("🔵 Vacaciones en curso:" + " " * 16 + f"{colors['vacaciones_en_curso']}")
    print("⚫ Vacaciones transcurridas:" + " " * 12 + f"{colors['vacaciones_transcurridas']}")
    print("🟠 Vacaciones próximas:" + " " * 17 + f"{colors['vacaciones_proximas']}")
    print()
    print("🔵 Compensados en curso:" + " " * 16 + f"{colors['compensados_en_curso']}")
    print("⚫ Compensados transcurridos:" + " " * 12 + f"{colors['compensados_transcurridos']}")
    print("🟠 Compensados próximos:" + " " * 17 + f"{colors['compensados_proximos']}")
    print()
    print("🟢 Notas realizadas:" + " " * 20 + f"{colors['nota_realizada']}")
    print("🔴 Notas rechazadas:" + " " * 20 + f"{colors['nota_rechazada']}")
    print("🟡 Notas pendientes:" + " " * 20 + f"{colors['nota_pendiente']}")

def main():
    """Función principal"""
    print("🎨 Selector de Paleta de Colores")
    print("=" * 40)
    print()
    print("Selecciona el modo de color:")
    print("1. 🌙 Modo Oscuro (colores intensos)")
    print("2. ☀️  Modo Claro (colores suaves)")
    print("3. 👁️  Vista previa de colores")
    print("4. ❌ Salir")
    print()

    while True:
        try:
            choice = input("Elige una opción (1-4): ").strip()

            if choice == "1":
                colors = set_dark_mode_colors()
                show_color_preview(colors, "Modo Oscuro")
                break
            elif choice == "2":
                colors = set_light_mode_colors()
                show_color_preview(colors, "Modo Claro")
                break
            elif choice == "3":
                print("\n🌙 Vista previa - Modo Oscuro:")
                dark_colors = {
                    'tarea_vencida': '#8B0000', 'tarea_en_curso': '#0066CC', 'tarea_pendiente': '#FF8C00',
                    'vacaciones_en_curso': '#1E90FF', 'vacaciones_transcurridas': '#696969', 'vacaciones_proximas': '#FF8C00',
                    'compensados_en_curso': '#1E90FF', 'compensados_transcurridos': '#696969', 'compensados_proximos': '#FF8C00',
                    'nota_realizada': '#32CD32', 'nota_rechazada': '#FF6347', 'nota_pendiente': '#FFD700'
                }
                show_color_preview(dark_colors, "Modo Oscuro")

                print("\n☀️  Vista previa - Modo Claro:")
                light_colors = {
                    'tarea_vencida': '#ffcccc', 'tarea_en_curso': 'lightblue', 'tarea_pendiente': '#FFD580',
                    'vacaciones_en_curso': 'lightblue', 'vacaciones_transcurridas': 'lightgray', 'vacaciones_proximas': '#FFD580',
                    'compensados_en_curso': 'lightblue', 'compensados_transcurridos': 'lightgray', 'compensados_proximos': 'orange',
                    'nota_realizada': 'green', 'nota_rechazada': 'red', 'nota_pendiente': 'orange'
                }
                show_color_preview(light_colors, "Modo Claro")
                print()
            elif choice == "4":
                print("👋 ¡Hasta luego!")
                sys.exit(0)
            else:
                print("❌ Opción no válida. Elige entre 1-4.")
                print()

        except KeyboardInterrupt:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)
        except EOFError:
            print("\n👋 ¡Hasta luego!")
            sys.exit(0)

if __name__ == "__main__":
    main()
