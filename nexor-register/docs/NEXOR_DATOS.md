# Contrato de datos · NEXOR REGISTER → NEXOR IA

Este documento describe el archivo que exporta NEXOR REGISTER. Es la referencia para que NEXOR IA
(o cualquier modelo al que se le pase el archivo) entienda los datos sin adivinar.

- **Versión del esquema:** `schema_version: 1`. Si un campo cambia de significado, se sube la versión.
- **Zona horaria:** `America/Lima`. `fecha` y `hora` son locales de Lima. `creado_en` y `completado_en` están en ISO UTC.
- **Moneda:** soles peruanos (`PEN`). Los montos son números con 2 decimales.
- **Campos vacíos:** `null` significa que no se registró. **No es cero.** No hay que inventar datos que falten.

## Archivo exportado

```json
{
  "app": "NEXOR REGISTER",
  "schema_version": 1,
  "destino": "NEXOR IA",
  "exportado_en": "2026-09-27T23:40:00.000Z",
  "zona_horaria": "America/Lima",
  "moneda": "PEN",
  "rango": { "desde": "2026-09-21", "hasta": "2026-09-27" },
  "resumen": { },
  "gastos": [ ],
  "ingresos": [ ],
  "cierres_dia": [ ],
  "respaldo_completo": true,
  "presets": [ ]
}
```

`respaldo_completo` y `presets` solo aparecen en "Exportar TODO".

## gasto

| Campo | Tipo | Significado |
|---|---|---|
| `id` | uuid | Identificador único (sirve para fusionar sin duplicar) |
| `tipo` | `"gasto"` | |
| `fecha`, `hora` | `YYYY-MM-DD`, `HH:MM` | Momento del gasto (hora de Lima) |
| `monto` | number | En soles |
| `item` | string | Qué se compró: "Papa rellena", "Pasaje"… |
| `categoria` | enum | `chatarra`, `bebida_azucarada`, `comida_real`, `transporte`, `salidas`, `tecnologia`, `servicios`, `estudios`, `casa`, `otros` |
| `planificado` | boolean | `false` = impulso |
| `motivo` | enum | `hambre`, `antojo`, `aburrimiento`, `estres`, `social`, `necesidad`, `cansancio` |
| `lugar` | string \| null | "Saliendo de Brighter", "Recreo SENATI", "Casa"… |
| `nota` | string \| null | |
| `creado_en` | ISO | Cuándo se registró en la app |
| `editado_en` | ISO (opcional) | Solo si se editó después |

"Chatarra" en los análisis = `chatarra` + `bebida_azucarada`.

## ingreso

`id`, `tipo: "ingreso"`, `fecha`, `monto`, `fuente` (`familia` | `practicas` | `freelance` | `otros`), `nota`, `creado_en`.

## cierre_dia

Hay uno por fecha. Su `id` es siempre `cierre_YYYY-MM-DD`.

| Campo | Significado |
|---|---|
| `sueno.hora_dormir_anoche`, `sueno.hora_despertar` | `HH:MM` |
| `sueno.horas` | Calculado. Si despertar ≤ dormir, se asume que cruzó la medianoche |
| `sueno.calidad`, `energia`, `animo` | 1–5 |
| `comidas.desayuno / almuerzo / cena` | `casera` \| `comprada` \| `chatarra` \| `no_comi` |
| `gaseosas`, `vasos_agua` | enteros |
| `tiempo_min.{pantalla_celular, juegos, estudio, proyectos, ingles, ejercicio}` | minutos (`null` = no registrado) |
| `puntual_trabajo` | `si` \| `no` \| `no_aplica` |
| `sintomas`, `logro_del_dia`, `que_salio_mal`, `nota` | texto libre o `null` |
| `completado_en` | ISO |

## resumen

Se calcula sobre el rango exportado: `dias_en_rango`, `gasto_total`, `gasto_promedio_diario`, `gastos_cantidad`,
`por_categoria`, `chatarra_bebida_total`, `chatarra_bebida_pct`, `no_planificados_pct`, `motivos` (conteo),
`motivo_mas_frecuente`, `sueno_promedio_h`, `dias_sueno_menor_6_5`, `ingresos_total`, `dias_registrados`
(días con al menos un gasto o cierre) y `dias_con_cierre`.

## Uso futuro en NEXOR IA

La idea es que NEXOR IA:

1. Lea los JSON exportados (o, más adelante, se sincronice directo con la app).
2. Valide el `schema_version` antes de analizar.
3. Cruce el sueño y la energía con el gasto en chatarra, busque las horas y los lugares donde se concentran los impulsos y compare cada semana con el diagnóstico base.
4. Proponga **una sola acción medible** por semana.
