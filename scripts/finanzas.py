"""
NEXOR IA · finanzas.py
======================
Lee un JSON exportado por NEXOR REGISTER, valida los datos, calcula el resumen
de la semana (con Python, no con la IA) y le pide a NEXOR que lo interprete.
El resultado se guarda como reporte en reportes/ y se agrega al índice.

Uso:
    python scripts/finanzas.py                                    # usa el JSON más reciente de datos/
    python scripts/finanzas.py datos/archivo.json
    python scripts/finanzas.py datos/archivo.json --sin-ia        # solo números
    python scripts/finanzas.py datos/archivo.json --modelo qwen3.5:2b
    python scripts/finanzas.py --cumpli si                        # cumpliste el reto anterior (si/no/parcial)

NEXOR te conoce gracias a dos archivos locales que no se suben a GitHub:
    perfil.local.md      quién eres, tus metas y cómo quieres que te hable
    memoria/semanas.json lo que pasó cada semana y el compromiso que aceptaste

Regla de oro: Python hace las cuentas; la IA solo interpreta.
"""

import argparse
import json
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent       # carpeta del repo
CARPETA_REPORTES = RAIZ / "reportes" / "semanas"    # reportes semanales: privados (no se suben)
OLLAMA_URL = "http://localhost:11434"
MODELO_POR_DEFECTO = "nexor"

CARPETA_MEMORIA = RAIZ / "memoria"                 # historial semanal (no se sube)
ARCHIVO_PERFIL = RAIZ / "perfil.local.md"          # quién eres (no se sube)
PERFIL_MAX_CARACTERES = 3000                        # ~750 tokens: el contexto es de 4096
SEMANAS_EN_MEMORIA = 3                              # cuántas semanas previas ve NEXOR

# Referencia inicial de chatarra por semana (del diagnóstico base del usuario)
CHATARRA_BASE_SEMANAL = 95.0

CATEGORIAS_CHATARRA = {"chatarra", "bebida_azucarada"}
MOTIVOS_EMOCIONALES = {"estres", "aburrimiento", "cansancio", "antojo"}
SUENO_MINIMO = 6.5
DIAS_SEMANA = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ── 1. Cargar y validar ───────────────────────────────────────
def cargar(ruta):
    """Abre el JSON y comprueba que sea un archivo de NEXOR REGISTER compatible."""
    with open(ruta, encoding="utf-8") as f:
        datos = json.load(f)
    if datos.get("schema_version") != 1:
        sys.exit(f"❌ schema_version {datos.get('schema_version')} no soportado (se esperaba 1).")
    return datos


def rango_de_fechas(desde, hasta):
    """Lista de fechas (YYYY-MM-DD) entre desde y hasta, inclusive."""
    d, fin = date.fromisoformat(desde), date.fromisoformat(hasta)
    dias = []
    while d <= fin:
        dias.append(d.isoformat())
        d += timedelta(days=1)
    return dias


def minutos(hora):
    """'HH:MM' -> minutos desde medianoche."""
    h, m = hora.split(":")
    return int(h) * 60 + int(m)


def validar(datos):
    """Busca errores de registro que la IA no detectaría sola. Devuelve una lista de avisos."""
    avisos = []
    gastos, cierres = datos["gastos"], datos["cierres_dia"]
    dias = rango_de_fechas(datos["rango"]["desde"], datos["rango"]["hasta"])

    # Sueño imposible (ej. 09:41 en vez de 21:41 da 18 horas)
    for c in cierres:
        h = c["sueno"].get("horas")
        if h is not None and (h > 12 or h < 3):
            avisos.append(f"{c['fecha']}: sueño de {h} h, probablemente mal registrado (¿formato 24 h?). Se excluye del promedio.")

    # Gastos registrados en lote: 4 o más en el mismo día dentro de 3 minutos
    por_dia = defaultdict(list)
    for g in gastos:
        por_dia[g["fecha"]].append(g)
    for f, lista in por_dia.items():
        lista = sorted(lista, key=lambda g: minutos(g["hora"]))
        for i in range(len(lista) - 3):
            if minutos(lista[i + 3]["hora"]) - minutos(lista[i]["hora"]) <= 3:
                avisos.append(f"{f}: varios gastos registrados en el mismo minuto ({lista[i]['hora']}). "
                              "Probablemente se anotaron juntos después; las horas no son confiables.")
                break

    # Días sin datos y días sin cierre
    con_gastos = {g["fecha"] for g in gastos}
    con_cierre = {c["fecha"] for c in cierres}
    sin_datos = [f for f in dias if f not in con_gastos and f not in con_cierre]
    sin_cierre = [f for f in dias if f in con_gastos and f not in con_cierre]
    if sin_datos:
        avisos.append(f"Días sin ningún registro: {', '.join(sin_datos)}.")
    if sin_cierre:
        avisos.append(f"Días sin cierre del día: {', '.join(sin_cierre)}.")

    # Montos fuera de lo normal
    for g in gastos:
        if g["monto"] <= 0:
            avisos.append(f"{g['fecha']} {g['hora']}: monto {g['monto']} en '{g['item']}' no es válido.")

    # Datos simulados (versión beta)
    simulados = sum(1 for x in gastos + cierres + datos["ingresos"] if x.get("simulado"))
    if simulados:
        avisos.append(f"BETA: {simulados} registros son simulados. Este reporte sirve para probar el sistema, no como diagnóstico real.")
    return avisos


# ── 2. Calcular el resumen ────────────────────────────────────
def franja(hora):
    """Franja del día según la hora del gasto."""
    m = minutos(hora)
    if 5 * 60 <= m < 12 * 60:
        return "mañana"
    if 12 * 60 <= m < 18 * 60:
        return "tarde"
    return "noche"


