'use strict';
/* NEXOR REGISTER · módulo de captura de datos para NEXOR IA
   JavaScript puro, sin dependencias. Persistencia en IndexedDB.
   Dentro del APK usa los plugins nativos de Capacitor (Filesystem, Share, App) si existen. */

// ---------- Constantes ----------
const TZ = 'America/Lima';
const APP = 'NEXOR REGISTER';
const SCHEMA = 1;

const CATEGORIAS = [
  ['chatarra', 'Chatarra'], ['bebida_azucarada', 'Bebida azucarada'], ['comida_real', 'Comida real'],
  ['transporte', 'Transporte'], ['salidas', 'Salidas'], ['tecnologia', 'Tecnología'],
  ['servicios', 'Servicios'], ['estudios', 'Estudios'], ['casa', 'Casa'], ['otros', 'Otros']
];
const JUNK = ['chatarra', 'bebida_azucarada'];
const MOTIVOS = [
  ['hambre', 'Hambre'], ['antojo', 'Antojo'], ['aburrimiento', 'Aburrimiento'], ['estres', 'Estrés'],
  ['social', 'Social'], ['necesidad', 'Necesidad'], ['cansancio', 'Cansancio']
];
const FUENTES = [['familia', 'Familia'], ['practicas', 'Prácticas'], ['freelance', 'Freelance'], ['otros', 'Otros']];
const COMIDAS = [['casera', 'Casera'], ['comprada', 'Comprada'], ['chatarra', 'Chatarra'], ['no_comi', 'No comí']];
const LUGARES = ['Saliendo de Brighter', 'Recreo SENATI', 'Casa', 'Calle'];
const TIEMPOS = [
  ['pantalla_celular', 'Pantalla del celular'], ['juegos', 'Juegos'], ['estudio', 'Estudio'],
  ['proyectos', 'Proyectos'], ['ingles', 'Inglés'], ['ejercicio', 'Ejercicio']
];
const TIEMPO_PRESETS = [0, 15, 30, 60, 90, 120, 180];
const DEFAULT_PRESETS = [
  { item: 'Papa rellena', monto: 3.5, categoria: 'chatarra' },
  { item: 'Pan + jamonada', monto: 4, categoria: 'chatarra' },
  { item: 'Helado grande', monto: 9.5, categoria: 'chatarra' },
  { item: 'Sándwich', monto: 2, categoria: 'chatarra' },
  { item: 'Galletas', monto: 2.5, categoria: 'chatarra' },
  { item: 'Gaseosa', monto: 1, categoria: 'bebida_azucarada' },
  { item: 'Pasaje', monto: 1.3, categoria: 'transporte' },
  { item: 'Taxi', monto: null, categoria: 'transporte' }
];

const label = (list, k) => (list.find(x => x[0] === k) || [k, k])[1];
const $ = sel => document.querySelector(sel);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const r2 = n => Math.round((Number(n) || 0) * 100) / 100;
const soles = n => 'S/ ' + (Number(n) || 0).toFixed(2);
const uuid = () => (crypto.randomUUID ? crypto.randomUUID() :
  'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = crypto.getRandomValues(new Uint8Array(1))[0] & 15;
    return (c === 'x' ? r : (r & 3) | 8).toString(16);
  }));

// ---------- Fechas (zona America/Lima) ----------
function ahora() {
  const p = new Intl.DateTimeFormat('en-CA', {
    timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  }).formatToParts(new Date());
  const g = t => p.find(x => x.type === t).value;
  const h = g('hour') === '24' ? '00' : g('hour');
  return { fecha: `${g('year')}-${g('month')}-${g('day')}`, hora: `${h}:${g('minute')}` };
}
const hoy = () => ahora().fecha;
const toUTC = f => { const [y, m, d] = f.split('-').map(Number); return Date.UTC(y, m - 1, d); };
const addDays = (f, n) => new Date(toUTC(f) + n * 864e5).toISOString().slice(0, 10);
const diffDays = (a, b) => Math.round((toUTC(b) - toUTC(a)) / 864e5);
const dow = f => new Date(toUTC(f)).getUTCDay(); // 0 = domingo
const lunes = f => addDays(f, -((dow(f) + 6) % 7));
const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'set', 'oct', 'nov', 'dic'];
const fFecha = f => { const [, m, d] = f.split('-').map(Number); return `${DIAS[dow(f)]} ${d} ${MESES[m - 1]}`; };
const minutos = hhmm => { const [h, m] = hhmm.split(':').map(Number); return h * 60 + m; };
function horasSueno(dormir, despertar) {
  if (!dormir || !despertar) return null;
  let d = minutos(despertar) - minutos(dormir);
  if (d <= 0) d += 1440;
  return r2(d / 60);
}

// ---------- IndexedDB ----------
const DB = {
  db: null,
  open() {
    return new Promise((res, rej) => {
      const rq = indexedDB.open('nexor_register', 1);
      rq.onupgradeneeded = () => {
        const d = rq.result;
        const s = d.createObjectStore('registros', { keyPath: 'id' });
        s.createIndex('fecha', 'fecha');
        s.createIndex('tipo', 'tipo');
        d.createObjectStore('presets', { keyPath: 'id' });
      };
      rq.onsuccess = () => { this.db = rq.result; res(); };
      rq.onerror = () => rej(rq.error);
    });
  },
  tx(store, mode, fn) {
    return new Promise((res, rej) => {
      const t = this.db.transaction(store, mode);
      const q = fn(t.objectStore(store));
      let out;
      if (q) q.onsuccess = () => { out = q.result; };
      t.oncomplete = () => res(out);
      t.onerror = t.onabort = () => rej(t.error);
    });
  },
  all: (st) => DB.tx(st, 'readonly', s => s.getAll()),
  get: (st, id) => DB.tx(st, 'readonly', s => s.get(id)),
  put: (st, v) => DB.tx(st, 'readwrite', s => s.put(v)),
  del: (st, id) => DB.tx(st, 'readwrite', s => s.delete(id)),
  clear: (st) => DB.tx(st, 'readwrite', s => s.clear()),
  putMany: (st, arr) => DB.tx(st, 'readwrite', s => { arr.forEach(v => s.put(v)); }),
  rango: (desde, hasta) => DB.tx('registros', 'readonly', s => s.index('fecha').getAll(IDBKeyRange.bound(desde, hasta)))
};

async function getPresets() {
  const p = await DB.all('presets');
  return p.sort((a, b) => a.orden - b.orden);
}
async function seedPresets() {
  await DB.clear('presets');
  await DB.putMany('presets', DEFAULT_PRESETS.map((p, i) => ({ id: uuid(), orden: i, ...p })));
}

