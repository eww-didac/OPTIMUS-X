"""Lightweight runtime translation for the Optimus X interface.

The application is written in English and every visible label is passed
through :func:`tr`.  English is the source language and therefore needs no
dictionary; Spanish lives in ``ES``.  Keys are the exact English source
strings (or templates with ``{named}`` placeholders), which keeps the call
sites readable and lets an untranslated label fall back to English instead of
showing a raw identifier.

Only display text is translated.  Internal identifiers, page keys, tweak ids
and filter values stay in English because they are used as logic keys.
"""

from __future__ import annotations

from threading import RLock
from typing import Any

# Language codes shown in Settings.  The labels themselves are intentionally
# native names so they are recognisable regardless of the active language.
LANGUAGES: dict[str, str] = {"en": "English", "es": "Español"}
LANGUAGE_CODES: dict[str, str] = {label: code for code, label in LANGUAGES.items()}

_lock = RLock()
_language = "en"


def get_language() -> str:
    with _lock:
        return _language


def set_language(language: str) -> str:
    """Switch the active language and return the effective code."""

    global _language
    code = (language or "en").lower()
    if code not in LANGUAGES:
        code = "en"
    with _lock:
        _language = code
    return code


def is_spanish() -> bool:
    return get_language() == "es"


def tr(text: str, **values: Any) -> str:
    """Translate ``text`` to the active language.

    Unknown strings are returned unchanged.  Named placeholders are formatted
    after translation so word order can change between languages.
    """

    if not text:
        return text
    if _language == "es":
        text = ES.get(text, text)
    if values:
        try:
            return text.format(**values)
        except (KeyError, IndexError, ValueError):
            return text
    return text


