import multiprocessing
import time
import random
import queue  # Añadido para manejar la excepción específica
from datetime import datetime
import tkinter as tk
from tkinter.scrolledtext import ScrolledText

# --- Base de datos de acciones (valores base reales aproximados) ---
# Este diccionario almacena algunos tickers junto con valores base aproximados.
STOCKS_DATA = {
    "AAPL": 175,
    "MSFT": 325,
    "AMZN": 120,
    "TSLA": 220,
    "GOOGL": 135,
    "META": 250,
    "BRK.B": 310,
    "JPM": 140,
    "JNJ": 160,
    "V": 230,
    "PG": 150,
    "NVDA": 450,
    "HD": 340,
    "DIS": 100,
    "MA": 380,
}

# --- Función auxiliar para enviar logs a la cola ---
# Esta función envía el mensaje 'msg' a la cola 'log_queue',
# de modo que la GUI pueda recuperar y mostrar los mensajes.
def log(msg, log_queue):
    log_queue.put(msg)

# --- Funciones de la simulación ---

def producer(producer_id, orders_queue, total_orders, stop_event, log_queue):
    """
    Genera órdenes de compra o venta para las acciones del S&P500.
    Cada orden contiene:
      - Ticker y precio base de STOCKS_DATA (con variación).
      - order_type: 'buy' o 'sell'.
      - Cantidad aleatoria de 1 a 10.
      - Marca de tiempo.
      - Identificador único.
    """
    for i in range(total_orders):
        # Si el evento de detención está activo, salimos del bucle.
        if stop_event.is_set():
            break

        # Se elige aleatoriamente si la orden es de compra o venta.
        order_type = random.choice(['buy', 'sell'])
        # Se elige un ticker aleatorio de la lista de acciones.
        stock = random.choice(list(STOCKS_DATA.keys()))
        # Obtenemos el precio base del ticker.
        base_price = STOCKS_DATA[stock]
        # Para la compra, el precio sube hasta un 5%, para venta, baja hasta un 5%.
        if order_type == 'buy':
            price = int(base_price * (1 + random.uniform(0, 0.05)))
        else:
            price = int(base_price * (1 - random.uniform(0, 0.05)))
        # La cantidad de acciones solicitadas es aleatoria entre 1 y 10.
        quantity = random.randint(1, 10)
        # Marca de tiempo de la orden.
        timestamp = time.time()
        # Generamos un identificador único para la orden.
        order_id = f"P{producer_id}-O{i}"

        # Se encapsulan todos los datos de la orden en un diccionario.
        order = {
            'order_id': order_id,
            'order_type': order_type,
            'stock': stock,
            'price': price,
            'quantity': quantity,
            'timestamp': timestamp
        }

        # Se agrega la orden a la cola compartida de órdenes.
        orders_queue.put(order)
        # Se registra el log con la información de la nueva orden.
        log(f"[PROD {producer_id}] -> Nueva orden generada: {order}", log_queue)
        # Se duerme un tiempo aleatorio para simular retardo en la generación de órdenes.
        time.sleep(0.3 * random.random())


