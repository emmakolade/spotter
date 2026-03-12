# Fuel Spotter Project

This project is a Django application to optimize fuel stops along a route.

## Setup

1.  Create a virtual environment: `python -m venv venv`
2.  Activate it: `vens\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
3.  Install dependencies: `pip install -r requirements.txt`
    *   **Note:** You must have GDAL/GEOS installed on your system for GeoDjango. Using Docker is recommended.
4.  Run migrations: `python manage.py migrate`
5.  Load fuel data: `python manage.py load_fuel_data`
6.  Geocode stations (Required for routing): `python manage.py geocode_stations --limit 5000` (This may take time due to rate limits)
7.  Run server: `python manage.py runserver`

## Docker Setup (Recommended)
1. `docker-compose up --build`
2. `docker-compose exec web python manage.py migrate`
3. `docker-compose exec web python manage.py load_fuel_data`
4. `docker-compose exec web python manage.py geocode_stations`

## API

*   `GET /api/route/?start=City,State&finish=City,State`


