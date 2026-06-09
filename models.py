from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Factura(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    periodo_inicio = db.Column(db.Date, nullable=False)
    periodo_fin = db.Column(db.Date, nullable=False)
    consumo_kwh = db.Column(db.Float, nullable=False)
    costo_total = db.Column(db.Float, nullable=False)
    costo_energia = db.Column(db.Float, nullable=True)  # Solo energía
    aseo = db.Column(db.Float, default=0)
    alumbrado_publico = db.Column(db.Float, default=0)
    tasa_seguridad = db.Column(db.Float, default=0)
    promedio_diario_kwh = db.Column(db.Float, nullable=True)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    imagen_path = db.Column(db.String(255), nullable=True)

    @property
    def total_impuestos(self):
        return (self.aseo or 0) + (self.alumbrado_publico or 0) + (self.tasa_seguridad or 0)

    def to_dict(self):
        return {
            'id': self.id,
            'periodo_inicio': self.periodo_inicio.strftime('%Y-%m-%d'),
            'periodo_fin': self.periodo_fin.strftime('%Y-%m-%d'),
            'consumo_kwh': self.consumo_kwh,
            'costo_total': self.costo_total,
            'costo_energia': self.costo_energia,
            'aseo': self.aseo,
            'alumbrado_publico': self.alumbrado_publico,
            'tasa_seguridad': self.tasa_seguridad,
            'promedio_diario_kwh': self.promedio_diario_kwh,
            'fecha_registro': self.fecha_registro.strftime('%Y-%m-%d %H:%M')
        }


class LecturaContador(db.Model):
    """Registro de lecturas del contador de energía."""
    id = db.Column(db.Integer, primary_key=True)
    lectura_kwh = db.Column(db.Float, nullable=False)
    fecha_lectura = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    nota = db.Column(db.String(200), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lectura_kwh': self.lectura_kwh,
            'fecha_lectura': self.fecha_lectura.strftime('%Y-%m-%d %H:%M'),
            'nota': self.nota
        }


class ConfiguracionMeta(db.Model):
    """Configuración del usuario: meta de costo máximo, tarifa, impuestos, etc."""
    id = db.Column(db.Integer, primary_key=True)
    costo_maximo_mes = db.Column(db.Float, default=700000)  # $700.000 COP
    tarifa_kwh = db.Column(db.Float, default=850)  # Tarifa promedio Afinia $/kWh
    # Cargos fijos mensuales (impuestos locales)
    aseo = db.Column(db.Float, default=0)  # Servicio de aseo
    alumbrado_publico = db.Column(db.Float, default=0)  # Alumbrado público
    tasa_seguridad = db.Column(db.Float, default=0)  # Tasa seguridad y convivencia ciudadana
    # Ciclo
    lectura_inicio_ciclo = db.Column(db.Float, nullable=True)
    fecha_inicio_ciclo = db.Column(db.Date, nullable=True)
    fecha_fin_ciclo = db.Column(db.Date, nullable=True)

    @property
    def total_cargos_fijos(self):
        return (self.aseo or 0) + (self.alumbrado_publico or 0) + (self.tasa_seguridad or 0)

    @property
    def presupuesto_energia_pura(self):
        """Lo que realmente queda para energía después de descontar cargos fijos."""
        return max(self.costo_maximo_mes - self.total_cargos_fijos, 0)

    @property
    def kwh_maximo(self):
        """kWh máximos que puedes consumir con tu presupuesto (descontando cargos fijos)."""
        if self.tarifa_kwh and self.tarifa_kwh > 0:
            return self.presupuesto_energia_pura / self.tarifa_kwh
        return 0


class Equipo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    potencia_watts = db.Column(db.Float, nullable=False)
    horas_uso_diario = db.Column(db.Float, nullable=False)
    horario_inicio = db.Column(db.String(5), nullable=True)  # HH:MM
    horario_fin = db.Column(db.String(5), nullable=True)      # HH:MM
    dias_uso_mes = db.Column(db.Integer, default=30)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def consumo_diario_kwh(self):
        return (self.potencia_watts * self.horas_uso_diario) / 1000

    @property
    def consumo_mensual_kwh(self):
        return self.consumo_diario_kwh * self.dias_uso_mes

    @property
    def es_horario_pico(self):
        """Horario pico en Colombia: 17:00 - 21:00"""
        if not self.horario_inicio:
            return False
        hora = int(self.horario_inicio.split(':')[0])
        return 17 <= hora < 21

    def to_dict(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'potencia_watts': self.potencia_watts,
            'horas_uso_diario': self.horas_uso_diario,
            'horario_inicio': self.horario_inicio,
            'horario_fin': self.horario_fin,
            'dias_uso_mes': self.dias_uso_mes,
            'consumo_diario_kwh': round(self.consumo_diario_kwh, 3),
            'consumo_mensual_kwh': round(self.consumo_mensual_kwh, 2),
            'es_horario_pico': self.es_horario_pico
        }