// ---------- Resumen (Historial y exportación) ----------
function resumen(regs, desde, hasta) {
  const gastos = regs.filter(r => r.tipo === 'gasto');
  const cierres = regs.filter(r => r.tipo === 'cierre_dia');
  const ingresos = regs.filter(r => r.tipo === 'ingreso');
  const dias = diffDays(desde, hasta) + 1;
  const total = gastos.reduce((a, g) => a + g.monto, 0);
  const porCat = {};
  gastos.forEach(g => { porCat[g.categoria] = r2((porCat[g.categoria] || 0) + g.monto); });
  const junk = gastos.filter(g => JUNK.includes(g.categoria)).reduce((a, g) => a + g.monto, 0);
  const noPlan = gastos.filter(g => !g.planificado).length;
  const motivos = {};
  gastos.forEach(g => { if (g.motivo) motivos[g.motivo] = (motivos[g.motivo] || 0) + 1; });
  const top = Object.entries(motivos).sort((a, b) => b[1] - a[1])[0];
  const suenos = cierres.map(c => c.sueno?.horas).filter(h => typeof h === 'number');
  const fechasReg = new Set([...gastos, ...cierres].map(r => r.fecha));
  return {
    dias_en_rango: dias,
    gasto_total: r2(total),
    gasto_promedio_diario: r2(total / dias),
    gastos_cantidad: gastos.length,
    por_categoria: porCat,
    chatarra_bebida_total: r2(junk),
    chatarra_bebida_pct: total ? r2(junk / total * 100) : 0,
    no_planificados_pct: gastos.length ? r2(noPlan / gastos.length * 100) : 0,
    motivos,
    motivo_mas_frecuente: top ? top[0] : null,
    sueno_promedio_h: suenos.length ? r2(suenos.reduce((a, b) => a + b, 0) / suenos.length) : null,
    dias_sueno_menor_6_5: suenos.filter(h => h < 6.5).length,
    ingresos_total: r2(ingresos.reduce((a, i) => a + i.monto, 0)),
    dias_registrados: fechasReg.size,
    dias_con_cierre: cierres.length
  };
}

// ---------- UI: navegación, hoja, diálogo, aviso ----------
let vistaActual = 'registrar';
function irA(v) {
  vistaActual = v;
  document.querySelectorAll('.view').forEach(s => s.classList.toggle('active', s.id === 'v-' + v));
  document.querySelectorAll('.nav button').forEach(b => b.classList.toggle('active', b.dataset.view === v));
  window.scrollTo(0, 0);
  ({ registrar: renderRegistrar, cierre: () => renderCierre($('#cierre-fecha').value || hoy()),
     historial: renderHistorial, exportar: renderExportar, ajustes: renderAjustes })[v]();
}

let sheetOpen = false;
function abrirHoja(html, onMount) {
  $('#sheet-body').innerHTML = html;
  $('#overlay').classList.add('show');
  $('#sheet').classList.add('show');
  $('#sheet').scrollTop = 0;
  sheetOpen = true;
  if (onMount) onMount($('#sheet-body'));
}
function cerrarHoja() {
  $('#overlay').classList.remove('show');
  $('#sheet').classList.remove('show');
  sheetOpen = false;
  if (document.activeElement) document.activeElement.blur();
}

let dialogResolve = null;
function confirmar(msg, okTxt = 'Borrar') {
  const d = $('#dialog');
  d.innerHTML = `<p>${esc(msg)}</p><div class="row">
    <button class="btn ghost" data-r="0">Cancelar</button>
    <button class="btn danger" data-r="1">${esc(okTxt)}</button></div>`;
  d.classList.add('show');
  return new Promise(res => {
    dialogResolve = res;
    d.querySelectorAll('button').forEach(b => b.onclick = () => cerrarDialogo(b.dataset.r === '1'));
  });
}
function cerrarDialogo(v) {
  $('#dialog').classList.remove('show');
  if (dialogResolve) { dialogResolve(v); dialogResolve = null; }
}

let toastTimer = null;
function aviso(msg, accion, fn, ms = 2500) {
  const t = $('#toast');
  t.innerHTML = `<span>${esc(msg)}</span>` + (accion ? `<button>${esc(accion)}</button><i class="toast-bar" style="--t:${ms}ms"></i>` : '');
  if (accion) t.querySelector('button').onclick = () => { t.classList.remove('show'); fn(); };
  t.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove('show'), ms);
}

// ---------- Efectos visuales y vibración ----------
const FX_COLORES = ['#a855f7', '#ec4899', '#22d3ee', '#f472b6', '#c084fc', '#67e8f9'];
const reduceMotion = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
const fx = {
  haptic(tipo = 'light') {
    const H = window.Capacitor?.Plugins?.Haptics;
    if (H?.impact) { H.impact({ style: tipo === 'heavy' ? 'HEAVY' : tipo === 'medium' ? 'MEDIUM' : 'LIGHT' }).catch(() => {}); return; }
    if (navigator.vibrate) navigator.vibrate(tipo === 'heavy' ? [18, 40, 24] : 12);
  },
  exito() {
    const H = window.Capacitor?.Plugins?.Haptics;
    if (H?.notification) { H.notification({ type: 'SUCCESS' }).catch(() => {}); return; }
    if (navigator.vibrate) navigator.vibrate([15, 50, 25]);
  },
  centro(el) { const r = el.getBoundingClientRect(); return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; },
  burst(x, y, n = 26, colores = FX_COLORES) {
    if (reduceMotion()) return;
    const capa = $('#fx');
    for (let i = 0; i < n; i++) {
      const p = document.createElement('i');
      const ang = (Math.PI * 2 * i) / n + Math.random() * .5;
      const dist = 50 + Math.random() * 90;
      p.className = 'particle' + (Math.random() < .35 ? ' star' : '');
      p.style.cssText = `left:${x}px;top:${y}px;--s:${4 + Math.random() * 6}px;--c:${colores[i % colores.length]};` +
        `--x:${Math.cos(ang) * dist}px;--y:${Math.sin(ang) * dist - 20}px;--d:${600 + Math.random() * 500}ms`;
      capa.appendChild(p);
      setTimeout(() => p.remove(), 1200);
    }
  },
  flotar(el, texto, ingreso = false) {
    if (reduceMotion()) return;
    const { x, y } = fx.centro(el);
    const f = document.createElement('div');
    f.className = 'float-amt' + (ingreso ? ' in' : '');
    f.textContent = texto;
    f.style.left = x + 'px';
    f.style.top = (y - 20) + 'px';
    $('#fx').appendChild(f);
    setTimeout(() => f.remove(), 1200);
  },
  brillo(el) { el.classList.remove('glow'); void el.offsetWidth; el.classList.add('glow'); },
  fijar(el, valor) { el._anim = null; el.textContent = soles(valor); },
  contar(el, desde, hasta, ms = 650) {
    if (reduceMotion() || desde === hasta) { fx.fijar(el, hasta); return; }
    const t0 = performance.now();
    const token = el._anim = {};
    const paso = t => {
      if (el._anim !== token) return;
      const k = Math.min(1, (t - t0) / ms);
      const e = 1 - Math.pow(1 - k, 3);
      el.textContent = soles(desde + (hasta - desde) * e);
      if (k < 1) requestAnimationFrame(paso);
    };
    requestAnimationFrame(paso);
  },
  ripple(e) {
    const b = e.target.closest('.btn, .preset, .chip, .scale button, .toggle button, .nav button, .stepper button, .lista .acts button');
    if (!b || b.disabled || reduceMotion()) return;
    const r = b.getBoundingClientRect();
    const d = Math.max(r.width, r.height) * 2.2;
    const s = document.createElement('span');
    s.className = 'ripple';
    s.style.cssText = `width:${d}px;height:${d}px;left:${e.clientX - r.left - d / 2}px;top:${e.clientY - r.top - d / 2}px`;
    b.appendChild(s);
    setTimeout(() => s.remove(), 600);
  }
};
// Estado para animar lo que se acaba de agregar
let totales = { hoy: 0, semana: 0 };
let celebrar = null; // { id, monto, ingreso }

