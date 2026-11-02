
import math
from fractions import Fraction
import tkinter as tk
from tkinter import ttk, messagebox

# Herramientas para crear e integrar las graficas en la ventana.
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.ticker import FuncFormatter, MultipleLocator


# ==========================================
# 1. CONSTANTES
# ==========================================

# Periodo comun de las tres senales: T = 2*pi.
T = 2 * math.pi
# Cantidades de armonicos disponibles para el usuario.
VALORES_N = [1, 2, 3, 5, 10, 20, 50, 100, 150, 200]
# Muestras usadas para aproximar el RMSE y las potencias.
NUM_MUESTRAS_METRICAS = 4000
# Puntos usados para dibujar las senales.
NUM_PUNTOS_GRAFICA = 4001
# Tolerancia para reconocer los puntos de salto.
TOLERANCIA_SALTOS = 1e-10


# ==========================================
# 2. SENALES ORIGINALES
# ==========================================

def senal_original(t, tipo):
    """Evalua una senal de amplitud 1, repetida con periodo T = 2*pi."""

    # Lleva cada tiempo a un solo periodo: [-pi, pi).
    t_periodico = (t + math.pi) % T - math.pi

    if tipo == "Cuadrada":
        # En los saltos toma el valor medio: cero.
        if abs(t_periodico) < TOLERANCIA_SALTOS or abs(t_periodico + math.pi) < TOLERANCIA_SALTOS:
            return 0
        # Fuera de los saltos alterna entre +1 y -1.
        return 1 if t_periodico > 0 else -1

    elif tipo == "Triangular":
        # Su amplitud cambia linealmente con la distancia al centro.
        return 1 - 2 * abs(t_periodico) / math.pi

    elif tipo == "Sierra":
        # En el salto toma el valor medio: cero.
        if abs(t_periodico + math.pi) < TOLERANCIA_SALTOS:
            return 0
        # Aumenta linealmente y se repite cada periodo.
        return t_periodico / math.pi


# ==========================================
# 3. RECONSTRUCCION DE FOURIER
# ==========================================

def reconstruir(t, tipo, N):
    """Suma los primeros N armonicos usando coeficientes de Fourier analiticos."""

    # Todas tienen media cero: no se necesita termino constante.
    suma = 0

    # Acumula los primeros N armonicos de Fourier.
    for n in range(1, N + 1):

        # Cuadrada: senos de armonicos impares; bn = 4/(n*pi).
        if tipo == "Cuadrada" and n % 2 != 0:
            bn = 4 / (n * math.pi)
            suma += bn * math.sin(n * t)

        # Triangular: cosenos de armonicos impares; an = 8/(n^2*pi^2).
        elif tipo == "Triangular" and n % 2 != 0:
            an = 8 / (n**2 * math.pi**2)
            suma += an * math.cos(n * t)

        # Sierra: senos de todos los armonicos, con signo alternante.
        elif tipo == "Sierra":
            bn = 2 * (-1)**(n + 1) / (n * math.pi)
            suma += bn * math.sin(n * t)

    # Devuelve la aproximacion formada por N armonicos.
    return suma


# ==========================================
# 4. MAGNITUD DE LOS COEFICIENTES COMPLEJOS
# ==========================================

def magnitud_cn(tipo, n):
    """Calcula |c_n| para mostrar el espectro de lineas bilateral."""

    # No hay componente continua: c_0 = 0.
    if n == 0:
        return 0

    # El espectro es simetrico en magnitud: |c_-n| = |c_n|.
    k = abs(n)

    if tipo == "Cuadrada":
        # Solo existen lineas en armonicos impares.
        return 2 / (math.pi * k) if k % 2 != 0 else 0

    elif tipo == "Triangular":
        # Los armonicos impares disminuyen como 1/n^2.
        return 4 / (math.pi**2 * k**2) if k % 2 != 0 else 0

    elif tipo == "Sierra":
        # Aparecen todos los armonicos y disminuyen como 1/n.
        return 1 / (math.pi * k)


# ==========================================
# 5. ERROR Y POTENCIAS
# ==========================================

def calcular_metricas(tipo, N):
    """Aproxima el RMSE y las dos potencias promedio en un periodo."""

    # Acumula error y cuadrados para calcular promedios.
    suma_error = 0
    suma_original = 0
    suma_reconstruida = 0

    for k in range(NUM_MUESTRAS_METRICAS):

        # Muestreo en puntos medios para evitar evaluar exactamente los saltos.
        t = -math.pi + (k + 0.5) * T / NUM_MUESTRAS_METRICAS

        x = senal_original(t, tipo)
        xr = reconstruir(t, tipo, N)

        # Error cuadratico y cuadrados de cada senal.
        suma_error += (x - xr)**2
        suma_original += x**2
        suma_reconstruida += xr**2

    # RMSE: raiz del promedio del error cuadratico.
    rmse = math.sqrt(suma_error / NUM_MUESTRAS_METRICAS)

    # Potencia: promedio temporal del cuadrado de la senal.
    p_original = suma_original / NUM_MUESTRAS_METRICAS
    p_reconstruida = suma_reconstruida / NUM_MUESTRAS_METRICAS

    return rmse, p_original, p_reconstruida


