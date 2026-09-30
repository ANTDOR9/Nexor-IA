# 🧭 Fases 3–5 · Evolución del mentor

[![Volver a reportes](https://img.shields.io/badge/%E2%86%90%20Volver-Reportes-8b5cf6?style=for-the-badge)](README.md)
[![Inicio](https://img.shields.io/badge/Inicio-README-ec4899?style=for-the-badge)](../README.md)

> **Fecha:** 30 de septiembre de 2026 · **Estado:** 🟡 Beta
>
> **Conclusión en una línea:** un modelo de 4B puede ser un buen mentor si Python pone la estructura y los números, y la IA pone la voz.

---

## 🎯 Objetivo

Pasar de un modelo que *resume* una semana a uno que actúa como **mentor**: conoce al usuario, conecta las distintas áreas de su vida, propone **un** reto medible y le da seguimiento semana a semana.

Todas las pruebas se hicieron con la misma **semana beta**: datos mayormente simulados, con los mismos patrones de uso, para comparar versiones en igualdad de condiciones.

---

## 📈 Versiones

| Versión | Cambio principal | Estructura | Precisión | Reto |
|---|---|:---:|:---:|:---:|
| v1 · Analista | Prompt con el JSON de resumen | 🟡 | 🟡 Mezclaba métricas | ❌ Vago |
| v2 · Mentor | Perfil del usuario + memoria semanal en el prompt | ❌ Ignoró los títulos | ❌ Confundió saldo con ahorro, soles con % | ❌ Sin relación con el problema |
| v3 · Estructurado | Respuesta con **esquema JSON** (`format`) + foco elegido por Python | ✅ | 🟡 Restas mal hechas, plazos inventados | ❌ Un solo día, incoherente |
| **v4 · Guiado** | Diferencias precalculadas, fechas clave, **biblioteca de retos**, detalle de qué/cuándo/dónde | ✅ | ✅ | ✅ Coherente con el foco |

---

## 🔍 Lecciones

### 1. Un 4B no debe hacer cuentas
Cada vez que el modelo tuvo que restar, comparar o calcular plazos, se equivocó. La solución fue entregarle **frases ya calculadas y con unidades**: *"S/ 2.12 más por día tras dormir poco"* en vez de dos números sueltos.

### 2. Las etiquetas importan tanto como los números
Con datos como `{"noche": 35}`, el modelo escribió "35%". Con *"noche S/ 35.00 (43% de la chatarra)"* dejó de equivocarse. Cada porcentaje necesita decir **de qué** es.

### 3. Las instrucciones largas se siguen a medias
En texto libre, el modelo se saltaba secciones. Con un **esquema JSON obligatorio** (6 campos fijos), la estructura quedó garantizada y Python arma el reporte.

### 4. Elegir es más fácil que inventar
Cuando el modelo diseñaba el reto desde cero, proponía acciones sin relación con el problema. Con **3 ideas por foco** para elegir y adaptar al horario del usuario, los retos pasaron a ser coherentes.

### 5. La medición la hace Python, no la memoria del usuario
El foco de la semana tiene una métrica calculable con los datos de la app (por ejemplo, *chatarra después de las 18:00 en S/ por día*). La semana siguiente, Python la mide solo y marca el reto como ✅ cumplido, 🟡 parcial o ❌ no cumplido. Si no se cumplió, el foco se mantiene.

### 6. Reglas de seguridad
Los retos son siempre de **hacer o reemplazar** (preparar, llevar, cambiar un hábito). Nunca de dejar de comer, ayunar o castigarse. El mentor no diagnostica salud ni recomienda productos financieros, y anima a apoyarse en otras personas.

---

## ⚙️ Arquitectura resultante

```
JSON de NEXOR REGISTER
      │
      ▼
finanzas.py ── valida (errores de registro, días vacíos, datos simulados)
      │     ── calcula (totales, franjas, motivos, sueño, comparaciones)
      │     ── mide el reto anterior (cumplido / parcial / no)
      │     ── elige el foco y su objetivo (−40%)
      ▼
Prompt = perfil + historial + hechos con unidades + foco + ideas de reto + fechas clave
      │
      ▼
NEXOR (qwen3.5:4b · sin thinking · esquema JSON · num_ctx 8192)
      │
      ▼
Reporte semanal privado (reportes/semanas/) + memoria actualizada
```

**Rendimiento:** ~35 s por reporte completo, ~18 tokens/s, 100% en GPU.

---

## ⏭️ Pendiente

- Validar con semanas **reales** (la beta es mayormente simulada).
- Errores menores que quedan: a veces confunde días del horario o agrega justificaciones que no están en los datos.
- Siguiente fase: chat interactivo con el mismo contexto (`chat.py`).