def consumer(consumer_id, orders_queue, buy_orders, sell_orders, lock,
             trades_counter, accepted_counter, stop_event, max_to_process, log_queue):
    """
    Extrae las órdenes de la cola 'orders_queue' y las procesa mediante la función de matching.
    Cada consumidor tiene un límite (max_to_process) de órdenes que puede procesar.
    Si se supera este límite, no procesa más órdenes y las regresa a la cola.
    """
    processed_count = 0  # Contador de cuántas órdenes ha procesado este consumidor.
    while True:
        # Si la señal de stop está activa y no hay órdenes en la cola, salimos.
        if stop_event.is_set() and orders_queue.empty():
            break

        try:
            # Intentamos obtener una orden de la cola con timeout.
            order = orders_queue.get(timeout=0.2)
        except queue.Empty:
            # Si no hay orden en la cola dentro de ese lapso, seguimos intentando.
            continue

        # Verificamos si el consumidor aún puede procesar órdenes.
        if processed_count < max_to_process:
            log(f"[CONS {consumer_id}] -> Procesando orden: {order}", log_queue)
            time.sleep(0.3)  # Simulamos algo de retardo.
            with lock:
                # Bloqueamos la sección crítica donde se hace el matching.
                if order['order_type'] == 'buy':
                    # Matching con órdenes de venta.
                    match_buy_order(order, sell_orders, trades_counter, log_queue)
                    # Si la orden no se completó, se pasa a la lista de órdenes de compra pendientes.
                    if order['quantity'] > 0:
                        buy_orders.append(order)
                        log(f"[CONS {consumer_id}] -> Orden de compra remanente añadida a buy_orders.", log_queue)
                else:
                    # Matching con órdenes de compra.
                    match_sell_order(order, buy_orders, trades_counter, log_queue)
                    # Si la orden no se completó, se pasa a la lista de órdenes de venta pendientes.
                    if order['quantity'] > 0:
                        sell_orders.append(order)
                        log(f"[CONS {consumer_id}] -> Orden de venta remanente añadida a sell_orders.", log_queue)
            # Incrementamos el conteo de órdenes procesadas tanto local como global.
            processed_count += 1
            accepted_counter.value += 1
            time.sleep(0.3)
        else:
            # Si el consumidor ya alcanzó su límite, regresa la orden a la cola y sale.
            orders_queue.put(order)
            break


def match_buy_order(buy_order, sell_orders, trades_counter, log_queue):
    """
    Matching para una orden de compra:
      - Localiza las órdenes de venta del mismo ticker.
      - Las ordena en base a su precio (ascendente).
      - Ejecuta trades siempre que el precio de venta sea <= al de compra.
    """
    # Filtramos las órdenes de venta del mismo stock y creamos una lista local.
    local_sell_orders = [o for o in list(sell_orders) if o['stock'] == buy_order['stock']]
    # Ordenamos esa lista local por precio de menor a mayor.
    local_sell_orders.sort(key=lambda x: x['price'])

    i = 0
    # Iteramos mientras queden órdenes de venta locales y la orden de compra aún tenga cantidad.
    while i < len(local_sell_orders) and buy_order['quantity'] > 0:
        sell_order = local_sell_orders[i]
        # Si el precio de venta es menor o igual al de compra, se produce el matching.
        if sell_order['price'] <= buy_order['price']:
            # Se determina cuántas acciones se pueden cruzar (mínimo de ambas órdenes).
            trade_qty = min(buy_order['quantity'], sell_order['quantity'])
            # Se descuenta la cantidad cruzada de la orden de compra y de la de venta.
            buy_order['quantity'] -= trade_qty
            sell_order['quantity'] -= trade_qty
            # Se incrementa el contador global de trades.
            trades_counter.value += 1
            # Registramos el match en los logs.
            log(
                f"   [MATCH] Buy {buy_order['order_id']} ({buy_order['stock']} @{buy_order['price']}) "
                f"<-> Sell {sell_order['order_id']} ({sell_order['stock']} @{sell_order['price']}) "
                f"-> Cantidad: {trade_qty}",
                log_queue
            )
            # Si la orden de venta se completó, se elimina de la lista local.
            if sell_order['quantity'] == 0:
                local_sell_orders.pop(i)
            else:
                i += 1
            time.sleep(0.4)
        else:
            # Si la siguiente orden de venta tiene un precio mayor al de compra,
            # no hay razón para seguir buscando, se rompe el bucle.
            break

    # Actualizamos la lista global de órdenes de venta:
    #  - Dejamos las órdenes de otros tickers.
    #  - Reemplazamos las órdenes del mismo ticker con las cantidades ya modificadas.
    updated_sell_orders = [o for o in sell_orders if o['stock'] != buy_order['stock']]
    updated_sell_orders.extend(local_sell_orders)
    sell_orders[:] = updated_sell_orders


