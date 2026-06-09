# Control de Energía - Afinia

Aplicación web para monitorear y controlar el consumo de energía eléctrica.

## Funcionalidades

- **Monitor en tiempo real**: Registra lecturas del contador y visualiza tu consumo con un gauge tipo semáforo (verde/naranja/rojo).
- **Control de presupuesto**: Define tu tope máximo mensual y la app te avisa si vas bien o necesitas ahorrar.
- **Desglose de impuestos**: Incluye aseo, alumbrado público y tasa de seguridad en los cálculos.
- **Historial de facturas**: Registra facturas pasadas para comparar mes a mes.
- **Inventario de equipos**: Registra tus equipos eléctricos y calcula el consumo proyectado.
- **Gráficos interactivos**: Visualiza tendencias con Plotly.

## Instalación local

```bash
pip install -r requirements.txt
python app.py
```

Abrir `http://localhost:8080`

## Deploy en Render

1. Sube el repo a GitHub
2. En Render, crea un nuevo "Blueprint" y conecta el repo
3. Render detectará el `render.yaml` y creará la base de datos PostgreSQL automáticamente

## Tecnologías

- Flask
- SQLAlchemy (SQLite local / PostgreSQL en producción)
- Plotly (gráficos interactivos)
- Bootstrap 5 (responsive)
- EasyOCR (extracción de datos de facturas, opcional)

## Variables de entorno (producción)

- `DATABASE_URL`: URL de conexión a PostgreSQL
- `SECRET_KEY`: Clave secreta para sesiones Flask
