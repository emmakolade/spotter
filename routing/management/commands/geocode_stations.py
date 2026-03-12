from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from routing.models import FuelStation
from routing.utils import get_coordinates
import time

class Command(BaseCommand):
    help = 'Geocode fuel stations (rate limited)'

    def add_arguments(self, parser):
        parser.add_argument('--limit', type=int, default=50, help='Number of stations to geocode')

    def handle(self, *args, **options):
        # We limit the number of *locations* (city/state pairs) we process, not total stations
        limit = options['limit']
        
        # Get unique city/state combinations that have at least one station with no location
        # This prevents geocoding "Austin, TX" multiple times in the same run
        locations_to_geocode = FuelStation.objects.filter(
            location__isnull=True
        ).values('city', 'state').distinct()[:limit]
        
        self.stdout.write(f"Found {len(locations_to_geocode)} unique locations to geocode...")
        
        updated_count = 0
        
        for loc in locations_to_geocode:
            city = loc['city']
            state = loc['state']
            
            query = f"{city}, {state}"
            lat, lon = get_coordinates(query)
            
            if lat and lon:
                # Create a PostGIS Point
                # Note: Point takes (x, y) which is (longitude, latitude)
                location_point = Point(lon, lat, srid=4326)
                
                # Update all stations in this city/state
                updated = FuelStation.objects.filter(city=city, state=state).update(location=location_point)
                
                self.stdout.write(self.style.SUCCESS(f"Geocoded {city}, {state} - Updated {updated} stations"))
                updated_count += updated
            else:
                self.stdout.write(self.style.WARNING(f"Failed to geocode {city}, {state}"))
            
            # Rate limit compliance for Nominatim (1 sec)
            time.sleep(1.1)
                
        self.stdout.write(self.style.SUCCESS(f"Finished. Total stations updated: {updated_count}"))
