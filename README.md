# Simulación Bolsa S&P500

Este proyecto simula un sistema básico de compra y venta de acciones (tipo bolsa de valores) utilizando:
- Múltiples procesos (con `multiprocessing`) para generar y procesar órdenes.
- Una interfaz gráfica con `tkinter`, que muestra en tiempo real los eventos que ocurren en el sistema.

## Características Principales
- **Productor**: Genera órdenes de compra y venta de manera aleatoria para un conjunto fijo de acciones.
- **Consumidores**: Procesan las órdenes, ejecutando el matching entre órdenes de compra y venta.
- **Interfaz Gráfica**: Muestra los logs en tiempo real, diferenciando mensajes de productores, consumidores y emparejamientos (matches).

## Requisitos
- Python
- Módulos estándar: `multiprocessing`, `random`, `datetime`, `tkinter`, etc.

## Ejecución
1. Ejecutar el archivo principal (por ejemplo, `python main.py`).
2. Se abrirá la ventana gráfica que mostrará los eventos de la simulación.
3. El proceso finaliza cuando se cierra la ventana o tras procesar todas las órdenes.

## Estructura
- **producer**: Genera órdenes y las ingresa en una cola compartida.
- **consumer**: Extrae órdenes de la cola, hace el matching y registra las operaciones.
- **simulation_process**: Orquesta toda la lógica, creando al productor, consumidores y recopilando estadísticas.
- **LogGUI**: Interfaz para mostrar registros en tiempo real.

## Link al repositorio
https://github.com/AlvaroSantamariaAnton/Bolsa_concurrente.git