def match_sell_order(sell_order, buy_orders, trades_counter, log_queue):
    """
    Matching para una orden de venta:
      - Localiza las órdenes de compra del mismo ticker.
      - Las ordena en base a su precio (descendente).
      - Ejecuta trades siempre que el precio de compra sea >= al de venta.
    """
    # Filtramos las órdenes de compra del mismo stock.
    local_buy_orders = [o for o in list(buy_orders) if o['stock'] == sell_order['stock']]
    # Ordenamos la lista local por precio de mayor a menor.
    local_buy_orders.sort(key=lambda x: x['price'], reverse=True)

    i = 0
    # Mientras haya órdenes de compra y la orden de venta aún tenga cantidad.
    while i < len(local_buy_orders) and sell_order['quantity'] > 0:
        buy_order = local_buy_orders[i]
        # Si el precio de compra es mayor o igual al de venta, ocurre el matching.
        if buy_order['price'] >= sell_order['price']:
            trade_qty = min(sell_order['quantity'], buy_order['quantity'])
            sell_order['quantity'] -= trade_qty
            buy_order['quantity'] -= trade_qty
            trades_counter.value += 1
            # Registramos el match.
            log(
                f"   [MATCH] Sell {sell_order['order_id']} ({sell_order['stock']} @{sell_order['price']}) "
                f"<-> Buy {buy_order['order_id']} ({buy_order['stock']} @{buy_order['price']}) "
                f"-> Cantidad: {trade_qty}",
                log_queue
            )
            if buy_order['quantity'] == 0:
                local_buy_orders.pop(i)
            else:
                i += 1
            time.sleep(0.4)
        else:
            break

    updated_buy_orders = [o for o in buy_orders if o['stock'] != sell_order['stock']]
    updated_buy_orders.extend(local_buy_orders)
    buy_orders[:] = updated_buy_orders


def simulation_process(log_queue):
    """
    Orquesta la simulación completa:
      1. Anuncia apertura de la "bolsa".
      2. Inicia un productor que genera un número aleatorio de órdenes.
      3. Inicia un número aleatorio de consumidores, cada uno con un límite aleatorio.
      4. Tras un tiempo, se cierra la sesión y se muestran estadísticas.
    """
    # Usamos un Manager para crear estructuras de datos compartidas entre procesos.
    manager = multiprocessing.Manager()

    # Cola de órdenes compartida.
    orders_queue = manager.Queue()
    # Listas compartidas para órdenes pendientes de compra y venta.
    buy_orders = manager.list()
    sell_orders = manager.list()
    # Lock para proteger la sección crítica.
    lock = manager.Lock()
    # Contadores compartidos para el número de trades realizados y órdenes aceptadas.
    trades_counter = manager.Value('i', 0)
    accepted_counter = manager.Value('i', 0)
    # Evento para señalar cuándo debe cerrarse la "sesión".
    stop_event = manager.Event()

    # Obtenemos la hora de apertura.
    apertura = datetime.now().strftime("%H:%M:%S")
    log(f"=== Bolsa abierta a las {apertura} ===", log_queue)

    # Configuración:
    # Se determina de forma aleatoria:
    #  - El total de órdenes (50 a 100)
    #  - El número de consumidores (2 a 5)
    #  - El límite de órdenes que cada consumidor puede procesar (20 a 40)
    TOTAL_ORDERS = random.randint(50, 100)
    NUM_CONSUMERS = random.randint(2, 5)
    consumer_limits = [random.randint(20, 40) for _ in range(NUM_CONSUMERS)]

    # Creamos e iniciamos el proceso del productor.
    prod = multiprocessing.Process(
        target=producer,
        args=(0, orders_queue, TOTAL_ORDERS, stop_event, log_queue)
    )

    consumers = []
    # Creamos e iniciamos los procesos de consumidor.
    for i in range(NUM_CONSUMERS):
        p = multiprocessing.Process(
            target=consumer,
            args=(
                i,
                orders_queue,
                buy_orders,
                sell_orders,
                lock,
                trades_counter,
                accepted_counter,
                stop_event,
                consumer_limits[i],
                log_queue,
            )
        )
        consumers.append(p)

    # Iniciamos el productor.
    prod.start()
    # Iniciamos los consumidores.
    for p in consumers:
        p.start()

    # Esperamos a que el productor termine.
    prod.join()

    # Damos un margen de 3 segundos para que se procesen las órdenes.
    time.sleep(3)
    # Se activa el evento de stop para indicar a los consumidores que deben terminar.
    stop_event.set()

    # Esperamos a que todos los consumidores finalicen.
    for p in consumers:
        p.join()

    # Procesamos si hay órdenes en la cola que quedaron sin atender.
    pending_queue = 0
    while not orders_queue.empty():
        try:
            orders_queue.get_nowait()
            pending_queue += 1
        except:
            break

    # Total de órdenes pendientes en cola + pendientes de compra y venta.
    total_pending = pending_queue + len(buy_orders) + len(sell_orders)

    # Obtenemos la hora de cierre.
    cierre = datetime.now().strftime("%H:%M:%S")
    log(f"=== Bolsa Cerrada a las {cierre} ===", log_queue)
    # Mostramos estadísticas finales.
    log(f"Órdenes totales generadas: {TOTAL_ORDERS}", log_queue)
    log(f"Órdenes aceptadas (procesadas): {accepted_counter.value}", log_queue)
    log(f"Trades realizados: {trades_counter.value}", log_queue)
    log(f"Órdenes pendientes (sin procesar o remanentes): {total_pending}", log_queue)

    # Si hay órdenes de compra pendientes, las listamos.
    if buy_orders:
        log("\nÓrdenes de compra pendientes:", log_queue)
        for o in buy_orders:
            log(f"   {o}", log_queue)

    # Si hay órdenes de venta pendientes, las listamos.
    if sell_orders:
        log("\nÓrdenes de venta pendientes:", log_queue)
        for o in sell_orders:
            log(f"   {o}", log_queue)

    log("Simulación finalizada.", log_queue)

