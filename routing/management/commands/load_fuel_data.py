import pandas as pd
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from routing.models import FuelStation

class Command(BaseCommand):
    help = 'Load fuel prices from CSV'

    def handle(self, *args, **options):
        csv_path = os.path.join(settings.BASE_DIR, 'fuel-prices.csv')
        
      
             
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f'File not found: {csv_path}. "fuel-prices.csv" is needed.'))
            return

        try:
            df = pd.read_csv(csv_path)
            
            records = []
            for _, row in df.iterrows():
                # Avoid duplicates
                if FuelStation.objects.filter(opis_id=row['OPIS Truckstop ID']).exists():
                    continue

                records.append(FuelStation(
                    opis_id=row['OPIS Truckstop ID'],
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    rack_id=row['Rack ID'],
                    retail_price=row['Retail Price']
                ))
            
            FuelStation.objects.bulk_create(records, ignore_conflicts=True)
            self.stdout.write(self.style.SUCCESS(f'Successfully loaded {len(records)} stations'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
