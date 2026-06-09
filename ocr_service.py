"""
Servicio de OCR para extraer datos de facturas de energía de Afinia.
Utiliza EasyOCR (carga lazy para no ralentizar el inicio de la app).
Si EasyOCR no está disponible, se puede usar ingreso manual.
"""
import re
from datetime import datetime

_reader = None
_ocr_available = None


def _check_ocr():
    """Verifica si easyocr está disponible sin importarlo completamente."""
    global _ocr_available
    if _ocr_available is None:
        try:
            import importlib
            importlib.import_module('easyocr')
            _ocr_available = True
        except ImportError:
            _ocr_available = False
    return _ocr_available


def _get_reader():
    """Inicializa el reader de EasyOCR de forma lazy."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(['es'], gpu=False)
    return _reader


def extraer_datos_factura(imagen_path):
    """
    Extrae datos relevantes de una imagen de factura de Afinia.
    Retorna (datos_dict, error_string).
    """
    if not _check_ocr():
        return None, ("EasyOCR no está instalado. Ejecute: pip install easyocr. "
                      "La primera ejecución descarga el modelo (~100MB). "
                      "Mientras tanto, puede ingresar datos manualmente.")

    try:
        reader = _get_reader()
        resultados = reader.readtext(imagen_path)
        texto = '\n'.join([r[1] for r in resultados])
        datos = parsear_texto_factura(texto)
        return datos, None
    except Exception as e:
        return None, f"Error procesando imagen: {str(e)}"


def parsear_texto_factura(texto):
    """
    Parsea el texto extraído por OCR y busca los campos relevantes
    de una factura de Afinia (Caribemar de la Costa).
    """
    datos = {
        'periodo_inicio': None,
        'periodo_fin': None,
        'consumo_kwh': None,
        'costo_total': None,
        'promedio_diario_kwh': None
    }

    # Buscar periodo facturado: formato "DD/MM/YYYY - DD/MM/YYYY"
    periodo_pattern = r'(\d{2}/\d{2}/\d{4})\s*[-–~]\s*(\d{2}/\d{2}/\d{4})'
    match = re.search(periodo_pattern, texto)
    if match:
        try:
            datos['periodo_inicio'] = datetime.strptime(match.group(1), '%d/%m/%Y').date()
            datos['periodo_fin'] = datetime.strptime(match.group(2), '%d/%m/%Y').date()
        except ValueError:
            pass

    # Buscar Total a Pagar o Total Mes
    total_patterns = [
        r'Total\s+a\s+Pagar[:\s]*\$?\s*([\d.,]+)',
        r'Total\s+Mes[:\s]*\$?\s*([\d.,]+)',
        r'Total\s+mes[:\s]*\$?\s*([\d.,]+)',
    ]
    for pattern in total_patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            valor = match.group(1).replace('.', '').replace(',', '.')
            try:
                datos['costo_total'] = float(valor)
                break
            except ValueError:
                continue

    # Buscar Promedio Consumo Diario
    promedio_patterns = [
        r'Promedio\s+Consumo\s+Diario\s*\[?kWh\]?[:\s]*([\d.,]+)',
        r'Promedio\s+Consumo\s+Diario.*?([\d]+[.,]\d+)',
        r'[Pp]romedio.*?[Dd]iario.*?([\d]+[.,]\d+)',
    ]
    for pattern in promedio_patterns:
        match = re.search(pattern, texto, re.IGNORECASE)
        if match:
            valor = match.group(1).replace(',', '.')
            try:
                datos['promedio_diario_kwh'] = float(valor)
                break
            except ValueError:
                continue

    # Calcular consumo total si tenemos promedio diario y periodo
    if datos['promedio_diario_kwh'] and datos['periodo_inicio'] and datos['periodo_fin']:
        dias = (datos['periodo_fin'] - datos['periodo_inicio']).days
        if dias > 0:
            datos['consumo_kwh'] = round(datos['promedio_diario_kwh'] * dias, 2)

    # Si no se pudo calcular, buscar en histograma
    if not datos['consumo_kwh']:
        kwh_patterns = [
            r'[Pp]eriodo\s+actual\s*\(?kWh\)?[:\s]*([\d]+)',
        ]
        for pattern in kwh_patterns:
            matches = re.findall(pattern, texto)
            if matches:
                try:
                    datos['consumo_kwh'] = float(matches[-1])
                    break
                except ValueError:
                    continue

    return datos
