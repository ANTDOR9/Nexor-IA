# 🧠 IA local en hardware modesto — Qwen3.5-4B en una GTX 1050 Ti

> Un modelo de lenguaje moderno, **gratis**, **sin internet** y corriendo en una PC de gama baja.

![Estado](https://img.shields.io/badge/estado-en%20desarrollo-orange)
![Fase](https://img.shields.io/badge/fase-1%20de%206-blue)
![Motor](https://img.shields.io/badge/motor-Ollama-black)
![Modelo](https://img.shields.io/badge/modelo-Qwen3.5--4B-purple)
![GPU](https://img.shields.io/badge/GPU-GTX%201050%20Ti%204GB-76B900)
![SO](https://img.shields.io/badge/SO-Windows-0078D6)

---

## 📌 Descripción

**qwen35-local-lowend** es un proyecto personal para demostrar que no hace falta una GPU cara ni una suscripción para usar IA moderna. Aquí se instala, configura y mide **Qwen3.5-4B** con **Ollama** en una PC con una **NVIDIA GTX 1050 Ti (4 GB de VRAM)**, y se muestran sus capacidades reales:

- 💬 Chat en español
- 👨‍💻 Ayuda con programación
- 🤔 Razonamiento con *thinking* visible
- 🖼️ Análisis de capturas de pantalla (visión)
- 🌐 Traducción
- 📴 Todo funciona **con el WiFi desconectado**

El proceso completo se documenta en este repositorio y en un video.

---

## 🚦 Avance del proyecto

| Fase | Descripción | Estado |
|:---:|---|:---:|
| 1 | Instalación de Ollama y del modelo + verificación de GPU | 🟡 En curso |
| 2 | `Modelfile` con system prompt en español y parámetros optimizados | ⏳ Pendiente |
| 3 | Scripts en Python (`chat.py`, `vision.py`, `benchmark.py`) | ⏳ Pendiente |
| 4 | Benchmarks reales (con y sin *thinking*) | ⏳ Pendiente |
| 5 | README final, capturas y publicación en GitHub | 🟡 Borrador (este archivo) |
| 6 | Guion y grabación del video (5–8 min) | ⏳ Pendiente |

### ✅ Hecho hasta ahora

- [x] Definidos el objetivo, el alcance y la estructura del repositorio
- [x] Elegido el motor: **Ollama** (API local en `http://localhost:11434`)
- [x] Elegido el modelo: **Qwen3.5-4B** (`qwen3.5:4b`, ~3,4 GB) con plan B `qwen3.5:2b` (~2,7 GB)
- [x] Revisados los tamaños de las variantes del modelo y descartadas las que no caben en 4 GB de VRAM
- [x] Localizados los enlaces oficiales de descarga
- [x] Definido el flujo de grabación (OBS + NVENC) y de edición (Filmora)

### 🔜 Próximos pasos

- [ ] Instalar Ollama en Windows y comprobar con `ollama --version`
- [ ] Descargar el modelo con `ollama pull qwen3.5:4b`
- [ ] Verificar que usa la GPU con `ollama ps` y `nvidia-smi`
- [ ] Hacer la primera prueba de chat en español

---

## 🖥️ Hardware de prueba

| Componente | Especificación | Observación |
|---|---|---|
| GPU | NVIDIA GTX 1050 Ti, **4 GB VRAM** (Pascal) | Límite principal para el tamaño del modelo |
| CPU | Intel Core i3-7100 (2 núcleos / 4 hilos) | Cuello de botella del sistema |
| RAM | 16 GB | Suficiente |
| Pantalla | 1366 × 768 | Se priorizan herramientas ligeras |
| Sistema | Windows 10/11 | — |

---

## 🧩 Stack

| Herramienta | Uso |
|---|---|
| [Ollama](https://ollama.com) | Motor para ejecutar modelos locales y API REST |
| [Qwen3.5-4B](https://ollama.com/library/qwen3.5) | Modelo multimodal (texto e imagen) con modo *thinking*, licencia Apache 2.0 |
| Python + `requests` / `ollama` | Scripts de chat, visión y benchmark (sin dependencias pesadas) |
| OBS Studio | Grabación (NVENC H.264, 30 fps) |
| Filmora | Edición del video |

---

## 📦 ¿Qué modelo descargar? (y por qué no 13 GB)

Estos son los tamaños según [ollama.com/library/qwen3.5/tags](https://ollama.com/library/qwen3.5/tags):

| Variante | Tamaño | ¿Cabe en 4 GB de VRAM? |
|---|---|:---:|
| `qwen3.5:2b` | 2,7 GB | ✅ Plan B |
| **`qwen3.5:4b`** | **3,4 GB** | ✅ **Elegido** |
| `qwen3.5:4b-bf16` | 9,3 GB | ❌ |
| `qwen3.5:9b` | 6,6 GB | ❌ Se pasaría al CPU |
| `qwen3.5:9b-q8_0` | 11 GB | ❌ |

> ⚠️ Las variantes de más de ~4 GB no caben en la VRAM de una GTX 1050 Ti. Ollama pasaría parte del modelo al CPU y la velocidad caería mucho. **Con unos 5 GB libres en disco basta** (Ollama y el modelo de 3,4 GB).

---

## ⚙️ Instalación (Fase 1)

### 1. Instalar Ollama

Descarga el instalador oficial para Windows: **[OllamaSetup.exe](https://ollama.com/download/OllamaSetup.exe)** (requiere Windows 10 o superior).

O instálalo desde PowerShell:

```powershell
irm https://ollama.com/install.ps1 | iex
```

Comprueba que quedó instalado:

```powershell
ollama --version
```

### 2. Descargar el modelo

```powershell
ollama pull qwen3.5:4b
```

Si falta VRAM, usa la alternativa ligera:

```powershell
ollama pull qwen3.5:2b
```

### 3. Probarlo

```powershell
ollama run qwen3.5:4b
```

### 4. Verificar que usa la GPU

Con el modelo cargado, abre **otra** ventana de PowerShell:

```powershell
ollama ps
```

En la columna `PROCESSOR` debería aparecer `100% GPU`. Si aparece un reparto como `40%/60% CPU/GPU`, parte del modelo se está ejecutando en el CPU.

```powershell
nvidia-smi
```

Debería aparecer un proceso de Ollama y un uso de memoria de unos 3–4 GB.

---

## 🗂️ Estructura del repositorio

```
qwen35-local-lowend/
├── README.md          ← este archivo
├── Modelfile          ← (Fase 2) system prompt y parámetros
├── requirements.txt   ← (Fase 3) dependencias mínimas
├── scripts/
│   ├── chat.py        ← (Fase 3) chat por consola con historial y streaming
│   ├── vision.py      ← (Fase 3) análisis de imágenes
│   └── benchmark.py   ← (Fase 3) tokens/s, TTFT y VRAM → CSV/Markdown
├── benchmarks.md      ← (Fase 4) resultados reales
├── docs/img/          ← capturas para el README
└── .gitignore         ← excluye *.gguf, *.mp4, *.mkv, venvs y temporales
```

---

## 🎛️ Configuración prevista (Fase 2)

| Parámetro | Valor | Motivo |
|---|---|---|
| `num_ctx` | 4096 | Equilibrio entre memoria y contexto en 4 GB de VRAM |
| `temperature` | 0.7 | Recomendado sin *thinking* |
| `top_p` | 0.8 | — |
| `top_k` | 20 | — |
| *Thinking* | Activado | La velocidad no es prioridad; los tiempos muertos se editan en el video |

> Estos valores quedarán en el `Modelfile` en la Fase 2.

---

## 📊 Resultados

> 🚧 **Pendiente (Fase 4).** Aquí irán las medidas reales de tokens por segundo, tiempo hasta el primer token y uso de VRAM, con y sin *thinking*. Todavía no hay cifras publicadas porque aún no se han medido.

---

## ⚠️ Limitaciones conocidas

- **Alucina en datos factuales**: puede inventar fechas, cifras o nombres. Conviene contrastar lo que dice.
- **No genera imágenes**: puede *analizar* imágenes, pero no crearlas.
- **Velocidad limitada**: el CPU de 2 núcleos y los 4 GB de VRAM marcan el techo de rendimiento.
- **Contexto reducido** (4096 tokens) para caber en memoria.

---

## 🎬 Video

> 🚧 Pendiente (Fase 6). Aquí irá el enlace al video.

---

## 📜 Licencias

- El modelo **Qwen3.5** se distribuye con licencia **Apache 2.0**.
- **Este repositorio no incluye el modelo.** Solo enlaza a [Ollama](https://ollama.com/library/qwen3.5) y a Hugging Face.
- Licencia del código de este repositorio: *por definir*.

---

## 👤 Autor

**Anthony**: estudiante de Ingeniería de Software con IA (SENATI, Arequipa, Perú) y practicante de desarrollo de software.

---

<p align="center"><i>Última actualización: 26 de septiembre de 2026 — Fase 1 en curso</i></p>
