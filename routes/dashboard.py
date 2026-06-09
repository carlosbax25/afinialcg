from flask import Blueprint, render_template
from models import db, Factura, Equipo
import json
import plotly
import plotly.graph_objs as go

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/dashboard')
def index():
    facturas = Factura.query.order_by(Factura.periodo_inicio.asc()).all()
    equipos = Equipo.query.all()

    # Gráfico de consumo kWh por periodo
    grafico_consumo = generar_grafico_consumo(facturas)
    # Gráfico de costos
    grafico_costos = generar_grafico_costos(facturas)
    # Gráfico comparativo
    grafico_comparativo = generar_grafico_comparativo(facturas)
    # Resumen de equipos
    consumo_proyectado = sum(e.consumo_mensual_kwh for e in equipos)
    recomendaciones = generar_recomendaciones(equipos, facturas)

    return render_template('dashboard.html',
                           facturas=facturas,
                           grafico_consumo=grafico_consumo,
                           grafico_costos=grafico_costos,
                           grafico_comparativo=grafico_comparativo,
                           consumo_proyectado=round(consumo_proyectado, 2),
                           recomendaciones=recomendaciones,
                           total_equipos=len(equipos))


def generar_grafico_consumo(facturas):
    if not facturas:
        return None

    periodos = [f"{f.periodo_inicio.strftime('%b %Y')}" for f in facturas]
    consumos = [f.consumo_kwh for f in facturas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=periodos,
        y=consumos,
        name='Consumo kWh',
        marker_color='#2196F3',
        text=[f"{c} kWh" for c in consumos],
        textposition='auto'
    ))
    fig.update_layout(
        title='Consumo de Energía por Periodo (kWh)',
        xaxis_title='Periodo',
        yaxis_title='kWh',
        template='plotly_white',
        height=400
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def generar_grafico_costos(facturas):
    if not facturas:
        return None

    periodos = [f"{f.periodo_inicio.strftime('%b %Y')}" for f in facturas]
    costos = [f.costo_total for f in facturas]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=periodos,
        y=costos,
        mode='lines+markers+text',
        name='Costo Total',
        line=dict(color='#4CAF50', width=3),
        marker=dict(size=10),
        text=[f"${c:,.0f}" for c in costos],
        textposition='top center'
    ))
    fig.update_layout(
        title='Costo de Energía por Periodo ($)',
        xaxis_title='Periodo',
        yaxis_title='Costo ($)',
        template='plotly_white',
        height=400
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def generar_grafico_comparativo(facturas):
    if len(facturas) < 2:
        return None

    periodos = [f"{f.periodo_inicio.strftime('%b %Y')}" for f in facturas]
    consumos = [f.consumo_kwh for f in facturas]
    costos = [f.costo_total for f in facturas]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=periodos,
        y=consumos,
        name='Consumo (kWh)',
        marker_color='#2196F3',
        yaxis='y'
    ))
    fig.add_trace(go.Scatter(
        x=periodos,
        y=costos,
        name='Costo ($)',
        line=dict(color='#FF5722', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    fig.update_layout(
        title='Comparativo Consumo vs Costo',
        xaxis_title='Periodo',
        yaxis=dict(title='kWh', side='left'),
        yaxis2=dict(title='Costo ($)', side='right', overlaying='y'),
        template='plotly_white',
        height=400,
        legend=dict(x=0.01, y=0.99)
    )
    return json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)


def generar_recomendaciones(equipos, facturas):
    """Genera recomendaciones de ahorro basadas en el inventario de equipos."""
    recomendaciones = []

    equipos_pico = [e for e in equipos if e.es_horario_pico]
    if equipos_pico:
        nombres = ', '.join([e.nombre for e in equipos_pico])
        ahorro_estimado = sum(e.consumo_mensual_kwh * 0.15 for e in equipos_pico)
        recomendaciones.append({
            'tipo': 'horario',
            'icono': '⏰',
            'titulo': 'Mover equipos fuera de horario pico',
            'detalle': f'Los equipos: {nombres} están programados en horario pico (17:00-21:00). '
                       f'Moverlos a horario valle podría ahorrar ~{ahorro_estimado:.1f} kWh/mes.',
            'prioridad': 'alta'
        })

    equipos_alto_consumo = sorted(equipos, key=lambda e: e.consumo_mensual_kwh, reverse=True)[:3]
    for equipo in equipos_alto_consumo:
        if equipo.consumo_mensual_kwh > 50:
            recomendaciones.append({
                'tipo': 'consumo',
                'icono': '⚡',
                'titulo': f'Alto consumo: {equipo.nombre}',
                'detalle': f'{equipo.nombre} consume {equipo.consumo_mensual_kwh:.1f} kWh/mes. '
                           f'Considere reducir su uso diario de {equipo.horas_uso_diario}h a '
                           f'{equipo.horas_uso_diario * 0.8:.1f}h.',
                'prioridad': 'media'
            })

    if len(facturas) >= 2:
        ultima = facturas[-1]
        anterior = facturas[-2]
        if ultima.consumo_kwh > anterior.consumo_kwh:
            incremento = ((ultima.consumo_kwh - anterior.consumo_kwh) / anterior.consumo_kwh) * 100
            recomendaciones.append({
                'tipo': 'tendencia',
                'icono': '📈',
                'titulo': 'Consumo en aumento',
                'detalle': f'Su consumo aumentó {incremento:.1f}% respecto al mes anterior. '
                           f'Revise los equipos que más consumen.',
                'prioridad': 'alta'
            })
        else:
            reduccion = ((anterior.consumo_kwh - ultima.consumo_kwh) / anterior.consumo_kwh) * 100
            recomendaciones.append({
                'tipo': 'tendencia',
                'icono': '📉',
                'titulo': 'Buen trabajo, consumo en reducción',
                'detalle': f'Su consumo se redujo {reduccion:.1f}% respecto al mes anterior. '
                           f'Siga así.',
                'prioridad': 'baja'
            })

    if not recomendaciones:
        recomendaciones.append({
            'tipo': 'info',
            'icono': '💡',
            'titulo': 'Agregue equipos para obtener recomendaciones',
            'detalle': 'Registre sus equipos eléctricos en el inventario para recibir '
                       'recomendaciones personalizadas de ahorro.',
            'prioridad': 'info'
        })

    return recomendaciones
