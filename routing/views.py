from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .utils import get_coordinates, get_route, find_stations_near_route, find_optimal_stops

class RouteView(APIView):
    def get(self, request):
        start_location = request.query_params.get('start')
        finish_location = request.query_params.get('finish')
        
        if not start_location or not finish_location:
            return Response({'error': 'Please provide start and finish locations'}, status=status.HTTP_400_BAD_REQUEST)
            
        start_coords = get_coordinates(start_location)
        finish_coords = get_coordinates(finish_location)
        
        if not start_coords or not finish_coords:
            return Response(
                {'error': 'Unable to find coordinates for one or more locations. Please check the location names and try again.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
            
        route_data = get_route(start_coords, finish_coords)
        if not route_data:
            return Response(
                {'error': 'Unable to calculate route between the provided locations. Please verify the addresses and try again.'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
             
        stations = find_stations_near_route(route_data['path'], max_distance_miles=10)
        
        optimization_result = {'stops': [], 'total_cost': 0}
        error_msg = None
        
        if not stations:
            error_msg = 'No fuel stations found along your route.'
        else:
            try:
                res = find_optimal_stops(route_data['path'], route_data['distance_miles'], stations)
                if isinstance(res, dict) and 'error' in res:
                    error_msg = res['error']
                else:
                    optimization_result = res
            except Exception as e:
                error_msg = f'Optimization error: {str(e)}'
        
        stops_list = []
        for s in optimization_result.get('stops', []):
             stops_list.append({
                'name': s.name,
                'city': s.city,
                'state': s.state,
                'price': float(s.retail_price),
                'address': s.address,
                'location': {'lat': s.location.y, 'lon': s.location.x}
             })

        response_data = {
            'total_distance_miles': round(route_data.get('distance_miles', 0), 2),
            'fuel_stops': stops_list,
            'total_fuel_cost': round(optimization_result.get('total_cost', 0), 2),
            'route_geometry': route_data.get('geometry'),

        }
        
        if error_msg:
            response_data['warning'] = error_msg
            
        return Response(response_data)