# --- Código de la Interfaz Gráfica (GUI) con Tkinter ---
class LogGUI(tk.Tk):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue
        # Configuramos la ventana principal.
        self.title("Simulación Bolsa S&P500")
        self.geometry("800x600")
        # Se crea un widget de texto con scroll para mostrar los mensajes.
        self.scrolled_text = ScrolledText(self, state="disabled", font=("Courier", 10))
        self.scrolled_text.pack(expand=True, fill="both")

        # Configuramos diferentes tags de color para distintos tipos de mensajes.
        self.scrolled_text.tag_config("prod", foreground="green")
        self.scrolled_text.tag_config("cons", foreground="blue")
        self.scrolled_text.tag_config("match", foreground="orange")
        self.scrolled_text.tag_config("other", foreground="black")

        # Programamos la función que estará verificando la cola de logs periódicamente.
        self.after(100, self.poll_queue)

    def poll_queue(self):
        """Verifica la cola de logs y actualiza la GUI con los mensajes que hayan llegado."""
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            # Definimos el tag en función del tipo de mensaje.
            if msg.startswith("[PROD"):
                tag = "prod"
            elif msg.startswith("[CONS"):
                tag = "cons"
            elif "[MATCH]" in msg:
                tag = "match"
            else:
                tag = "other"

            # Habilitamos la edición temporal, insertamos el texto y luego la deshabilitamos de nuevo.
            self.scrolled_text.config(state="normal")
            self.scrolled_text.insert(tk.END, msg + "\n", tag)
            self.scrolled_text.config(state="disabled")
            # Hacemos scroll automático al final para mostrar el mensaje más reciente.
            self.scrolled_text.see(tk.END)

        # Programamos la siguiente verificación de la cola.
        self.after(100, self.poll_queue)

# --- Main: Inicia la simulación en un proceso y la GUI en el principal ---
if __name__ == "__main__":
    # Creamos la cola de logs para comunicar el proceso de simulación con la GUI.
    log_queue = multiprocessing.Queue()

    # Iniciamos el proceso que ejecutará toda la lógica de la simulación.
    sim_proc = multiprocessing.Process(target=simulation_process, args=(log_queue,))
    sim_proc.start()

    # Iniciamos la GUI en el proceso principal.
    app = LogGUI(log_queue)
    app.mainloop()

    # Esperamos a que el proceso de simulación termine.
    sim_proc.join()
