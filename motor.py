"""
motor.py — Motor de renderizado caligráfico.

Convierte texto digital en una IMAGEN que simula escritura con pluma real.
No depende de la interfaz: se puede usar solo desde la terminal:

    python motor.py "Hola mundo" -o hola.png --estilo 0 --tinta Sepia

Capas del render (ver docs/analisis-socratico.md):
  1. Forma   -> fuente caligráfica (copperplate, cursiva o brush pen).
  2. Mano    -> línea base ondulada + rotación leve por letra (ruido SUAVE).
  3. Tinta   -> acumulación en trazos gruesos + densidad variable por palabra.
  4. Papel   -> color crema, textura y pauta (cuadriculado, rayado, etc.).
"""
from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

CARPETA_FUENTES = Path(__file__).resolve().parent / "fonts"

# Estilos de pluma -> fuente (todas con licencia OFL, ver fonts/OFL.txt).
# 'escala' compensa que cada fuente tiene un tamaño visual distinto.
ESTILOS = {
    "Copperplate (plumín de punta fina)": {"archivo": "PinyonScript-Regular.ttf", "escala": 1.00},
    "Cursiva inglesa (pluma estilográfica)": {"archivo": "GreatVibes-Regular.ttf", "escala": 1.08},
    "Brush pen (pincel)": {"archivo": "AlexBrush-Regular.ttf", "escala": 1.05},
}

# Colores de tinta inspirados en tintas reales de pluma (RGB).
TINTAS = {
    "Sepia": (78, 48, 24),
    "Negro hierro": (30, 28, 34),
    "Azul real": (38, 50, 150),
    "Turquesa": (14, 110, 128),
    "Burdeos": (112, 22, 42),
    "Verde bosque": (28, 82, 52),
}

PAPELES = ["Cuadriculado", "Rayado", "Pautado caligráfico", "Liso"]

COLOR_PAPEL = np.array([247, 243, 232], dtype=np.float32)  # crema, no blanco puro
SUPERMUESTREO = 2  # se dibuja al doble y se reduce: bordes suaves como la tinta


@dataclass
class Config:
    estilo: str = next(iter(ESTILOS))
    tinta: str = "Sepia"
    papel: str = "Cuadriculado"
    tamano: int = 56          # alto aproximado de la letra en píxeles (salida final)
    ancho: int = 1200         # ancho de la hoja en píxeles
    temblor: float = 0.5      # 0 = perfecto (fuente), 1 = mano muy suelta
    sombreado: float = 0.6    # 0 = tinta plana, 1 = mucha acumulación en trazos gruesos
    presion: float = 0.7      # 0 = plumín apenas apoyado, 1 = mucha presión (trazo más grueso)
    semilla: int = 7          # misma semilla + mismo texto = misma imagen


@lru_cache(maxsize=16)
def _fuente(archivo: str, px: int) -> ImageFont.FreeTypeFont:
    # Cache: abrir la fuente en cada tecla haría lenta la vista previa en tiempo real.
    return ImageFont.truetype(str(CARPETA_FUENTES / archivo), px)


# --------------------------------------------------------------------------- texto
def _partir_lineas(texto: str, fuente, ancho_max: float) -> list[str]:
    """Ajuste de línea por palabras, respetando los saltos de línea del usuario."""
    lineas: list[str] = []
    for parrafo in texto.split("\n"):
        actual = ""
        for palabra in parrafo.split():
            prueba = f"{actual} {palabra}".strip()
            if fuente.getlength(prueba) <= ancho_max or not actual:
                actual = prueba
            else:
                lineas.append(actual)
                actual = palabra
        lineas.append(actual)  # párrafo vacío = renglón en blanco (como en un cuaderno)
    return lineas


