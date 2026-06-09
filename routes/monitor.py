from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, LecturaContador, ConfiguracionMeta
from datetime import datetime, date
from sqlalchemy import desc

monitor_bp = Blueprint('monitor', __name__)


def get_config():
    """Obtiene o crea la configuración del usuario."""
    config = ConfiguracionMeta.query.first()
    if not config:
        config = ConfiguracionMeta(
            costo_maximo_mes=700000,
            tarifa_kwh=850,
            fecha_inicio_ciclo=date.today().replace(day=1),
        )
        db.session.add(config)
        db.session.commit()
    return config


@monitor_bp.route('/')
@monitor_bp.route('/monitor')
def index():
    config = get_config()
    lecturas = LecturaContador.query.order_by(desc(LecturaContador.fecha_lectura)).all()

    # Calcular consumo acumulado del ciclo actual
    consumo_actual = 0
    kwh_maximo = 0
    porcentaje = 0
    costo_estimado = 0
    promedio_diario = 0
    dias_transcurridos = 0
    dias_restantes = 0
    proyeccion_fin_mes = 0
    costo_total_estimado = 0

    if config.tarifa_kwh and config.costo_maximo_mes:
        # Descontar cargos fijos para saber cuánto queda para energía pura
        kwh_maximo = config.kwh_maximo

    if lecturas and config.lectura_inicio_ciclo is not None:
        lectura_mas_reciente = lecturas[0]
        consumo_actual = lectura_mas_reciente.lectura_kwh - config.lectura_inicio_ciclo

        if consumo_actual < 0:
            consumo_actual = 0

        costo_estimado = consumo_actual * config.tarifa_kwh
        costo_total_estimado = costo_estimado + config.total_cargos_fijos

        if kwh_maximo > 0:
            porcentaje = (consumo_actual / kwh_maximo) * 100

        # Calcular promedio diario y proyección
        if config.fecha_inicio_ciclo:
            dias_transcurridos = (date.today() - config.fecha_inicio_ciclo).days
            if dias_transcurridos > 0:
                promedio_diario = consumo_actual / dias_transcurridos

            if config.fecha_fin_ciclo:
                dias_restantes = (config.fecha_fin_ciclo - date.today()).days
                dias_total_ciclo = (config.fecha_fin_ciclo - config.fecha_inicio_ciclo).days
            else:
                dias_restantes = 30 - dias_transcurridos
                dias_total_ciclo = 30

            if promedio_diario > 0:
                proyeccion_fin_mes = promedio_diario * dias_total_ciclo

    # Determinar estado del semáforo
    if porcentaje <= 60:
        estado = 'verde'
        estado_texto = 'Vas bien, consumo bajo control'
        estado_color = '#4CAF50'
    elif porcentaje <= 85:
        estado = 'naranja'
        estado_texto = 'Atención, acercándose al límite'
        estado_color = '#FF9800'
    else:
        estado = 'rojo'
        estado_texto = 'Alerta! Cerca o superando el tope'
        estado_color = '#F44336'

    return render_template('monitor.html',
                           config=config,
                           lecturas=lecturas[:20],
                           consumo_actual=round(consumo_actual, 2),
                           costo_estimado=round(costo_estimado, 0),
                           costo_total_estimado=round(costo_total_estimado, 0),
                           kwh_maximo=round(kwh_maximo, 1),
                           porcentaje=round(porcentaje, 1),
                           promedio_diario=round(promedio_diario, 2),
                           dias_transcurridos=dias_transcurridos,
                           dias_restantes=max(dias_restantes, 0),
                           proyeccion_fin_mes=round(proyeccion_fin_mes, 1),
                           costo_proyectado=round((proyeccion_fin_mes * config.tarifa_kwh) + config.total_cargos_fijos, 0) if proyeccion_fin_mes else 0,
                           estado=estado,
                           estado_texto=estado_texto,
                           estado_color=estado_color)


@monitor_bp.route('/monitor/lectura', methods=['POST'])
def registrar_lectura():
    try:
        lectura_kwh = float(request.form['lectura_kwh'])
        fecha_str = request.form.get('fecha_lectura')
        nota = request.form.get('nota', '').strip()

        if fecha_str:
            fecha_lectura = datetime.fromisoformat(fecha_str)
        else:
            fecha_lectura = datetime.now()

        lectura = LecturaContador(
            lectura_kwh=lectura_kwh,
            fecha_lectura=fecha_lectura,
            nota=nota if nota else None
        )
        db.session.add(lectura)
        db.session.commit()
        flash(f'Lectura {lectura_kwh} kWh registrada correctamente', 'success')
    except Exception as e:
        flash(f'Error al registrar lectura: {str(e)}', 'error')

    return redirect(url_for('monitor.index'))


@monitor_bp.route('/monitor/configurar', methods=['GET', 'POST'])
def configurar():
    config = get_config()

    if request.method == 'POST':
        try:
            config.costo_maximo_mes = float(request.form.get('costo_maximo_mes', 700000))
            config.tarifa_kwh = float(request.form.get('tarifa_kwh', 850))

            # Cargos fijos / impuestos
            config.aseo = float(request.form.get('aseo', 0) or 0)
            config.alumbrado_publico = float(request.form.get('alumbrado_publico', 0) or 0)
            config.tasa_seguridad = float(request.form.get('tasa_seguridad', 0) or 0)

            lectura_inicio = request.form.get('lectura_inicio_ciclo')
            if lectura_inicio:
                config.lectura_inicio_ciclo = float(lectura_inicio)

            fecha_inicio = request.form.get('fecha_inicio_ciclo')
            if fecha_inicio:
                config.fecha_inicio_ciclo = date.fromisoformat(fecha_inicio)

            fecha_fin = request.form.get('fecha_fin_ciclo')
            if fecha_fin:
                config.fecha_fin_ciclo = date.fromisoformat(fecha_fin)

            db.session.commit()
            flash('Configuración actualizada', 'success')
            return redirect(url_for('monitor.index'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')

    return render_template('monitor_config.html', config=config)


@monitor_bp.route('/monitor/nuevo-ciclo', methods=['POST'])
def nuevo_ciclo():
    """Inicia un nuevo ciclo de facturación con la lectura actual como base."""
    config = get_config()
    ultima_lectura = LecturaContador.query.order_by(desc(LecturaContador.fecha_lectura)).first()

    if ultima_lectura:
        config.lectura_inicio_ciclo = ultima_lectura.lectura_kwh
        config.fecha_inicio_ciclo = date.today()
        config.fecha_fin_ciclo = None
        db.session.commit()
        flash(f'Nuevo ciclo iniciado con lectura base: {ultima_lectura.lectura_kwh} kWh', 'success')
    else:
        flash('Registre al menos una lectura antes de iniciar un nuevo ciclo', 'warning')

    return redirect(url_for('monitor.index'))


@monitor_bp.route('/monitor/eliminar/<int:id>', methods=['POST'])
def eliminar_lectura(id):
    lectura = LecturaContador.query.get_or_404(id)
    db.session.delete(lectura)
    db.session.commit()
    flash('Lectura eliminada', 'success')
    return redirect(url_for('monitor.index'))
