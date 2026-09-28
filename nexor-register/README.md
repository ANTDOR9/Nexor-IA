# NEXOR REGISTER

App Android para registrar **cada gasto en 3 toques** y hacer el **cierre del día en menos de 90 segundos**.
Es el módulo de captura de datos de **NEXOR IA**: todo lo que se registra aquí se exporta en un JSON
con un formato estable (`schema_version: 1`) para que en el futuro NEXOR lo lea, lo analice y proponga optimizaciones.

- HTML + CSS + JavaScript puro (sin frameworks), empaquetado a APK con **Capacitor 8** y **Android Studio**.
- Funciona 100 % sin internet. Los datos viven en el celular (IndexedDB dentro de la app).
- Zona horaria `America/Lima`, moneda soles (S/).

## Pantallas

| Pantalla | Qué hace |
|---|---|
| **Registrar** | Total de hoy y de la semana (lun–dom), botones rápidos (papa rellena, gaseosa, pasaje…), "Otro", ingresos y la lista de hoy. Después de guardar aparece *Deshacer* durante 5 s. |
| **Cierre** | Sueño (las horas se calculan solas y se ponen en rojo si son menos de 6.5), energía, ánimo, comidas, gaseosas, agua, tiempos y reflexión. Hay un solo cierre por fecha: si ya existe, se edita. |
| **Historial** | Resumen de los últimos 7 días, un gráfico SVG (chatarra frente al resto) y la lista de días. Cada registro se puede editar o borrar. |
| **Exportar** | JSON por rango (para NEXOR o una IA), CSV de gastos para Excel, respaldo completo e importación sin duplicados. En el APK usa el menú Compartir de Android (WhatsApp, Drive, Archivos…). |
| **Ajustes** | Editar, agregar, reordenar y borrar los botones rápidos. |

Desde las 22:00 (y hasta las 4:00), si no has hecho el cierre, la pantalla Registrar muestra un recordatorio.

## Estructura

```
nexor-register/
├── www/                  ← la app (lo único que editas)
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── docs/NEXOR_DATOS.md   ← contrato de datos para NEXOR IA
├── capacitor.config.json
├── package.json
└── android/              ← lo genera Capacitor (paso 3)
```

## Generar el APK (Windows)

Requisitos: **Node.js 22 o superior** (`node -v`) y Android Studio (ya instalado).

```powershell
cd "C:\Users\ANT DOR\OneDrive\Documentos\GitHub\Nexor-IA\nexor-register"

# 1. Dependencias
npm install

# 2. Crear el proyecto Android (solo la primera vez)
npx cap add android

# 3. Copiar www/ y los plugins al proyecto Android
npx cap sync android

# 4. Abrir en Android Studio
npx cap open android
```

En Android Studio:

1. Espera a que termine el *Gradle Sync* (la primera vez tarda varios minutos).
2. **Probar en tu celular:** activa *Opciones de desarrollador → Depuración USB*, conéctalo por USB y dale a ▶ **Run**.
3. **Generar el APK:** menú **Build → Generate App Bundles or APKs → Generate APKs**.
   El archivo sale en `android/app/build/outputs/apk/debug/app-debug.apk`. Pásalo al celular e instálalo.

**Cada vez que cambies algo en `www/`:** ejecuta `npx cap sync android` y vuelve a darle a Run.

## Identidad visual

- Paleta: morado `#8b5cf6`, rosa `#ec4899`, cian `#22d3ee` sobre fondo `#0b0616`.
- El ícono y la pantalla de inicio salen de `assets/` (las fuentes en SVG están en `assets/src/`).
  Si cambias el diseño, vuelve a generar los recursos de Android con:

```powershell
npx @capacitor/assets generate --android --iconBackgroundColor "#150827" --iconBackgroundColorDark "#150827" --splashBackgroundColor "#0b0616" --splashBackgroundColorDark "#0b0616"
```

> 💡 OneDrive: la carpeta `android/` genera muchos archivos de compilación. Si OneDrive se pone lento
> o bloquea archivos durante la compilación, pausa la sincronización mientras compilas.

### Probar rápido en la PC (sin compilar)

```powershell
npm run serve
```

Abre `http://localhost:8080` en Chrome, pulsa F12 y activa la vista de celular (Ctrl+Shift+M).
Fuera del APK, la exportación descarga el archivo en lugar de abrir el menú Compartir.

## Pruebas antes de usarla en serio

1. Registrar un gasto con un botón rápido en 3 toques (botón → motivo → Guardar).
2. Registrar con el modo avión activado.
3. Cerrar la app por completo (quitarla de recientes), volver a abrirla y ver que los datos siguen ahí.
4. Usar *Deshacer* después de guardar.
5. Usar "Otro" con monto decimal (`12,50` o `12.50`).
6. Hacer el cierre del día y luego volver a abrirlo para editarlo.
7. Borrar un registro desde el Historial (debe pedir confirmación).
8. Exportar JSON y enviarlo por WhatsApp o Drive.
9. Exportar CSV y abrirlo en Excel (las tildes deben verse bien).
10. Exportar TODO e importarlo de nuevo: debe decir "0 registros nuevos" (sin duplicados).
11. Botón atrás de Android: cierra la hoja abierta y luego vuelve a Registrar.

## Respaldo

Los datos se borran si desinstalas la app o borras sus datos desde Ajustes de Android.
**Exporta TODO cada domingo** y guárdalo en Drive.
