# CleanerKota

Bot para Windows basado en template matching de OpenCV y entradas de PyDirectInput, siguiendo la base de Forabot.

## Preparación

```powershell
python -m pip install -r requirements.txt
```

Mantén el juego visible en el monitor principal. Los recursos `resource/dirty.png` y `resource/add.png` deben coincidir con la escala y apariencia del juego. No cambies la resolución, posición de la ventana ni escala de interfaz después de grabar.

## Registrar el patrón pendiente

```powershell
python record_clicks.py
```

Tienes 5 segundos para volver al juego. Haz clic izquierdo en cada ubicación deseada, en orden. Pulsa **F8** para terminar y guardar `pattern.json`. Los clics también llegan al juego. El archivo anterior se reemplaza si registras puntos; sin puntos se conserva. Puedes usar `--output otro_patron.json` para guardar otra versión.

El bot se niega a ejecutarse con el patrón vacío. Los clics sirven para capturar coordenadas; al limpiar, el bot mueve el cursor por ellas, sin reproducir los clics. Se posiciona en el primer punto y recorre cada tramo en línea recta durante 0,2 segundos, enviando posiciones intermedias.

## Ejecutar

```powershell
python main.py
```

Tras 5 segundos de preparación, detecta `dirty.png`, espera 3 segundos, confirma que sigue visible y recorre el patrón. Espera 2 segundos, busca `add.png` durante un máximo de 15 segundos y hace clic en su centro para guardar. Después de pulsar el botón, espera 3 segundos y vuelve a buscar suciedad, repitiendo el flujo continuamente. Si no aparece el botón, se detiene. Usa `--once` solo si quieres completar un único ciclo.

```powershell
python main.py
python main.py --hold-left --move-duration 0.2
python main.py --threshold 0.85 --save-timeout 20 --pattern otro_patron.json
```

`--hold-left` mantiene el botón izquierdo pulsado durante el recorrido, si la limpieza lo requiere. `--move-duration` ajusta los segundos que dura cada desplazamiento (por defecto 0.2). `--point-delay` agrega una pausa al llegar a cada punto (por defecto 0). `--threshold` controla la similitud mínima, de 0 a 1 (por defecto 0.8).

Pulsa **F8** para detener o **Ctrl+C** en la consola. PyDirectInput conserva su parada de emergencia al llevar el cursor a la esquina superior izquierda. La resolución del patrón se comprueba antes de iniciar; la posición de la ventana debe mantenerse manualmente.

La detección y el recorrido requieren validación dentro del juego; el patrón real queda a cargo del registro de coordenadas.
