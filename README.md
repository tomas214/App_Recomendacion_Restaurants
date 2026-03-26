# Restaurante Recomendador

Sistema de recomendacion interactivo basado en Filtro Colaborativo.

## Caracteristicas
* Motor de recomendacion: Similitud de coseno.
* Base de datos: SQLite3.
* Interfaz: Flask + Jinja2.

## Estructura del Proyecto
```text
.
├── app.py
├── requirements.txt
├── datos/
│   └── Datos.db
└── templates/
    ├── login.html
    └── recomendaciones.html
```

## Instalacion
1. pip install -r requirements.txt
2. python app.py