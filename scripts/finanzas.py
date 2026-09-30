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

Regla de oro: Python hace las cuentas; la IA solo interpreta.
"""

import argparse
import json
import sys
import time
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path

# ── Configuración ─────────────────────────────────────────────
RAIZ = Path(__file__).resolve().parent.parent       # carpeta del repo
CARPETA_REPORTES = RAIZ / "reportes"
OLLAMA_URL = "http://localhost:11434"
MODELO_POR_DEFECTO = "nexor"

# Referencia del diagnóstico base (27/09/2026): chatarra estimada por semana
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
    }


# ── 3. Pedirle a NEXOR que lo interprete ──────────────────────
def construir_prompt(r, avisos):
    """Mensaje corto con cifras ya calculadas. Nada de JSON crudo: no cabe ni hace falta."""
    return (
        "Analiza mi semana. Todas las cifras ya están calculadas y son correctas: no las recalcules ni inventes otras.\n\n"
        f"RESUMEN (soles):\n{json.dumps(r, ensure_ascii=False)}\n\n"
        f"AVISOS DE CALIDAD DE DATOS:\n- " + ("\n- ".join(avisos) if avisos else "ninguno") + "\n\n"
        "Referencia: el diagnóstico base estimó S/ 95 por semana en chatarra.\n"
        "Responde con: 1) Números clave 2) Patrón principal 3) UNA sola acción medible para la próxima semana. "
        "Máximo 200 palabras."
    )


def preguntar_a_nexor(prompt, modelo):
    """Llama a la API local de Ollama sin thinking. Devuelve (texto, métricas) o (None, error)."""
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
        return data["message"]["content"].strip(), metricas
    except Exception as e:  # Ollama apagado, modelo inexistente, etc.
        return None, f"no se pudo contactar a Ollama ({e}). ¿Está abierto? Prueba: ollama serve"


# ── 4. Escribir el reporte ────────────────────────────────────
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


def tabla(dic, col1, col2, formato=lambda v: v):
    filas = [f"| {col1} | {col2} |", "|---|---:|"]
    filas += [f"| {k} | {formato(v)} |" for k, v in dic.items()]
    return "\n".join(filas)


def escribir_reporte(datos, r, avisos, analisis, metricas, archivo_origen):
    CARPETA_REPORTES.mkdir(exist_ok=True)
    nombre, semana = nombre_reporte(datos)
    s = lambda v: f"S/ {v:.2f}"
    beta = datos.get("beta")
    desde, hasta = r["rango"]["desde"], r["rango"]["hasta"]

    partes = [
        f"# 💰 Semana {semana}{' · BETA' if beta else ''}",
        "",
        boton("← Reportes", "README.md", "8b5cf6") + "\n" + boton("Inicio", "../README.md", "ec4899"),
        "",
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
        f"| Chatarra + bebidas azucaradas | {s(r['chatarra_total'])} ({r['chatarra_pct']}%) |",
        f"| Chatarra proyectada a 7 días | {s(r['chatarra_proyeccion_semanal'])} "
        f"({'+' if r['chatarra_vs_base'] >= 0 else ''}{r['chatarra_vs_base']:.2f} vs base de S/ {CHATARRA_BASE_SEMANAL:.0f}) |",
        f"| Chatarra por motivos emocionales | {r['chatarra_emocional_pct']}% de las compras |",
        f"| Gastos por impulso | {r['impulsivos_pct']}% |",
        f"| Peor día | {r['peor_dia']['dia']} {r['peor_dia']['fecha']} · {s(r['peor_dia']['monto'])} |",
        f"| Sueño promedio | {r['sueno_promedio_h']} h · {r['dias_sueno_bajo']} días con menos de {SUENO_MINIMO} h |",
        f"| Ingresos / balance | {s(r['ingresos_total'])} / {s(r['balance'])} |",
        "", "---", "", "## 🤖 Análisis de NEXOR", "",
    ]
    if analisis:
        partes += [analisis, "",
                   f"<sub>Modelo `{metricas['modelo']}` · {metricas['segundos']} s · "
                   f"{metricas['tokens']} tokens · {metricas['tokens_s']} tokens/s · sin thinking</sub>"]
    else:
        partes += [f"_Sin análisis de IA: {metricas}_"]

    partes += [
        "", "---", "", "## 🔎 Detalle", "",
        "### Gasto por día", "", tabla(r["gasto_por_dia"], "Fecha", "Gasto", s), "",
        "### Por categoría", "", tabla(r["por_categoria"], "Categoría", "Monto", s), "",
        "### ¿Por qué compro chatarra?", "", tabla(r["motivos_chatarra"], "Motivo", "Compras"), "",
        "### ¿Cuándo compro chatarra?", "", tabla(r["chatarra_por_franja"], "Franja", "Monto", s), "",
        "### Sueño y chatarra", "",
        f"- Días con menos de {SUENO_MINIMO} h de sueño: chatarra promedio de "
        f"{s(r['chatarra_prom_dias_sueno_bajo']) if r['chatarra_prom_dias_sueno_bajo'] is not None else 'sin datos'}",
        f"- Días con {SUENO_MINIMO} h o más: chatarra promedio de "
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
    actualizar_indice(nombre, semana, r, beta)
    return ruta


def actualizar_indice(nombre, semana, r, beta):
    """Agrega (o reemplaza) la fila de esta semana en reportes/README.md."""
    indice = CARPETA_REPORTES / "README.md"
    if not indice.exists():
        return
    texto = indice.read_text(encoding="utf-8")
    titulo = f"Semana {semana}{' · BETA' if beta else ''}"
    resumen = (f"Gasto S/ {r['gasto_total']:.2f} · chatarra {r['chatarra_pct']}% · "
               f"sueño {r['sueno_promedio_h']} h")
    fila = (f"| {titulo} | {r['rango']['desde']} a {r['rango']['hasta']} | {resumen} | "
            f"{boton('Abrir', nombre, '22d3ee', semana)} |")
    lineas = [l for l in texto.splitlines() if f"]({nombre})" not in l]   # quita la fila vieja
    # inserta después de la última fila de la tabla
    ultima = max(i for i, l in enumerate(lineas) if l.startswith("|"))
    lineas.insert(ultima + 1, fila)
    indice.write_text("\n".join(lineas) + "\n", encoding="utf-8")


# ── Programa principal ────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="Reporte semanal de NEXOR IA")
    p.add_argument("archivo", nargs="?", help="JSON exportado por NEXOR REGISTER (por defecto: el más reciente de datos/)")
    p.add_argument("--modelo", default=MODELO_POR_DEFECTO, help="modelo de Ollama (por defecto: nexor)")
    p.add_argument("--sin-ia", action="store_true", help="solo calcula los números, sin llamar a la IA")
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
    print(f"📊 {resumen['dias_registrados']} días · gasto S/ {resumen['gasto_total']:.2f} · "
          f"chatarra {resumen['chatarra_pct']}% · {len(avisos)} avisos")

    analisis, metricas = None, "se ejecutó con --sin-ia"
    if not a.sin_ia:
        print(f"🤖 Consultando a {a.modelo}…")
        analisis, metricas = preguntar_a_nexor(construir_prompt(resumen, avisos), a.modelo)
        if analisis is None:
            print(f"⚠️  {metricas}")

    ruta = escribir_reporte(datos, resumen, avisos, analisis, metricas, a.archivo)
    print(f"✅ Reporte: {ruta.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
