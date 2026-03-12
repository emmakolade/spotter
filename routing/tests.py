from django.test import TestCase, Client
from django.urls import reverse
from unittest.mock import patch, MagicMock
from decimal import Decimal
from django.contrib.gis.geos import Point
from .models import FuelStation

class FuelStationModelTest(TestCase):
    def test_fuel_station_str(self):
        station = FuelStation(
            opis_id=12345,
            name="Test Station",
            address="123 Test St",
            city="Test City",
            state="TS",
            rack_id=67890,
            retail_price=Decimal("3.459"),
            location=Point(-74.0060, 40.7128)
        )
        
        expected_str = "Test Station (Test City, TS) - $3.459"
        self.assertEqual(str(station), expected_str)

class UtilsTest(TestCase):
    @patch('routing.utils.requests.get')
    def test_get_coordinates_success(self, mock_get):
        from routing.utils import get_coordinates
        
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{'lat': '40.7128', 'lon': '-74.0060', 'display_name': 'New York'}]
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("New York, NY")
        
        self.assertEqual(lat, 40.7128)
        self.assertEqual(lon, -74.0060)

    @patch('routing.utils.requests.get')
    def test_get_coordinates_failure(self, mock_get):
        from routing.utils import get_coordinates

        # Mock failure (empty list or error)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        lat, lon = get_coordinates("Invalid Place")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

        # Mock exception
        mock_get.side_effect = Exception("API Error")
        lat, lon = get_coordinates("Error Place")
        self.assertIsNone(lat)
        self.assertIsNone(lon)

    @patch('routing.utils.requests.get')
    @patch('routing.utils.polyline.decode')
    def test_get_route_success(self, mock_decode, mock_get):
        from routing.utils import get_route
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'code': 'Ok',
            'routes': [{
                'geometry': 'encoded_polyline',
                'distance': 10000  # meters
            }]
        }
        mock_get.return_value = mock_response
        
        # Mock polyline decode
        mock_decode.return_value = [(40.0, -74.0), (41.0, -75.0)]

        result = get_route((40.0, -74.0), (41.0, -75.0))
        
        self.assertIsNotNone(result)
        self.assertEqual(result['geometry'], 'encoded_polyline')
        self.assertAlmostEqual(result['distance_miles'], 10000 * 0.000621371, places=5)
        self.assertEqual(result['path'], [(40.0, -74.0), (41.0, -75.0)])

    @patch('routing.utils.requests.get')
    def test_get_route_failure(self, mock_get):
        from routing.utils import get_route
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        result = get_route((40.0, -74.0), (41.0, -75.0))
        self.assertIsNone(result)

class RouteViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = '/api/route/' 

    @patch('routing.views.get_coordinates')
    @patch('routing.views.get_route')
    @patch('routing.views.find_stations_near_route')
    @patch('routing.views.find_optimal_stops')
    def test_route_view_success(self, mock_optimal, mock_find_stations, mock_get_route, mock_get_coords):
    
        mock_get_coords.side_effect = [(30.2672, -97.7431), (32.7767, -96.7970)] 
        
        mock_get_route.return_value = {
            'geometry': 'some_polyline',
            'path': [(30.2672, -97.7431), (32.7767, -96.7970)],
            'distance_miles': 200.0
        }
        
        mock_find_stations.return_value = [MagicMock()] 
        
        station_1 = MagicMock()
        station_1.name = "Fuel Stop 1"
        station_1.city = "Waco"
        station_1.state = "TX"
        station_1.retail_price = Decimal("2.99")
        station_1.address = "I-35 Frontage"
        station_1.location = Point(-97.1467, 31.5493) 
        
        mock_optimal.return_value = {
            'stops': [station_1],
            'total_cost': 45.50
        }

        response = self.client.get(self.url, {'start': 'Austin, TX', 'finish': 'Dallas, TX'})
                
        if response.status_code == 404:
             response = self.client.get('/route/', {'start': 'Austin, TX', 'finish': 'Dallas, TX'})

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertEqual(data['total_distance_miles'], 200.0)
        self.assertEqual(data['total_fuel_cost'], 45.50)
        self.assertEqual(len(data['fuel_stops']), 1)
        self.assertEqual(data['fuel_stops'][0]['name'], "Fuel Stop 1")

    @patch('routing.views.get_coordinates')
    def test_missing_params(self, mock_get):
        response = self.client.get('/api/route/')
        if response.status_code == 404:
             response = self.client.get('/route/')
             
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())
