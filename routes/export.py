from flask import Blueprint, send_file, render_template, request, flash, redirect, url_for
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


@export_bp.route('/importar', methods=['GET', 'POST'])
def importar_excel():
    """Importa datos desde un Excel exportado previamente."""

    if request.method == 'GET':
        return render_template('importar.html')

    archivo = request.files.get('archivo')
    if not archivo or not archivo.filename.endswith('.xlsx'):
        flash('Debes subir un archivo .xlsx válido.', 'error')
        return redirect(url_for('export.importar_excel'))

    try:
        contenido = archivo.read()
        resumen = {'facturas': 0, 'lecturas': 0, 'equipos': 0, 'config': False, 'errores': []}

        # --- Facturas ---
        try:
            df_f = pd.read_excel(io.BytesIO(contenido), sheet_name='Facturas')
            if not df_f.empty:
                Factura.query.delete()
                for _, row in df_f.iterrows():
                    try:
                        f = Factura(
                            periodo_inicio=pd.to_datetime(row['Periodo Inicio'], dayfirst=True).date(),
                            periodo_fin=pd.to_datetime(row['Periodo Fin'], dayfirst=True).date(),
                            consumo_kwh=float(row['Consumo (kWh)']),
                            costo_total=float(row['Costo Total ($)']),
                            costo_energia=float(row['Costo Energía ($)']) if pd.notna(row.get('Costo Energía ($)')) and row.get('Costo Energía ($)') != '' else None,
                            aseo=float(row['Aseo ($)']) if pd.notna(row.get('Aseo ($)')) else 0,
                            alumbrado_publico=float(row['Alumbrado Público ($)']) if pd.notna(row.get('Alumbrado Público ($)')) else 0,
                            tasa_seguridad=float(row['Tasa Seguridad ($)']) if pd.notna(row.get('Tasa Seguridad ($)')) else 0,
                            promedio_diario_kwh=float(row['Promedio Diario (kWh)']) if pd.notna(row.get('Promedio Diario (kWh)')) and row.get('Promedio Diario (kWh)') != '' else None,
                        )
                        db.session.add(f)
                        resumen['facturas'] += 1
                    except Exception as e:
                        resumen['errores'].append(f'Factura fila {_ + 2}: {str(e)}')
        except Exception as e:
            resumen['errores'].append(f'Hoja Facturas: {str(e)}')

        # --- Lecturas Contador ---
        try:
            df_l = pd.read_excel(io.BytesIO(contenido), sheet_name='Lecturas Contador')
            if not df_l.empty:
                LecturaContador.query.delete()
                for _, row in df_l.iterrows():
                    try:
                        l = LecturaContador(
                            fecha_lectura=pd.to_datetime(row['Fecha'], dayfirst=True),
                            lectura_kwh=float(row['Lectura (kWh)']),
                            nota=str(row['Nota']) if pd.notna(row.get('Nota')) and row.get('Nota') != '' else None,
                        )
                        db.session.add(l)
                        resumen['lecturas'] += 1
                    except Exception as e:
                        resumen['errores'].append(f'Lectura fila {_ + 2}: {str(e)}')
        except Exception as e:
            resumen['errores'].append(f'Hoja Lecturas Contador: {str(e)}')

        # --- Equipos ---
        try:
            df_e = pd.read_excel(io.BytesIO(contenido), sheet_name='Inventario Equipos')
            if not df_e.empty:
                Equipo.query.delete()
                for _, row in df_e.iterrows():
                    try:
                        e = Equipo(
                            nombre=str(row['Nombre']),
                            potencia_watts=float(row['Potencia (W)']),
                            horas_uso_diario=float(row['Horas Uso Diario']),
                            horario_inicio=str(row['Horario Inicio']) if pd.notna(row.get('Horario Inicio')) and row.get('Horario Inicio') != '' else None,
                            horario_fin=str(row['Horario Fin']) if pd.notna(row.get('Horario Fin')) and row.get('Horario Fin') != '' else None,
                            dias_uso_mes=int(row['Días Uso al Mes']) if pd.notna(row.get('Días Uso al Mes')) else 30,
                        )
                        db.session.add(e)
                        resumen['equipos'] += 1
                    except Exception as e:
                        resumen['errores'].append(f'Equipo fila {_ + 2}: {str(e)}')
        except Exception as e:
            resumen['errores'].append(f'Hoja Inventario Equipos: {str(e)}')

        # --- Configuración ---
        try:
            df_c = pd.read_excel(io.BytesIO(contenido), sheet_name='Configuración')
            if not df_c.empty:
                row = df_c.iloc[0]
                ConfiguracionMeta.query.delete()
                config = ConfiguracionMeta(
                    costo_maximo_mes=float(row['Costo Máximo Mes ($)']),
                    tarifa_kwh=float(row['Tarifa kWh ($)']),
                    aseo=float(row['Aseo ($)']) if pd.notna(row.get('Aseo ($)')) else 0,
                    alumbrado_publico=float(row['Alumbrado Público ($)']) if pd.notna(row.get('Alumbrado Público ($)')) else 0,
                    tasa_seguridad=float(row['Tasa Seguridad ($)']) if pd.notna(row.get('Tasa Seguridad ($)')) else 0,
                    lectura_inicio_ciclo=float(row['Lectura Inicio Ciclo (kWh)']) if pd.notna(row.get('Lectura Inicio Ciclo (kWh)')) and row.get('Lectura Inicio Ciclo (kWh)') != '' else None,
                    fecha_inicio_ciclo=pd.to_datetime(row['Fecha Inicio Ciclo'], dayfirst=True).date() if pd.notna(row.get('Fecha Inicio Ciclo')) and row.get('Fecha Inicio Ciclo') != '' else None,
                    fecha_fin_ciclo=pd.to_datetime(row['Fecha Fin Ciclo'], dayfirst=True).date() if pd.notna(row.get('Fecha Fin Ciclo')) and row.get('Fecha Fin Ciclo') != '' else None,
                )
                db.session.add(config)
                resumen['config'] = True
        except Exception as e:
            resumen['errores'].append(f'Hoja Configuración: {str(e)}')

        db.session.commit()
        return render_template('importar.html', resumen=resumen)

    except Exception as e:
        db.session.rollback()
        flash(f'Error al procesar el archivo: {str(e)}', 'error')
        return redirect(url_for('export.importar_excel'))
