# CarbonSense Backend

Django REST Framework backend API for CarbonSense.

## Tech Stack

- Python 3.10+
- Django 5.0
- Django REST Framework
- SQLite (development) / PostgreSQL (production)
- Session-based authentication

## Project Structure

```
carbonsense-backend/
├── manage.py                 # Django management script
├── carbonsense/              # Project settings
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   ├── wsgi.py              # WSGI configuration
│   └── asgi.py              # ASGI configuration
├── api/                      # Main API application
│   ├── models.py            # Database models
│   ├── serializers.py       # DRF serializers
│   ├── views.py             # API views
│   ├── urls.py              # API URL patterns
│   └── admin.py             # Django admin configuration
├── requirements.txt          # Python dependencies
└── .env.example             # Environment variables template
```

## Setup

### 1. Create a virtual environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your settings
```

### 4. Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a superuser (optional)

```bash
python manage.py createsuperuser
```

## Development

Start the development server:

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000`

### Admin Interface

Access the Django admin panel at `http://localhost:8000/admin`

## API Endpoints

### Authentication

- `POST /api/auth/signup` - User signup
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user

### Emissions

- `GET /api/emissions/` - List all emission data
- `GET /api/emissions/{id}/` - Get specific emission data

Query parameters:
- `area_id` - Filter by area ID
- `sector` - Filter by sector (transport, industry, energy, waste, buildings)
- `start_date` - Filter by start date (YYYY-MM-DD)
- `end_date` - Filter by end date (YYYY-MM-DD)
- `data_type` - Filter by type (historical, forecast)

### Areas

- `GET /api/areas/` - List all areas
- `GET /api/areas/{id}/` - Get specific area

### Leaderboard

- `GET /api/leaderboard/` - Get leaderboard entries

## Database

### Run migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Create migrations after model changes

```bash
python manage.py makemigrations
```

## Testing

Run tests (if configured):

```bash
python manage.py test
```

Or with pytest:

```bash
pytest
```

## Production Deployment

### 1. Update settings for production

- Set `DEBUG = False`
- Configure `ALLOWED_HOSTS`
- Set a strong `SECRET_KEY`
- Configure PostgreSQL database

### 2. Collect static files

```bash
python manage.py collectstatic
```

### 3. Use a production server

Use Gunicorn or uWSGI:

```bash
pip install gunicorn
gunicorn carbonsense.wsgi:application
```

## Database Migration to PostgreSQL

To use PostgreSQL instead of SQLite:

1. Install PostgreSQL adapter:
```bash
pip install psycopg2-binary
```

2. Update `DATABASES` in `settings.py`:
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'carbonsense',
        'USER': 'your_username',
        'PASSWORD': 'your_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

3. Run migrations:
```bash
python manage.py migrate
```

## Useful Commands

```bash
# Create new app
python manage.py startapp app_name

# Create superuser
python manage.py createsuperuser

# Open Django shell
python manage.py shell

# Check for issues
python manage.py check

# Show migrations
python manage.py showmigrations

# Database shell
python manage.py dbshell
```
