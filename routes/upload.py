from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from models import db, Factura
from ocr_service import extraer_datos_factura
from datetime import date
from werkzeug.utils import secure_filename
import os

upload_bp = Blueprint('upload', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@upload_bp.route('/upload', methods=['GET', 'POST'])
def upload():
    if request.method == 'POST':
        # Verificar si se subió archivo
        if 'factura_img' not in request.files:
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        file = request.files['factura_img']
        if file.filename == '':
            flash('No se seleccionó ningún archivo', 'error')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            # Intentar OCR
            datos, error = extraer_datos_factura(filepath)

            if error:
                flash(f'Error en OCR: {error}. Ingrese los datos manualmente.', 'warning')
                return render_template('upload.html', manual=True, imagen=filename)

            if datos and datos['costo_total']:
                # Si OCR extrajo datos, mostrar para confirmación
                return render_template('upload.html',
                                       datos=datos,
                                       imagen=filename,
                                       confirmar=True)
            else:
                flash('No se pudieron extraer datos automáticamente. Ingrese manualmente.', 'warning')
                return render_template('upload.html', manual=True, imagen=filename)
        else:
            flash('Formato de archivo no permitido. Use PNG, JPG, BMP o TIFF.', 'error')
            return redirect(request.url)

    return render_template('upload.html')


@upload_bp.route('/upload/guardar', methods=['POST'])
def guardar_factura():
    try:
        periodo_inicio = date.fromisoformat(request.form['periodo_inicio'])
        periodo_fin = date.fromisoformat(request.form['periodo_fin'])
        consumo_kwh = float(request.form['consumo_kwh'])
        costo_total = float(request.form['costo_total'])
        promedio_diario = request.form.get('promedio_diario_kwh')
        imagen = request.form.get('imagen', '')

        # Impuestos / cargos fijos
        costo_energia = request.form.get('costo_energia')
        aseo = request.form.get('aseo')
        alumbrado = request.form.get('alumbrado_publico')
        tasa = request.form.get('tasa_seguridad')

        factura = Factura(
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            consumo_kwh=consumo_kwh,
            costo_total=costo_total,
            costo_energia=float(costo_energia) if costo_energia else None,
            aseo=float(aseo) if aseo else 0,
            alumbrado_publico=float(alumbrado) if alumbrado else 0,
            tasa_seguridad=float(tasa) if tasa else 0,
            promedio_diario_kwh=float(promedio_diario) if promedio_diario else None,
            imagen_path=imagen
        )
        db.session.add(factura)
        db.session.commit()
        flash('Factura registrada exitosamente', 'success')
        return redirect(url_for('dashboard.index'))
    except Exception as e:
        flash(f'Error al guardar: {str(e)}', 'error')
        return redirect(url_for('upload.upload'))
