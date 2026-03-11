# python -m pip install paddlepaddle==2.6.2 -i https://www.paddlepaddle.org.cn/packages/stable/cpu/
import os
import re
from paddleocr import PaddleOCR


# ===============================
# 0. Ruta a tu foto del ticket
# ===============================
ruta_imagen = "procesar_ticket/tickets_imgs/ticket1.jpg"
if not os.path.exists(ruta_imagen):
    print(f"ERROR: No se encuentra la imagen en:\n{ruta_imagen}")
    exit()

# ===============================
# 1. Crear objeto OCR
# ===============================
ocr = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    det_model_dir='C:/paddleocr_models/en/en_PP-OCRv3_det_infer',
    rec_model_dir='C:/paddleocr_models/en/en_PP-OCRv4_rec_infer',
    cls_model_dir='C:/paddleocr_models/en/ch_ppocr_mobile_v2.0_cls_infer'
)

# ===============================
# 2. Ejecutar OCR
# ===============================
print(f"\nProcesando: {os.path.basename(ruta_imagen)} ...")
resultado = ocr.ocr(ruta_imagen, cls=True)

# ===============================
# 3. Guardar todo el texto limpio en una lista
# ===============================
lineas_texto = [linea[1][0].strip() for bloque in resultado for linea in bloque]

# ===============================
# 4. Mostrar texto raw reconocido
# ===============================
print("\n" + "=" * 60)
print("TEXTO RAW RECONOCIDO DEL TICKET:\n")
for l in lineas_texto:
    print(l)
print("=" * 60)

# ===============================
# 5. Encontrar la sección de productos
# ===============================
try:
    idx_inicio = next(i for i, l in enumerate(lineas_texto) if "Descripcion" in l)
except StopIteration:
    print("No se encontró la palabra 'Descripcion' en el ticket")
    idx_inicio = 0

productos = lineas_texto[idx_inicio + 1:]

# ===============================
# 6. Extraer productos robustamente
# ===============================
resultado_productos = []

precio_temp = None
unidad_temp = None
nombre_temp = None

# patrones
patron_precio = re.compile(r'^\d+[.,]\d{2}$')
patron_unidad_nombre = re.compile(r'^(\d+)?\s*(.+)$')  # detecta posible unidad al inicio

for linea in productos:
    linea = linea.strip().replace(",", ".")
    if not linea:
        continue

    # Detectar precio
    if patron_precio.match(linea):
        precio_temp = linea
        # Guardar producto si tenemos nombre + unidad
        if nombre_temp:
            if not unidad_temp:
                unidad_temp = "1"
            resultado_productos.append(f"{nombre_temp} - {unidad_temp} - {precio_temp}")
            nombre_temp = None
            unidad_temp = None
            precio_temp = None
        continue

    # Detectar unidad + nombre
    m = patron_unidad_nombre.match(linea)
    if m:
        uni = m.group(1)
        nom = m.group(2).strip()
        if uni:
            unidad_temp = uni
        else:
            unidad_temp = "1"
        nombre_temp = nom
        # Si ya tenemos precio temporal previo, asociarlo
        if precio_temp:
            resultado_productos.append(f"{nombre_temp} - {unidad_temp} - {precio_temp}")
            nombre_temp = None
            unidad_temp = None
            precio_temp = None

# ===============================
# 7. Mostrar productos postprocesados
# ===============================
print("\nPRODUCTOS EXTRAÍDOS POSTPROCESADOS:")
print("=" * 60)
for p in resultado_productos:
    print(p)