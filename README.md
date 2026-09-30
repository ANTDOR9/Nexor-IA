# 🧠 NEXOR IA

> Una IA **local, gratis y sin internet** que aprende de mis registros diarios para ayudarme a **gestionar mi vida**: dinero, sueño, comida, tiempo y hábitos.

![Estado](https://img.shields.io/badge/estado-en%20desarrollo-8b5cf6)
![Motor](https://img.shields.io/badge/motor-Ollama-ec4899)
![Modelo](https://img.shields.io/badge/modelo-Qwen3.5--4B-22d3ee)
![App](https://img.shields.io/badge/app-NEXOR%20REGISTER-8b5cf6)
![Android](https://img.shields.io/badge/Android-Capacitor%208-ec4899)

[![Reportes](https://img.shields.io/badge/%F0%9F%97%82%EF%B8%8F%20Reportes-Ver%20todos-8b5cf6?style=for-the-badge)](reportes/README.md)
[![Diagnóstico Fase 1](https://img.shields.io/badge/%F0%9F%93%8A%20Diagn%C3%B3stico-Fase%201%20%C2%B7%20Motor-22d3ee?style=for-the-badge)](reportes/fase-1-diagnostico-motor.md)

---

## 📌 ¿Qué es NEXOR?

NEXOR tiene dos partes que trabajan juntas:

| Parte | Qué hace | Estado |
|---|---|:---:|
| **NEXOR REGISTER** | App Android para registrar el consumo del día a día y el dinero. | ✅ v0.1 |
| **NEXOR IA** | Modelo de lenguaje local que lee esos registros, encuentra patrones y propone acciones concretas. | 🟡 En curso |

La idea es simple: **primero medir, después optimizar.** NEXOR REGISTER captura los datos reales del día a día y NEXOR IA los convierte en decisiones.

---

## 📱 NEXOR REGISTER

<p align="center">
  <img src="docs/img/nexor-register-icon.png" width="140" alt="Ícono de NEXOR REGISTER">
</p>

<p align="center"><b>Consumo y dinero, día a día</b><br>
<sub>HTML + CSS + JavaScript puro · empaquetado a APK con Capacitor · 100 % offline</sub></p>

Registra el consumo del día a día y el dinero, de forma rápida y simple. Los datos se quedan en el celular y se exportan para que NEXOR IA los analice.

📂 Código, instalación y generación del APK: [`nexor-register/`](nexor-register/README.md)

📄 Formato de los datos: [`nexor-register/docs/NEXOR_DATOS.md`](nexor-register/docs/NEXOR_DATOS.md)

---

## 🔄 Cómo se conectan

```
 NEXOR REGISTER (celular)            NEXOR IA (PC, local)
 ────────────────────────            ──────────────────────────────
 consumo del día a día      ──JSON──▶  lee el registro semanal
 dinero                                detecta patrones
                                       compara con semanas anteriores
                                       propone UNA acción medible
```

Cada exportación incluye `schema_version`, zona horaria y moneda, para que la IA entienda los datos sin adivinar.

---

## 🤖 Motor de IA

| Herramienta | Uso |
|---|---|
| [Ollama](https://ollama.com) | Ejecuta el modelo en local y expone una API REST en `http://localhost:11434` |
| [Qwen3.5-4B](https://ollama.com/library/qwen3.5) | Modelo principal: multimodal (texto e imagen), con modo *thinking*, licencia Apache 2.0 |
| Qwen3.5-2B | Plan B, más ligero |
| Python + `requests` / `ollama` | Scripts para leer los registros y hablar con el modelo |

**Lo que puede hacer el motor:**

- 💬 Conversar en español
- 🤔 Razonar con *thinking* visible
- 🖼️ Analizar imágenes y capturas de pantalla
- 📴 Funcionar con el WiFi desconectado

### Instalación del motor

```powershell
# 1. Instalar Ollama (o descargar OllamaSetup.exe desde ollama.com)
irm https://ollama.com/install.ps1 | iex
ollama --version

# 2. Descargar el modelo
ollama pull qwen3.5:4b      # principal (~3,4 GB)
ollama pull qwen3.5:2b      # alternativa ligera (~2,7 GB)

# 3. Probarlo
ollama run qwen3.5:4b

# 4. Ver el modelo cargado y dónde se está ejecutando
ollama ps

# 5. Crear NEXOR (usa el Modelfile de este repo) y hablar con él sin thinking
ollama create nexor -f Modelfile
ollama run nexor --think=false
```

> 💡 En una GPU de 4 GB, Ollama deja por defecto parte del modelo en la CPU. El `Modelfile` fuerza todas las capas a la GPU (`num_gpu 99`). Detalles y mediciones en el [diagnóstico de la Fase 1](reportes/fase-1-diagnostico-motor.md).

---

## 🚦 Avance

| Fase | Descripción | Estado |
|:---:|---|:---:|
| 1 | Motor local: Ollama + Qwen3.5 funcionando en español · [diagnóstico](reportes/fase-1-diagnostico-motor.md) | ✅ Hecho |
| 2 | **NEXOR REGISTER v0.1**: app Android de registro con exportación JSON | ✅ Hecho |
| 3 | `Modelfile` de NEXOR: system prompt en español que conoce el formato de los registros | 🟡 En curso |
| 4 | Script de análisis semanal: lee el JSON exportado y genera el informe (`scripts/finanzas.py`) | 🟡 Beta |
| 5 | Memoria de NEXOR: comparar semanas y seguir la evolución | ⏳ Pendiente |
| 6 | Sincronización directa entre la app y NEXOR IA, sin exportar a mano | ⏳ Futuro |

---

## 🗂️ Estructura del repositorio

```
Nexor-IA/
├── README.md               ← este archivo
├── Modelfile               ← configuración y personalidad de NEXOR
├── analizar_semana.bat     ← doble clic: genera el reporte de la semana
├── scripts/finanzas.py     ← valida el JSON, calcula el resumen y consulta a NEXOR
├── datos/                  ← JSON exportados (los reales no se suben)
├── reportes/               ← diagnósticos, benchmarks y reportes semanales
├── docs/img/               ← imágenes del README
└── nexor-register/         ← app Android de registro
    ├── www/                ← la app (HTML, CSS, JS)
    ├── assets/             ← ícono y pantalla de inicio
    ├── docs/NEXOR_DATOS.md ← contrato de datos para NEXOR IA
    └── android/            ← proyecto Android (Capacitor)
```



---

## ⚠️ Limitaciones conocidas

- **Puede alucinar datos:** el modelo puede inventar cifras o fechas. Por eso NEXOR trabaja sobre los registros reales y debe decir cuando falta un dato, no rellenarlo.
- **Contexto limitado:** conviene analizar por semanas, no meses enteros de una sola vez.
- **Registro manual:** la calidad del análisis depende de registrar todos los días.

---

## 📜 Licencias

- El modelo **Qwen3.5** se distribuye con licencia **Apache 2.0**. Este repositorio no incluye el modelo, solo enlaza a [Ollama](https://ollama.com/library/qwen3.5).
- Licencia del código de este repositorio: *por definir*.

---

## 👤 Autor

**Anthony** · Arequipa, Perú

<p align="center"><i>Última actualización: 30 de septiembre de 2026</i></p>