def calcular(datos):
    """Todas las cifras del reporte. La IA recibe esto, ya calculado."""
    gastos, cierres, ingresos = datos["gastos"], datos["cierres_dia"], datos["ingresos"]
    dias = rango_de_fechas(datos["rango"]["desde"], datos["rango"]["hasta"])
    dias_registrados = sorted({g["fecha"] for g in gastos} | {c["fecha"] for c in cierres})
    n_dias = max(len(dias_registrados), 1)

    total = round(sum(g["monto"] for g in gastos), 2)
    por_categoria = Counter()
    por_dia = defaultdict(float)
    chatarra_por_dia = defaultdict(float)
    for g in gastos:
        por_categoria[g["categoria"]] += g["monto"]
        por_dia[g["fecha"]] += g["monto"]
        if g["categoria"] in CATEGORIAS_CHATARRA:
            chatarra_por_dia[g["fecha"]] += g["monto"]

    compras_chatarra = [g for g in gastos if g["categoria"] in CATEGORIAS_CHATARRA]
    chatarra = round(sum(g["monto"] for g in compras_chatarra), 2)
    motivos_chatarra = Counter(g["motivo"] for g in compras_chatarra)
    emocionales = sum(v for k, v in motivos_chatarra.items() if k in MOTIVOS_EMOCIONALES)
    franjas = Counter()
    for g in compras_chatarra:
        franjas[franja(g["hora"])] += g["monto"]
    impulsivos = [g for g in gastos if not g["planificado"]]

    # Qué se compra y qué días en cada franja (para que el reto ataque cosas reales)
    detalle_franja = {}
    for fr in ["mañana", "tarde", "noche"]:
        compras = [g for g in compras_chatarra if franja(g["hora"]) == fr]
        items = defaultdict(lambda: [0, 0.0])
        for g in compras:
            items[g["item"]][0] += 1
            items[g["item"]][1] += g["monto"]
        top = sorted(items.items(), key=lambda kv: kv[1][1], reverse=True)[:3]
        dias_fr = sorted({date.fromisoformat(g["fecha"]).weekday() for g in compras})
        lugares = Counter(g["lugar"] for g in compras if g.get("lugar"))
        detalle_franja[fr] = {
            "items": [{"item": k, "veces": v[0], "monto": round(v[1], 2)} for k, v in top],
            "dias": [DIAS_SEMANA[d] for d in dias_fr],
            "lugar_frecuente": lugares.most_common(1)[0][0] if lugares else None,
        }

    # Sueño: solo valores plausibles
    suenos = [c for c in cierres if c["sueno"].get("horas") is not None and 3 <= c["sueno"]["horas"] <= 12]
    sueno_prom = round(sum(c["sueno"]["horas"] for c in suenos) / len(suenos), 2) if suenos else None

    # ¿Gasta más en chatarra los días que durmió poco? (el cierre de la fecha X = noche anterior a X)
    poco = [chatarra_por_dia.get(c["fecha"], 0) for c in suenos if c["sueno"]["horas"] < SUENO_MINIMO]
    bien = [chatarra_por_dia.get(c["fecha"], 0) for c in suenos if c["sueno"]["horas"] >= SUENO_MINIMO]
    prom = lambda xs: round(sum(xs) / len(xs), 2) if xs else None

    comidas = Counter()
    for c in cierres:
        for v in c["comidas"].values():
            if v:
                comidas[v] += 1

    def prom_tiempo(clave):
        vals = [c["tiempo_min"].get(clave) for c in cierres if c["tiempo_min"].get(clave) is not None]
        return round(sum(vals) / len(vals)) if vals else None

    peor = max(por_dia.items(), key=lambda kv: kv[1]) if por_dia else (None, 0)
    ingresos_total = round(sum(i["monto"] for i in ingresos), 2)
    chatarra_semanal = round(chatarra / n_dias * 7, 2)

    return {
        "rango": datos["rango"],
        "dias_registrados": len(dias_registrados),
        "dias_con_cierre": len({c["fecha"] for c in cierres}),
        "gasto_total": total,
        "gasto_promedio_diario": round(total / n_dias, 2),
        "por_categoria": {k: round(v, 2) for k, v in por_categoria.most_common()},
        "gasto_por_dia": {f: round(por_dia.get(f, 0), 2) for f in dias},
        "peor_dia": {"fecha": peor[0], "dia": DIAS_SEMANA[date.fromisoformat(peor[0]).weekday()] if peor[0] else None,
                     "monto": round(peor[1], 2)},
        "chatarra_total": chatarra,
        "chatarra_pct": round(chatarra / total * 100, 1) if total else 0,
        "chatarra_proyeccion_semanal": chatarra_semanal,
        "chatarra_vs_base": round(chatarra_semanal - CHATARRA_BASE_SEMANAL, 2),
        "compras_chatarra": len(compras_chatarra),
        "motivos_chatarra": dict(motivos_chatarra.most_common()),
        "chatarra_emocional_pct": round(emocionales / len(compras_chatarra) * 100, 1) if compras_chatarra else 0,
        "chatarra_por_franja": {k: round(v, 2) for k, v in franjas.most_common()},
        "chatarra_franja_prom_diario": {k: round(franjas.get(k, 0) / n_dias, 2) for k in ["mañana", "tarde", "noche"]},
        "detalle_franja": detalle_franja,
        "impulsivos_pct": round(len(impulsivos) / len(gastos) * 100, 1) if gastos else 0,
        "sueno_promedio_h": sueno_prom,
        "dias_sueno_bajo": sum(1 for c in suenos if c["sueno"]["horas"] < SUENO_MINIMO),
        "chatarra_prom_dias_sueno_bajo": prom(poco),
        "chatarra_prom_dias_sueno_ok": prom(bien),
        "comidas": dict(comidas.most_common()),
        "tiempo_promedio_min": {k: prom_tiempo(k) for k in
                                ["pantalla_celular", "juegos", "estudio", "proyectos", "ingles", "ejercicio"]},
        "ingresos_total": ingresos_total,
        "balance": round(ingresos_total - total, 2),
        "comidas_caseras": comidas.get("casera", 0),
        "pantalla_prom_min": prom_tiempo("pantalla_celular"),
    }