const chipsHTML = (list, sel, name, cls = '') =>
  `<div class="chips" data-chips="${name}">` +
  list.map(([k, l]) => `<button type="button" class="chip ${cls} ${sel === k ? 'on' : ''}" data-v="${esc(k)}">${esc(l)}</button>`).join('') +
  '</div>';
function bindChips(root, name, onPick) {
  const box = root.querySelector(`[data-chips="${name}"]`);
  box.addEventListener('click', e => {
    const b = e.target.closest('.chip');
    if (!b) return;
    box.querySelectorAll('.chip').forEach(x => x.classList.toggle('on', x === b));
    box.classList.remove('err');
    onPick(b.dataset.v);
  });
}
const parseMonto = v => { const n = parseFloat(String(v).replace(',', '.')); return isFinite(n) && n > 0 ? r2(n) : null; };

// ---------- REGISTRAR ----------
async function renderRegistrar() {
  const h = hoy();
  $('#top-date').textContent = fFecha(h);
  const ws = lunes(h);
  const regs = await DB.rango(ws, addDays(ws, 6));
  const gastos = regs.filter(r => r.tipo === 'gasto');
  const sum = arr => arr.reduce((a, g) => a + g.monto, 0);
  const gh = gastos.filter(g => g.fecha === h);
  const nuevos = { hoy: sum(gh), semana: sum(gastos) };
  const cel = celebrar;
  if (cel && !cel.ingreso) {
    fx.contar($('#t-hoy'), totales.hoy, nuevos.hoy);
    fx.contar($('#t-semana'), totales.semana, nuevos.semana);
  } else {
    fx.fijar($('#t-hoy'), nuevos.hoy);
    fx.fijar($('#t-semana'), nuevos.semana);
  }
  totales = nuevos;
  const jh = sum(gh.filter(g => JUNK.includes(g.categoria)));
  const js = sum(gastos.filter(g => JUNK.includes(g.categoria)));
  $('#t-hoy-ch').textContent = jh ? `chatarra ${soles(jh)}` : '';
  $('#t-semana-ch').textContent = js ? `chatarra ${soles(js)}` : '';

  const presets = await getPresets();
  $('#presets').innerHTML = presets.map(p => `
    <button class="preset ${JUNK.includes(p.categoria) ? 'junk' : ''}" data-id="${p.id}">
      <b>${esc(p.item)}</b><i>${p.monto ? soles(p.monto) : 'monto libre'}</i></button>`).join('') +
    `<button class="preset otro" data-id="otro"><b>Otro</b><i>formulario</i></button>`;
  $('#presets').onclick = e => {
    const b = e.target.closest('.preset');
    if (!b) return;
    b.classList.remove('tapped'); void b.offsetWidth; b.classList.add('tapped');
    fx.haptic();
    if (b.dataset.id === 'otro') abrirGasto(null);
    else abrirGasto(presets.find(p => p.id === b.dataset.id));
  };

  const lista = regs.filter(r => r.fecha === h && r.tipo !== 'cierre_dia')
    .sort((a, b) => (b.hora || '').localeCompare(a.hora || '') || (b.creado_en || '').localeCompare(a.creado_en || ''));
  renderListaRegistros($('#hoy-lista'), lista, renderRegistrar, cel?.id);
  await renderBannerCierre();
  if (cel) {
    celebrar = null;
    const card = $('#t-hoy').closest('.total');
    const { x, y } = fx.centro(card);
    fx.brillo(card);
    fx.burst(x, y, cel.ingreso ? 18 : 28, cel.ingreso ? ['#34d399', '#22d3ee', '#67e8f9', '#a855f7'] : FX_COLORES);
    fx.flotar(card, (cel.ingreso ? '+' : '−') + soles(cel.monto), cel.ingreso);
  }
}

async function renderBannerCierre() {
  const { fecha, hora } = ahora();
  const hh = Number(hora.slice(0, 2));
  let objetivo = null;
  if (hh >= 22) objetivo = fecha;
  else if (hh < 4) objetivo = addDays(fecha, -1);
  const box = $('#banner-cierre');
  if (!objetivo || await DB.get('registros', 'cierre_' + objetivo)) { box.innerHTML = ''; return; }
  box.innerHTML = `<div class="banner"><span>Aún no haces el cierre del ${esc(fFecha(objetivo))}.</span>
    <button class="btn primary">Hacerlo</button></div>`;
  box.querySelector('button').onclick = () => { $('#cierre-fecha').value = objetivo; irA('cierre'); };
}

function renderListaRegistros(ul, lista, refrescar, resaltarId) {
  if (!lista.length) { ul.innerHTML = '<li class="empty">Sin registros</li>'; return; }
  ul.innerHTML = lista.map(r => {
    if (r.tipo === 'ingreso') return `<li data-id="${r.id}"><div class="main"><b>Ingreso · ${esc(label(FUENTES, r.fuente))}</b>
      <small>${esc(r.nota || '')}</small></div><span class="amt in">+${soles(r.monto)}</span>
      <div class="acts"><button data-a="edit" aria-label="Editar">✎</button><button data-a="del" aria-label="Borrar">🗑</button></div></li>`;
    if (r.tipo === 'cierre_dia') return `<li data-id="${r.id}"><div class="main"><b>Cierre del día</b>
      <small>Sueño ${r.sueno?.horas ?? '–'} h · energía ${r.energia ?? '–'} · ánimo ${r.animo ?? '–'}</small></div>
      <div class="acts"><button data-a="edit" aria-label="Editar">✎</button><button data-a="del" aria-label="Borrar">🗑</button></div></li>`;
    return `<li data-id="${r.id}"><div class="main"><b>${esc(r.item)}</b>
      <small>${esc(r.hora || 'sin hora')} · <span class="tag ${JUNK.includes(r.categoria) ? 'junk' : ''}">${esc(label(CATEGORIAS, r.categoria))}</span>${esc(label(MOTIVOS, r.motivo) || '')}${r.planificado ? ' · planificado' : ''}</small></div>
      <span class="amt">${soles(r.monto)}</span>
      <div class="acts"><button data-a="edit" aria-label="Editar">✎</button><button data-a="del" aria-label="Borrar">🗑</button></div></li>`;
  }).join('');
  if (resaltarId) ul.querySelector(`li[data-id="${resaltarId}"]`)?.classList.add('nuevo');
  ul.onclick = async e => {
    const b = e.target.closest('button[data-a]');
    if (!b) return;
    const r = lista.find(x => x.id === b.closest('li').dataset.id);
    if (b.dataset.a === 'del') {
      const que = r.tipo === 'gasto' ? `"${r.item}" (${soles(r.monto)})` : r.tipo === 'ingreso' ? 'este ingreso' : 'este cierre del día';
      if (await confirmar(`¿Borrar ${que}?`)) { await DB.del('registros', r.id); aviso('Borrado'); refrescar(); }
    } else if (r.tipo === 'gasto') abrirGasto(null, r, refrescar);
    else if (r.tipo === 'ingreso') abrirIngreso(r, refrescar);
    else { cerrarHoja(); $('#cierre-fecha').value = r.fecha; irA('cierre'); }
  };
}