# ==========================================
# 5A. FORMATO TEMPORAL CON FRACCIONES DE PI
# ==========================================

def etiqueta_pi(valor, posicion):
    """Convierte los valores del eje t en etiquetas como -3pi/2, pi/2, 2pi."""
    # Expresa cada marca como una fraccion sencilla de pi.
    fraccion = Fraction(valor / math.pi).limit_denominator(4)
    numerador = fraccion.numerator
    denominador = fraccion.denominator

    # El cero no necesita simbolo pi.
    if numerador == 0:
        return "0"

    # Separa el signo para construir la etiqueta.
    signo = "-" if numerador < 0 else ""
    numerador = abs(numerador)

    # Escribe multiplos enteros de pi.
    if denominador == 1:
        coeficiente = "" if numerador == 1 else str(numerador)
        return rf"${signo}{coeficiente}\pi$"

    # Escribe fracciones de pi cuando hace falta.
    coeficiente = "" if numerador == 1 else str(numerador)
    return rf"${signo}\frac{{{coeficiente}\pi}}{{{denominador}}}$"


def configurar_eje_tiempo(eje, t_inicio, t_fin):
    """Distribuye marcas legibles sin modificar los datos ni el intervalo temporal."""
    # Ajusta la separacion de marcas al intervalo visible.
    paso_pi = 0.25
    ancho_en_pi = (t_fin - t_inicio) / math.pi
    while ancho_en_pi / paso_pi > 8:
        paso_pi *= 2

    # Cambia solo la presentacion del eje, no los calculos.
    eje.xaxis.set_major_locator(MultipleLocator(paso_pi * math.pi))
    eje.xaxis.set_major_formatter(FuncFormatter(etiqueta_pi))
    eje.set_xlim(t_inicio, t_fin)
    eje.set_xlabel("Tiempo (t)")


# ==========================================
# 6. CREAR LA VENTANA
# ==========================================

# Crea la ventana principal de la aplicacion.
ventana = tk.Tk()
ventana.title("Reconstruccion de senales - Fourier")
ventana.geometry("1200x850")

# Reserva una franja superior para los controles.
controles = ttk.Frame(ventana, padding=10)
controles.pack(fill="x")

# Selector del tipo de senal.
ttk.Label(controles, text="Señal:").grid(row=0, column=0)

selector_senal = ttk.Combobox(
    controles,
    values=["Cuadrada", "Triangular", "Sierra"],
    state="readonly",
    width=14
)
# La cuadrada aparece al abrir el programa.
selector_senal.set("Cuadrada")
selector_senal.grid(row=0, column=1, padx=8)

# Selector del numero de armonicos N.
ttk.Label(controles, text="Armónicos N:").grid(row=0, column=2)

selector_n = ttk.Combobox(
    controles,
    values=VALORES_N,
    state="readonly",
    width=8
)
# Inicia con cinco armonicos.
selector_n.set("5")
selector_n.grid(row=0, column=3, padx=8)

# Entrada del limite inicial, expresado en multiplos de pi.
ttk.Label(controles, text="Desde (x pi):").grid(row=0, column=4)

entrada_inicio = ttk.Entry(controles, width=7)
entrada_inicio.insert(0, "-2")
entrada_inicio.grid(row=0, column=5, padx=5)

# Entrada del limite final, tambien en multiplos de pi.
ttk.Label(controles, text="Hasta (x pi):").grid(row=0, column=6)

entrada_fin = ttk.Entry(controles, width=7)
entrada_fin.insert(0, "2")
entrada_fin.grid(row=0, column=7, padx=5)


# ==========================================
# 7. CREAR LAS CUATRO GRAFICAS
# ==========================================

# Distribuye las cuatro graficas en una matriz de 2 x 2.
figura = Figure(figsize=(11, 7), dpi=95)
ejes = figura.subplots(2, 2)

# Inserta las graficas de Matplotlib en la ventana Tkinter.
canvas = FigureCanvasTkAgg(figura, master=ventana)
canvas.get_tk_widget().pack(fill="both", expand=True)

# Espacio inferior para mostrar RMSE y potencias.
resultado = ttk.Label(
    ventana,
    text="",
    font=("Arial", 12),
    padding=10
)
resultado.pack()


# ==========================================
# 8. FUNCION PARA ACTUALIZAR LA INTERFAZ
# ==========================================