# ── 3. Perfil y memoria: lo que hace que NEXOR te conozca ──────
def cargar_perfil():
    """Lee perfil.local.md (sin comentarios HTML). Si no existe, NEXOR trabaja sin conocerte."""
    if not ARCHIVO_PERFIL.exists():
        return None
    texto = ARCHIVO_PERFIL.read_text(encoding="utf-8")
    texto = re.sub(r"<!--.*?-->", "", texto, flags=re.S)           # quita las instrucciones
    texto = "\n".join(l for l in texto.splitlines() if l.strip())   # quita líneas vacías
    if len(texto) > PERFIL_MAX_CARACTERES:
        print(f"⚠️  perfil.local.md es largo ({len(texto)} caracteres); se recorta a {PERFIL_MAX_CARACTERES}.")
        texto = texto[:PERFIL_MAX_CARACTERES]
    return texto


def archivo_memoria(beta):
    """Las semanas beta van aparte para no mezclarse con tu historial real."""
    return CARPETA_MEMORIA / ("semanas-beta.json" if beta else "semanas.json")


def cargar_memoria(beta):
    ruta = archivo_memoria(beta)
    if not ruta.exists():
        return []
    return json.loads(ruta.read_text(encoding="utf-8"))


def guardar_memoria(beta, semana, r, foco, reto, evaluacion, cumpli_usuario):
    """Guarda (o reemplaza) la semana actual con su foco, su reto y la evaluación del reto anterior."""
    memoria = [m for m in cargar_memoria(beta) if m["semana"] != semana]
    if cumpli_usuario and memoria:
        memoria[-1]["cumplido_segun_usuario"] = cumpli_usuario
    if evaluacion and memoria:
        memoria[-1]["resultado"] = evaluacion["resultado"]
    memoria.append({
        "semana": semana,
        "rango": r["rango"],
        "gasto_total": r["gasto_total"],
        "chatarra_total": r["chatarra_total"],
        "chatarra_pct": r["chatarra_pct"],
        "chatarra_emocional_pct": r["chatarra_emocional_pct"],
        "impulsivos_pct": r["impulsivos_pct"],
        "sueno_promedio_h": r["sueno_promedio_h"],
        "foco": foco,            # qué se mide la próxima semana y con qué objetivo
        "reto": reto,            # el reto que propuso NEXOR
        "resultado": None,       # lo llena Python la semana siguiente
    })
    memoria.sort(key=lambda m: m["semana"])
    CARPETA_MEMORIA.mkdir(exist_ok=True)
    archivo_memoria(beta).write_text(json.dumps(memoria, ensure_ascii=False, indent=2), encoding="utf-8")


# ── 4. Focos: Python elige qué mejorar y lo mide solo ─────────
# Cada foco sabe cómo medirse con los datos de NEXOR REGISTER.
FOCOS = {
    "chatarra_noche":  {"descripcion": "Chatarra después de las 18:00", "unidad": "S/ por día", "mejor": "menos",
                        "medir": lambda r: r["chatarra_franja_prom_diario"]["noche"]},
    "chatarra_tarde":  {"descripcion": "Chatarra entre las 12:00 y las 18:00", "unidad": "S/ por día", "mejor": "menos",
                        "medir": lambda r: r["chatarra_franja_prom_diario"]["tarde"]},
    "chatarra_mañana": {"descripcion": "Chatarra antes de las 12:00", "unidad": "S/ por día", "mejor": "menos",
                        "medir": lambda r: r["chatarra_franja_prom_diario"]["mañana"]},
    "sueno":           {"descripcion": "Horas de sueño por noche", "unidad": "h", "mejor": "más",
                        "medir": lambda r: r["sueno_promedio_h"]},
    "comidas_caseras": {"descripcion": "Comidas caseras en la semana", "unidad": "comidas", "mejor": "más",
                        "medir": lambda r: r["comidas_caseras"]},
    "pantalla":        {"descripcion": "Minutos de celular por día", "unidad": "min", "mejor": "menos",
                        "medir": lambda r: r["pantalla_prom_min"]},
}


