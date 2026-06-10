from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, Equipo

inventory_bp = Blueprint('inventory', __name__)


@inventory_bp.route('/inventario')
def listar():
    equipos = Equipo.query.all()
    equipos.sort(key=lambda e: e.consumo_mensual_kwh, reverse=True)
    # Calcular totales
    total_consumo_diario = sum(e.consumo_diario_kwh for e in equipos)
    total_consumo_mensual = sum(e.consumo_mensual_kwh for e in equipos)

    return render_template('inventory.html',
                           equipos=equipos,
                           total_consumo_diario=round(total_consumo_diario, 2),
                           total_consumo_mensual=round(total_consumo_mensual, 2))


def _calcular_horas(form):
    """Convierte tiempo de uso a horas (acepta horas o minutos)."""
    tiempo = float(form['tiempo_uso'])
    unidad = form.get('unidad_tiempo', 'horas')
    if unidad == 'minutos':
        return tiempo / 60
    return tiempo


@inventory_bp.route('/inventario/agregar', methods=['GET', 'POST'])
def agregar():
    if request.method == 'POST':
        try:
            equipo = Equipo(
                nombre=request.form['nombre'],
                potencia_watts=float(request.form['potencia_watts']),
                horas_uso_diario=_calcular_horas(request.form),
                horario_inicio=request.form.get('horario_inicio') or None,
                horario_fin=request.form.get('horario_fin') or None,
                dias_uso_mes=int(request.form.get('dias_uso_mes', 30))
            )
            db.session.add(equipo)
            db.session.commit()
            flash(f'Equipo "{equipo.nombre}" agregado exitosamente', 'success')
            return redirect(url_for('inventory.listar'))
        except Exception as e:
            flash(f'Error al agregar equipo: {str(e)}', 'error')

    return render_template('inventory_form.html', equipo=None)


@inventory_bp.route('/inventario/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    equipo = Equipo.query.get_or_404(id)

    if request.method == 'POST':
        try:
            equipo.nombre = request.form['nombre']
            equipo.potencia_watts = float(request.form['potencia_watts'])
            equipo.horas_uso_diario = _calcular_horas(request.form)
            equipo.horario_inicio = request.form.get('horario_inicio') or None
            equipo.horario_fin = request.form.get('horario_fin') or None
            equipo.dias_uso_mes = int(request.form.get('dias_uso_mes', 30))
            db.session.commit()
            flash(f'Equipo "{equipo.nombre}" actualizado', 'success')
            return redirect(url_for('inventory.listar'))
        except Exception as e:
            flash(f'Error al actualizar: {str(e)}', 'error')

    return render_template('inventory_form.html', equipo=equipo)


@inventory_bp.route('/inventario/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    equipo = Equipo.query.get_or_404(id)
    nombre = equipo.nombre
    db.session.delete(equipo)
    db.session.commit()
    flash(f'Equipo "{nombre}" eliminado', 'success')
    return redirect(url_for('inventory.listar'))
