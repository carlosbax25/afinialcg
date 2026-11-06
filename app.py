from flask import Flask
from models import db
from routes.monitor import monitor_bp
from routes.upload import upload_bp
from routes.dashboard import dashboard_bp
from routes.inventory import inventory_bp
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'energy-control-secret-key')

# Base de datos: usa PostgreSQL si DATABASE_URL existe, sino SQLite local
database_url = os.environ.get('DATABASE_URL', '')
if database_url:
    # Algunos proveedores usan "postgres://", SQLAlchemy necesita "postgresql://"
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    # Neon requiere SSL; SQLAlchemy lo acepta como connect_args o en la URL
    connect_args = {}
    if 'neon.tech' in database_url or 'sslmode=require' in database_url:
        connect_args = {'sslmode': 'require'}
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': connect_args,
        'pool_pre_ping': True,  # Reconecta automáticamente si la BD estuvo inactiva
    }
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///energy.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db.init_app(app)

# Monitor es la vista principal (ruta /)
app.register_blueprint(monitor_bp)
app.register_blueprint(upload_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(inventory_bp)

with app.app_context():
    db.create_all()
    # Resetear secuencias en PostgreSQL después de migración
    if database_url:
        try:
            from sqlalchemy import text
            with db.engine.connect() as conn:
                tables = ['lectura_contador', 'factura', 'equipo', 'configuracion_meta']
                for table in tables:
                    conn.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                        f"COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                    ))
                conn.commit()
        except Exception:
            pass


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