# Ideas de reto por foco: todas son de HACER o REEMPLAZAR, nunca de dejar de comer.
# NEXOR elige una y la adapta a tu horario. Puedes agregar las tuyas.
RETOS = {
    "chatarra_noche": [
        "Cocinar el domingo una tanda (arroz, huevo, papa) y cenarla de lunes a viernes antes de las 20:00",
        "Dejar lista en casa una alternativa para la noche (fruta, pan con huevo, agua) antes de salir por la mañana",
        "Comprar el pan del día por la mañana con lista, para no tener que ir a la tienda en la noche",
    ],
    "chatarra_tarde": [
        "Llevar almuerzo o un táper de casa los días largos de trabajo o estudio",
        "Llevar una botella de agua y una fruta para el descanso o la salida",
        "Planificar el almuerzo del día siguiente la noche anterior y dejarlo listo",
    ],
    "chatarra_mañana": [
        "Desayunar en casa algo rápido (pan con huevo, avena) antes de salir",
        "Llevar agua desde casa para no comprar bebidas azucaradas en el camino",
        "Preparar el desayuno la noche anterior para no salir con hambre",
    ],
    "sueno": [
        "Poner una alarma a las 21:30 para dejar el celular cargando fuera de la cama",
        "Cortar juegos y videos a una hora fija entre semana",
        "Dejar la ropa y la mochila listas la noche anterior para acostarse antes",
    ],
    "comidas_caseras": [
        "Cocinar dos veces por semana en lugar de una, en tandas para varios días",
        "Hacer una lista de compras semanal con ingredientes para 3 comidas caseras",
        "Aprender una receta nueva, simple y barata, cada semana",
    ],
    "pantalla": [
        "Activar un límite diario de YouTube o Facebook en Bienestar digital",
        "Reemplazar 30 minutos de videos en la noche por un bloque de estudio o de proyecto",
        "Dejar el celular fuera del baño y fuera de la mesa",
    ],
}


def formato(foco_id, valor):
    """Cada foco con su unidad, para que nadie confunda soles con porcentajes."""
    if valor is None:
        return "sin datos"
    u = FOCOS[foco_id]["unidad"]
    if u.startswith("S/"):
        return f"S/ {valor:.2f} por día"
    if u == "h":
        return f"{valor:.1f} h"
    return f"{valor:g} {u}"


def evaluar_reto(previa, r):
    """Compara el foco de la semana anterior con los datos de esta semana. Sin opiniones: números."""
    foco = (previa or {}).get("foco")
    if not foco or foco.get("id") not in FOCOS:
        return None
    f = FOCOS[foco["id"]]
    actual = f["medir"](r)
    if actual is None:
        return {**foco, "actual": None, "resultado": "sin datos"}
    if f["mejor"] == "menos":
        cumplido, mejoro = actual <= foco["objetivo"], actual < foco["inicial"]
    else:
        cumplido, mejoro = actual >= foco["objetivo"], actual > foco["inicial"]
    resultado = "cumplido" if cumplido else ("parcial" if mejoro else "no cumplido")
    return {**foco, "actual": actual, "resultado": resultado}


def elegir_foco(r, evaluacion):
    """El foco de la semana: si el reto anterior no se cumplió, se insiste; si no, se ataca el problema más grande."""
    if evaluacion and evaluacion["resultado"] in ("no cumplido", "parcial"):
        # Se mantiene el mismo foco y el mismo objetivo: constancia antes que novedad
        return {**{k: evaluacion[k] for k in ("id", "descripcion", "objetivo")}, "inicial": evaluacion["actual"]}

    def nuevo(foco_id, objetivo):
        inicial = FOCOS[foco_id]["medir"](r)
        return {"id": foco_id, "descripcion": FOCOS[foco_id]["descripcion"],
                "inicial": inicial, "objetivo": objetivo}

    ya_cumplido = evaluacion["id"] if evaluacion and evaluacion["resultado"] == "cumplido" else None
    franjas = r["chatarra_franja_prom_diario"]
    if r["chatarra_pct"] >= 40:
        # la franja con más chatarra, sin repetir la que ya se cumplió
        orden = sorted(franjas, key=franjas.get, reverse=True)
        for fr in orden:
            fid = f"chatarra_{fr}"
            if fid != ya_cumplido and franjas[fr] > 0:
                return nuevo(fid, round(franjas[fr] * 0.6, 1))      # bajar 40%: difícil pero posible
    if r["sueno_promedio_h"] is not None and r["sueno_promedio_h"] < SUENO_MINIMO and ya_cumplido != "sueno":
        return nuevo("sueno", round(min(r["sueno_promedio_h"] + 0.5, 7.0), 1))
    if r["comidas_caseras"] < 7 and ya_cumplido != "comidas_caseras":
        return nuevo("comidas_caseras", r["comidas_caseras"] + 3)
    if r["pantalla_prom_min"]:
        return nuevo("pantalla", round(r["pantalla_prom_min"] * 0.8))
    return None


# ── 5. El paquete para NEXOR ──────────────────────────────────
def lista(dic, formato_valor):
    """{'noche': 35} -> 'noche S/ 35.00, tarde ...' — siempre con unidades."""
    return ", ".join(f"{k} {formato_valor(v)}" for k, v in dic.items()) or "sin datos"


