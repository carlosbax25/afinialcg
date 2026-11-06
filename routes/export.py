from flask import Blueprint, send_file
from models import db, Factura, LecturaContador, Equipo, ConfiguracionMeta
import pandas as pd
import io
from datetime import datetime

export_bp = Blueprint('export', __name__)


@export_bp.route('/exportar')
def exportar_excel():
    """Exporta todos los datos a un archivo Excel con múltiples hojas."""

    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:

        # --- Hoja 1: Facturas ---
        facturas = Factura.query.order_by(Factura.periodo_inicio.asc()).all()
        if facturas:
            df_facturas = pd.DataFrame([{
                'Periodo Inicio': f.periodo_inicio.strftime('%d/%m/%Y'),
                'Periodo Fin': f.periodo_fin.strftime('%d/%m/%Y'),
                'Consumo (kWh)': f.consumo_kwh,
                'Costo Energía ($)': f.costo_energia or '',
                'Aseo ($)': f.aseo or 0,
                'Alumbrado Público ($)': f.alumbrado_publico or 0,
                'Tasa Seguridad ($)': f.tasa_seguridad or 0,
                'Total Impuestos ($)': f.total_impuestos,
                'Costo Total ($)': f.costo_total,
                'Promedio Diario (kWh)': f.promedio_diario_kwh or '',
                'Fecha Registro': f.fecha_registro.strftime('%d/%m/%Y %H:%M'),
            } for f in facturas])
        else:
            df_facturas = pd.DataFrame(columns=[
                'Periodo Inicio', 'Periodo Fin', 'Consumo (kWh)',
                'Costo Energía ($)', 'Aseo ($)', 'Alumbrado Público ($)',
                'Tasa Seguridad ($)', 'Total Impuestos ($)', 'Costo Total ($)',
                'Promedio Diario (kWh)', 'Fecha Registro'
            ])
        df_facturas.to_excel(writer, sheet_name='Facturas', index=False)

        # --- Hoja 2: Lecturas del Contador ---
        lecturas = LecturaContador.query.order_by(LecturaContador.fecha_lectura.asc()).all()
        if lecturas:
            df_lecturas = pd.DataFrame([{
                'Fecha': l.fecha_lectura.strftime('%d/%m/%Y %H:%M'),
                'Lectura (kWh)': l.lectura_kwh,
                'Nota': l.nota or '',
            } for l in lecturas])
        else:
            df_lecturas = pd.DataFrame(columns=['Fecha', 'Lectura (kWh)', 'Nota'])
        df_lecturas.to_excel(writer, sheet_name='Lecturas Contador', index=False)

        # --- Hoja 3: Inventario de Equipos ---
        equipos = Equipo.query.order_by(Equipo.nombre.asc()).all()
        if equipos:
            df_equipos = pd.DataFrame([{
                'Nombre': e.nombre,
                'Potencia (W)': e.potencia_watts,
                'Horas Uso Diario': e.horas_uso_diario,
                'Horario Inicio': e.horario_inicio or '',
                'Horario Fin': e.horario_fin or '',
                'Días Uso al Mes': e.dias_uso_mes,
                'Consumo Diario (kWh)': round(e.consumo_diario_kwh, 3),
                'Consumo Mensual (kWh)': round(e.consumo_mensual_kwh, 2),
                'Fecha Registro': e.fecha_registro.strftime('%d/%m/%Y'),
            } for e in equipos])
        else:
            df_equipos = pd.DataFrame(columns=[
                'Nombre', 'Potencia (W)', 'Horas Uso Diario',
                'Horario Inicio', 'Horario Fin', 'Días Uso al Mes',
                'Consumo Diario (kWh)', 'Consumo Mensual (kWh)', 'Fecha Registro'
            ])
        df_equipos.to_excel(writer, sheet_name='Inventario Equipos', index=False)

        # --- Hoja 4: Configuración ---
        config = ConfiguracionMeta.query.first()
        if config:
            df_config = pd.DataFrame([{
                'Costo Máximo Mes ($)': config.costo_maximo_mes,
                'Tarifa kWh ($)': config.tarifa_kwh,
                'Aseo ($)': config.aseo or 0,
                'Alumbrado Público ($)': config.alumbrado_publico or 0,
                'Tasa Seguridad ($)': config.tasa_seguridad or 0,
                'Lectura Inicio Ciclo (kWh)': config.lectura_inicio_ciclo or '',
                'Fecha Inicio Ciclo': config.fecha_inicio_ciclo.strftime('%d/%m/%Y') if config.fecha_inicio_ciclo else '',
                'Fecha Fin Ciclo': config.fecha_fin_ciclo.strftime('%d/%m/%Y') if config.fecha_fin_ciclo else '',
            }])
        else:
            df_config = pd.DataFrame(columns=[
                'Costo Máximo Mes ($)', 'Tarifa kWh ($)', 'Aseo ($)',
                'Alumbrado Público ($)', 'Tasa Seguridad ($)',
                'Lectura Inicio Ciclo (kWh)', 'Fecha Inicio Ciclo', 'Fecha Fin Ciclo'
            ])
        df_config.to_excel(writer, sheet_name='Configuración', index=False)

        # Ajustar ancho de columnas en todas las hojas
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for col in worksheet.columns:
                max_len = max((len(str(cell.value)) for cell in col if cell.value), default=10)
                worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

    output.seek(0)
    fecha_hoy = datetime.now().strftime('%Y%m%d_%H%M')
    nombre_archivo = f'afinia_backup_{fecha_hoy}.xlsx'

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=nombre_archivo
    )
