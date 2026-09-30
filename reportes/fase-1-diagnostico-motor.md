# 📊 Fase 1 · Diagnóstico del motor local

[![Volver a reportes](https://img.shields.io/badge/%E2%86%90%20Volver-Reportes-8b5cf6?style=for-the-badge)](README.md)
[![Inicio](https://img.shields.io/badge/Inicio-README-ec4899?style=for-the-badge)](../README.md)

> **Fecha:** 30 de septiembre de 2026 · **Estado:** ✅ Cerrada
>
> **Conclusión en una línea:** no era el hardware, era la configuración. Con `num_gpu 99`, el modelo 4B entra entero en una GTX 1050 Ti de 4 GB.

---

## 🖥️ Equipo de prueba

| Componente | Detalle |
|---|---|
| GPU | NVIDIA GeForce GTX 1050 Ti · 4 GB VRAM · driver 582.66 (WDDM) |
| CPU | Intel Core i3-7100 (2 núcleos / 4 hilos) |
| RAM | 16 GB |
| Sistema | Windows 11 |
| Motor | Ollama |
| Modelos | `qwen3.5:4b` (4.7B parámetros, Q4_K_M, 3.4 GB) · `qwen3.5:2b` (2.7 GB) |

---

## 🔍 Hallazgos

### 1. El escritorio no era el problema
Con el modelo descargado, Windows y los programas abiertos (Edge, VS Code, Claude) usan solo **~407 MiB** de VRAM. Quedan unos **3.6 GB** libres.

### 2. Ollama reparte el modelo por precaución
Por defecto, Ollama (llama.cpp por dentro) deja parte del modelo en la CPU aunque haya espacio en la GPU:

| Modelo | Reparto por defecto | Detalle del log |
|---|---|---|
| 4b | 50% CPU / 50% GPU | — |
| 2b | 33% CPU / 67% GPU | `offloaded 19/26 layers to GPU` con **1726 MiB todavía libres** |

### 3. `num_gpu 99` lo resuelve
Forzar todas las capas a la GPU deja **los dos modelos al 100% GPU**, sin errores de memoria. El 4b ocupa **3.1 GB**.

### 4. La VRAM cambia la velocidad, no la calidad
Dónde corre el modelo solo afecta a la velocidad. La calidad depende del **tamaño** del modelo: en las pruebas, el 2b cometió errores de sentido y mezcló "tú" y "usted"; el 4b fue más sólido.

### 5. El contexto casi no pesa
Qwen3.5 es **híbrido**: solo 6 capas usan atención clásica. El caché del contexto con 4096 tokens ocupa **~48 MiB**, así que bajar a 2048 no cambia nada.

### 6. El *thinking* es el que más tiempo cuesta
Para una respuesta de 3 líneas, el modelo pensó **3,203 tokens** y tardó **casi 2 minutos**. Sin *thinking*: **58 tokens en 2.3 segundos**.

### 7. En chats largos, el prompt se reprocesa
Por su diseño recurrente, llama.cpp vuelve a procesar el prompt completo en cada turno. En `chat.py` habrá que recortar el historial.

---

## ⏱️ Benchmarks

Prompt: *"Explica en 3 líneas qué es un presupuesto personal."* · Medido con `ollama run --verbose`.

| Modelo | GPU | Thinking | Tokens | Tiempo total | Velocidad |
|---|---|:---:|---:|---:|---:|
| 2b | 100% (`num_gpu 99`) | ✅ | 3,203 | 1 min 59 s | 28.3 t/s |
| 2b | 100% (`num_gpu 99`) | ❌ | 58 | **2.3 s** | **28.0 t/s** |
| 2b | 33/67 (por defecto) | ❌ | 88 | 5.0 s | 18.9 t/s |
| **4b** | **100% (`num_gpu 99`)** | ❌ | 71 | ~4.2 s *(+6.6 s de carga)* | **18.4 t/s** |
| 4b | 50/50 (por defecto) | ❌ | — | — | *pendiente* |

**Lectura:** forzar la GPU acelera el 2b un **~48%**. Y el 4b al 100% GPU va **igual de rápido** que el 2b por defecto, con mejor calidad.

---

## ✅ Decisiones

- **Modelo principal:** `qwen3.5:4b` con `num_gpu 99` y `num_ctx 4096`.
- **Modelo de apoyo:** `qwen3.5:2b` para tareas rápidas y repetitivas.
- ***Thinking* apagado por defecto.** Se activa solo para código, razonamiento difícil o demostraciones.
- **Siguiente fase:** fijar todo esto en el `Modelfile` de NEXOR.

---

## 🧪 Cómo reproducirlo

```bash
ollama stop qwen3.5:4b                 # asegura que el modelo se recargue
winpty ollama run qwen3.5:4b --verbose # en PowerShell, sin winpty
```

```
/set parameter num_gpu 99
/set nothink
Explica en 3 líneas qué es un presupuesto personal.
```

En otra terminal: `ollama ps` (columna **PROCESSOR**) y `nvidia-smi` (columna **Memory-Usage**).

> ⚠️ Si `load duration` sale en milisegundos, el modelo no se recargó y la medición no vale. Ejecuta `ollama stop` antes de cada prueba.
