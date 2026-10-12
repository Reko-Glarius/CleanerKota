# CleanerKota

Bot para Windows basado en template matching de OpenCV y entradas de PyDirectInput, siguiendo la base de Forabot. Detecta suciedad, recorre un patrón de coordenadas y pulsa el botón de guardar; repite el proceso hasta que lo detengas o no encuentre el botón.

## Preparación

Necesitas Python y las dependencias del proyecto:

```powershell
python -m pip install -r requirements.txt
```

Mantén el juego visible en el monitor principal. Los recursos `resource/dirty.png` y `resource/add.png` deben coincidir con la escala y apariencia del juego. No cambies la resolución, posición de la ventana ni escala de interfaz después de grabar.

El repositorio incluye las dos imágenes de referencia y un `pattern.json` con 16 puntos registrado para una pantalla de **1920 × 1080**. Si las coordenadas no corresponden a tu juego, registra tu propio patrón. Tener la misma resolución no garantiza que la ventana esté en la posición correcta.

## Registrar un patrón

```powershell
python record_clicks.py
```

Tienes 5 segundos para volver al juego antes de que comience el registro. Haz clic izquierdo en cada ubicación deseada, en orden. Pulsa **F8** para terminar y guardar `pattern.json`. Los clics también llegan al juego. El archivo anterior se reemplaza si registras puntos; sin puntos se conserva. Puedes usar `--output otro_patron.json` para guardar otra versión.

El archivo guarda la resolución de pantalla y las coordenadas enteras `x` e `y` de cada punto. El bot se niega a ejecutarse con un patrón vacío y comprueba que la resolución coincida con la registrada.

Los clics sirven para capturar coordenadas; al limpiar, el bot mueve el cursor por ellas, sin reproducir los clics. Se posiciona en el primer punto y recorre cada tramo en línea recta durante **0,3 segundos** por defecto, enviando posiciones intermedias.

## Ejecutar

```powershell
python main.py
```

El flujo actual es:

1. Espera 5 segundos para que vuelvas al juego.
2. Busca `dirty.png`; si no lo detecta, vuelve a comprobar cada 0,25 segundos.
3. Al detectarlo, espera 0,25 segundos y confirma que sigue visible.
4. Recorre el patrón y espera 0,25 segundos.
5. Busca `add.png` durante un máximo de 15 segundos, comprobando cada 0,25 segundos, y hace clic en su centro para guardar. Si no aparece el botón, se detiene.
6. Tras guardar, espera 0,1 segundos y vuelve a buscar suciedad. Con `--once`, termina después del primer ciclo guardado.

### Opciones

| Opción | Valor predeterminado | Función |
| --- | --- | --- |
| `--pattern` | `pattern.json` junto a `main.py` | Archivo con el recorrido y la resolución registrada. |
| `--threshold` | `0.6` | Similitud mínima para ambas imágenes; debe ser mayor que 0 y menor o igual que 1. |
| `--move-duration` | `0.3` | Segundos por tramo; debe ser un número finito mayor que 0. |
| `--point-delay` | `0` | Pausa adicional al llegar a cada punto después del primero; debe ser mayor o igual que 0. |
| `--save-timeout` | `15` | Tiempo máximo en segundos para buscar el botón de guardar; debe ser mayor que 0. |
| `--hold-left` | Desactivado | Mantiene el botón izquierdo pulsado durante el recorrido y lo libera al finalizar. |
| `--once` | Desactivado | Completa un único ciclo. |

Ejemplos:

```powershell
python main.py --once
python main.py --hold-left --move-duration 0.2
python main.py --threshold 0.85 --save-timeout 20 --pattern otro_patron.json
```

## Detener

Pulsa **F8** para detener o **Ctrl+C** en la consola. PyDirectInput conserva su parada de emergencia al llevar el cursor a la esquina superior izquierda. La posición de la ventana debe mantenerse manualmente.

La detección y el recorrido requieren validación dentro del juego. Ajusta las imágenes de referencia, el umbral y las coordenadas según tu configuración.

## Interfaz gráfica

```powershell
python gui.py
```

La ventana permite elegir el patrón, ajustar las mismas opciones que la consola y pulsar **Comenzar** o **Detener**. Usa el mismo motor de `main.py`, con los mismos tiempos y valores predeterminados. El proceso corre en segundo plano para que la ventana siga respondiendo. F8 y la parada de emergencia también funcionan en esta versión; cerrar la ventana solicita la parada y espera a que el motor se detenga y libere el botón del mouse.

## Ejecutable para Windows

La compilación genera un único `CleanerKota.exe` con Python, las dependencias, las dos imágenes y el patrón predeterminado incluidos. Puedes ejecutarlo sin instalar Python. Para usar otro patrón, selecciónalo en la ventana o coloca un `pattern.json` junto al ejecutable; ese archivo tiene prioridad sobre el incluido.

### Generar el EXE localmente

Desde Windows, con Python 3.12:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-build.txt
python -m unittest discover -s tests -v
.\build_exe.ps1
```

El resultado queda en `dist/CleanerKota.exe`. `CleanerKota.spec` define el empaquetado con PyInstaller; `build/`, `dist/` y `.venv/` están excluidos del repositorio.

### Descargas en GitHub

El flujo **Build Windows EXE** compila y verifica la aplicación en Windows cuando se suben cambios del bot, recursos o configuración de compilación a `main`. También puede ejecutarse manualmente desde **Actions → Build Windows EXE → Run workflow**, seleccionando `main`.

Cada ejecución correcta publica una release con su propio tag `build-<ejecución>-<intento>`, el commit usado y `CleanerKota.exe` como descarga. Las versiones anteriores permanecen disponibles y la nueva se marca como la más reciente. El ejecutable también se conserva como artefacto de Actions.

Una vez publicada la primera compilación con este flujo:

- [Descargar el EXE más reciente](https://github.com/Reko-Glarius/CleanerKota/releases/latest/download/CleanerKota.exe)
- [Ver todas las versiones](https://github.com/Reko-Glarius/CleanerKota/releases)

El workflow necesita GitHub Actions habilitado y permiso de escritura de contenido para publicar releases. El EXE se distribuye a través de releases, sin incluir el binario en el historial del código.