function abrirGasto(preset, existente, alGuardar, fechaDia) {
  const n = ahora();
  const pasado = !existente && fechaDia && fechaDia !== n.fecha;
  const r = existente ? { ...existente } : {
    item: preset?.item || '', monto: preset?.monto ?? null, categoria: preset?.categoria || null,
    motivo: null, planificado: false, lugar: '', nota: '',
    fecha: fechaDia || n.fecha, hora: pasado ? '' : n.hora
  };
  const camposFecha = `<div class="two" style="margin-top:14px">
        <div><label class="lbl">Fecha</label><input type="date" class="input date" id="g-fecha" value="${r.fecha}"></div>
        <div><label class="lbl">Hora ${pasado ? '<span class="muted">(opcional)</span>' : ''}</label><input type="time" class="input date" id="g-hora" value="${r.hora || ''}"></div>
      </div>`;
  const formularioCompleto = !preset;
  const titulo = existente ? 'Editar gasto' : (preset ? preset.item : 'Nuevo gasto');
  const lugaresChips = LUGARES.map(l => [l, l]);
  const html = `
    <h3>${esc(titulo)}</h3>
    ${pasado ? `<div class="dia-pasado">📅 Registrando para el <b>${esc(fFecha(r.fecha))}</b></div>` : ''}
    <input class="input monto" id="g-monto" inputmode="decimal" placeholder="0.00" value="${r.monto ?? ''}">
    ${formularioCompleto ? `
      <label class="lbl">¿Qué compraste?</label>
      <input class="input" id="g-item" value="${esc(r.item)}" placeholder="menú, recarga, cuaderno…">
      <label class="lbl">Categoría</label>${chipsHTML(CATEGORIAS, r.categoria, 'cat', 'sm')}` : ''}
    <label class="lbl">¿Por qué?</label>${chipsHTML(MOTIVOS, r.motivo, 'motivo')}
    <label class="lbl">¿Planificado?</label>
    <div class="toggle" id="g-plan"><button type="button" data-v="1" class="${r.planificado ? 'on' : ''}">Sí</button>
      <button type="button" data-v="0" class="no ${r.planificado ? '' : 'on'}">No</button></div>
    <details ${existente && (r.lugar || r.nota) ? 'open' : ''}><summary>Más opciones (lugar, nota${pasado ? '' : ', fecha'}${formularioCompleto ? '' : ', categoría'})</summary>
      ${formularioCompleto ? '' : `<label class="lbl">Categoría</label>${chipsHTML(CATEGORIAS, r.categoria, 'cat', 'sm')}`}
      <label class="lbl">Lugar</label>${chipsHTML(lugaresChips, r.lugar, 'lugar', 'sm')}
      <input class="input" id="g-lugar" value="${esc(r.lugar)}" placeholder="u otro lugar" style="margin-top:6px">
      <label class="lbl">Nota</label><input class="input" id="g-nota" value="${esc(r.nota)}">
      ${pasado ? '' : camposFecha}
    </details>
    ${pasado ? camposFecha : ''}
    <button class="btn primary full big" id="g-guardar">GUARDAR</button>`;
  abrirHoja(html, root => {
    bindChips(root, 'motivo', v => { r.motivo = v; });
    bindChips(root, 'cat', v => { r.categoria = v; });
    bindChips(root, 'lugar', v => { r.lugar = v; root.querySelector('#g-lugar').value = v; });
    root.querySelector('#g-plan').onclick = e => {
      const b = e.target.closest('button'); if (!b) return;
      r.planificado = b.dataset.v === '1';
      root.querySelectorAll('#g-plan button').forEach(x => x.classList.toggle('on', x === b));
    };
    if (r.monto == null) setTimeout(() => root.querySelector('#g-monto').focus(), 250);
    root.querySelector('#g-guardar').onclick = async () => {
      const monto = parseMonto(root.querySelector('#g-monto').value);
      const item = formularioCompleto ? root.querySelector('#g-item').value.trim() : r.item;
      let ok = true;
      const marcar = (el, cond) => { el.classList.toggle('err', !cond); if (!cond) ok = false; };
      marcar(root.querySelector('#g-monto'), monto);
      if (formularioCompleto) marcar(root.querySelector('#g-item'), item);
      marcar(root.querySelector('[data-chips="motivo"]'), r.motivo);
      if (!r.categoria) {
        if (!formularioCompleto) root.querySelector('details').open = true;
        marcar(root.querySelector('[data-chips="cat"]'), false);
      }
      if (!ok) { aviso('Completa lo marcado en rojo'); return; }
      const gasto = {
        id: existente?.id || uuid(), tipo: 'gasto',
        fecha: root.querySelector('#g-fecha').value || r.fecha,
        hora: root.querySelector('#g-hora').value || (pasado ? null : r.hora),
        monto, item, categoria: r.categoria, planificado: r.planificado, motivo: r.motivo,
        lugar: root.querySelector('#g-lugar').value.trim() || null,
        nota: root.querySelector('#g-nota').value.trim() || null,
        creado_en: existente?.creado_en || new Date().toISOString()
      };
      if (existente) gasto.editado_en = new Date().toISOString();
      await DB.put('registros', gasto);
      fx.exito();
      if (!existente && !alGuardar) celebrar = { id: gasto.id, monto, ingreso: false };
      cerrarHoja();
      if (existente) aviso('Actualizado');
      else aviso(`Guardado${gasto.fecha !== n.fecha ? ' en ' + fFecha(gasto.fecha) : ''} · ${soles(monto)}`, 'Deshacer', async () => {
        await DB.del('registros', gasto.id); aviso('Deshecho'); (alGuardar || refrescarVista)();
      }, 5000);
      (alGuardar || refrescarVista)();
    };
  });
}

function abrirIngreso(existente, alGuardar, fechaDia) {
  const r = existente ? { ...existente } : { monto: null, fuente: null, nota: '', fecha: fechaDia || hoy() };
  const pasado = !existente && r.fecha !== hoy();
  abrirHoja(`
    <h3>${existente ? 'Editar ingreso' : 'Registrar ingreso'}</h3>
    ${pasado ? `<div class="dia-pasado">📅 Registrando para el <b>${esc(fFecha(r.fecha))}</b></div>` : ''}
    <input class="input monto" id="i-monto" inputmode="decimal" placeholder="0.00" value="${r.monto ?? ''}">
    <label class="lbl">Fuente</label>${chipsHTML(FUENTES, r.fuente, 'fuente')}
    <label class="lbl">Fecha</label><input type="date" class="input date" id="i-fecha" value="${r.fecha}">
    <label class="lbl">Nota</label><input class="input" id="i-nota" value="${esc(r.nota)}">
    <button class="btn primary full big" id="i-guardar">GUARDAR</button>`, root => {
    bindChips(root, 'fuente', v => { r.fuente = v; });
    if (!existente) setTimeout(() => root.querySelector('#i-monto').focus(), 250);
    root.querySelector('#i-guardar').onclick = async () => {
      const monto = parseMonto(root.querySelector('#i-monto').value);
      root.querySelector('#i-monto').classList.toggle('err', !monto);
      root.querySelector('[data-chips="fuente"]').classList.toggle('err', !r.fuente);
      if (!monto || !r.fuente) { aviso('Completa lo marcado en rojo'); return; }
      const idIng = existente?.id || uuid();
      fx.exito();
      if (!existente && !alGuardar) celebrar = { id: idIng, monto, ingreso: true };
      await DB.put('registros', {
        id: idIng, tipo: 'ingreso', fecha: root.querySelector('#i-fecha').value || r.fecha,
        monto, fuente: r.fuente, nota: root.querySelector('#i-nota').value.trim() || null,
        creado_en: existente?.creado_en || new Date().toISOString()
      });
      cerrarHoja();
      aviso(existente ? 'Actualizado' : `Ingreso guardado · ${soles(monto)}`);
      (alGuardar || refrescarVista)();
    };
  });
}