# --------------------------------------------------------------------------- papel
def _ruido_suave(alto: int, ancho: int, celda: int, rng: np.random.Generator) -> np.ndarray:
    """Ruido de baja frecuencia en [0,1]: grilla aleatoria chica ampliada con bicúbica."""
    pequeno = rng.random((max(2, alto // celda + 2), max(2, ancho // celda + 2))).astype(np.float32)
    img = Image.fromarray((pequeno * 255).astype(np.uint8)).resize((ancho, alto), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32) / 255.0


def _dibujar_papel(alto, ancho, cfg: Config, interlineado, y_bases, margen_izq, x_alto, rng):
    S = SUPERMUESTREO
    # Textura: variación lenta (manchas) + grano fino, como papel real fotografiado.
    manchas = _ruido_suave(alto, ancho, 160 * S, rng)
    grano = rng.normal(0, 1, (alto, ancho)).astype(np.float32)
    base = COLOR_PAPEL[None, None, :] * (0.975 + 0.025 * manchas[..., None]) + 2.2 * grano[..., None]
    papel = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    d = ImageDraw.Draw(papel)

    gris = (205, 208, 214)
    if cfg.papel == "Cuadriculado":
        paso = max(8, round(interlineado / 4))  # 4 cuadritos por renglón, como la foto de referencia
        off = y_bases[0] % paso if y_bases else 0  # alinear la cuadrícula con la línea base
        for x in range(0, ancho, paso):
            d.line([(x, 0), (x, alto)], fill=gris, width=S)
        for y in range(off, alto, paso):
            d.line([(0, y), (ancho, y)], fill=gris, width=S)
    elif cfg.papel == "Rayado":
        for yb in y_bases:
            d.line([(0, yb), (ancho, yb)], fill=(170, 190, 220), width=S)
        d.line([(margen_izq - 25 * S, 0), (margen_izq - 25 * S, alto)], fill=(225, 140, 140), width=S)
    elif cfg.papel == "Pautado caligráfico":
        # Pauta de copperplate: línea base, altura de x y líneas inclinadas a 55° (foto 3).
        for yb in y_bases:
            d.line([(0, yb), (ancho, yb)], fill=gris, width=S)
            d.line([(0, yb - x_alto), (ancho, yb - x_alto)], fill=(222, 224, 228), width=S)
        dx = alto / math.tan(math.radians(55))
        for x in range(-int(dx), ancho, 70 * S):
            d.line([(x, alto), (x + dx, 0)], fill=(228, 229, 233), width=S)
    return papel


# --------------------------------------------------------------------------- render
def renderizar(texto: str, cfg: Config | None = None) -> Image.Image:
    cfg = cfg or Config()
    S = SUPERMUESTREO
    rng = random.Random(cfg.semilla)            # todas las decisiones "humanas" salen de acá
    nprng = np.random.default_rng(cfg.semilla)

    estilo = ESTILOS[cfg.estilo]
    fuente = _fuente(estilo["archivo"], int(cfg.tamano * estilo["escala"] * S * 1.6))
    ascenso, descenso = fuente.getmetrics()
    interlineado = int(cfg.tamano * S * 1.9)
    x_alto = int(cfg.tamano * S * 0.45)

    ancho = cfg.ancho * S
    margen_izq, margen_der, margen_sup = 70 * S, 60 * S, int(interlineado * 0.9)
    lineas = _partir_lineas(texto or " ", fuente, ancho - margen_izq - margen_der)
    alto = margen_sup + interlineado * len(lineas) + int(interlineado * 0.2)
    y_bases = [margen_sup + i * interlineado + int(interlineado * 0.15) for i in range(len(lineas))]

    mascara = np.zeros((alto, ancho), dtype=np.float32)  # 0 = papel, 1 = tinta plena
    pad = int(fuente.size * 0.8)                         # margen para que los rasgos no se corten

    amp = cfg.temblor * cfg.tamano * S * 0.06            # amplitud de la ondulación de la línea base
    for linea, yb in zip(lineas, y_bases):
        # La mano no sigue una regla: cada renglón tiene inclinación y ondulación propias.
        pendiente = math.radians(rng.uniform(-0.5, 0.5) * cfg.temblor)
        ondas = [(rng.uniform(0.002, 0.006) / S, rng.uniform(0, 2 * math.pi), w) for w in (0.65, 0.35)]
        x0 = margen_izq + rng.uniform(-8, 8) * S * cfg.temblor

        def y_onda(x):
            return amp * sum(w * math.sin(f * x + ph) for f, ph, w in ondas) + math.tan(pendiente) * (x - x0)

        x_palabra = x0
        espacio = fuente.getlength(" ")
        for palabra in linea.split(" "):
            densidad = rng.uniform(0.86, 1.0) if cfg.temblor else 1.0  # la pluma carga distinta tinta
            for i, ch in enumerate(palabra):
                # getlength(prefijo) incluye kerning -> las letras siguen enlazadas.
                x = x_palabra + fuente.getlength(palabra[:i])
                y = yb + y_onda(x)
                # Rotación según la pendiente local de la onda + un poco de azar.
                derivada = (y_onda(x + 5) - y_onda(x - 5)) / 10
                angulo = -math.degrees(math.atan(derivada)) + rng.gauss(0, 1.2 * cfg.temblor)

                bb = fuente.getbbox(ch, anchor="ls")
                if bb[2] <= bb[0]:
                    continue  # carácter sin tinta (espacio, etc.)
                w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
                ox, oy = pad - bb[0], pad - bb[1]          # punto de la línea base dentro del glifo
                glifo = Image.new("L", (w, h), 0)
                ImageDraw.Draw(glifo).text((ox, oy), ch, font=fuente, fill=255, anchor="ls")
                if abs(angulo) > 0.05:
                    glifo = glifo.rotate(angulo, resample=Image.BICUBIC, center=(ox, oy))

                gx, gy = int(round(x - ox)), int(round(y - oy))
                _pegar_max(mascara, np.asarray(glifo, dtype=np.float32) / 255.0 * densidad, gx, gy)
            x_palabra += fuente.getlength(palabra) + espacio

    papel = _dibujar_papel(alto, ancho, cfg, interlineado, y_bases, margen_izq, x_alto, nprng)
    resultado = _entintar(papel, mascara, cfg, nprng)
    return resultado.resize((cfg.ancho, alto // S), Image.LANCZOS)


def _pegar_max(destino: np.ndarray, src: np.ndarray, x: int, y: int) -> None:
    """Superpone con máximo (no suma): dos trazos que se cruzan no 'duplican' la tinta."""
    H, W = destino.shape
    h, w = src.shape
    x1, y1, x2, y2 = max(0, x), max(0, y), min(W, x + w), min(H, y + h)
    if x1 >= x2 or y1 >= y2:
        return
    region = destino[y1:y2, x1:x2]
    np.maximum(region, src[y1 - y:y2 - y, x1 - x:x2 - x], out=region)


def _entintar(papel: Image.Image, mascara: np.ndarray, cfg: Config, rng) -> Image.Image:
    """Simula tinta: más oscura y opaca donde el trazo es grueso (acumulación/'shading')."""
    S = SUPERMUESTREO
    m_img = Image.fromarray((mascara * 255).astype(np.uint8))
    # Presión: el plumín se abre y deposita un trazo más ancho -> dilatación de la máscara.
    if cfg.presion > 0:
        ancho_extra = m_img.filter(ImageFilter.MaxFilter(3))
        if cfg.presion > 0.5:
            ancho_extra = ancho_extra.filter(ImageFilter.MaxFilter(3))
        k = cfg.presion if cfg.presion <= 0.5 else (cfg.presion - 0.5) * 2
        m_img = Image.blend(m_img, ancho_extra, min(1.0, k))
    m = np.asarray(m_img.filter(ImageFilter.GaussianBlur(0.5 * S)), dtype=np.float32) / 255.0  # borde absorbido

    # "Grosor": el difuminado es alto solo dentro de trazos gruesos; en los finos se diluye.
    grosor = np.asarray(m_img.filter(ImageFilter.GaussianBlur(cfg.tamano * S * 0.05)), dtype=np.float32) / 255.0
    grosor = np.clip(grosor / max(grosor.max(), 1e-6) * 1.4, 0, 1)
    # Borde: la tinta de pluma se seca más concentrada en el contorno del trazo (halo oscuro).
    erosion = np.asarray(m_img.filter(ImageFilter.MinFilter(3)), dtype=np.float32) / 255.0
    borde = np.clip(m - erosion, 0, 1)
    flujo = _ruido_suave(*m.shape, 90 * S, rng)  # el flujo de tinta varía a lo largo de la hoja

    s = cfg.sombreado
    # Trazos de pelo semitransparentes, trazos gruesos opacos: contraste típico de la pluma.
    opacidad = (1 - s) * 0.95 + s * np.clip(0.45 + 0.60 * grosor + 0.15 * (flujo - 0.5) + 0.25 * borde, 0, 1)
    alfa = (m * opacidad)[..., None]

    tinta = np.array(TINTAS[cfg.tinta], dtype=np.float32)
    # Más oscuro donde se acumula (centro de trazos gruesos) y en el borde (efecto foto 1);
    # algo más claro en los trazos finos, donde la capa de tinta es delgada.
    oscurecer = 0.50 * s * grosor + 0.35 * s * borde
    aclarar = 0.35 * s * (1 - grosor)
    color = tinta[None, None, :] * (1 - oscurecer[..., None]) + (255 - tinta[None, None, :]) * aclarar[..., None] * 0.5
    base = np.asarray(papel, dtype=np.float32)
    out = base * (1 - alfa) + color * alfa
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGB")


# --------------------------------------------------------------------------- abecedario
def texto_abecedario() -> str:
    mayus = "ABCDEFGHIJKLMNÑOPQRSTUVWXYZ"
    pares = [f"{m}{m.lower()}" for m in mayus]
    filas = [" ".join(pares[i:i + 7]) for i in range(0, len(pares), 7)]
    return "\n".join(filas + ["á é í ó ú ü ¿? ¡!", "0 1 2 3 4 5 6 7 8 9"])


# --------------------------------------------------------------------------- CLI
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Convierte texto a escritura caligráfica simulada.")
    ap.add_argument("texto")
    ap.add_argument("-o", "--salida", default="caligrafia.png")
    ap.add_argument("--estilo", type=int, default=0, help=f"0..{len(ESTILOS) - 1}")
    ap.add_argument("--tinta", default="Sepia", choices=list(TINTAS))
    ap.add_argument("--papel", default="Cuadriculado", choices=PAPELES)
    ap.add_argument("--tamano", type=int, default=56)
    ap.add_argument("--temblor", type=float, default=0.5)
    ap.add_argument("--presion", type=float, default=0.7)
    ap.add_argument("--semilla", type=int, default=7)
    a = ap.parse_args()
    cfg = Config(estilo=list(ESTILOS)[a.estilo], tinta=a.tinta, papel=a.papel,
                 tamano=a.tamano, temblor=a.temblor, presion=a.presion, semilla=a.semilla)
    renderizar(a.texto.replace("\\n", "\n"), cfg).save(a.salida)
    print(f"Guardado en {a.salida}")