def hechos(r, avisos, previa):
    """El resumen en frases con etiquetas y unidades exactas. Así un modelo 4B no mezcla métricas."""
    s = lambda v: f"S/ {v:.2f}"
    ch = r["chatarra_total"] or 1
    emoc = sum(v for k, v in r["motivos_chatarra"].items() if k in MOTIVOS_EMOCIONALES)
    f = [
        f"- Días con registros: {r['dias_registrados']} (con cierre del día: {r['dias_con_cierre']}).",
        f"- Gasto total: {s(r['gasto_total'])}. Promedio por día registrado: {s(r['gasto_promedio_diario'])}.",
        f"- Gasto en chatarra y bebidas azucaradas: {s(r['chatarra_total'])} = {r['chatarra_pct']}% del gasto total.",
        f"- Chatarra proyectada a 7 días: {s(r['chatarra_proyeccion_semanal'])} (el diagnóstico base estimaba "
        f"S/ {CHATARRA_BASE_SEMANAL:.0f}).",
        f"- Compras de chatarra según motivo: {lista(r['motivos_chatarra'], lambda v: f'{v} compras')}. "
        f"En total, {emoc} de {r['compras_chatarra']} compras ({r['chatarra_emocional_pct']}%) fueron por "
        f"estrés, aburrimiento, cansancio o antojo, no por hambre.",
        f"- Chatarra según momento del día: " + ", ".join(
            f"{k} {s(v)} ({v / ch * 100:.0f}% de la chatarra)" for k, v in r["chatarra_por_franja"].items()) + ".",
        f"- Gastos no planificados (cualquier categoría): {r['impulsivos_pct']}% de la cantidad de gastos.",
        f"- Día con más gasto: {r['peor_dia']['dia']}, {s(r['peor_dia']['monto'])}.",
        f"- Gasto por categoría: {lista(r['por_categoria'], s)}.",
        f"- Sueño promedio: {r['sueno_promedio_h']} h por noche. {r['dias_sueno_bajo']} de {r['dias_con_cierre']} "
        f"noches registradas tuvieron menos de {SUENO_MINIMO} h.",
    ]
    if r["chatarra_prom_dias_sueno_bajo"] is not None and r["chatarra_prom_dias_sueno_ok"] is not None:
        dif_sueno = r["chatarra_prom_dias_sueno_bajo"] - r["chatarra_prom_dias_sueno_ok"]
        f.append(f"- Chatarra promedio en un día tras dormir poco: {s(r['chatarra_prom_dias_sueno_bajo'])}; "
                 f"tras dormir bien: {s(r['chatarra_prom_dias_sueno_ok'])}. "
                 f"Diferencia: {s(abs(dif_sueno))} {'MÁS' if dif_sueno >= 0 else 'MENOS'} por día tras dormir poco.")
    f += [
        f"- Comidas del día: {lista(r['comidas'], lambda v: f'{v} vez' if v == 1 else f'{v} veces')}.",
        f"- Tiempo promedio por día: {lista({k: v for k, v in r['tiempo_promedio_min'].items() if v is not None}, lambda v: f'{v} min')}.",
        f"- Ingresos registrados: {s(r['ingresos_total'])}. Diferencia entre ingresos y gastos registrados: "
        f"{s(r['balance'])}. OJO: esto NO es ahorro confirmado (faltan gastos fijos y no se sabe cuánto quedó).",
    ]
    if previa:
        d = r["chatarra_total"] - previa["chatarra_total"]
        dg = r["gasto_total"] - previa["gasto_total"]
        dif = lambda v: f"{'+' if v >= 0 else '-'}S/ {abs(v):.2f}"
        f.append(f"- Frente a la semana {previa['semana']}: chatarra {dif(d)}, gasto total {dif(dg)}.")
    if avisos:
        f.append("- Avisos de calidad de datos: " + " | ".join(avisos))
    return "\n".join(f)


def texto_historial(previas):
    if not previas:
        return "Primera semana registrada: no hay historial."
    return "\n".join(f"- Semana {m['semana']}: gasto S/ {m['gasto_total']:.2f}, chatarra S/ {m['chatarra_total']:.2f} "
                     f"({m['chatarra_pct']}%), sueño {m['sueno_promedio_h']} h."
                     for m in previas[-SEMANAS_EN_MEMORIA:])


def texto_seguimiento(previa, evaluacion, cumpli_usuario):
    if not evaluacion:
        return "No hubo reto la semana anterior: es el primer reto."
    t = (f"Reto anterior: \"{previa.get('reto') or 'sin texto'}\". Meta: {evaluacion['descripcion']} de "
         f"{formato(evaluacion['id'], evaluacion['inicial'])} a {formato(evaluacion['id'], evaluacion['objetivo'])}. "
         f"Resultado medido esta semana: {formato(evaluacion['id'], evaluacion['actual'])} → {evaluacion['resultado'].upper()}.")
    if cumpli_usuario:
        t += f" El usuario dice que lo cumplió: {cumpli_usuario}."
    return t


def texto_foco(foco, r):
    if not foco:
        return "No hay foco definido: propón el reto que más ayude según los datos."
    t = [f"{foco['descripcion']}: esta semana {formato(foco['id'], foco['inicial'])}. "
         f"Objetivo para la próxima semana: {formato(foco['id'], foco['objetivo'])} (promedio de TODOS los días). "
         "El reto tiene que ayudar a llegar a ESE objetivo y se medirá automáticamente con ese número."]
    if foco["id"].startswith("chatarra_"):
        d = r["detalle_franja"][foco["id"].split("_", 1)[1]]
        vez = lambda n: "1 vez" if n == 1 else f"{n} veces"
        items = ", ".join(f"{x['item']} ({vez(x['veces'])}, S/ {x['monto']:.2f})" for x in d["items"])
        t.append(f"Qué se compra en esa franja: {items or 'sin datos'}.")
        t.append(f"Días en que pasa: {', '.join(d['dias']) or 'sin datos'}."
                 + (f" Lugar más frecuente: {d['lugar_frecuente']}." if d["lugar_frecuente"] else ""))
    ideas = RETOS.get(foco["id"], [])
    if ideas:
        t.append("IDEAS DE RETO (elige UNA y adáptala a mi horario real, con días y horas):")
        t += [f"  {i}. {idea}" for i, idea in enumerate(ideas, 1)]
    return "\n".join(t)


def fechas_clave(perfil, hoy):
    """Busca líneas '- AAAA-MM-DD: evento' en el perfil y calcula cuánto falta. La IA no calcula plazos."""
    if not perfil:
        return "Sin fechas clave."
    salida = []
    for fecha, evento in re.findall(r"(\d{4}-\d{2}-\d{2})\s*[:\-–]\s*(.+)", perfil):
        dias = (date.fromisoformat(fecha) - hoy).days
        if dias >= 0:
            salida.append(f"- {evento.strip()}: faltan {dias} días (unas {round(dias / 7)} semanas).")
    return "\n".join(salida) or "Sin fechas clave próximas."


