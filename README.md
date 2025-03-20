# Simulación Bolsa S&P500

Este proyecto implementa una simulación básica de un sistema bursátil para un conjunto determinado de acciones, haciendo uso de:
- **Multiprocessing**: para ejecutar el productor y varios consumidores en procesos separados.
- **Tkinter**: para mostrar una interfaz gráfica (GUI) con los registros (logs) de la simulación en tiempo real.
- **Mecanismos de sincronización**: colas de mensajes (para pasar órdenes entre procesos) y un `Lock` que protege la sección de matching.

## ¿Qué hace el programa?

1. **Genera Órdenes (Productor)**  
   - Un proceso productor genera órdenes de compra o venta de manera aleatoria para acciones listadas en un diccionario (`STOCKS_DATA`).  
   - Cada orden contiene: ticker, precio (con variación aleatoria de ±5%), cantidad y un timestamp.

2. **Procesa Órdenes (Consumidores)**  
   - Se crean varios procesos consumidores (un número aleatorio entre 2 y 5).  
   - Cada consumidor extrae órdenes de la cola y las procesa, emparejando (matching) órdenes de compra con órdenes de venta.  
   - Cada consumidor puede procesar únicamente un número limitado de órdenes (también aleatorio).

3. **Interfaz Gráfica (GUI con Tkinter)**  
   - Se utiliza para mostrar los mensajes de manera ordenada, diferenciando quién genera las órdenes (productor), quién las procesa (consumidor) y cuándo se produce un match entre compra y venta.  
   - Permite ver en tiempo real la actividad de la simulación.

## Características Principales

- **Uso de `multiprocessing.Manager()`**: para crear estructuras de datos (listas y colas) que son compartidas y seguras entre procesos.
- **Uso de `queue.Empty`**: para controlar de forma explícita la excepción al tomar órdenes de la cola y no enmascarar otros posibles errores.
- **Protección de Sección Crítica**: al hacer matching de órdenes, se emplea un `Lock` que evita condiciones de carrera.
- **Parámetros Aleatorios**:
  - Número total de órdenes (50 a 100).
  - Número de consumidores (2 a 5).
  - Límite máximo de órdenes por consumidor (20 a 40).

## Requisitos

- Python.
- Módulos estándar: `multiprocessing`, `queue`, `random`, `tkinter`, etc.
  - Tkinter suele venir preinstalado en la mayoría de distribuciones de Python, pero en algunos entornos podría requerir instalación adicional.

## Link al repositorio
https://github.com/AlvaroSantamariaAnton/Bolsa_concurrente.git