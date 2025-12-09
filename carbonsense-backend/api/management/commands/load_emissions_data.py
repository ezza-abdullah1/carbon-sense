import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import AreaInfo, EmissionData
from datetime import datetime


class Command(BaseCommand):
    help = 'Load emission data from JSON file into database'

    def handle(self, *args, **kwargs):
        # Path to JSON file
        json_path = os.path.join(settings.BASE_DIR, 'data', 'power_forecasts.json')

        if not os.path.exists(json_path):
            self.stdout.write(self.style.ERROR(f'File not found: {json_path}'))
            return

        self.stdout.write(self.style.SUCCESS(f'Loading data from: {json_path}'))

        # Load JSON data
        with open(json_path, 'r') as f:
            data = json.load(f)

        sector = data.get('sector', 'energy')  # Default to energy since this is power data
        locations = data.get('locations', [])

        self.stdout.write(f'Found {len(locations)} locations')

        # Clear existing data (optional - comment out if you want to keep existing data)
        self.stdout.write('Clearing existing emission data...')
        EmissionData.objects.all().delete()
        AreaInfo.objects.all().delete()

        locations_created = 0
        emissions_created = 0

        # Process each location
        for location in locations:
            source_name = location.get('source_name')
            lat = location.get('lat')
            lon = location.get('lon')
            location_data = location.get('data', [])

            # Skip locations with missing coordinates
            if lat is None or lon is None:
                self.stdout.write(self.style.WARNING(f'  Skipping {source_name}: missing coordinates'))
                continue

            # Create or get AreaInfo
            area, created = AreaInfo.objects.get_or_create(
                id=source_name.lower().replace(' ', '_'),
                defaults={
                    'name': source_name,
                    'latitude': lat,
                    'longitude': lon,
                    'bounds_lat_min': lat - 0.1,
                    'bounds_lat_max': lat + 0.1,
                    'bounds_lng_min': lon - 0.1,
                    'bounds_lng_max': lon + 0.1,
                }
            )

            if created:
                locations_created += 1

            # Create EmissionData for each data point
            for entry in location_data:
                date_str = entry.get('date')
                emissions_value = entry.get('emissions', 0)
                data_type = entry.get('type', 'historical')

                # Parse date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                # Create emission data
                # For now, putting all emissions in the 'energy' field since it's power data
                emission = EmissionData.objects.create(
                    area=area,
                    date=date_obj,
                    transport=0,
                    industry=0,
                    energy=emissions_value,  # Power sector emissions go here
                    waste=0,
                    buildings=0,
                    data_type=data_type
                )
                emissions_created += 1

            self.stdout.write(f'  Processed {source_name}: {len(location_data)} data points')

        self.stdout.write(self.style.SUCCESS(
            f'Successfully loaded data: {locations_created} locations, {emissions_created} emission records'
        ))
