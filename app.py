"""
app.py — Interfaz gráfica (Tkinter) del Conversor Caligráfico.

Tres pestañas, siguiendo la estructura del proyecto de referencia (JapaneseMiniProject):
  1. Conversor          -> escribís y ves el texto "escrito a pluma" en tiempo real.
  2. Abecedario         -> tabla de referencia con todas las letras del estilo elegido.
  3. Frases aleatorias  -> genera frases para practicar caligrafía a mano.

Ejecutar:  python app.py
"""
import random
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageTk

import motor
from frases import PANGRAMA, frase_aleatoria

DEMORA_MS = 350  # debounce: renderizar 350 ms después de la última tecla, no en cada una
FONDO = "#efe9dc"


class PanelOpciones(ttk.LabelFrame):
    """Controles de estilo compartidos: cada pestaña tiene los suyos para poder comparar."""

    def __init__(self, padre, al_cambiar, tamano=48):
        super().__init__(padre, text="Pluma, tinta y papel", padding=10)
        self.al_cambiar = al_cambiar
        self.estilo = tk.StringVar(value=next(iter(motor.ESTILOS)))
        self.tinta = tk.StringVar(value="Sepia")
        self.papel = tk.StringVar(value="Cuadriculado")
        self.tamano = tk.IntVar(value=tamano)
        self.temblor = tk.DoubleVar(value=0.5)
        self.presion = tk.DoubleVar(value=0.7)
        self.sombreado = tk.DoubleVar(value=0.6)
        self.semilla = random.randint(1, 9999)

        fila = 0
        for etiqueta, var, valores in [("Estilo", self.estilo, list(motor.ESTILOS)),
                                       ("Tinta", self.tinta, list(motor.TINTAS)),
                                       ("Papel", self.papel, motor.PAPELES)]:
            ttk.Label(self, text=etiqueta).grid(row=fila, column=0, sticky="w", pady=2)
            combo = ttk.Combobox(self, textvariable=var, values=valores, state="readonly", width=34)
            combo.grid(row=fila, column=1, sticky="ew", pady=2)
            combo.bind("<<ComboboxSelected>>", lambda e: self.al_cambiar())
            fila += 1

        for etiqueta, var, desde, hasta in [("Tamaño", self.tamano, 24, 110),
                                            ("Temblor de la mano", self.temblor, 0, 1),
                                            ("Presión del plumín", self.presion, 0, 1),
                                            ("Acumulación de tinta", self.sombreado, 0, 1)]:
            ttk.Label(self, text=etiqueta).grid(row=fila, column=0, sticky="w", pady=2)
            # ButtonRelease: se renderiza al soltar el deslizador, no en cada píxel de arrastre.
            esc = ttk.Scale(self, variable=var, from_=desde, to=hasta, orient="horizontal")
            esc.grid(row=fila, column=1, sticky="ew", pady=2)
            esc.bind("<ButtonRelease-1>", lambda e: self.al_cambiar())
            fila += 1

        ttk.Button(self, text="🎲 Otra mano (variar)", command=self._nueva_semilla).grid(
            row=fila, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.columnconfigure(1, weight=1)

    def _nueva_semilla(self):
        # Misma frase, distinta "toma": como volver a escribirla a mano.
        self.semilla = random.randint(1, 9999)
        self.al_cambiar()

    def config(self, ancho=1200, escala=1) -> motor.Config:
        # escala=2 al guardar: misma composición (mismos saltos de línea) pero al doble de resolución.
        return motor.Config(estilo=self.estilo.get(), tinta=self.tinta.get(), papel=self.papel.get(),
                            tamano=int(self.tamano.get()) * escala, ancho=ancho * escala, temblor=self.temblor.get(),
                            presion=self.presion.get(), sombreado=self.sombreado.get(),
                            semilla=self.semilla)


class VistaHoja(ttk.Frame):
    """Muestra la imagen renderizada escalada al ancho disponible, con scroll vertical."""

    def __init__(self, padre):
        super().__init__(padre)
        self.lienzo = tk.Canvas(self, bg=FONDO, highlightthickness=0)
        barra = ttk.Scrollbar(self, orient="vertical", command=self.lienzo.yview)
        self.lienzo.configure(yscrollcommand=barra.set)
        self.lienzo.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.imagen: Image.Image | None = None
        self._foto = None  # referencia obligatoria: si no, Tkinter borra la imagen (garbage collector)
        self.lienzo.bind("<Configure>", lambda e: self._dibujar())

    def ancho_util(self) -> int:
        # Renderizar al ancho real del panel: así el tamaño elegido se ve 1:1, sin achicar.
        self.lienzo.update_idletasks()
        return max(500, self.lienzo.winfo_width() - 20)

    def mostrar(self, imagen: Image.Image):
        self.imagen = imagen
        self._dibujar()

    def _dibujar(self):
        if self.imagen is None:
            return
        ancho = max(200, self.lienzo.winfo_width() - 20)
        escala = min(1.0, ancho / self.imagen.width)
        vista = self.imagen.resize((int(self.imagen.width * escala), int(self.imagen.height * escala)),
                                   Image.LANCZOS)
        self._foto = ImageTk.PhotoImage(vista)
        self.lienzo.delete("all")
        self.lienzo.create_image(10, 10, image=self._foto, anchor="nw")
        self.lienzo.configure(scrollregion=(0, 0, vista.width + 20, vista.height + 20))


def guardar_png(generar, nombre="caligrafia.png"):
    """generar: función que devuelve la imagen en alta resolución (se calcula solo al guardar)."""
    ruta = filedialog.asksaveasfilename(defaultextension=".png", initialfile=nombre,
                                        filetypes=[("Imagen PNG", "*.png"), ("JPEG", "*.jpg")])
    if ruta:
        generar().convert("RGB").save(ruta)
        messagebox.showinfo("Guardado", f"Imagen guardada en:\n{ruta}")


# ----------------------------------------------------------------------------- pestañas
class PestanaConversor(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre, padding=10)
        izq = ttk.Frame(self)
        izq.pack(side="left", fill="y", padx=(0, 10))

        ttk.Label(izq, text="Escribí tu texto:", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        self.entrada = tk.Text(izq, width=40, height=10, wrap="word", font=("Segoe UI", 11),
                               relief="solid", borderwidth=1)
        self.entrada.pack(fill="x", pady=(4, 10))
        self.entrada.insert("1.0", "Querida Ana:\nte escribo estas líneas con tinta sepia, ¿qué te parece?")
        self.entrada.bind("<KeyRelease>", lambda e: self.programar())

        self.opciones = PanelOpciones(izq, self.programar)
        self.opciones.pack(fill="x")
        ttk.Button(izq, text="💾 Guardar como imagen",
                   command=lambda: guardar_png(lambda: self._render(2))).pack(fill="x", pady=(10, 0))
        self.estado = ttk.Label(izq, text="", foreground="#6b5b45")
        self.estado.pack(anchor="w", pady=(6, 0))

        self.hoja = VistaHoja(self)
        self.hoja.pack(side="left", fill="both", expand=True)
        self._pendiente = None
        self.after(100, self.renderizar)

    def programar(self):
        # Debounce: cancelar el render anterior si el usuario sigue escribiendo.
        if self._pendiente:
            self.after_cancel(self._pendiente)
        self.estado.config(text="Escribiendo…")
        self._pendiente = self.after(DEMORA_MS, self.renderizar)

    def _render(self, escala=1):
        texto = self.entrada.get("1.0", "end-1c")
        return motor.renderizar(texto, self.opciones.config(self.hoja.ancho_util(), escala))

    def renderizar(self):
        self._pendiente = None
        texto = self.entrada.get("1.0", "end-1c")
        self.hoja.mostrar(self._render())
        self.estado.config(text=f"{len(texto)} caracteres convertidos ✓")


class PestanaAbecedario(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre, padding=10)
        izq = ttk.Frame(self)
        izq.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(izq, text="Abecedario de referencia", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(izq, wraplength=300, justify="left",
                  text="Todas las letras (con Ñ, acentos y números) en el estilo elegido. "
                       "Usalo como modelo para copiar a mano.").pack(anchor="w", pady=(4, 10))
        self.opciones = PanelOpciones(izq, self.renderizar, tamano=44)
        self.opciones.papel.set("Pautado caligráfico")
        self.opciones.tinta.set("Azul real")
        self.opciones.temblor.set(0.2)  # menos temblor: es un modelo, debe ser prolijo
        self.opciones.pack(fill="x")
        ttk.Button(izq, text="💾 Guardar abecedario",
                   command=lambda: guardar_png(lambda: self._render(2), "abecedario.png")).pack(fill="x", pady=(10, 0))
        self.hoja = VistaHoja(self)
        self.hoja.pack(side="left", fill="both", expand=True)
        self.after(150, self.renderizar)

    def _render(self, escala=1):
        return motor.renderizar(motor.texto_abecedario(), self.opciones.config(self.hoja.ancho_util(), escala))

    def renderizar(self):
        self.hoja.mostrar(self._render())


class PestanaFrases(ttk.Frame):
    def __init__(self, padre):
        super().__init__(padre, padding=10)
        izq = ttk.Frame(self)
        izq.pack(side="left", fill="y", padx=(0, 10))
        ttk.Label(izq, text="Frases para practicar", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Label(izq, wraplength=300, justify="left",
                  text="Generá una frase al azar, mirá cómo queda en caligrafía y "
                       "copiala en tu cuaderno.").pack(anchor="w", pady=(4, 10))
        self.frase = tk.StringVar(value=PANGRAMA)
        ttk.Label(izq, textvariable=self.frase, wraplength=300, font=("Segoe UI", 11, "italic"),
                  foreground="#4e3018").pack(anchor="w", pady=(0, 10))
        ttk.Button(izq, text="✨ Nueva frase aleatoria", command=self.nueva).pack(fill="x", pady=(0, 10))
        self.opciones = PanelOpciones(izq, self.renderizar, tamano=60)
        self.opciones.papel.set("Rayado")
        self.opciones.pack(fill="x")
        ttk.Button(izq, text="💾 Guardar frase",
                   command=lambda: guardar_png(lambda: self._render(2), "frase.png")).pack(fill="x", pady=(10, 0))
        self.hoja = VistaHoja(self)
        self.hoja.pack(side="left", fill="both", expand=True)
        self.after(200, self.renderizar)

    def nueva(self):
        self.frase.set(frase_aleatoria(self.frase.get()))
        self.renderizar()

    def _render(self, escala=1):
        return motor.renderizar(self.frase.get(), self.opciones.config(self.hoja.ancho_util(), escala))

    def renderizar(self):
        self.hoja.mostrar(self._render())


# ----------------------------------------------------------------------------- app
def main():
    raiz = tk.Tk()
    raiz.title("Conversor Caligráfico ✒ — texto a letra de pluma")
    raiz.geometry("1280x760")
    raiz.minsize(900, 560)
    estilo = ttk.Style(raiz)
    if "clam" in estilo.theme_names():
        estilo.theme_use("clam")
    estilo.configure("TNotebook.Tab", padding=(16, 6), font=("Segoe UI", 10, "bold"))

    cuaderno = ttk.Notebook(raiz)
    cuaderno.pack(fill="both", expand=True)
    cuaderno.add(PestanaConversor(cuaderno), text="✒ Conversor")
    cuaderno.add(PestanaAbecedario(cuaderno), text="🔤 Abecedario")
    cuaderno.add(PestanaFrases(cuaderno), text="🎲 Frases aleatorias")
    raiz.mainloop()


if __name__ == "__main__":
    main()