# Estructura obligatoria de la respuesta (Ollama la hace cumplir con "format")
ESQUEMA = {
    "type": "object",
    "properties": {
        "como_te_fue": {"type": "string"},
        "seguimiento": {"type": "string"},
        "lo_que_veo": {"type": "string"},
        "reto": {"type": "string"},
        "por_que_este_reto": {"type": "string"},
        "pregunta": {"type": "string"},
    },
    "required": ["como_te_fue", "seguimiento", "lo_que_veo", "reto", "por_que_este_reto", "pregunta"],
}


def construir_prompt(r, avisos, perfil, previas, evaluacion, foco, cumpli_usuario):
    """Quién eres + historial + esta semana + seguimiento + foco. Todo ya calculado por Python."""
    previa = previas[-1] if previas else None
    return (
        "Eres mi mentor. Escribe mi informe semanal en JSON con los campos pedidos.\n"
        "Las cifras están calculadas y son correctas: cópialas tal cual, con su unidad (S/, %, h, min). No hagas cuentas.\n\n"
        f"=== QUIÉN SOY ===\n{perfil or 'Sin perfil: no supongas nada sobre mi vida.'}\n\n"
        f"=== HISTORIAL ===\n{texto_historial(previas)}\n\n"
        f"=== ESTA SEMANA ({r['rango']['desde']} a {r['rango']['hasta']}) ===\n{hechos(r, avisos, previa)}\n\n"
        f"=== SEGUIMIENTO (medido por el sistema) ===\n{texto_seguimiento(previa, evaluacion, cumpli_usuario)}\n\n"
        f"=== FOCO DE LA PRÓXIMA SEMANA (elegido por el sistema) ===\n{texto_foco(foco, r)}\n\n"
        f"=== FECHAS CLAVE (calculadas al {r['rango']['hasta']}) ===\n"
        f"{fechas_clave(perfil, date.fromisoformat(r['rango']['hasta']))}\n\n"
        "=== QUÉ VA EN CADA CAMPO ===\n"
        "como_te_fue: 2-3 frases con las cifras más importantes. Reconoce algo que salió bien.\n"
        "seguimiento: qué pasó con el reto anterior según el resultado medido. Si es el primero, dilo en una frase.\n"
        "lo_que_veo: el patrón principal y por qué importa, conectado con mis metas y otras áreas de mi vida (3-4 frases). "
        "Si mencionas un porcentaje, di de qué es (del gasto total o de la chatarra). Para plazos usa solo FECHAS CLAVE.\n"
        "reto: elige UNA de las IDEAS DE RETO y adáptala a mi horario: qué hago, qué días y a qué hora. "
        "Tiene que servir para TODOS los días en que pasa el problema, no solo uno. "
        "Debe ser algo que HAGO (preparar, llevar, cambiar, reemplazar), nunca prohibir comer ni saltarme comidas.\n"
        "por_que_este_reto: por qué este reto y no otro, con el dato que lo justifica (2 frases).\n"
        "pregunta: una sola pregunta para reflexionar, sin sermón.\n"
        "Tutéame. Máximo 280 palabras en total."
    )


def preguntar_a_nexor(prompt, modelo):
    """Llama a Ollama sin thinking y con la estructura obligatoria. Devuelve (dict o None, métricas o error)."""
    try:
        import requests
    except ImportError:
        return None, "falta la librería requests (pip install requests)"
    try:
        inicio = time.time()
        resp = requests.post(f"{OLLAMA_URL}/api/chat", timeout=600, json={
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "think": False,          # sin thinking: segundos en vez de minutos
            "format": ESQUEMA,       # respuesta en JSON con los campos fijos
            "stream": False,
        })
        resp.raise_for_status()
        data = resp.json()
        metricas = {
            "modelo": modelo,
            "segundos": round(time.time() - inicio, 1),
            "tokens": data.get("eval_count"),
            "tokens_s": round(data["eval_count"] / (data["eval_duration"] / 1e9), 1)
                        if data.get("eval_count") and data.get("eval_duration") else None,
        }
        contenido = data["message"]["content"].strip()
        try:
            return json.loads(contenido), metricas
        except json.JSONDecodeError:
            return {"texto_libre": contenido}, metricas   # por si el modelo no respetó el JSON
    except Exception as e:  # Ollama apagado, modelo inexistente, etc.
        return None, f"no se pudo contactar a Ollama ({e}). ¿Está abierto? Prueba: ollama serve"


# ── 6. Escribir el reporte ────────────────────────────────────
def boton(texto, destino, color, detalle=None):
    """Botón estilo shields.io para GitHub: [texto | detalle]."""
    from urllib.parse import quote
    esc = lambda t: quote(t.replace("-", "--").replace("_", "__"))
    partes = f"{esc(texto)}-{esc(detalle)}" if detalle else esc(texto)
    return f"[![{texto}](https://img.shields.io/badge/{partes}-{color}?style=for-the-badge)]({destino})"


def nombre_reporte(datos):
    desde = date.fromisoformat(datos["rango"]["desde"])
    anio, semana, _ = desde.isocalendar()
    sufijo = "-beta" if datos.get("beta") else ""
    return f"semana-{anio}-W{semana:02d}{sufijo}.md", f"{anio}-W{semana:02d}"


def tabla(dic, col1, col2, formato_valor=lambda v: v):
    filas = [f"| {col1} | {col2} |", "|---|---:|"]
    filas += [f"| {k} | {formato_valor(v)} |" for k, v in dic.items()]
    return "\n".join(filas)