# --------------------------------------------------------------------------- ES
# Spanish translations keyed by the English source string.  Entries are grouped
# by area to make review and maintenance straightforward.
ES: dict[str, str] = {
    # ------------------------------------------------------------------ common
    "Dashboard": "Panel",
    "Tweaks & Privacy": "Ajustes y privacidad",
    "Deep Cleaner": "Limpieza profunda",
    "Game Boost": "Impulso de juego",
    "Toolbox": "Herramientas",
    "Settings": "Configuración",
    "Refresh": "Actualizar",
    "Apply changes": "Aplicar cambios",
    "Discard": "Descartar",
    "Recommended": "Recomendado",
    "Extreme · all": "Extremo · todo",
    "All": "Todo",
    "Services": "Servicios",
    "Kernel": "Núcleo",
    "Network": "Red",
    "Visual": "Visual",
    "Privacy": "Privacidad",
    "Action audit": "Auditoría de acciones",
    "Technical log": "Registro técnico",
    "English": "English",
    "Español": "Español",
    "Create": "Crear",
    "Cancel": "Cancelar",
    "Close": "Cerrar",
    "Confirm": "Confirmar",
    "Not now": "Ahora no",
    "Got it": "Entendido",
    "Continue": "Continuar",
    "Run task": "Ejecutar tarea",
    "Remove": "Quitar",
    "Uninstall": "Desinstalar",
    "Disable": "Desactivar",
    "Re-enable": "Reactivar",
    "Removed": "Eliminado",
    "Restart": "Reiniciar",
    "Activate": "Activar",
    "Deactivate": "Desactivar",
    "Open folder": "Abrir carpeta",
    "Open logs": "Abrir registros",
    "Export report": "Exportar informe",
    "Create point": "Crear punto",
    "Run SFC": "Ejecutar SFC",
    "Run DISM": "Ejecutar DISM",
    "Flush DNS": "Vaciar DNS",
    "Reset network": "Restablecer red",
    "Clean now": "Limpiar ahora",
    "Scan disk": "Analizar disco",
    "Elevated": "Elevado",
    "LIVE": "EN VIVO",
    "IDLE": "INACTIVO",
    "ACTIVE": "ACTIVO",
    "UNAVAILABLE": "NO DISPONIBLE",
    "APPLIED": "APLICADO",
    "OFF": "INACTIVO",
    "STAGED ON": "PENDIENTE: ACTIVAR",
    "STAGED OFF": "PENDIENTE: DESACTIVAR",
    "REBOOT": "REINICIO",
    "SAFE": "SEGURO",
    "ADVANCED": "AVANZADO",
    "EXTREME": "EXTREMO",
    "ADMIN": "ADMIN",
    "ADMINISTRATOR": "ADMINISTRADOR",
    "STANDARD USER": "USUARIO ESTÁNDAR",
    "SYSTEM READY": "SISTEMA LISTO",
    "LOCAL ONLY": "SOLO LOCAL",
    "LOCAL": "LOCAL",
    "Never": "Nunca",
    "Today": "Hoy",
    "READY": "LISTO",
    "PROTECTED": "PROTEGIDO",
    "CHECKING…": "COMPROBANDO…",
    "OPTIONAL": "OPCIONAL",
    "PRESENT": "PRESENTE",
    "DISABLED": "DESACTIVADO",
    "REMOVED": "ELIMINADO",
    # -------------------------------------------------------------- navigation
    "W O R K S P A C E": "E S P A C I O",
    "S Y S T E M   O P T I M I Z E R": "O P T I M I Z A D O R   D E L   S I S T E M A",
    "STANDARD USER": "USUARIO ESTÁNDAR",
    "ADMINISTRATOR": "ADMINISTRADOR",
    "DRY RUN MODE": "MODO DE PRUEBA",
    # --------------------------------------------------------------- categories
    "WINDOWS SERVICES": "SERVICIOS DE WINDOWS",
    "REGISTRY & KERNEL": "REGISTRO Y NÚCLEO",
    "NETWORK & LATENCY": "RED Y LATENCIA",
    "VISUAL & DWM": "VISUAL Y DWM",
    "PRIVACY & TELEMETRY": "PRIVACIDAD Y TELEMETRÍA",
    "SYSTEM COMPONENTS": "COMPONENTES DEL SISTEMA",
    # -------------------------------------------------------------------- tweaks
    "Disable SysMain (SuperFetch)": "Desactivar SysMain (SuperFetch)",
    "Stops background app precaching. Saves RAM and reduces unnecessary SSD writes.": (
        "Detiene la precarga de aplicaciones en segundo plano. Ahorra RAM y reduce "
        "escrituras innecesarias en el SSD."
    ),
    "Apps may open a little slower right after a reboot.": (
        "Las aplicaciones pueden abrirse algo más lentas justo después de reiniciar."
    ),
    "Disable Windows Search Indexing": "Desactivar la indexación de Windows Search",
    "Stops the file indexer from scanning drives in the background while you play.": (
        "Detiene el indexador de archivos para que no analice las unidades en segundo "
        "plano mientras juegas."
    ),
    "Start-menu and File Explorer searches become slower.": (
        "Las búsquedas del menú Inicio y del Explorador serán más lentas."
    ),
    "Disable Telemetry & Diagnostics": "Desactivar telemetría y diagnósticos",
    "Stops DiagTrack and the WAP push service, and applies the diagnostic data policy.": (
        "Detiene DiagTrack y el servicio de notificaciones WAP, y aplica la directiva "
        "de datos de diagnóstico."
    ),
    "Windows Update — Manual Mode": "Windows Update — modo manual",
    "Sets Windows Update to manual and stops it now. Updates can still be installed when you choose.": (
        "Pone Windows Update en modo manual y lo detiene ahora. Aún puedes instalar "
        "actualizaciones cuando quieras."
    ),
    "Security updates will not download automatically while this is applied.": (
        "Las actualizaciones de seguridad no se descargarán automáticamente mientras "
        "esté aplicado."
    ),
    "Disable Fax Service": "Desactivar el servicio de fax",
    "Turns off the legacy fax service. It is unused on almost every modern PC.": (
        "Desactiva el servicio de fax heredado. No se usa en casi ningún PC moderno."
    ),
    "Disable Geolocation": "Desactivar la geolocalización",
    "Stops the location service and its background tracking of your position.": (
        "Detiene el servicio de ubicación y su seguimiento de tu posición en segundo plano."
    ),
    "Disable Print Spooler": "Desactivar la cola de impresión",
    "Turns off the printing subsystem. Recommended only on PCs without a printer.": (
        "Desactiva el subsistema de impresión. Solo se recomienda en PC sin impresora."
    ),
    "Printing and some PDF printers will stop working.": (
        "La impresión y algunas impresoras PDF dejarán de funcionar."
    ),
    "Disable Downloaded Maps Manager": "Desactivar el administrador de mapas descargados",
    "Stops the offline map download service.": (
        "Detiene el servicio de descarga de mapas sin conexión."
    ),
    "Disable Xbox Live Services": "Desactivar los servicios de Xbox Live",
    "Stops Xbox authentication, cloud saves and networking services.": (
        "Detiene los servicios de autenticación, guardado en la nube y red de Xbox."
    ),
    "Microsoft Store / Game Pass games may not sign in.": (
        "Los juegos de Microsoft Store / Game Pass pueden no iniciar sesión."
    ),
    "Disable WMP Network Sharing": "Desactivar el uso compartido en red de WMP",
    "Stops the legacy Windows Media Player media-sharing service.": (
        "Detiene el servicio heredado de uso compartido multimedia de Windows Media Player."
    ),
    "Keep Kernel & Drivers in RAM": "Mantener el núcleo y los controladores en RAM",
    "Sets DisablePagingExecutive=1 so kernel code stays in physical memory instead of the page file.": (
        "Establece DisablePagingExecutive=1 para que el código del núcleo permanezca "
        "en memoria física en lugar del archivo de paginación."
    ),
    "Prioritize Foreground Games": "Priorizar los juegos en primer plano",
    "Uses a short, fixed processor quantum (Win32PrioritySeparation=38) for faster foreground response.": (
        "Usa un quantum de procesador corto y fijo (Win32PrioritySeparation=38) para "
        "una respuesta más rápida en primer plano."
    ),
    "Lower Multimedia System Responsiveness": "Reducir la respuesta multimedia del sistema",
    "Sets SystemResponsiveness=0 so background multimedia work reserves less CPU for games.": (
        "Establece SystemResponsiveness=0 para que el trabajo multimedia en segundo "
        "plano reserve menos CPU para los juegos."
    ),
    "Boost Games Task Priority": "Aumentar la prioridad de la tarea Juegos",
    "Raises the GPU and CPU scheduling priority Windows gives to the Games task profile.": (
        "Eleva la prioridad de GPU y CPU que Windows asigna al perfil de tareas Juegos."
    ),
    "Disable Power Throttling": "Desactivar la limitación de energía",
    "Prevents Windows from capping background CPU clocks for efficiency.": (
        "Evita que Windows limite los relojes de CPU en segundo plano por eficiencia."
    ),
    "Raw Input / Low-Latency Peripherals": "Entrada directa / periféricos de baja latencia",
    "Removes mouse acceleration, disables pointer smoothing and tightens USB mouse/keyboard queues.": (
        "Elimina la aceleración del ratón, desactiva el suavizado del puntero y reduce "
        "las colas USB de ratón y teclado."
    ),
    "Queue-size changes are advanced; revert them if you notice dropped inputs.": (
        "Los cambios de tamaño de cola son avanzados; revierte si notas pérdida de entradas."
    ),
    "Disable Hardware GPU Scheduling": "Desactivar la programación de GPU por hardware",
    "Sets HwSchMode=1 to let the driver manage GPU scheduling itself. Reboot required.": (
        "Establece HwSchMode=1 para que el controlador gestione la programación de la "
        "GPU. Requiere reinicio."
    ),
    "Some modern titles run better with HAGS enabled. Toggle and benchmark both.": (
        "Algunos juegos modernos funcionan mejor con HAGS activado. Prueba y compara ambos."
    ),
    "Enable Hardware GPU Scheduling": "Activar la programación de GPU por hardware",
    "Sets HwSchMode=2 so the GPU driver schedules work directly with lower latency. Reboot required.": (
        "Establece HwSchMode=2 para que el controlador de GPU programe el trabajo "
        "directamente con menor latencia. Requiere reinicio."
    ),
    "HAGS improves latency on many modern GPUs but can reduce stability in a few titles.": (
        "HAGS mejora la latencia en muchas GPU modernas, pero puede reducir la "
        "estabilidad en algunos juegos."
    ),
    "Disable Hibernation": "Desactivar la hibernación",
    "Runs powercfg -h off, deleting hiberfil.sys and freeing several GB on the system drive.": (
        "Ejecuta powercfg -h off, elimina hiberfil.sys y libera varios GB en la unidad "
        "del sistema."
    ),
    "Fast Startup and hibernate will be unavailable until reverted.": (
        "El inicio rápido y la hibernación no estarán disponibles hasta revertirlo."
    ),
    "Disable Game Bar & DVR Capture": "Desactivar Game Bar y la captura DVR",
    "Turns off background gameplay recording and the Game Bar capture pipeline.": (
        "Desactiva la grabación de partidas en segundo plano y el flujo de captura de Game Bar."
    ),
    "Disable Fullscreen Optimizations": "Desactivar las optimizaciones de pantalla completa",
    "Forces legacy exclusive fullscreen behavior for games that ignore the Windows compositor.": (
        "Fuerza el comportamiento heredado de pantalla completa exclusiva en juegos que "
        "ignoran el compositor de Windows."
    ),
    "Disable Network Throttling": "Desactivar la limitación de red",
    "Removes Windows' 10-packet multimedia throttle (NetworkThrottlingIndex=0xFFFFFFFF).": (
        "Elimina el límite multimedia de 10 paquetes de Windows "
        "(NetworkThrottlingIndex=0xFFFFFFFF)."
    ),
    "Disable Nagle & Delayed ACK": "Desactivar Nagle y ACK retardado",
    "Sets TCPNoDelay and TcpAckFrequency=1 on active adapters so small game packets leave immediately.": (
        "Establece TCPNoDelay y TcpAckFrequency=1 en los adaptadores activos para que "
        "los paquetes pequeños de los juegos salgan de inmediato."
    ),
    "Applied to active IPv4 adapters. New adapters need the tweak re-applied.": (
        "Se aplica a los adaptadores IPv4 activos. Los adaptadores nuevos necesitan que "
        "se vuelva a aplicar."
    ),
    "Optimize DNS Cache": "Optimizar la caché de DNS",
    "Extends the positive DNS cache and flushes the resolver so lookups stop repeating.": (
        "Amplía la caché DNS positiva y vacía el resolutor para que las consultas dejen "
        "de repetirse."
    ),
    "Release Reserved QoS Bandwidth": "Liberar el ancho de banda reservado de QoS",
    "Sets the reserved bandwidth policy to 0 instead of the legacy 20% ceiling.": (
        "Establece la directiva de ancho de banda reservado en 0 en lugar del límite "
        "heredado del 20 %."
    ),
    "Most networks are unaffected; this is a legacy policy.": (
        "La mayoría de redes no se ven afectadas; es una directiva heredada."
    ),
    "Disable Aero, Transparency & Animations": "Desactivar Aero, transparencia y animaciones",
    "Turns off window animations, acrylic transparency, Aero Peek and drag-full-windows effects.": (
        "Desactiva las animaciones de ventanas, la transparencia acrílica, Aero Peek y "
        "el arrastre de ventanas completas."
    ),
    "Explorer Performance Mode": "Modo de rendimiento del Explorador",
    "Disables thumbnail generation and the floating status bar in File Explorer.": (
        "Desactiva la generación de miniaturas y la barra de estado flotante del "
        "Explorador de archivos."
    ),
    "Folders will show icons instead of image previews.": (
        "Las carpetas mostrarán iconos en lugar de vistas previas de imágenes."
    ),
    "Disable Ads & Suggested Content": "Desactivar anuncios y contenido sugerido",
    "Turns off the advertising ID, suggested apps, and silent content installs.": (
        "Desactiva el ID de publicidad, las aplicaciones sugeridas y las instalaciones "
        "silenciosas de contenido."
    ),
    # ---------------------------------------------------------- cleaner tweaks
    "Windows Copilot": "Windows Copilot",
    "Disables the Copilot button and AI data analysis through policy, including background model access.": (
        "Desactiva el botón Copilot y el análisis de datos de IA mediante directiva, "
        "incluido el acceso al modelo en segundo plano."
    ),
    "Copilot disappears from the taskbar and Edge sidebar on next sign-in.": (
        "Copilot desaparecerá de la barra de tareas y de la barra lateral de Edge al "
        "iniciar sesión de nuevo."
    ),
    "Windows Recall": "Windows Recall",
    "Disables Recall's local screenshot history and the AI data analysis pipeline.": (
        "Desactiva el historial local de capturas de Recall y el flujo de análisis de "
        "datos de IA."
    ),
    "Existing Recall snapshots may remain until removed in Windows Settings.": (
        "Las capturas existentes de Recall pueden permanecer hasta que las elimines en "
        "Configuración de Windows."
    ),
    "Microsoft Edge": "Microsoft Edge",
    "Force-uninstalls Edge through its own installer. Chromium engines used by other apps are kept.": (
        "Desinstala Edge a la fuerza mediante su propio instalador. Se conservan los "
        "motores Chromium usados por otras aplicaciones."
    ),
    "Windows may reinstall Edge after a feature update. Some apps rely on WebView2, not Edge.": (
        "Windows puede reinstalar Edge tras una actualización de características. "
        "Algunas aplicaciones dependen de WebView2, no de Edge."
    ),
    "Microsoft OneDrive": "Microsoft OneDrive",
    "Uninstalls the OneDrive sync client and stops its background process. Your cloud files are not deleted.": (
        "Desinstala el cliente de sincronización de OneDrive y detiene su proceso en "
        "segundo plano. Tus archivos en la nube no se eliminan."
    ),
    "File Explorer OneDrive shortcuts are removed. Local files stay untouched.": (
        "Se eliminan los accesos directos de OneDrive del Explorador. Los archivos "
        "locales no se tocan."
    ),
    "Windows Media Player (Legacy)": "Windows Media Player (heredado)",
    "Removes the old Media Player feature through DISM. Modern Media Player is separate.": (
        "Elimina la característica antigua de Media Player mediante DISM. El Media "
        "Player moderno es independiente."
    ),
    "DirectPlay": "DirectPlay",
    "Disables the legacy DirectX 3/5/6 compatibility layer that modern games do not use.": (
        "Desactiva la capa de compatibilidad heredada de DirectX 3/5/6 que los juegos "
        "modernos no usan."
    ),
    "Very old games from the 1990s/2000s may need it.": (
        "Los juegos muy antiguos de los años 90 y 2000 pueden necesitarla."
    ),
    # -------------------------------------------------------------- appx titles
    "Xbox Console Companion": "Xbox Console Companion",
    "Legacy Xbox companion app.": "Aplicación de acompañamiento de Xbox heredada.",
    "Xbox": "Xbox",
    "Xbox app and Game Pass sign-in.": "Aplicación Xbox e inicio de sesión de Game Pass.",
    "Xbox Game Bar": "Xbox Game Bar",
    "Overlay, captures and Game Bar shortcuts.": "Superposición, capturas y atajos de Game Bar.",
    "Xbox Identity Provider": "Proveedor de identidad de Xbox",
    "Required by Xbox / Game Pass titles.": "Necesario para títulos de Xbox / Game Pass.",
    "Xbox Speech To Text": "Voz a texto de Xbox",
    "Accessibility overlay for the Game Bar.": "Superposición de accesibilidad para Game Bar.",
    "Xbox TCUI": "Xbox TCUI",
    "Xbox user interface components.": "Componentes de interfaz de usuario de Xbox.",
    "Mail & Calendar": "Correo y Calendario",
    "Replaced by Outlook web or your mail client.": (
        "Sustituido por Outlook web o tu cliente de correo."
    ),
    "Maps": "Mapas",
    "Offline maps and location search.": "Mapas sin conexión y búsqueda de ubicaciones.",
    "Movies & TV": "Películas y TV",
    "Microsoft's video store and player.": "Tienda y reproductor de vídeo de Microsoft.",
    "Media Player": "Reproductor multimedia",
    "Modern Media Player / Groove package.": "Paquete moderno de Media Player / Groove.",
    "Modern Media Player package.": "Paquete moderno de Media Player.",
    "Weather": "El Tiempo",
    "Microsoft Weather app.": "Aplicación El Tiempo de Microsoft.",
    "Phone Link (Your Phone)": "Vínculo con el teléfono (Tu teléfono)",
    "Android phone mirroring and notifications.": (
        "Duplicación y notificaciones de teléfonos Android."
    ),
    "Get Help": "Obtener ayuda",
    "Microsoft support app.": "Aplicación de soporte de Microsoft.",
    "Tips": "Sugerencias",
    "Windows tips and suggestions.": "Sugerencias y consejos de Windows.",
    "Solitaire Collection": "Colección de Solitario",
    "Preinstalled card games.": "Juegos de cartas preinstalados.",
    "People": "Contactos",
    "Contacts app.": "Aplicación de contactos.",
    "Microsoft 365 (Office Hub)": "Microsoft 365 (Office Hub)",
    "Office promotional hub; not Office itself.": (
        "Centro promocional de Office; no es Office en sí."
    ),
    "Skype": "Skype",
    "Skype UWP client.": "Cliente UWP de Skype.",
    "Feedback Hub": "Centro de opiniones",
    "Microsoft feedback submission app.": "Aplicación de envío de opiniones de Microsoft.",
    "News": "Noticias",
    "Microsoft News feed.": "Fuente de noticias de Microsoft.",
    "Clipchamp": "Clipchamp",
    "Video editor with online export.": "Editor de vídeo con exportación en línea.",
    "Microsoft To Do": "Microsoft To Do",
    "Task list app.": "Aplicación de listas de tareas.",
    "Power Automate": "Power Automate",
    "Desktop automation app.": "Aplicación de automatización de escritorio.",
    "Microsoft Teams (personal)": "Microsoft Teams (personal)",
    "Personal Teams client.": "Cliente personal de Teams.",
    "Sound Recorder": "Grabadora de sonido",
    "Simple voice recorder.": "Grabadora de voz sencilla.",
    "Alarms & Clock": "Alarmas y reloj",
    "Alarms, timers and stopwatch.": "Alarmas, temporizadores y cronómetro.",
    # ----------------------------------------------------------------- dashboard
    "System Status": "Estado del sistema",
    "(Gaming Mode: STANDBY)": "(Modo juego: EN ESPERA)",
    "(Gaming Mode: ACTIVATED)": "(Modo juego: ACTIVADO)",
    "Live telemetry, latency and two reversible optimization profiles.": (
        "Telemetría en vivo, latencia y dos perfiles de optimización reversibles."
    ),
    "Normal optimization": "Optimización normal",
    "Extreme optimization": "Optimización extrema",
    "RECOMMENDED PROFILE  ·  ANALYZING…": "PERFIL RECOMENDADO  ·  ANALIZANDO…",
    "ALL TWEAKS  ·  ADVANCED CHANGES  ·  RESTORE POINT": (
        "TODOS LOS AJUSTES  ·  CAMBIOS AVANZADOS  ·  PUNTO DE RESTAURACIÓN"
    ),
    "Last optimization: {value}": "Última optimización: {value}",
    "Estimated performance gain: +{gain}% FPS": "Ganancia estimada de rendimiento: +{gain}% FPS",
    "Activity log": "Registro de actividad",
    "NETWORK LATENCY": "LATENCIA DE RED",
    "Measuring 1.1.1.1…": "Midiendo 1.1.1.1…",
    "OPTIMIZATION SCORE": "PUNTUACIÓN DE OPTIMIZACIÓN",
    "Analyzing tweaks…": "Analizando ajustes…",
    "Latency probe unavailable": "Sonda de latencia no disponible",
    "Excellent route to 1.1.1.1": "Ruta excelente a 1.1.1.1",
    "Good route to 1.1.1.1": "Buena ruta a 1.1.1.1",
    "Elevated route latency": "Latencia de ruta elevada",
    "{applied} of {total} tweaks active": "{applied} de {total} ajustes activos",
    "RECOMMENDED PROFILE  ·  {normal_count} REVERSIBLE TWEAKS": (
        "PERFIL RECOMENDADO  ·  {normal_count} AJUSTES REVERSIBLES"
    ),
    "ALL {extreme_count} TWEAKS  ·  ADVANCED CHANGES  ·  RESTORE POINT": (
        "LOS {extreme_count} AJUSTES  ·  CAMBIOS AVANZADOS  ·  PUNTO DE RESTAURACIÓN"
    ),
    "Could not refresh system profile: {error}": (
        "No se pudo actualizar el perfil del sistema: {error}"
    ),
    "UTILIZATION": "USO",
    "CURRENT CLOCK": "RELOJ ACTUAL",
    "TOTAL MEMORY": "MEMORIA TOTAL",
    "PHYSICAL MEMORY": "MEMORIA FÍSICA",
    "PROCESSOR LOAD": "CARGA DEL PROCESADOR",
    "NO TELEMETRY": "SIN TELEMETRÍA",
    "RENDER DEVICE": "DISPOSITIVO DE RENDERIZADO",
    "3D ENGINE LOAD": "CARGA DEL MOTOR 3D",
    "3D engine telemetry unavailable": "Telemetría del motor 3D no disponible",
    # The total is already shown in the side column; keeping the Spanish
    # centre label short avoids collisions with it on narrow cards.
    "GB USED / {total}": "GB USADOS",
    "{free} GB free": "{free} GB libres",
    # -------------------------------------------------------------- tweaks page
    "Stage system changes, review them, then apply with a single restore point.": (
        "Prepara cambios del sistema, revísalos y aplícalos con un único punto de restauración."
    ),
    "Windows control center": "Centro de control de Windows",
    "{count} APPLIED": "{count} APLICADOS",
    "All selected tweaks are up to date": "Todos los ajustes seleccionados están al día",
    "Toggle a row to stage a change, or run a quick profile.": (
        "Activa una fila para preparar un cambio o ejecuta un perfil rápido."
    ),
    "{count} to apply": "{count} por aplicar",
    "{count} to restore": "{count} por restaurar",
    "Review before applying. A restore point is created when possible.": (
        "Revisa antes de aplicar. Se crea un punto de restauración cuando es posible."
    ),
    "Dry-run is enabled: commands will be logged but not executed.": (
        "El modo de prueba está activo: los comandos se registrarán pero no se ejecutarán."
    ),
    "Apply {count} change": "Aplicar {count} cambio",
    "Apply {count} changes": "Aplicar {count} cambios",
    "No tweaks in this category.": "No hay ajustes en esta categoría.",
    "Loading tweaks…": "Cargando ajustes…",
    "Checking tweak states…": "Comprobando el estado de los ajustes…",
    "Could not load tweak states.": "No se pudieron cargar los estados de los ajustes.",
    "Could not refresh tweak states: {error}": (
        "No se pudieron actualizar los estados de los ajustes: {error}"
    ),
    "{count} OPTIONS": "{count} OPCIONES",
    "Run normal optimization?": "¿Ejecutar la optimización normal?",
    "Run extreme optimization?": "¿Ejecutar la optimización extrema?",
    "Optimize now": "Optimizar ahora",
    "Apply extreme": "Aplicar extremo",
    "Normal optimization": "Optimización normal",
    "Extreme optimization": "Optimización extrema",
    "Normal profile": "Perfil normal",
    "Extreme profile": "Perfil extremo",
    "Optimizing…": "Optimizando…",
    "Optimized": "Optimizado",
    "The normal profile is already applied.": "El perfil normal ya está aplicado.",
    "The extreme profile is already applied.": "El perfil extremo ya está aplicado.",
    "The normal profile changes Windows services and system registry values.": (
        "El perfil normal cambia servicios de Windows y valores del registro del sistema."
    ),
    "The extreme profile changes Windows services, registry values and system policies.": (
        "El perfil extremo cambia servicios de Windows, valores del registro y directivas del sistema."
    ),
    "Extreme mode disables automatic Windows updates and printing until reverted.": (
        "El modo extremo desactiva las actualizaciones automáticas de Windows y la "
        "impresión hasta que se revierta."
    ),
    "Conflicting hardware-scheduling alternatives are skipped; the modern option is used.": (
        "Se omiten las alternativas de programación por hardware en conflicto; se usa "
        "la opción moderna."
    ),
    # ------------------------------------------------------------ settings page
    "Safety controls, privilege state, backups and the local audit trail.": (
        "Controles de seguridad, privilegios, copias de seguridad y registro de "
        "auditoría local."
    ),
    "VERSION {version}": "VERSIÓN {version}",
    "Safety defaults": "Valores predeterminados de seguridad",
    "Controls how every staged change is executed.": (
        "Controla cómo se ejecuta cada cambio preparado."
    ),
    "Dry-run mode": "Modo de prueba",
    "Log commands without writing registry, services or files.": (
        "Registra los comandos sin escribir en el registro, servicios ni archivos."
    ),
    "Restore point by default": "Punto de restauración por defecto",
    "Preselect the Windows checkpoint before applying changes.": (
        "Preselecciona el punto de control de Windows antes de aplicar cambios."
    ),
    "BACKUP & RESTORE": "COPIA Y RESTAURACIÓN",
    "BEHAVIOR": "COMPORTAMIENTO",
    "Reversible by design": "Reversible por diseño",
    "Reading backups…": "Leyendo copias de seguridad…",
    "Create restore point": "Crear punto de restauración",
    "Open data folder": "Abrir carpeta de datos",
    "Revert backed-up tweaks": "Revertir ajustes respaldados",
    "LOCAL ACTIVITY": "ACTIVIDAD LOCAL",
    "Every change is written to disk": "Cada cambio se escribe en disco",
    "LANGUAGE": "IDIOMA",
    "Application language": "Idioma de la aplicación",
    "Choose the interface language. Changes apply immediately.": (
        "Elige el idioma de la interfaz. Los cambios se aplican al instante."
    ),
    "Language changed to Spanish.": "Idioma cambiado a Español.",
    "Language changed to English.": "Idioma cambiado a Inglés.",
    "Administrator session": "Sesión de administrador",
    "Standard user session": "Sesión de usuario estándar",
    "System-wide changes are available.": "Los cambios en todo el sistema están disponibles.",
    "Registry, service, AppX and repair tasks need elevation.": (
        "El registro, los servicios, AppX y las tareas de reparación necesitan elevación."
    ),
    "Restart as admin": "Reiniciar como administrador",
    "{count} reversible change stored  •  {value}": (
        "{count} cambio reversible guardado  •  {value}"
    ),
    "{count} reversible changes stored  •  {value}": (
        "{count} cambios reversibles guardados  •  {value}"
    ),
    "Dry-run enabled: commands will be logged only.": (
        "Modo de prueba activado: los comandos solo se registrarán."
    ),
    "Dry-run disabled.": "Modo de prueba desactivado.",
    "Already running with administrator rights.": (
        "Ya se está ejecutando con derechos de administrador."
    ),
    "Restart as administrator?": "¿Reiniciar como administrador?",
    "Windows will show a UAC prompt. Optimus X will close and reopen elevated; your settings and backups are kept.": (
        "Windows mostrará un aviso de UAC. Optimus X se cerrará y volverá a abrirse "
        "con elevación; tus ajustes y copias de seguridad se conservan."
    ),
    "Restart elevated": "Reiniciar con elevación",
    "Could not open folder: {error}": "No se pudo abrir la carpeta: {error}",
    "Creating a restore point requires administrator rights.": (
        "Crear un punto de restauración requiere derechos de administrador."
    ),
    "Restore point created.": "Punto de restauración creado.",
    "Restore point failed.": "No se pudo crear el punto de restauración.",
    "Windows System Protection checkpoint": "Punto de control de Protección del sistema de Windows",
    "Create restore point?": "¿Crear un punto de restauración?",
    "Windows may need System Protection enabled. This can take a minute.": (
        "Puede que Windows necesite la Protección del sistema activada. Esto puede "
        "tardar un minuto."
    ),
    "There are no stored tweaks to revert.": "No hay ajustes guardados que revertir.",
    "Restoring backed-up system values requires administrator rights.": (
        "Restaurar los valores respaldados del sistema requiere derechos de administrador."
    ),
    "Dry-run complete — no values were restored.": (
        "Prueba completada: no se restauró ningún valor."
    ),
    "{count} tweak(s) restored to their previous values.": (
        "{count} ajuste(s) restaurado(s) a sus valores anteriores."
    ),
    "Reverting all applied tweaks": "Revirtiendo todos los ajustes aplicados",
    "Restoring {count} backed-up system state(s)": (
        "Restaurando {count} estado(s) del sistema respaldado(s)"
    ),
    "Revert every applied tweak?": "¿Revertir todos los ajustes aplicados?",
    "Optimus X will restore the registry values and service start types saved in the local backup. Changes that had no backup (such as Edge removal) cannot be undone.": (
        "Optimus X restaurará los valores del registro y los tipos de inicio de "
        "servicios guardados en la copia local. Los cambios sin copia (como la "
        "eliminación de Edge) no se pueden deshacer."
    ),
    "Revert everything": "Revertir todo",
    "This restores all tweaks recorded in the backup store.": (
        "Esto restaura todos los ajustes registrados en el almacén de copias."
    ),
    "A reboot may be required for kernel and network changes.": (
        "Puede ser necesario reiniciar para los cambios de núcleo y red."
    ),
    "I want to restore all backed-up values": "Quiero restaurar todos los valores respaldados",
    "OPTIMUS X": "OPTIMUS X",
    "Version {version}  •  local-only utility  •  no telemetry, no cloud, no bundled installers. Registry and service backups stay on this machine.": (
        "Versión {version}  •  utilidad solo local  •  sin telemetría, sin nube y sin "
        "instaladores incluidos. Las copias del registro y de servicios permanecen en "
        "este equipo."
    ),
    "No activity recorded yet.": "Todavía no hay actividad registrada.",
    "No technical log recorded yet.": "Todavía no hay registro técnico.",
    "Could not read activity log: {error}": "No se pudo leer el registro de actividad: {error}",
    "Could not read technical log: {error}": "No se pudo leer el registro técnico: {error}",
    # ------------------------------------------------------------- cleaner page
    "Remove preinstalled bloat, disable legacy components and reclaim disk space.": (
        "Elimina software preinstalado, desactiva componentes heredados y recupera "
        "espacio en disco."
    ),
    "Bloatware control": "Control de software preinstalado",
    "Rescan system": "Volver a analizar",
    "SYSTEM DRIVE": "UNIDAD DEL SISTEMA",
    "C:\\  —": "C:\\  —",
    "Reading disk usage…": "Leyendo el uso del disco…",
    "RECLAIMABLE": "RECUPERABLE",
    "Scanning…": "Analizando…",
    "Deep clean": "Limpieza profunda",
    "Edge, OneDrive, Copilot, Recall and legacy runtimes": (
        "Edge, OneDrive, Copilot, Recall y entornos heredados"
    ),
    "6 COMPONENTS": "6 COMPONENTES",
    "PREINSTALLED APPS": "APLICACIONES PREINSTALADAS",
    "Packages installed for the current Windows user": (
        "Paquetes instalados para el usuario actual de Windows"
    ),
    "Scanning installed packages…": "Analizando los paquetes instalados…",
    "Filter apps…": "Filtrar aplicaciones…",
    "Select recommended": "Seleccionar recomendadas",
    "Remove selected": "Quitar seleccionadas",
    "Scanning the installed AppX package list. This can take a few seconds…": (
        "Analizando la lista de paquetes AppX instalados. Esto puede tardar unos segundos…"
    ),
    "DEEP CLEAN TARGETS": "OBJETIVOS DE LIMPIEZA",
    "Temporary files, shader cache, update cache and Recycle Bin": (
        "Archivos temporales, caché de sombreadores, caché de actualizaciones y Papelera"
    ),
    "Scanning cleanup targets…": "Analizando objetivos de limpieza…",
    "Querying Get-AppxPackage and Windows optional features…": (
        "Consultando Get-AppxPackage y las características opcionales de Windows…"
    ),
    "  Scanning…  ": "  Analizando…  ",
    "Scan warning: {error}": "Aviso del análisis: {error}",
    "Package list incomplete": "Lista de paquetes incompleta",
    "Select packages to remove. Removal applies to the current user and provisioned image.": (
        "Selecciona paquetes para quitar. La eliminación se aplica al usuario actual y "
        "a la imagen aprovisionada."
    ),
    "No curated bloatware packages found for this user.": (
        "No se encontraron paquetes de software preinstalado para este usuario."
    ),
    "No matching packages.": "No hay paquetes coincidentes.",
    "{total} package found  •  {selected} selected": (
        "{total} paquete encontrado  •  {selected} seleccionados"
    ),
    "{total} packages found  •  {selected} selected": (
        "{total} paquetes encontrados  •  {selected} seleccionados"
    ),
    "Removing AppX packages requires administrator rights.": (
        "Quitar paquetes AppX requiere derechos de administrador."
    ),
    "Removing {count} package(s)…": "Quitando {count} paquete(s)…",
    "Packages removed.": "Paquetes eliminados.",
    "Selected packages were removed.": "Se quitaron los paquetes seleccionados.",
    "Package removal reported issues.": "La eliminación de paquetes informó de problemas.",
    "Removing preinstalled apps": "Quitando aplicaciones preinstaladas",
    "{count} AppX package(s) · current user + provisioned image": (
        "{count} paquete(s) AppX · usuario actual + imagen aprovisionada"
    ),
    "Remove selected apps?": "¿Quitar las aplicaciones seleccionadas?",
    "These UWP packages will be uninstalled for your user and removed from the provisioned image. Microsoft Store and system-critical packages are never included.": (
        "Estos paquetes UWP se desinstalarán para tu usuario y se quitarán de la "
        "imagen aprovisionada. Microsoft Store y los paquetes críticos del sistema "
        "nunca se incluyen."
    ),
    "Remove {count} apps": "Quitar {count} aplicaciones",
    "Removing Xbox components can break Game Pass sign-in and Game Bar captures.": (
        "Quitar componentes de Xbox puede romper el inicio de sesión de Game Pass y "
        "las capturas de Game Bar."
    ),
    "I understand this is not easily reversible": (
        "Entiendo que esto no se revierte fácilmente"
    ),
    "{name} requires administrator rights.": (
        "{name} requiere derechos de administrador."
    ),
    "{name}: action completed.": "{name}: acción completada.",
    "Applying a system component change": "Aplicando un cambio de componente del sistema",
    "Restoring {name} requires administrator rights.": (
        "Restaurar {name} requiere derechos de administrador."
    ),
    "{name}: previous state restored.": "{name}: estado anterior restaurado.",
    "Restore {name}": "Restaurar {name}",
    "Restoring the saved backed-up state": "Restaurando el estado respaldado guardado",
    "Re-enable {name}?": "¿Reactivar {name}?",
    "The previous registry and service state will be restored from the local backup.": (
        "El estado anterior del registro y de los servicios se restaurará desde la "
        "copia local."
    ),
    "{free} free  •  {percent}% used": "{free} libres  •  {percent}% usado",
    "Used {used} of {total}": "Usado {used} de {total}",
    "Rescanning…": "Volviendo a analizar…",
    "Nothing to clean right now.": "No hay nada que limpiar ahora mismo.",
    "No cleanup targets are available.": "No hay objetivos de limpieza disponibles.",
    "{size} reclaimed.": "{size} recuperados.",
    "Deep clean system files": "Limpieza profunda de archivos del sistema",
    "Temporary files, caches, update payloads and Recycle Bin": (
        "Archivos temporales, cachés, paquetes de actualización y Papelera"
    ),
    "Start deep clean?": "¿Iniciar la limpieza profunda?",
    "Only temporary and cache locations are touched. Windows Update downloads and the Recycle Bin are included, so review the list before continuing.": (
        "Solo se tocan ubicaciones temporales y de caché. Se incluyen las descargas "
        "de Windows Update y la Papelera, así que revisa la lista antes de continuar."
    ),
    "Administrator-only targets are skipped when the app is not elevated.": (
        "Los objetivos que requieren administrador se omiten cuando la aplicación no "
        "está elevada."
    ),
    # ------------------------------------------------------------ gameboost page
    "A competitive profile for latency, frame-time consistency and background noise.": (
        "Un perfil competitivo para latencia, consistencia de fotogramas y ruido de fondo."
    ),
    "Performance profile": "Perfil de rendimiento",
    "POWER PLAN  •  —": "PLAN DE ENERGÍA  •  —",
    "GAME BOOST": "IMPULSO DE JUEGO",
    "COMPETITIVE": "COMPETITIVO",
    "Applies the reversible gaming profile: kernel priority, input latency, network throttling, telemetry, search and visual effects.": (
        "Aplica el perfil de juego reversible: prioridad del núcleo, latencia de "
        "entrada, limitación de red, telemetría, búsqueda y efectos visuales."
    ),
    "STAND BY": "EN ESPERA",
    "Tweak count: 13  •  Reboot recommended  •  Backup enabled": (
        "Ajustes: 13  •  Reinicio recomendado  •  Copia activada"
    ),
    "GAMING MODE": "MODO JUEGO",
    "Activate profile": "Activar perfil",
    "Deactivate profile": "Desactivar perfil",
    "APPLIED TWEAKS": "AJUSTES APLICADOS",
    "Counted from the gaming profile": "Contados del perfil de juego",
    "REBOOT STATUS": "ESTADO DE REINICIO",
    "Kernel changes need one restart": "Los cambios de núcleo necesitan un reinicio",
    "SAFETY": "SEGURIDAD",
    "Restore point + local backup": "Punto de restauración + copia local",
    "PROFILE CHECKLIST": "LISTA DEL PERFIL",
    "Changes included in Game Boost": "Cambios incluidos en Impulso de juego",
    "{count} CHECKS": "{count} COMPROBACIONES",
    "BACKGROUND PROCESSES": "PROCESOS EN SEGUNDO PLANO",
    "High-memory apps that can steal frame time": (
        "Aplicaciones con mucha memoria que pueden robar tiempo de fotograma"
    ),
    "Reading process list…": "Leyendo la lista de procesos…",
    "End selected": "Finalizar seleccionados",
    "POWER PLAN": "PLAN DE ENERGÍA",
    "Windows processor scheduling for the current session": (
        "Programación del procesador de Windows para la sesión actual"
    ),
    "Reading active power plan…": "Leyendo el plan de energía activo…",
    "Balanced": "Equilibrado",
    "High performance": "Alto rendimiento",
    "ACTIVATED": "ACTIVADO",
    "{count} tweaks in profile  •  Reboot recommended  •  Fully reversible": (
        "{count} ajustes en el perfil  •  Reinicio recomendado  •  Totalmente reversible"
    ),
    "{count} tweaks in profile  •  Backup enabled  •  Fully reversible": (
        "{count} ajustes en el perfil  •  Copia activada  •  Totalmente reversible"
    ),
    "RECOMMENDED": "RECOMENDADO",
    "NOT ACTIVE": "NO ACTIVO",
    "PROTECTED": "PROTEGIDO",
    "Unknown power plan": "Plan de energía desconocido",
    "{guid}  •  switch to High performance before a long session": (
        "{guid}  •  cambia a Alto rendimiento antes de una sesión larga"
    ),
    "POWER PLAN  •  {name}": "PLAN DE ENERGÍA  •  {name}",
    "Gaming profile is already active.": "El perfil de juego ya está activo.",
    "Activating Game Boost requires administrator rights.": (
        "Activar Impulso de juego requiere derechos de administrador."
    ),
    "Dry-run complete — Game Boost was not applied.": (
        "Prueba completada: no se aplicó Impulso de juego."
    ),
    "Game Boost applied with issues.": "Impulso de juego aplicado con problemas.",
    "Game Boost activated.": "Impulso de juego activado.",
    "Reboot to finish applying kernel and network tweaks.": (
        "Reinicia para terminar de aplicar los ajustes de núcleo y red."
    ),
    "Activating Game Boost": "Activando Impulso de juego",
    "{count} reversible changes · competitive profile": (
        "{count} cambios reversibles · perfil competitivo"
    ),
    "Activate Game Boost?": "¿Activar Impulso de juego?",
    "Optimus X will apply the competitive profile. Existing values are backed up first, so Deactivate can restore them later.": (
        "Optimus X aplicará el perfil competitivo. Los valores existentes se respaldan "
        "primero, así que Desactivar puede restaurarlos después."
    ),
    "ENABLE  ·  {name}": "ACTIVAR  ·  {name}",
    "Kernel and network changes take full effect after a reboot.": (
        "Los cambios de núcleo y red surten efecto completo tras reiniciar."
    ),
    "Create a Windows restore point first": "Crear primero un punto de restauración de Windows",
    "Restoring the gaming profile requires administrator rights.": (
        "Restaurar el perfil de juego requiere derechos de administrador."
    ),
    "Dry-run complete — the gaming profile was not reverted.": (
        "Prueba completada: el perfil de juego no se revirtió."
    ),
    "Game Boost deactivated. Previous values restored.": (
        "Impulso de juego desactivado. Valores anteriores restaurados."
    ),
    "Deactivating Game Boost": "Desactivando Impulso de juego",
    "Restoring {count} backed-up values": "Restaurando {count} valores respaldados",
    "Deactivate Game Boost?": "¿Desactivar Impulso de juego?",
    "The values saved when Game Boost was activated will be restored.": (
        "Se restaurarán los valores guardados cuando se activó Impulso de juego."
    ),
    "RESTORE  ·  {name}": "RESTAURAR  ·  {name}",
    "No heavy background apps detected.": "No se detectaron aplicaciones pesadas en segundo plano.",
    "No memory-heavy background apps found.": (
        "No se encontraron aplicaciones con mucho consumo de memoria."
    ),
    "Top {count} by working set  •  select to end": (
        "Los {count} principales por memoria  •  selecciona para finalizar"
    ),
    "Ended {count} process(es).": "Se finalizaron {count} proceso(s).",
    "{count} could not be closed.": "{count} no se pudieron cerrar.",
    # -------------------------------------------------------------- toolbox page
    "Repair Windows, reset networking and export a complete diagnostic snapshot.": (
        "Repara Windows, restablece la red y exporta un informe de diagnóstico completo."
    ),
    "Maintenance & repair": "Mantenimiento y reparación",
    "SYSTEM REPAIR": "REPARACIÓN DEL SISTEMA",
    "Signed Microsoft tools only": "Solo herramientas firmadas de Microsoft",
    "ADMIN RECOMMENDED": "ADMINISTRADOR RECOMENDADO",
    "Checkpoint the current registry and system state before making changes.": (
        "Crea un punto de control del registro y del estado actual del sistema antes "
        "de hacer cambios."
    ),
    "System File Checker": "Comprobador de archivos del sistema",
    "Run sfc /scannow to repair corrupt protected Windows files.": (
        "Ejecuta sfc /scannow para reparar archivos protegidos de Windows dañados."
    ),
    "Scans and repairs protected Windows files.": (
        "Analiza y repara archivos protegidos de Windows."
    ),
    "DISM component repair": "Reparación de componentes DISM",
    "Restore the component store with DISM /RestoreHealth.": (
        "Restaura el almacén de componentes con DISM /RestoreHealth."
    ),
    "Repairs the Windows component store. This can take a while.": (
        "Repara el almacén de componentes de Windows. Esto puede tardar un rato."
    ),
    "Flush DNS cache": "Vaciar la caché de DNS",
    "Clear stale resolver entries after changing DNS or network settings.": (
        "Borra las entradas obsoletas del resolutor tras cambiar DNS o la configuración de red."
    ),
    "Clears the local DNS resolver cache.": "Borra la caché del resolutor DNS local.",
    "Reset network stack": "Restablecer la pila de red",
    "Reset Winsock and TCP/IP, then flush DNS. Requires a restart.": (
        "Restablece Winsock y TCP/IP, y vacía el DNS. Requiere reiniciar."
    ),
    "Resets Winsock and TCP/IP configuration. Network adapters may briefly disconnect.": (
        "Restablece la configuración de Winsock y TCP/IP. Los adaptadores de red "
        "pueden desconectarse brevemente."
    ),
    "A reboot is required after the reset.": "Es necesario reiniciar después del restablecimiento.",
    "Restart Explorer": "Reiniciar el Explorador",
    "Restart the shell to apply Explorer and visual changes immediately.": (
        "Reinicia el shell para aplicar los cambios del Explorador y visuales de inmediato."
    ),
    "Stops explorer.exe; Windows starts it again automatically.": (
        "Detiene explorer.exe; Windows lo inicia de nuevo automáticamente."
    ),
    "Clean temporary files": "Limpiar archivos temporales",
    "Remove user temp, shader cache, crash dumps and the Recycle Bin.": (
        "Elimina los temporales del usuario, la caché de sombreadores, los volcados de "
        "fallos y la Papelera."
    ),
    "High performance plan": "Plan de alto rendimiento",
    "Switch the active Windows power plan for maximum clock responsiveness.": (
        "Cambia el plan de energía activo de Windows para obtener la máxima respuesta del reloj."
    ),
    "Check disk health": "Comprobar el estado del disco",
    "Run a read-only chkdsk scan on the system volume.": (
        "Ejecuta un análisis chkdsk de solo lectura en el volumen del sistema."
    ),
    "Runs a read-only NTFS health scan on the system drive.": (
        "Ejecuta un análisis de estado NTFS de solo lectura en la unidad del sistema."
    ),
    "System report": "Informe del sistema",
    "Export OS, hardware, applied tweaks and safety state as a Markdown report.": (
        "Exporta el sistema operativo, el hardware, los ajustes aplicados y el estado "
        "de seguridad como informe Markdown."
    ),
    "Open report folder": "Abrir carpeta de informes",
    "Open the local Optimus X report and backup folder.": (
        "Abre la carpeta local de informes y copias de seguridad de Optimus X."
    ),
    "Review every applied or reverted change in the local audit trail.": (
        "Revisa cada cambio aplicado o revertido en el registro de auditoría local."
    ),
    "{name} requires administrator rights.": (
        "{name} requiere derechos de administrador."
    ),
    "{name}: completed.": "{name}: completado.",
    "{name}: completed with errors.": "{name}: completado con errores.",
    "Requesting a Windows restore point…": "Solicitando un punto de restauración de Windows…",
    "Restore point could not be created.": "No se pudo crear el punto de restauración.",
    "System Protection checkpoint": "Punto de control de Protección del sistema",
    "Create a restore point?": "¿Crear un punto de restauración?",
    "Windows System Protection may need to be enabled. This can take a minute.": (
        "Puede que sea necesario activar la Protección del sistema de Windows. Esto "
        "puede tardar un minuto."
    ),
    "High performance power plan activated.": "Plan de energía de alto rendimiento activado.",
    "Could not change power plan: {error}": "No se pudo cambiar el plan de energía: {error}",
    "Could not export report: {error}": "No se pudo exportar el informe: {error}",
    "Report saved to {name}": "Informe guardado en {name}",
    "System report exported": "Informe del sistema exportado",
    "The report was saved locally:\n\n{path}\n\nNo data was uploaded.": (
        "El informe se guardó localmente:\n\n{path}\n\nNo se subió ningún dato."
    ),
    "User temporary files": "Archivos temporales del usuario",
    "DirectX shader cache": "Caché de sombreadores de DirectX",
    "Crash dumps": "Volcados de fallos",
    "Thumbnail cache": "Caché de miniaturas",
    "Recycle Bin": "Papelera",
    "Windows temporary files": "Archivos temporales de Windows",
    "System-wide temp files in C:\\Windows\\Temp.": (
        "Archivos temporales del sistema en C:\\Windows\\Temp."
    ),
    "Explorer thumbnail cache": "Caché de miniaturas del Explorador",
    "Cached thumbnails used by File Explorer.": (
        "Miniaturas en caché usadas por el Explorador de archivos."
    ),
    "Delivery Optimization cache": "Caché de Optimización de entrega",
    "Windows update delivery cache shared on your network.": (
        "Caché de entrega de actualizaciones de Windows compartida en tu red."
    ),
    "Windows Update download cache": "Caché de descargas de Windows Update",
    "Already-installed update payloads in SoftwareDistribution.": (
        "Paquetes de actualización ya instalados en SoftwareDistribution."
    ),
    "Files waiting in the Recycle Bin on the system drive.": (
        "Archivos pendientes en la Papelera de la unidad del sistema."
    ),
    "Leftover installers, caches and crash artefacts in your profile.": (
        "Instaladores, cachés y restos de fallos acumulados en tu perfil."
    ),
    "Compiled shaders that Windows can rebuild automatically.": (
        "Sombreadores compilados que Windows puede reconstruir automáticamente."
    ),
    "Application crash reports and minidumps.": (
        "Informes de fallos de aplicaciones y volcados de memoria."
    ),
    "Temporary locations cleaned.": "Ubicaciones temporales limpiadas.",
    "Clean temporary files?": "¿Limpiar los archivos temporales?",
    "Only cache and temporary locations are touched. The Recycle Bin will be emptied.": (
        "Solo se tocan cachés y ubicaciones temporales. La Papelera se vaciará."
    ),
    # -------------------------------------------------------------------- dialogs
    "Review the changes before continuing.": "Revisa los cambios antes de continuar.",
    "REVIEW CHANGES": "REVISAR CAMBIOS",
    "Starting…": "Iniciando…",
    "Running…": "Ejecutando…",
    "Preparing task…": "Preparando la tarea…",
    "Cancelling…": "Cancelando…",
    "Completed successfully": "Completado correctamente",
    "Completed with issues": "Completado con problemas",
    "TASK COMPLETE": "TAREA COMPLETADA",
    "TASK COMPLETE WITH ISSUES": "TAREA COMPLETADA CON PROBLEMAS",
    "Create a Windows restore point before applying": (
        "Crear un punto de restauración de Windows antes de aplicar"
    ),
    "These changes modify Windows services and system registry values.": (
        "Estos cambios modifican servicios de Windows y valores del registro del sistema."
    ),
    "Staged changes": "Cambios preparados",
    "ENABLE  ·  {name}": "ACTIVAR  ·  {name}",
    "RESTORE  ·  {name}": "RESTAURAR  ·  {name}",
    "Plus {count} more warning(s) listed in the task output.": (
        "Hay {count} advertencia(s) más en la salida de la tarea."
    ),
    "Dry-run complete — no changes were written.": (
        "Prueba completada: no se escribió ningún cambio."
    ),
    "Finished with {count} issue(s). Review the task output.": (
        "Finalizó con {count} problema(s). Revisa la salida de la tarea."
    ),
    "{count} change applied and logged.": "{count} cambio aplicado y registrado.",
    "{count} changes applied and logged.": "{count} cambios aplicados y registrados.",
    "Restart Windows to finish applying kernel and network tweaks.": (
        "Reinicia Windows para terminar de aplicar los ajustes de núcleo y red."
    ),
    "LATENCY": "LATENCIA",
    "One or more changes take full effect after a reboot.": (
        "Uno o más cambios surten efecto completo tras reiniciar."
    ),
    "Apply staged changes?": "¿Aplicar los cambios preparados?",
    "Optimus X will write the selected registry values and service states. Previous values are saved to a local backup and can be restored from Settings.": (
        "Optimus X escribirá los valores del registro y los estados de servicio "
        "seleccionados. Los valores anteriores se guardan en una copia local y se "
        "pueden restaurar desde Configuración."
    ),
    "Apply now": "Aplicar ahora",
    "Applying these tweaks requires administrator rights.": (
        "Aplicar estos ajustes requiere derechos de administrador."
    ),
    "Applying system changes": "Aplicando cambios del sistema",
    "Apply the recommended profile?": "¿Aplicar el perfil recomendado?",
    "Optimus X will enable the recommended, reversible performance profile: background services, telemetry, kernel responsiveness, input latency, network throttling and privacy. Existing values are backed up first.": (
        "Optimus X activará el perfil de rendimiento recomendado y reversible: "
        "servicios en segundo plano, telemetría, respuesta del núcleo, latencia de "
        "entrada, limitación de red y privacidad. Los valores existentes se respaldan "
        "primero."
    ),
    "Apply recommended": "Aplicar recomendado",
    "Applying recommended profile": "Aplicando el perfil recomendado",
    "Recommended profile": "Perfil recomendado",
    "Apply the extreme profile?": "¿Aplicar el perfil extremo?",
    "Extreme mode enables every reversible tweak in the catalog, including advanced changes such as Windows Update manual mode, print spooler, Xbox services, visual effects and hardware GPU scheduling. Review the list before continuing.": (
        "El modo extremo activa todos los ajustes reversibles del catálogo, incluidos "
        "cambios avanzados como Windows Update en modo manual, la cola de impresión, "
        "los servicios de Xbox, los efectos visuales y la programación de GPU por "
        "hardware. Revisa la lista antes de continuar."
    ),
    "Applying extreme profile": "Aplicando el perfil extremo",
    "Ready": "Listo",
    "End processes": "Finalizar procesos",
    "End selected processes?": "¿Finalizar los procesos seleccionados?",
    "Unsaved work in these applications may be lost.": (
        "El trabajo no guardado en estas aplicaciones puede perderse."
    ),
    "Could not load tweak states: {error}": (
        "No se pudieron cargar los estados de los ajustes: {error}"
    ),
    "Power plan set to {name}.": "Plan de energía cambiado a {name}.",
    "I understand this may change system configuration": (
        "Entiendo que esto puede cambiar la configuración del sistema"
    ),
    "User temp, shader cache, crash dumps, thumbnails and Recycle Bin": (
        "Temporales del usuario, caché de sombreadores, volcados de fallos, "
        "miniaturas y Papelera"
    ),
    "\nRestoring selected tweaks…": "\nRestaurando los ajustes seleccionados…",
    "{count} change · {profile} · backup and restore point enabled": (
        "{count} cambio · {profile} · copia y punto de restauración activados"
    ),
    "{count} changes · {profile} · backup and restore point enabled": (
        "{count} cambios · {profile} · copia y punto de restauración activados"
    ),
    "Administrator rights required": "Se requieren derechos de administrador",
    "\n\nRestart Optimus X as administrator? Windows will show a UAC prompt.": (
        "\n\n¿Reiniciar Optimus X como administrador? Windows mostrará un aviso de UAC."
    ),
    "Administrator launch requested. Closing this window…": (
        "Se solicitó el inicio como administrador. Cerrando esta ventana…"
    ),
    "Elevation was cancelled or unavailable.": "La elevación se canceló o no está disponible.",
    # ------------------------------------------------------------- global errors
    "Could not open {name}: {error}": "No se pudo abrir {name}: {error}",
    "{name}: {error}": "{name}: {error}",
    "Could not refresh dashboard: {error}": "No se pudo actualizar el panel: {error}",
    "Background task failed: {error}": "La tarea en segundo plano falló: {error}",
    "Could not refresh system profile: {error}": (
        "No se pudo actualizar el perfil del sistema: {error}"
    ),
    "OPTIMUS X  •  v2.0  •  LOCAL ONLY": "OPTIMUS X  •  v2.0  •  SOLO LOCAL",
    "OPTIMUS X  •  v2.0": "OPTIMUS X  •  v2.0",
    "ADMINISTRATOR     ·     SYSTEM READY": (
        "ADMINISTRADOR     ·     SISTEMA LISTO"
    ),
    "STANDARD USER     ·     SYSTEM READY": (
        "USUARIO ESTÁNDAR     ·     SISTEMA LISTO"
    ),
    "CPU {cpu}%     ·     RAM {ram}%     ·     GPU {gpu}     ·     LATENCY {latency}": (
        "CPU {cpu}%     ·     RAM {ram}%     ·     GPU {gpu}     ·     LATENCIA {latency}"
    ),
}
