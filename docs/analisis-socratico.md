# Análisis socrático del proyecto (council-socrates, modo standalone)

> Aplicación del prompt `council-socrates.md` al enunciado: *"convertir texto normal a letra caligráfica y mostrarlo como si estuviera escrito con una pluma real"*.

## Essential Question
¿Qué significa que un texto "parezca escrito a pluma"? Una fuente cursiva **no** lo logra: es perfecta, repetible y uniforme. Lo que el ojo reconoce como "pluma" son las **imperfecciones físicas**: la línea base que ondula, la tinta que se acumula en los trazos gruesos, la presión que cambia, el papel que tiene textura y pauta.

## Assumptions Examined

1. **"Convertir" es traducir letra por letra (como romaji → hiragana).**
   Si fuera cierto, la salida sería texto. Pero el objetivo es *ver cómo quedaría*: la salida es una **imagen**. → El proyecto no es un traductor, es un **motor de renderizado**. La analogía con el proyecto de referencia vale para la estructura (3 vistas, tiempo real), no para el algoritmo.

2. **"Con una fuente caligráfica alcanza."**
   Si alcanzara, escribir "aaaa" daría cuatro letras idénticas. En las imágenes de referencia ninguna letra se repite igual. → Hace falta **variabilidad controlada**: ondulación de la línea base, rotación leve por letra, densidad de tinta por palabra.

3. **"La aleatoriedad pura imita lo humano."**
   Si cada letra saltara al azar, el texto temblaría como escrito en un colectivo. La mano humana es *continua*: la deriva es suave. → Usar **ruido suave (suma de senoidales con fase aleatoria)**, no ruido blanco. Y una **semilla** para que el mismo texto dé siempre el mismo resultado (reproducible, testeable).

4. **"Dibujar letra por letra rompe la caligrafía."**
   Cierto si cada letra se posiciona sola: se pierden el *kerning* y las uniones. → Posicionar cada carácter en `font.getlength(palabra[:i])`, que ya incluye el kerning, y mantener las perturbaciones pequeñas para que los enlaces sigan tocándose.

## The Hidden Question
¿Qué rasgos visuales de las fotos de referencia son reproducibles con matemática simple?
- **Foto 1** (sepia sobre cuadriculado): tinta que se acumula y oscurece en los trazos gruesos (*shading*), papel con cuadrícula.
- **Foto 2** (brush pen turquesa): contraste fuerte grueso/fino, tinta de color.
- **Foto 3** (copperplate azul): pauta con líneas inclinadas guía, trazos de pelo muy finos.

Esto se traduce en tres decisiones: **3 estilos** (copperplate, cursiva estilográfica, brush pen), **paletas de tinta reales** y **4 tipos de papel**.

## What Survives Examination
- Estructura en 3 vistas, igual que el proyecto de referencia: Conversor / Abecedario (tabla de referencia) / Frases aleatorias (práctica).
- Conversión en tiempo real con *debounce* para no renderizar en cada tecla.
- Separar **motor** (`motor.py`, sin interfaz, testeable) de **interfaz** (`app.py`, Tkinter).

## Verdict
El proyecto es un **renderizador de escritura simulada**: fuente caligráfica (forma) + física simulada de tinta y papel (realismo) + variabilidad continua con semilla (humanidad). Sin las dos últimas capas el resultado es "una fuente bonita", no "escrito a pluma".

## Confidence
**Media-alta.** La simulación de tinta por difuminado del trazo es una aproximación, no física real de fluidos; engaña bien al ojo a tamaño normal, menos en zoom extremo.

## Where I May Be Wrong
Asumo que el usuario quiere realismo fotográfico. Si el objetivo fuera *aprender* caligrafía, lo valioso sería mostrar el orden y dirección de los trazos, cosa que una fuente no contiene.