ICONO_RESULTADO = {"cumplido": "✅", "parcial": "🟡", "no cumplido": "❌", "sin datos": "❔"}


def seccion_mentor(respuesta, metricas, foco, evaluacion, con_perfil):
    partes = ["## 🧭 NEXOR, tu mentor", ""]
    if respuesta and "reto" in respuesta:
        partes += [f"> 🎯 **Reto:** {respuesta['reto']}  "]
    if foco:
        partes += [f"> 📏 **Meta:** {foco['descripcion']}: de {formato(foco['id'], foco['inicial'])} a "
                   f"{formato(foco['id'], foco['objetivo'])}. Se revisa sola la próxima semana."]
    partes.append("")
    if evaluacion:
        partes += ["| Reto anterior | Inicio | Objetivo | Esta semana | Resultado |", "|---|---:|---:|---:|:---:|",
                   f"| {evaluacion['descripcion']} | {formato(evaluacion['id'], evaluacion['inicial'])} | "
                   f"{formato(evaluacion['id'], evaluacion['objetivo'])} | {formato(evaluacion['id'], evaluacion['actual'])} | "
                   f"{ICONO_RESULTADO.get(evaluacion['resultado'], '')} {evaluacion['resultado']} |", ""]
    if not respuesta:
        return partes + [f"_Sin análisis de IA: {metricas}_"]
    if "texto_libre" in respuesta:
        partes += [respuesta["texto_libre"]]
    else:
        for titulo, clave in [("Cómo te fue", "como_te_fue"), ("Seguimiento", "seguimiento"),
                              ("Lo que veo", "lo_que_veo"), ("Por qué este reto", "por_que_este_reto"),
                              ("Pregunta para pensar", "pregunta")]:
            texto = respuesta.get(clave, "").strip()
            if texto:
                partes += [f"### {titulo}", f"*{texto}*" if clave == "pregunta" else texto, ""]
    partes += [f"<sub>Modelo `{metricas['modelo']}` · {metricas['segundos']} s · {metricas['tokens']} tokens · "
               f"{metricas['tokens_s']} tokens/s · sin thinking · perfil {'cargado' if con_perfil else 'no encontrado'}</sub>"]
    return partes


def escribir_reporte(datos, r, avisos, respuesta, metricas, archivo_origen, foco, evaluacion, con_perfil):
    CARPETA_REPORTES.mkdir(parents=True, exist_ok=True)
    nombre, semana = nombre_reporte(datos)
    s = lambda v: f"S/ {v:.2f}"
    beta = datos.get("beta")
    desde, hasta = r["rango"]["desde"], r["rango"]["hasta"]

    partes = [
        f"# 💰 Semana {semana}{' · BETA' if beta else ''}", "",
        boton("← Mis semanas", "README.md", "8b5cf6") + "\n" + boton("Inicio", "../../README.md", "ec4899"), "",
        f"> **Periodo:** {desde} a {hasta} · **Días registrados:** {r['dias_registrados']} · "
        f"**Días con cierre:** {r['dias_con_cierre']}",
    ]
    if beta:
        partes += [">", "> ⚠️ **Reporte BETA:** mezcla datos reales y simulados. Sirve para probar el sistema, no como diagnóstico."]
    partes += [
        "", "---", "", "## 📌 Números clave", "",
        "| Indicador | Valor |", "|---|---:|",
        f"| Gasto total | {s(r['gasto_total'])} |",
        f"| Promedio por día registrado | {s(r['gasto_promedio_diario'])} |",
        f"| Chatarra + bebidas azucaradas | {s(r['chatarra_total'])} ({r['chatarra_pct']}% del gasto) |",
        f"| Chatarra proyectada a 7 días | {s(r['chatarra_proyeccion_semanal'])} "
        f"({'+' if r['chatarra_vs_base'] >= 0 else ''}{r['chatarra_vs_base']:.2f} vs base de S/ {CHATARRA_BASE_SEMANAL:.0f}) |",
        f"| Chatarra por motivos emocionales | {r['chatarra_emocional_pct']}% de las compras de chatarra |",
        f"| Gastos no planificados | {r['impulsivos_pct']}% de los gastos |",
        f"| Peor día | {r['peor_dia']['dia']} {r['peor_dia']['fecha']} · {s(r['peor_dia']['monto'])} |",
        f"| Sueño promedio | {r['sueno_promedio_h']} h · {r['dias_sueno_bajo']} de {r['dias_con_cierre']} noches con menos de {SUENO_MINIMO} h |",
        f"| Ingresos − gastos registrados | {s(r['ingresos_total'])} − {s(r['gasto_total'])} = {s(r['balance'])} *(no es ahorro confirmado)* |",
        "", "---", "",
    ]
    partes += seccion_mentor(respuesta, metricas, foco, evaluacion, con_perfil)
    partes += [
        "", "---", "", "## 🔎 Detalle", "",
        "### Gasto por día", "", tabla(r["gasto_por_dia"], "Fecha", "Gasto", s), "",
        "### Por categoría", "", tabla(r["por_categoria"], "Categoría", "Monto", s), "",
        "### ¿Por qué compro chatarra?", "", tabla(r["motivos_chatarra"], "Motivo", "Compras"), "",
        "### ¿Cuándo compro chatarra?", "", tabla(r["chatarra_por_franja"], "Franja", "Monto", s), "",
        "### Sueño y chatarra", "",
        f"- Días tras dormir menos de {SUENO_MINIMO} h: chatarra promedio de "
        f"{s(r['chatarra_prom_dias_sueno_bajo']) if r['chatarra_prom_dias_sueno_bajo'] is not None else 'sin datos'}",
        f"- Días tras dormir {SUENO_MINIMO} h o más: chatarra promedio de "
        f"{s(r['chatarra_prom_dias_sueno_ok']) if r['chatarra_prom_dias_sueno_ok'] is not None else 'sin datos'}",
        "", "### Comidas", "", tabla(r["comidas"], "Tipo", "Veces"), "",
        "### Tiempo promedio por día (min)", "",
        tabla({k: ("—" if v is None else v) for k, v in r["tiempo_promedio_min"].items()}, "Actividad", "Minutos"),
        "", "---", "", "## ⚠️ Calidad de los datos", "",
    ]
    partes += [f"- {a}" for a in avisos] if avisos else ["- Sin problemas detectados."]
    partes += ["", f"<sub>Generado por `scripts/finanzas.py` el {datetime.now():%Y-%m-%d %H:%M} "
                   f"desde `{Path(archivo_origen).name}`.</sub>", ""]

    ruta = CARPETA_REPORTES / nombre
    ruta.write_text("\n".join(partes), encoding="utf-8")
    actualizar_indice(nombre, semana, r, beta, evaluacion)
    return ruta


