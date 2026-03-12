import requests
import polyline
from django.conf import settings
from .models import FuelStation

def get_coordinates(address):
    headers = {'User-Agent': 'FuelSpotter/1.0'}
    params = {'q': address, 'format': 'json', 'limit': 1}
    try:
        response = requests.get(settings.NOMINATIM_API_URL, params=params, headers=headers)
        if response.status_code == 200 and response.json():
            data = response.json()[0]
            return float(data['lat']), float(data['lon'])
    except Exception as e:
        print(f"Geocoding error: {e}")
    return None, None

def get_route(start_coords, end_coords):
    # start_lon, start_lat = start_coords[1], start_coords[0]
    # end_lon, end_lat = end_coords[1], end_coords[0]
    
    # coordinates = f"{start_lon},{start_lat};{end_lon},{end_lat}"
    coordinates = f"{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}"
    url = f"{settings.OSRM_API_URL}/route/v1/driving/{coordinates}?overview=full&geometries=polyline"

    try:
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            if data['code'] == 'Ok':
                route = data['routes'][0]
                geometry = route['geometry']
                distance = route['distance'] 
                decoded_path = polyline.decode(geometry)
                return {
                    'geometry': geometry,
                    'path': decoded_path,
                    'distance_miles': distance * 0.000621371
                }
    except Exception as e:
        print(f"Routing error: {e}")
    return None


    

def find_stations_near_route(route_path, max_distance_miles=10):
    try:
        from django.contrib.gis.geos import LineString
    except ImportError as e:
        print(f"Cannot run spatial queries. Error: {e}")
        return []

   
    route_points = [(lon, lat) for lat, lon in route_path]
    route_line = LineString(route_points, srid=4326)

    degree_radius = max_distance_miles / 69.0

    stations = FuelStation.objects.filter(
         location__dwithin=(route_line, degree_radius)
    )
    return stations

# def find_stations_near_route_naive(route_path, max_distance_miles=10):
#     # This is a naive implementation. PostGIS is better and i used it already in the main function, but this is here is just to demonstrate the logic without spatial queries.
#     lats = [p[0] for p in route_path]
#     lons = [p[1] for p in route_path]
#     min_lat, max_lat = min(lats), max(lats)
#     min_lon, max_lon = min(lons), max(lons)
    
#     margin = max_distance_miles / 69.0 
#     stations = FuelStation.objects.filter(
#         latitude__gte=min_lat - margin,
#         latitude__lte=max_lat + margin,
#         longitude__gte=min_lon - margin,
#         longitude__lte=max_lon + margin
#     )
    
#     valid_stations = []
#     step = 20 
#     sampled_path = route_path[::step]
    
#     for station in stations:
#         station_loc = (station.latitude, station.longitude)
#         min_dist = float('inf')
#         for point in sampled_path:
#             dist = geodesic(station_loc, point).miles
#             if dist < min_dist:
#                 min_dist = dist
#             if min_dist <= max_distance_miles:
#                 valid_stations.append(station)
#                 break
                
#     return valid_stations



def find_optimal_stops(route_path, total_distance_miles, stations):
    # Vehicle Range = 500 miles, MPG = 10.
    # Assumption: Start with full tank (500 miles range).
    
    stops = []
    total_cost = 0
    station_distances = []
    
    # Calculate distance of each station from start along the route
    # I used PostGIS ST_LineLocatePoint to project stations onto the route line
    try:
        from django.contrib.gis.geos import LineString
        from django.contrib.gis.db.models.functions import LineLocatePoint
        from django.db.models import F
        
        route_points = [(lon, lat) for lat, lon in route_path]
        route_line = LineString(route_points, srid=4326)
        
        
        annotated_stations = stations.annotate(
            fraction=LineLocatePoint(route_line, F('location'))
        ).order_by('fraction')
        
        for station in annotated_stations:
            dist_from_start = station.fraction * total_distance_miles
            station_distances.append({
                'station': station,
                'dist': dist_from_start,
                'price': float(station.retail_price)
            })
            
    except ImportError:
        return {"error": "GeoDjango dependencies missing", "stops": []}
    except Exception as e:
        print(f"Error in spatial projection: {e}")
        return {"error": f"Spatial projection failed: {e}", "stops": []}
    
    # Sort stations by distance from start
    station_distances.sort(key=lambda x: x['dist'])
    
    current_pos_miles = 0
    # Range is 500 miles. We assume we start full.
    
    last_stop_dist = 0
    
    while current_pos_miles + 500 < total_distance_miles:
        candidates = [s for s in station_distances if s['dist'] > current_pos_miles and s['dist'] <= current_pos_miles + 500]
        
        if not candidates:
            return {"error": "No stations in range", "stops": []}
            
        # Strategy: Go to the cheapest one. If prices match, go to the furthest one (maximize cheap fuel usage)
        best_station = min(candidates, key=lambda x: (x['price'], -x['dist']))
        
        # Calculate fuel used to get there
        dist_traveled = best_station['dist'] - last_stop_dist
        gallons_used = dist_traveled / 10
        
        # Add cost to fill back to full
        cost = gallons_used * best_station['price']
        total_cost += cost
        
        stops.append(best_station['station'])
        current_pos_miles = best_station['dist']
        last_stop_dist = current_pos_miles 
        
    return {
        "stops": stops,
        "total_cost": total_cost 
    }
