import cv2
import easyocr
import re
import requests
from typing import List, Dict

def preprocess_and_read(image_path: str, languages: List[str] = ['es']):
    """
    Preprocesa la imagen (mejora contraste y elimina ruido) y hace OCR con EasyOCR.
    Soporta perfectamente español.
    """
    # Cargar y preprocesar (OpenCV)
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError("No se pudo leer la imagen. Comprueba la ruta.")
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Reducción de ruido + mejora de contraste (ideal para tickets)
    denoised = cv2.fastNlMeansDenoising(gray)
    enhanced = cv2.convertScaleAbs(denoised, alpha=1.3, beta=-5) # CONTRASTE, BRILLO

    # ← Aquí mostramos la imagen preprocesada final
    cv2.imshow("Imagen preprocesada", enhanced)
    cv2.waitKey(0)              # Pulsa cualquier tecla para cerrar
    cv2.destroyAllWindows()
    
    # EasyOCR (descarga modelos la primera vez, ~100 MB)
    reader = easyocr.Reader(languages, gpu=False)  # gpu=True si tienes CUDA
    result = reader.readtext(enhanced, detail=0, paragraph=False)
    text = '\n'.join(result)
    return text

def parse_products(text: str) -> List[Dict]:
    """
    Parser adaptado a tickets donde nombre y precio suelen estar en líneas consecutivas.
    - Ignora cabecera y pie de ticket
    - Solo considera líneas con letras como posible nombre
    - Toma la línea siguiente como precio si parece numérico
    """
    text = text.upper()
    lines = [line.strip() for line in text.split('\n') if line.strip()]
    
    products = []
    i = 0
    
    while i < len(lines) - 1:
        curr = lines[i]
        nxt = lines[i + 1]
        
        # Línea parece nombre si tiene letras y longitud razonable
        if re.search(r'[A-ZÁÉÍÓÚÑ]{3,}', curr) and len(curr) >= 6:
            
            # Intentar extraer precio de la siguiente línea
            # Acepta formatos muy sucios: 3,00]  4, 20  1,65  7 ,98  4 4  15  2,6u)
            price_raw = re.sub(r'[^0-9.,]', '', nxt)  # solo números, coma, punto
            price_raw = price_raw.replace(',', '.').strip()
            
            # Corregir decimales rotos (4 4 → 4.40, 2 6 → 2.60, 15 → 15.00)
            if '.' not in price_raw and len(price_raw) <= 3:
                if len(price_raw) <= 2:
                    price_raw += '.00'
                else:
                    price_raw = price_raw[:-2] + '.' + price_raw[-2:]
            elif '.' in price_raw and len(price_raw.split('.')[-1]) == 1:
                price_raw += '0'
            
            # Validar que sea precio razonable (0.01 a 99.99)
            try:
                price_float = float(price_raw)
                if 0.01 <= price_float <= 99.99:
                    # Limpieza nombre
                    name = re.sub(r'^\s*\d+[xX]?\s*', '', curr).strip()
                    name = re.sub(r'\s{2,}', ' ', name)
                    
                    if len(name) >= 5:
                        products.append({
                            'raw_name': curr,
                            'raw_price': nxt,
                            'product_name': name,
                            'price': price_raw,
                        })
                        i += 2  # saltamos la línea del precio
                        continue
            except ValueError:
                pass
        
        i += 1
    
    return products

def search_openfoodfacts(product_name: str, limit: int = 1):
    """
    Busca el producto en Open Food Facts (API pública y gratuita).
    Devuelve el primer resultado con barcode, nombre oficial, Nutri-Score, etc.
    """
    url = "https://world.openfoodfacts.org/cgi/search.pl"
    params = {
        'search_terms': product_name,
        'search_simple': 1,
        'action': 'process',
        'json': 1,
        'page_size': limit
    }
    try:
        r = requests.get(url, params=params, timeout=6)
        data = r.json()
        products = data.get('products', [])
        if products:
            p = products[0]
            return {
                'barcode': p.get('code'),
                'name': p.get('product_name_es') or p.get('product_name'),
                'nutriscore': p.get('nutriscore_grade'),
                'brands': p.get('brands'),
                'image_url': p.get('image_url')
            }
    except:
        pass
    return None

# ====================== USO ======================
if __name__ == "__main__":
    image_path = "procesar_ticket/tickets_imgs/ticket1.jpg"
    
    print("🔍 Leyendo ticket con EasyOCR...")
    text = preprocess_and_read(image_path)
    
    print("\n📄 Texto detectado (primeras líneas):")
    print(text[:600] + "..." if len(text) > 600 else text)
    
    products = parse_products(text)
    
    print(f"\n✅ Productos detectados: {len(products)}")
    for i, p in enumerate(products, 1):
        print(f"\n{i}. {p['product_name']}")
        print(f"   Precio: {p['price']} €")
        
        # Para depurar (puedes comentarlo después)
        # print(f"   Raw nombre: {p['raw_name']}")
        # print(f"   Raw precio: {p['raw_price']}")
        
        # === ENLACE CON OPEN FOOD FACTS (descomenta si quieres) ===
        # off = search_openfoodfacts(p['product_name'])
        # if off:
        #     print(f"   → OFF: {off['name']} | Nutri-Score: {off['nutriscore']} | Barcode: {off['barcode']}")