// ---------- CIERRE DEL DÍA ----------
function cierreVacio(fecha) {
  return {
    id: 'cierre_' + fecha, tipo: 'cierre_dia', fecha,
    sueno: { hora_dormir_anoche: '', hora_despertar: '', horas: null, calidad: null },
    energia: null, animo: null,
    comidas: { desayuno: null, almuerzo: null, cena: null },
    gaseosas: 0, vasos_agua: 0,
    tiempo_min: Object.fromEntries(TIEMPOS.map(([k]) => [k, null])),
    puntual_trabajo: null, sintomas: '', logro_del_dia: '', que_salio_mal: '', nota: ''
  };
}

async function renderCierre(fecha) {
  $('#cierre-fecha').value = fecha;
  const existente = await DB.get('registros', 'cierre_' + fecha);
  const c = existente ? structuredClone(existente) : cierreVacio(fecha);
  $('#cierre-estado').textContent = existente
    ? `Editando el cierre del ${fFecha(fecha)} (guardado ${new Date(existente.completado_en).toLocaleString('es-PE', { timeZone: TZ, hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' })}).`
    : `Nuevo cierre para el ${fFecha(fecha)}.`;

  const escala = (name, val) => `<div class="scale" data-scale="${name}">${[1, 2, 3, 4, 5].map(n =>
    `<button type="button" class="${val === n ? 'on' : ''}" data-v="${n}">${n}</button>`).join('')}</div>`;
  const stepper = (name, val) => `<div class="stepper" data-step="${name}"><button type="button" data-d="-1">−</button>
    <output>${val}</output><button type="button" data-d="1">+</button></div>`;

  const form = $('#cierre-form');
  form.innerHTML = `
    <div class="bloque"><h4>Sueño</h4>
      <div class="two">
        <div><label class="lbl">Dormí anoche</label><input type="time" class="input date" id="c-dormir" value="${c.sueno.hora_dormir_anoche || ''}"></div>
        <div><label class="lbl">Desperté</label><input type="time" class="input date" id="c-despertar" value="${c.sueno.hora_despertar || ''}"></div>
      </div>
      <div class="dur" id="c-horas"></div>
      <label class="lbl">Calidad del sueño</label>${escala('calidad', c.sueno.calidad)}
    </div>
    <div class="bloque"><h4>Cuerpo</h4>
      <label class="lbl">Energía</label>${escala('energia', c.energia)}
      <label class="lbl">Ánimo</label>${escala('animo', c.animo)}
      <label class="lbl">Comidas</label>
      ${['desayuno', 'almuerzo', 'cena'].map(k => `<div class="comida-row"><span>${k[0].toUpperCase() + k.slice(1)}</span>${chipsHTML(COMIDAS, c.comidas[k], 'com-' + k, 'sm')}</div>`).join('')}
      <div class="two" style="margin-top:10px">
        <div><label class="lbl">Gaseosas</label>${stepper('gaseosas', c.gaseosas)}</div>
        <div><label class="lbl">Vasos de agua</label>${stepper('vasos_agua', c.vasos_agua)}</div>
      </div>
      <label class="lbl">Síntomas (opcional)</label>
      <input class="input" id="c-sintomas" value="${esc(c.sintomas)}" placeholder="ej: mareo en la tarde">
    </div>
    <div class="bloque"><h4>Tiempo (minutos)</h4>
      ${TIEMPOS.map(([k, l]) => `<div class="tiempo"><label class="lbl">${l}${k === 'pantalla_celular' ? ' <span class="muted">· de Bienestar digital</span>' : ''}</label>
        <div class="row">${TIEMPO_PRESETS.map(m => `<button type="button" class="chip sm ${c.tiempo_min[k] === m ? 'on' : ''}" data-t="${k}" data-v="${m}">${m}</button>`).join('')}
        <input class="input" type="number" inputmode="numeric" min="0" id="t-${k}" value="${c.tiempo_min[k] ?? ''}" placeholder="min"></div></div>`).join('')}
      <label class="lbl">¿Llegué puntual al trabajo?</label>
      ${chipsHTML([['si', 'Sí'], ['no', 'No'], ['no_aplica', 'No aplica']], c.puntual_trabajo, 'puntual')}
    </div>
    <div class="bloque"><h4>Reflexión</h4>
      <label class="lbl">Logro del día</label><input class="input" id="c-logro" value="${esc(c.logro_del_dia)}" maxlength="200">
      <label class="lbl">Qué salió mal</label><input class="input" id="c-mal" value="${esc(c.que_salio_mal)}" maxlength="200">
      <label class="lbl">Nota (opcional)</label><textarea class="input" id="c-nota">${esc(c.nota)}</textarea>
    </div>
    <button type="submit" class="btn primary full big">${existente ? 'ACTUALIZAR CIERRE' : 'GUARDAR CIERRE'}</button>
    ${existente ? '<button type="button" class="btn danger full" id="c-borrar">Borrar este cierre</button>' : ''}`;

  const actualizarHoras = () => {
    const h = horasSueno(form.querySelector('#c-dormir').value, form.querySelector('#c-despertar').value);
    const el = form.querySelector('#c-horas');
    el.textContent = h == null ? '' : `${h} h de sueño`;
    el.classList.toggle('low', h != null && h < 6.5);
  };
  form.querySelector('#c-dormir').oninput = actualizarHoras;
  form.querySelector('#c-despertar').oninput = actualizarHoras;
  actualizarHoras();

  form.querySelectorAll('[data-scale]').forEach(box => box.onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    const v = Number(b.dataset.v);
    box.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b));
    if (box.dataset.scale === 'calidad') c.sueno.calidad = v; else c[box.dataset.scale] = v;
  });
  ['desayuno', 'almuerzo', 'cena'].forEach(k => bindChips(form, 'com-' + k, v => { c.comidas[k] = v; }));
  bindChips(form, 'puntual', v => { c.puntual_trabajo = v; });
  form.querySelectorAll('[data-step]').forEach(box => box.onclick = e => {
    const b = e.target.closest('button'); if (!b) return;
    const k = box.dataset.step;
    c[k] = Math.max(0, c[k] + Number(b.dataset.d));
    box.querySelector('output').textContent = c[k];
  });
  form.querySelectorAll('[data-t]').forEach(b => b.onclick = () => {
    const k = b.dataset.t;
    form.querySelector('#t-' + k).value = b.dataset.v;
    form.querySelectorAll(`[data-t="${k}"]`).forEach(x => x.classList.toggle('on', x === b));
  });
  TIEMPOS.forEach(([k]) => form.querySelector('#t-' + k).oninput = e => {
    form.querySelectorAll(`[data-t="${k}"]`).forEach(x => x.classList.toggle('on', x.dataset.v === e.target.value));
  });

  const borrar = form.querySelector('#c-borrar');
  if (borrar) borrar.onclick = async () => {
    if (await confirmar(`¿Borrar el cierre del ${fFecha(fecha)}?`)) {
      await DB.del('registros', c.id); aviso('Cierre borrado'); renderCierre(fecha);
    }
  };

  form.onsubmit = async e => {
    e.preventDefault();
    const dormir = form.querySelector('#c-dormir').value;
    const despertar = form.querySelector('#c-despertar').value;
    c.sueno.hora_dormir_anoche = dormir || null;
    c.sueno.hora_despertar = despertar || null;
    c.sueno.horas = horasSueno(dormir, despertar);
    TIEMPOS.forEach(([k]) => {
      const v = form.querySelector('#t-' + k).value;
      c.tiempo_min[k] = v === '' ? null : Math.max(0, parseInt(v, 10) || 0);
    });
    c.sintomas = form.querySelector('#c-sintomas').value.trim() || null;
    c.logro_del_dia = form.querySelector('#c-logro').value.trim() || null;
    c.que_salio_mal = form.querySelector('#c-mal').value.trim() || null;
    c.nota = form.querySelector('#c-nota').value.trim() || null;
    c.completado_en = new Date().toISOString();
    const faltan = [];
    if (c.sueno.horas == null) faltan.push('sueño');
    if (c.energia == null) faltan.push('energía');
    if (c.animo == null) faltan.push('ánimo');
    await DB.put('registros', c);
    const btn = form.querySelector('button[type=submit]');
    const { x, y } = fx.centro(btn);
    fx.burst(x, y, 34);
    fx.exito();
    aviso(faltan.length ? `Guardado (falta: ${faltan.join(', ')})` : 'Cierre guardado', null, null, 3000);
    renderCierre(fecha);
  };
}

