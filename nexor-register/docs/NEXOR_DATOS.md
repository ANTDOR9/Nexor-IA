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
  "alertas": [ ],
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
| `fecha`, `hora` | `YYYY-MM-DD`, `HH:MM` (24 h) | Momento del gasto (hora de Lima). `hora` puede ser `null` si se anotó después y no se recordaba |
| `hora_manual` | boolean \| null | `true` = la hora la puso o corrigió el usuario. `false` = es la hora automática del momento en que se anotó (puede no ser la hora real de la compra). `null`/ausente = registro anterior a este campo |
| `monto` | number | En soles |
| `item` | string | Qué se compró: "Papa rellena", "Pasaje"… |
| `categoria` | enum | `chatarra`, `bebida_azucarada`, `comida_real`, `transporte`, `salidas`, `tecnologia`, `servicios`, `estudios`, `casa`, `otros` |
| `planificado` | boolean | `false` = impulso |
| `motivo` | enum | `hambre`, `antojo`, `aburrimiento`, `estres`, `social`, `necesidad`, `cansancio` |
| `lugar` | string \| null | "Trabajo", "Instituto", "Casa"… |
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
| `sueno.horas` | Calculado. Si despertar ≤ dormir, se asume que cruzó la medianoche. Fuera de 3–12 h se considera dato sospechoso (ver `alertas`) |
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
`motivo_mas_frecuente`, `sueno_promedio_h`, `dias_sueno_menor_6_5`, `dias_sueno_fuera_de_rango`, `ingresos_total`,
`dias_registrados` (días con al menos un gasto o cierre) y `dias_con_cierre`.

- `gasto_promedio_diario` = `gasto_total / dias_registrados` (`gasto_promedio_base: "dias_registrados"`).
  Los días del rango sin ningún registro **no** cuentan: no se sabe si se gastó 0 o si no se anotó.
- `sueno_promedio_h` y `dias_sueno_menor_6_5` excluyen los sueños fuera de 3–12 h (se cuentan aparte en `dias_sueno_fuera_de_rango`).

## alertas

Lista de datos sospechosos que hay que revisar **antes** de analizar. NEXOR IA no debe sacar conclusiones de ellos.

| `tipo` | Cuándo aparece |
|---|---|
| `sueno_fuera_de_rango` | Un cierre con menos de 3 h o más de 12 h de sueño. Suele ser un error de AM/PM (09:41 en vez de 21:41). |
| `posible_registro_tardio` | 3 o más gastos con hora automática (`hora_manual` ≠ `true`) dentro de 5 minutos el mismo día. Probablemente se anotaron juntos al final del día y su hora no es la real: no usarlos para analizar "a qué hora compro". |

Cada alerta trae `fecha` y un `detalle` legible.

## Uso futuro en NEXOR IA

La idea es que NEXOR IA:

1. Lea los JSON exportados (o, más adelante, se sincronice directo con la app).
2. Valide el `schema_version` antes de analizar.
3. Cruce el sueño y la energía con el gasto en chatarra, busque las horas y los lugares donde se concentran los impulsos y compare cada semana con el diagnóstico base.
4. Proponga **una sola acción medible** por semana.
