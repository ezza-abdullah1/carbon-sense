import json
import math
import os
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import AreaInfo, EmissionData
from datetime import datetime


class Command(BaseCommand):
    help = 'Load emission data from all sector JSON files into database'

    # Mapping of metadata sector names to model field names
    SECTOR_FIELD_MAP = {
        'energy': 'energy',
        'electricity-generation': 'energy',
        'power': 'energy',
        'transportation': 'transport',
        'transport': 'transport',
        'industrial': 'industry',
        'industry': 'industry',
        'manufacturing': 'industry',
        'waste': 'waste',
        'buildings': 'buildings',
        'residential': 'buildings',
        'commercial': 'buildings',
    }

    # JSON files to load and their corresponding sectors
    DATA_FILES = [
        ('power_forecasts.json', 'energy'),
        ('transport.json', 'transport'),
        ('industry.json', 'industry'),
        ('waste.json', 'waste'),
        ('buildings.json', 'buildings'),
    ]

    def add_arguments(self, parser):
        parser.add_argument(
            '--append',
            action='store_true',
            help='Append data instead of clearing existing data',
        )

    def handle(self, *args, **options):
        append_mode = options.get('append', False)

        if not append_mode:
            # Clear existing data
            self.stdout.write('Clearing existing emission data...')
            EmissionData.objects.all().delete()
            AreaInfo.objects.all().delete()

        total_locations = 0
        total_emissions = 0

        for filename, default_sector in self.DATA_FILES:
            json_path = os.path.join(settings.BASE_DIR, 'data', filename)

            if not os.path.exists(json_path):
                self.stdout.write(self.style.WARNING(f'File not found: {filename}, skipping...'))
                continue

            self.stdout.write(self.style.SUCCESS(f'\nLoading data from: {filename}'))
            locations, emissions = self.load_file(json_path, default_sector)
            total_locations += locations
            total_emissions += emissions

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Successfully loaded all data: {total_locations} locations, {total_emissions} emission records'
        ))

    def load_file(self, json_path, default_sector):
        """Load a single JSON file into the database."""
        with open(json_path, 'r') as f:
            data = json.load(f)

        # Get sector from metadata or use default
        metadata = data.get('metadata', {})
        sector_name = metadata.get('sector', default_sector).lower()
        sector_field = self.SECTOR_FIELD_MAP.get(sector_name, default_sector)

        locations = data.get('locations', [])
        self.stdout.write(f'  Sector: {sector_name} -> {sector_field} field')
        self.stdout.write(f'  Found {len(locations)} locations')

        locations_created = 0
        emissions_created = 0

        for location in locations:
            source_name = location.get('source_name')
            lat = location.get('lat')
            lon = location.get('lon')

            # Skip locations with missing coordinates
            if lat is None or lon is None:
                self.stdout.write(self.style.WARNING(f'    Skipping {source_name}: missing coordinates'))
                continue

            # Convert lat/lon to float if they're strings
            try:
                lat = float(lat)
                lon = float(lon)
                # Check for NaN values
                if math.isnan(lat) or math.isnan(lon):
                    self.stdout.write(self.style.WARNING(f'    Skipping {source_name}: NaN coordinates'))
                    continue
            except (ValueError, TypeError):
                self.stdout.write(self.style.WARNING(f'    Skipping {source_name}: invalid coordinates'))
                continue

            # Create unique ID for area (include sector to avoid conflicts)
            area_id = f"{source_name.lower().replace(' ', '_')}_{sector_field}"

            # Create or get AreaInfo
            area, created = AreaInfo.objects.get_or_create(
                id=area_id,
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

            # Check for new format (chart_data) vs old format (data)
            chart_data = location.get('chart_data')
            if chart_data:
                # New format with chart_data.historical and chart_data.forecast
                historical = chart_data.get('historical', [])
                forecast = chart_data.get('forecast', [])

                # Process historical data
                for entry in historical:
                    self.create_emission_record(area, entry, sector_field, 'historical')
                    emissions_created += 1

                # Process forecast data
                for entry in forecast:
                    self.create_emission_record(area, entry, sector_field, 'forecast')
                    emissions_created += 1
            else:
                # Old format with flat data array
                location_data = location.get('data', [])
                for entry in location_data:
                    date_str = entry.get('date')
                    emissions_value = entry.get('emissions', 0)
                    data_type = entry.get('type', 'historical')

                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

                    emission_data = {
                        'area': area,
                        'date': date_obj,
                        'transport': 0,
                        'industry': 0,
                        'energy': 0,
                        'waste': 0,
                        'buildings': 0,
                        'data_type': data_type,
                    }
                    emission_data[sector_field] = emissions_value

                    EmissionData.objects.create(**emission_data)
                    emissions_created += 1

            self.stdout.write(f'    Processed {source_name}: {sector_field}')

        return locations_created, emissions_created

    def create_emission_record(self, area, entry, sector_field, data_type):
        """Create a single emission record from chart data entry."""
        date_str = entry.get('date')
        emissions_value = entry.get('value', 0)

        # Parse date (handle both YYYY-MM-DD and other formats)
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            # Try alternate format if needed
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()

        emission_data = {
            'area': area,
            'date': date_obj,
            'transport': 0,
            'industry': 0,
            'energy': 0,
            'waste': 0,
            'buildings': 0,
            'data_type': data_type,
        }
        emission_data[sector_field] = emissions_value

        EmissionData.objects.create(**emission_data)