def actualizar():
    """Valida los controles y actualiza las cuatro graficas y las metricas."""

    try:
        # Lee la senal y el numero de armonicos seleccionados.
        tipo = selector_senal.get()
        N = int(selector_n.get())

        # Interpreta los limites como multiplos de pi.
        t_inicio = float(entrada_inicio.get()) * math.pi
        t_fin = float(entrada_fin.get()) * math.pi

        # Rechaza NaN e infinito.
        if not math.isfinite(t_inicio) or not math.isfinite(t_fin):
            raise ValueError("Los tiempos deben ser finitos")

        # Evita intervalos vacios o invertidos.
        if t_inicio >= t_fin:
            raise ValueError("El tiempo inicial debe ser menor")

        # Prepara los datos de las tres graficas temporales.
        tiempos = []

        originales = []
        reconstruidas = []
        errores = []

        # Recorre el intervalo, incluyendo ambos extremos.
        for i in range(NUM_PUNTOS_GRAFICA):

            t = t_inicio + i * (t_fin - t_inicio) / (NUM_PUNTOS_GRAFICA - 1)

            # Compara el valor original con su reconstruccion.
            x = senal_original(t, tipo)
            xr = reconstruir(t, tipo, N)

            tiempos.append(t)
            originales.append(x)
            reconstruidas.append(xr)
            errores.append(abs(x - xr))

        # Prepara las lineas del espectro bilateral: n = f/f0.
        frecuencias = []
        magnitudes = []

        for n in range(-N, N + 1):

            mag = magnitud_cn(tipo, n)

            if mag > 0:
                frecuencias.append(n)
                magnitudes.append(mag)

        # Limpia los cuatro paneles antes de actualizarlos.
        for eje in ejes.flat:
            eje.clear()
            eje.grid(True, alpha=0.3)

        # GRAFICA 1: senal original de referencia.
        ejes[0, 0].plot(tiempos, originales)
        ejes[0, 0].set_title("Señal original")
        ejes[0, 0].set_xlabel("Tiempo")
        ejes[0, 0].set_ylabel("s(t)")

        # GRAFICA 2: compara la original con la reconstruccion.
        ejes[0, 1].plot(tiempos, originales, "--",
                        label="Original")
        ejes[0, 1].plot(tiempos, reconstruidas,
                        label="Reconstruida")
        ejes[0, 1].set_title("Reconstruccion de Fourier")
        ejes[0, 1].set_xlabel("Tiempo")
        ejes[0, 1].legend()

        # GRAFICA 3: diferencia absoluta en cada instante.
        ejes[1, 0].plot(tiempos, errores)
        ejes[1, 0].set_title("Error absoluto")
        ejes[1, 0].set_xlabel("Tiempo")
        ejes[1, 0].set_ylabel("Error")

        # Etiqueta el tiempo en fracciones de pi.
        for eje_tiempo in (ejes[0, 0], ejes[0, 1], ejes[1, 0]):
            configurar_eje_tiempo(eje_tiempo, t_inicio, t_fin)

        # GRAFICA 4: magnitud de los coeficientes de Fourier.
        ejes[1, 1].vlines(frecuencias, 0, magnitudes)
        ejes[1, 1].set_title("Espectro de lineas")
        ejes[1, 1].set_xlabel("Frecuencia normalizada (f/f0)")
        ejes[1, 1].set_ylabel("|c_n|")

        # Ajusta los espacios y vuelve a dibujar las graficas.
        figura.tight_layout()
        canvas.draw_idle()

        # Calcula el RMSE y las potencias promedio.
        rmse, p0, pr = calcular_metricas(tipo, N)

        # Presenta los resultados numericos bajo las graficas.
        resultado.config(
            text=f"RMSE: {rmse:.6f}     "
                 f"Potencia original: {p0:.6f}     "
                 f"Potencia reconstruida: {pr:.6f}"
        )

    # Muestra un aviso si los parametros ingresados son invalidos.
    except ValueError as error:
        messagebox.showerror("Error en parametros", str(error))


# ==========================================
# 9. CONECTAR LOS CONTROLES
# ==========================================

# Boton para actualizar manualmente las graficas.
boton = ttk.Button(
    controles,
    text="Actualizar",
    command=actualizar
)
boton.grid(row=0, column=8, padx=10)

# Actualiza al cambiar la senal o el numero de armonicos.
selector_senal.bind(
    "<<ComboboxSelected>>",
    lambda evento: actualizar()
)

selector_n.bind(
    "<<ComboboxSelected>>",
    lambda evento: actualizar()
)

# Tambien permite actualizar al presionar Enter en un limite.
entrada_inicio.bind("<Return>", lambda evento: actualizar())
entrada_fin.bind("<Return>", lambda evento: actualizar())


# ==========================================
# 10. INICIAR LA APLICACION
# ==========================================

# Dibuja los primeros resultados al abrir la aplicacion.
actualizar()
# Mantiene la ventana abierta y responde a las acciones del usuario.
ventana.mainloop()