INDICE_SEMANAS = """# 🔒 Mis semanas

""" + "[![Reportes](https://img.shields.io/badge/%E2%86%90%20Reportes-8b5cf6?style=for-the-badge)](../README.md)" + """

Reportes semanales de NEXOR. **Esta carpeta es privada:** está en `.gitignore` y no se sube a GitHub.

| Semana | Periodo | Resumen | |
|---|---|---|---|
"""


def actualizar_indice(nombre, semana, r, beta, evaluacion):
    """Agrega (o reemplaza) la fila de esta semana en reportes/README.md."""
    indice = CARPETA_REPORTES / "README.md"
    if not indice.exists():
        indice.write_text(INDICE_SEMANAS, encoding="utf-8")
    texto = indice.read_text(encoding="utf-8")
    titulo = f"Semana {semana}{' · BETA' if beta else ''}"
    reto_ant = f" · reto anterior {ICONO_RESULTADO.get(evaluacion['resultado'], '')}" if evaluacion else ""
    resumen = f"Gasto S/ {r['gasto_total']:.2f} · chatarra {r['chatarra_pct']}% · sueño {r['sueno_promedio_h']} h{reto_ant}"
    fila = (f"| {titulo} | {r['rango']['desde']} a {r['rango']['hasta']} | {resumen} | "
            f"{boton('Abrir', nombre, '22d3ee', semana)} |")
    lineas = [l for l in texto.splitlines() if f"]({nombre})" not in l]   # quita la fila vieja
    ultima = max(i for i, l in enumerate(lineas) if l.startswith("|"))
    lineas.insert(ultima + 1, fila)
    indice.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ── Programa principal ────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Reporte semanal de NEXOR IA")
    p.add_argument("archivo", nargs="?", help="JSON exportado por NEXOR REGISTER (por defecto: el más reciente de datos/)")
    p.add_argument("--modelo", default=MODELO_POR_DEFECTO, help="modelo de Ollama (por defecto: nexor)")
    p.add_argument("--sin-ia", action="store_true", help="solo calcula los números, sin llamar a la IA")
    p.add_argument("--cumpli", choices=["si", "no", "parcial"],
                   help="tu opinión sobre el reto anterior (Python además lo mide con los datos)")
    a = p.parse_args()

    if not a.archivo:
        candidatos = sorted((RAIZ / "datos").rglob("*.json"), key=lambda f: f.stat().st_mtime)
        if not candidatos:
            sys.exit("❌ No hay archivos .json en datos/. Exporta desde NEXOR REGISTER y cópialo ahí.")
        a.archivo = str(candidatos[-1])
        print(f"📂 Usando {Path(a.archivo).relative_to(RAIZ)}")

    datos = cargar(a.archivo)
    avisos = validar(datos)
    resumen = calcular(datos)
    beta = bool(datos.get("beta"))
    _, semana = nombre_reporte(datos)
    print(f"📊 {resumen['dias_registrados']} días · gasto S/ {resumen['gasto_total']:.2f} · "
          f"chatarra {resumen['chatarra_pct']}% · {len(avisos)} avisos")

    perfil = cargar_perfil()
    previas = [m for m in cargar_memoria(beta) if m["semana"] < semana]
    evaluacion = evaluar_reto(previas[-1] if previas else None, resumen)
    foco = elegir_foco(resumen, evaluacion)
    print(f"🧠 Perfil: {'sí' if perfil else 'no (crea perfil.local.md)'} · semanas en memoria: {len(previas)}")
    if evaluacion:
        print(f"🔁 Reto anterior: {evaluacion['descripcion']} → {evaluacion['resultado']}")
    if foco:
        print(f"🎯 Foco: {foco['descripcion']} · de {formato(foco['id'], foco['inicial'])} a {formato(foco['id'], foco['objetivo'])}")

    respuesta, metricas = None, "se ejecutó con --sin-ia"
    if not a.sin_ia:
        print(f"🤖 Consultando a {a.modelo}…")
        prompt = construir_prompt(resumen, avisos, perfil, previas, evaluacion, foco, a.cumpli)
        respuesta, metricas = preguntar_a_nexor(prompt, a.modelo)
        if respuesta is None:
            print(f"⚠️  {metricas}")
        else:
            guardar_memoria(beta, semana, resumen, foco, respuesta.get("reto"), evaluacion, a.cumpli)

    ruta = escribir_reporte(datos, resumen, avisos, respuesta, metricas, a.archivo, foco, evaluacion, bool(perfil))
    print(f"✅ Reporte: {ruta.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