// ---------- HISTORIAL ----------
async function renderHistorial() {
  const h = hoy();
  const desde7 = addDays(h, -6);
  const todos = await DB.all('registros');
  const ult7 = todos.filter(r => r.fecha >= desde7 && r.fecha <= h);
  const s = resumen(ult7, desde7, h);
  $('#resumen7').innerHTML = `<div class="stats">
    <div class="stat"><small>Gasto total</small><b>${soles(s.gasto_total)}</b></div>
    <div class="stat"><small>Promedio diario</small><b>${soles(s.gasto_promedio_diario)}</b></div>
    <div class="stat"><small>Chatarra + bebida</small><b>${s.chatarra_bebida_pct}%</b> <span class="muted">${soles(s.chatarra_bebida_total)}</span></div>
    <div class="stat"><small>No planificados</small><b>${s.no_planificados_pct}%</b></div>
    <div class="stat"><small>Motivo más frecuente</small><b>${s.motivo_mas_frecuente ? esc(label(MOTIVOS, s.motivo_mas_frecuente)) : '–'}</b></div>
    <div class="stat"><small>Sueño promedio</small><b class="${s.sueno_promedio_h != null && s.sueno_promedio_h < 6.5 ? 'low' : ''}">${s.sueno_promedio_h ?? '–'} h</b></div>
    <div class="stat"><small>Días registrados</small><b>${s.dias_registrados} de 7</b></div>
    <div class="stat"><small>Cierres hechos</small><b>${s.dias_con_cierre} de 7</b></div></div>`;

  // Gráfico de barras SVG: chatarra+bebida vs resto
  const dias = Array.from({ length: 7 }, (_, i) => addDays(desde7, i));
  const datos = dias.map(f => {
    const g = ult7.filter(r => r.tipo === 'gasto' && r.fecha === f);
    const junk = g.filter(x => JUNK.includes(x.categoria)).reduce((a, x) => a + x.monto, 0);
    const resto = g.reduce((a, x) => a + x.monto, 0) - junk;
    return { f, junk, resto };
  });
  const max = Math.max(10, ...datos.map(d => d.junk + d.resto));
  const W = 320, H = 170, pb = 22, pt = 16, bw = 30, gap = (W - 7 * bw) / 8;
  const y = v => (H - pb) - v / max * (H - pb - pt);
  const bars = datos.map((d, i) => {
    const x = gap + i * (bw + gap);
    const total = d.junk + d.resto;
    return `<rect x="${x}" y="${y(d.resto)}" width="${bw}" height="${(H - pb) - y(d.resto)}" rx="3" fill="#22d3ee"/>
      <rect x="${x}" y="${y(total)}" width="${bw}" height="${y(d.resto) - y(total)}" rx="3" fill="#f472b6"/>
      ${total ? `<text x="${x + bw / 2}" y="${y(total) - 4}" text-anchor="middle" font-size="9" fill="#a99cc8">${Math.round(total)}</text>` : ''}
      <text x="${x + bw / 2}" y="${H - 6}" text-anchor="middle" font-size="10" fill="${d.f === h ? '#f5f3ff' : '#a99cc8'}">${DIAS[dow(d.f)]}</text>`;
  }).join('');
  $('#grafico').innerHTML = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Gasto por día">
    <line x1="0" x2="${W}" y1="${H - pb}" y2="${H - pb}" stroke="#34245a"/>${bars}</svg>
    <div class="legend"><span><i style="background:#f472b6"></i>Chatarra + bebida</span><span><i style="background:#22d3ee"></i>Resto</span></div>`;

  // Lista de días
  const porDia = {};
  todos.forEach(r => { (porDia[r.fecha] = porDia[r.fecha] || []).push(r); });
  const fechas = [...new Set([...Object.keys(porDia).filter(f => f <= h), ...dias])].sort().reverse();
  const ul = $('#dias-lista');
  ul.innerHTML = fechas.map(f => {
    const rs = porDia[f] || [];
    if (!rs.length) return `<li class="tap vacio" data-f="${f}"><div class="main"><b>${fFecha(f)}${f === h ? ' · hoy' : ''}</b>
      <small><span class="tag bad">sin registros</span></small></div><span class="amt muted">＋</span></li>`;
    const g = rs.filter(r => r.tipo === 'gasto');
    const tot = g.reduce((a, x) => a + x.monto, 0);
    const junk = g.filter(x => JUNK.includes(x.categoria)).reduce((a, x) => a + x.monto, 0);
    const c = rs.find(r => r.tipo === 'cierre_dia');
    const hs = c?.sueno?.horas;
    return `<li class="tap" data-f="${f}"><div class="main"><b>${fFecha(f)}${f === h ? ' · hoy' : ''}</b>
      <small><span class="tag junk">chatarra ${soles(junk)}</span>${hs != null ? `<span class="tag ${hs < 6.5 ? 'bad' : ''}">${hs} h</span>` : ''}<span class="tag ${c ? 'ok' : 'bad'}">${c ? 'cierre ✓' : 'sin cierre'}</span></small></div>
      <span class="amt">${soles(tot)}</span></li>`;
  }).join('');
  ul.onclick = e => { const li = e.target.closest('li[data-f]'); if (li) abrirDia(li.dataset.f); };
  const otro = $('#otro-dia');
  otro.max = h;
  otro.onchange = () => { if (otro.value && otro.value <= h) abrirDia(otro.value); otro.value = ''; };
}

async function abrirDia(fecha) {
  const regs = (await DB.rango(fecha, fecha)).sort((a, b) =>
    (a.tipo === 'cierre_dia') - (b.tipo === 'cierre_dia') || (a.hora || '').localeCompare(b.hora || ''));
  const tot = regs.filter(r => r.tipo === 'gasto').reduce((a, x) => a + x.monto, 0);
  const ing = regs.filter(r => r.tipo === 'ingreso').reduce((a, x) => a + x.monto, 0);
  const tieneCierre = regs.some(r => r.tipo === 'cierre_dia');
  const presets = await getPresets();
  abrirHoja(`<h3>${fFecha(fecha)} · ${soles(tot)}${ing ? ` <span class="in-txt">+${soles(ing)}</span>` : ''}</h3>
    <ul class="lista" id="dia-lista"></ul>
    <label class="lbl">Agregar a este día</label>
    <div class="grid mini" id="dia-presets">
      ${presets.map(p => `<button class="preset ${JUNK.includes(p.categoria) ? 'junk' : ''}" data-id="${p.id}"><b>${esc(p.item)}</b><i>${p.monto ? soles(p.monto) : 'libre'}</i></button>`).join('')}
      <button class="preset otro" data-id="otro"><b>Otro</b><i>gasto</i></button>
      <button class="preset ingreso" data-id="ingreso"><b>Ingreso</b><i>+ dinero</i></button>
    </div>
    <button class="btn ${tieneCierre ? 'secondary' : 'primary'} full" id="dia-cierre">${tieneCierre ? 'Ver cierre del día' : 'Terminar este día (cierre)'}</button>`, root => {
    const refrescar = async () => { await renderHistorial(); abrirDia(fecha); };
    renderListaRegistros(root.querySelector('#dia-lista'), regs, refrescar);
    root.querySelector('#dia-presets').onclick = e => {
      const b = e.target.closest('.preset');
      if (!b) return;
      fx.haptic();
      if (b.dataset.id === 'ingreso') abrirIngreso(null, refrescar, fecha);
      else if (b.dataset.id === 'otro') abrirGasto(null, null, refrescar, fecha);
      else abrirGasto(presets.find(p => p.id === b.dataset.id), null, refrescar, fecha);
    };
    root.querySelector('#dia-cierre').onclick = () => { cerrarHoja(); $('#cierre-fecha').value = fecha; irA('cierre'); };
  });
}

// ---------- EXPORTAR / IMPORTAR ----------
function renderExportar() {
  const h = hoy();
  if (!$('#exp-hasta').value) $('#exp-hasta').value = h;
  if (!$('#exp-desde').value) $('#exp-desde').value = addDays(h, -6);
}

function construirExport(regs, desde, hasta, extra = {}) {
  const orden = (a, b) => a.fecha.localeCompare(b.fecha) || (a.hora || '').localeCompare(b.hora || '') ||
    (a.creado_en || '').localeCompare(b.creado_en || '');
  return {
    app: APP,
    schema_version: SCHEMA,
    destino: 'NEXOR IA',
    exportado_en: new Date().toISOString(),
    zona_horaria: TZ,
    moneda: 'PEN',
    rango: { desde, hasta },
    resumen: resumen(regs, desde, hasta),
    gastos: regs.filter(r => r.tipo === 'gasto').sort(orden),
    ingresos: regs.filter(r => r.tipo === 'ingreso').sort(orden),
    cierres_dia: regs.filter(r => r.tipo === 'cierre_dia').sort(orden),
    ...extra
  };
}

function csvGastos(gastos) {
  const cols = ['fecha', 'hora', 'monto', 'item', 'categoria', 'planificado', 'motivo', 'lugar', 'nota'];
  const cel = v => {
    let s = v == null ? '' : typeof v === 'boolean' ? (v ? 'si' : 'no') : typeof v === 'number' ? v.toFixed(2) : String(v);
    return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return '﻿' + [cols.join(','), ...gastos.map(g => cols.map(c => cel(g[c])).join(','))].join('\r\n') + '\r\n';
}

async function compartirArchivo(nombre, contenido, mime) {
  const cap = window.Capacitor;
  const P = cap?.Plugins;
  if (cap?.isNativePlatform?.() && P?.Filesystem && P?.Share) {
    const w = await P.Filesystem.writeFile({ path: nombre, data: contenido, directory: 'CACHE', encoding: 'utf8' });
    try { await P.Share.share({ title: nombre, files: [w.uri], dialogTitle: 'Enviar ' + nombre }); }
    catch (e) { if (!/cancel/i.test(String(e?.message))) throw e; }
    return;
  }
  const file = new File([contenido], nombre, { type: mime });
  if (navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file], title: nombre }); return; }
    catch (e) { if (e.name === 'AbortError') return; }
  }
  const a = document.createElement('a');
  a.href = URL.createObjectURL(file);
  a.download = nombre;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 1000);
}

function rangoElegido() {
  let d = $('#exp-desde').value, h = $('#exp-hasta').value;
  if (!d || !h) { aviso('Elige el rango de fechas'); return null; }
  if (d > h) [d, h] = [h, d];
  return [d, h];
}

async function exportarJSON() {
  const rg = rangoElegido(); if (!rg) return;
  const regs = await DB.rango(rg[0], rg[1]);
  const data = construirExport(regs, rg[0], rg[1]);
  await compartirArchivo(`nexor_register_${rg[0]}_a_${rg[1]}.json`, JSON.stringify(data, null, 2), 'application/json');
  $('#exp-info').textContent = `JSON: ${data.gastos.length} gastos, ${data.ingresos.length} ingresos, ${data.cierres_dia.length} cierres.`;
}
async function exportarCSV() {
  const rg = rangoElegido(); if (!rg) return;
  const g = (await DB.rango(rg[0], rg[1])).filter(r => r.tipo === 'gasto')
    .sort((a, b) => a.fecha.localeCompare(b.fecha) || (a.hora || '').localeCompare(b.hora || '') || (a.creado_en || '').localeCompare(b.creado_en || ''));
  await compartirArchivo(`nexor_register_gastos_${rg[0]}_a_${rg[1]}.csv`, csvGastos(g), 'text/csv');
  $('#exp-info').textContent = `CSV: ${g.length} gastos.`;
}
async function exportarTodo() {
  const regs = await DB.all('registros');
  const fechas = regs.map(r => r.fecha).sort();
  const desde = fechas[0] || hoy(), hasta = fechas[fechas.length - 1] || hoy();
  const data = construirExport(regs, desde, hasta, { respaldo_completo: true, presets: await getPresets() });
  await compartirArchivo(`nexor_register_respaldo_${hoy()}.json`, JSON.stringify(data, null, 2), 'application/json');
  $('#exp-info').textContent = `Respaldo: ${regs.length} registros.`;
}
async function importar(file) {
  let data;
  try { data = JSON.parse(await file.text()); } catch { aviso('El archivo no es un JSON válido'); return; }
  const regs = [...(data.gastos || []), ...(data.ingresos || []), ...(data.cierres_dia || [])]
    .filter(r => r && r.id && r.fecha && ['gasto', 'ingreso', 'cierre_dia'].includes(r.tipo));
  if (!regs.length && !data.presets) { aviso('No encontré registros en ese archivo'); return; }
  const existentes = new Set((await DB.all('registros')).map(r => r.id));
  const nuevos = regs.filter(r => !existentes.has(r.id));
  await DB.putMany('registros', nuevos);
  let msgP = '';
  if (Array.isArray(data.presets) && data.presets.length) {
    const act = await getPresets();
    const ids = new Set(act.map(p => p.id));
    const nombres = new Set(act.map(p => p.item.trim().toLowerCase()));
    const np = data.presets
      .filter(p => p.id && p.item && !ids.has(p.id) && !nombres.has(p.item.trim().toLowerCase()))
      .map((p, i) => ({ ...p, orden: act.length + i }));
    if (np.length) { await DB.putMany('presets', np); msgP = `, ${np.length} botones`; }
  }
  const msg = `Importados ${nuevos.length} registros nuevos${msgP} (${regs.length - nuevos.length} ya existían).`;
  $('#exp-info').textContent = msg;
  aviso('Importación lista', null, null, 3000);
}

// ---------- AJUSTES ----------
async function renderAjustes() {
  const presets = await getPresets();
  const ul = $('#presets-edit');
  ul.innerHTML = presets.length ? presets.map((p, i) => `<li data-id="${p.id}"><div class="main"><b>${esc(p.item)}</b>
    <small>${p.monto ? soles(p.monto) : 'monto libre'} · ${esc(label(CATEGORIAS, p.categoria))}</small></div>
    <div class="acts"><button data-a="up" ${i === 0 ? 'disabled' : ''} aria-label="Subir">↑</button>
    <button data-a="down" ${i === presets.length - 1 ? 'disabled' : ''} aria-label="Bajar">↓</button>
    <button data-a="edit" aria-label="Editar">✎</button><button data-a="del" aria-label="Borrar">🗑</button></div></li>`).join('')
    : '<li class="empty">Sin botones</li>';
  ul.onclick = async e => {
    const b = e.target.closest('button[data-a]'); if (!b) return;
    const i = presets.findIndex(p => p.id === b.closest('li').dataset.id);
    const p = presets[i];
    if (b.dataset.a === 'up' || b.dataset.a === 'down') {
      const j = b.dataset.a === 'up' ? i - 1 : i + 1;
      [presets[i], presets[j]] = [presets[j], presets[i]];
      await DB.putMany('presets', presets.map((x, k) => ({ ...x, orden: k })));
      renderAjustes();
    } else if (b.dataset.a === 'edit') abrirPreset(p);
    else if (await confirmar(`¿Quitar el botón "${p.item}"?`, 'Quitar')) { await DB.del('presets', p.id); renderAjustes(); }
  };

  const info = $('#storage-info');
  let txt = '';
  if (navigator.storage?.persisted) txt += (await navigator.storage.persisted()) ? 'Almacenamiento persistente: activado. ' : 'Almacenamiento persistente: no confirmado. ';
  const n = (await DB.all('registros')).length;
  txt += `Registros guardados: ${n}.`;
  info.textContent = txt;
}

function abrirPreset(p) {
  const r = p ? { ...p } : { item: '', monto: null, categoria: null };
  abrirHoja(`<h3>${p ? 'Editar botón' : 'Nuevo botón'}</h3>
    <label class="lbl">Nombre</label><input class="input" id="p-item" value="${esc(r.item)}" maxlength="30">
    <label class="lbl">Monto (vacío = monto libre)</label><input class="input" id="p-monto" inputmode="decimal" value="${r.monto ?? ''}">
    <label class="lbl">Categoría</label>${chipsHTML(CATEGORIAS, r.categoria, 'pcat', 'sm')}
    <button class="btn primary full big" id="p-guardar">GUARDAR</button>`, root => {
    bindChips(root, 'pcat', v => { r.categoria = v; });
    root.querySelector('#p-guardar').onclick = async () => {
      const item = root.querySelector('#p-item').value.trim();
      const montoTxt = root.querySelector('#p-monto').value.trim();
      const monto = montoTxt ? parseMonto(montoTxt) : null;
      root.querySelector('#p-item').classList.toggle('err', !item);
      root.querySelector('#p-monto').classList.toggle('err', !!montoTxt && !monto);
      root.querySelector('[data-chips="pcat"]').classList.toggle('err', !r.categoria);
      if (!item || (montoTxt && !monto) || !r.categoria) { aviso('Completa lo marcado en rojo'); return; }
      const orden = p ? p.orden : (await getPresets()).length;
      await DB.put('presets', { id: p?.id || uuid(), orden, item, monto, categoria: r.categoria });
      cerrarHoja(); renderAjustes();
    };
  });
}

// ---------- Arranque ----------
function refrescarVista() { irA(vistaActual); }

async function iniciar() {
  await DB.open();
  if (!(await getPresets()).length) await seedPresets();
  if (navigator.storage?.persist) { try { await navigator.storage.persist(); } catch { /* sin soporte */ } }

  document.addEventListener('pointerdown', fx.ripple, { passive: true });
  document.querySelectorAll('.nav button').forEach(b => b.onclick = () => { if (b.dataset.view !== vistaActual) fx.haptic(); irA(b.dataset.view); });
  $('#overlay').onclick = cerrarHoja;
  $('#btn-ingreso').onclick = () => abrirIngreso(null);
  $('#cierre-fecha').onchange = e => { if (e.target.value) renderCierre(e.target.value); };
  $('#btn-json').onclick = () => exportarJSON().catch(err => aviso('Error al exportar: ' + err.message, null, null, 4000));
  $('#btn-csv').onclick = () => exportarCSV().catch(err => aviso('Error al exportar: ' + err.message, null, null, 4000));
  $('#btn-todo').onclick = () => exportarTodo().catch(err => aviso('Error al exportar: ' + err.message, null, null, 4000));
  $('#btn-importar').onclick = () => $('#file-import').click();
  $('#file-import').onchange = async e => { const f = e.target.files[0]; if (f) await importar(f); e.target.value = ''; };
  $('#btn-add-preset').onclick = () => abrirPreset(null);
  $('#btn-reset-presets').onclick = async () => {
    if (await confirmar('¿Reemplazar tus botones por los de fábrica?', 'Restaurar')) { await seedPresets(); renderAjustes(); }
  };

  // Botón "atrás" de Android (plugin @capacitor/app)
  const AppP = window.Capacitor?.Plugins?.App;
  if (AppP?.addListener) {
    AppP.addListener('backButton', () => {
      if ($('#dialog').classList.contains('show')) cerrarDialogo(false);
      else if (sheetOpen) cerrarHoja();
      else if (vistaActual !== 'registrar') irA('registrar');
      else AppP.exitApp();
    });
  }
  // Al volver a la app, refrescar (cambia el día, aparece el recordatorio de las 22:00)
  document.addEventListener('visibilitychange', () => { if (!document.hidden && !sheetOpen) refrescarVista(); });

  irA('registrar');
}

iniciar().catch(err => {
  document.body.insertAdjacentHTML('afterbegin', `<div class="aviso" style="margin:16px">No se pudo iniciar la base de datos: ${esc(err.message)}</div>`);
});
