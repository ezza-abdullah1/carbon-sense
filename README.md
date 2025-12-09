# CarbonSense

An interactive web application for visualizing and forecasting carbon emissions.

## Project Structure

This project has been structured into separate frontend and backend applications:

```
carbon-sense/
├── carbonsense-frontend/     # React + Vite frontend
│   ├── src/                 # React components, pages, hooks
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── carbonsense-backend/      # Django REST API
│   ├── api/                 # Main API app
│   ├── carbonsense/         # Django settings
│   ├── manage.py
│   ├── requirements.txt
│   └── README.md
│
└── start-all.ps1            # One-click startup script
```

## Tech Stack

### Frontend

- React 18
- TypeScript
- Vite
- TailwindCSS
- Radix UI
- React Query
- Recharts & Leaflet

### Backend

- Python 3.10+
- Django 5.0
- Django REST Framework
- SQLite (development) / PostgreSQL (production)

## Quick Start

### Prerequisites

- **Node.js** 18+ and npm
- **Python** 3.10+ and pip

### 🚀 Run the Project (One Command!)

```powershell
.\start-all.ps1
```

That's it! This single command will:

- Create Python virtual environment (first time)
- Install all backend dependencies (first time)
- Set up the database (first time)
- Install all frontend dependencies (first time)
- Start Django backend → http://localhost:8000
- Start React frontend → http://localhost:5173
- Open both in separate windows

**Then open your browser to http://localhost:5173**

> **PowerShell Execution Policy Error?** Run this once:
>
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Daily Development

### Starting the Project

```powershell
.\start-all.ps1
```

### Stopping the Servers

Press `Ctrl+C` in each terminal window

### Access Points

- **Frontend App:** http://localhost:5173
- **Backend API:** http://localhost:8000/api/
- **Django Admin:** http://localhost:8000/admin/

---

## API Endpoints

The backend provides these REST endpoints:

- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login
- `POST /api/auth/logout` - User logout
- `GET /api/auth/me` - Get current user
- `GET /api/emissions/` - Get emission data (with filtering)
- `GET /api/areas/` - Get area information
- `GET /api/leaderboard/` - Get leaderboard entries

See `carbonsense-backend/README.md` for detailed API documentation.

---

## Individual Scripts

If you prefer to run backend and frontend separately:

### Backend Only

```powershell
cd carbonsense-backend
.\start-backend.ps1
```

### Frontend Only

```powershell
cd carbonsense-frontend
.\start-frontend.ps1
```

---

## Configuration

### Frontend Config (Optional)

The Vite proxy is already configured to forward API requests to Django.

To customize, edit `carbonsense-frontend/vite.config.ts`:

```typescript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
    }
  }
}
```

### Backend Config (Optional)

Copy and edit environment variables:

```bash
cd carbonsense-backend
cp .env.example .env
# Edit .env with your settings
```

---

## Building for Production

### Frontend

```bash
cd carbonsense-frontend
npm run build
# Output in dist/
```

### Backend

```bash
cd carbonsense-backend
pip install gunicorn
gunicorn carbonsense.wsgi:application --bind 0.0.0.0:8000
```

---

## Troubleshooting

### "Python not found" or "Node not found"

- Install Python 3.10+ from https://www.python.org/
- Install Node.js 18+ from https://nodejs.org/
- Make sure they're added to your PATH

### Port already in use

- **Backend:** Change port with `python manage.py runserver 8001`
- **Frontend:** Vite will automatically try the next available port

### CSS/Styling not working

- Stop the frontend (`Ctrl+C`)
- Run `.\start-frontend.ps1` again
- Clear browser cache and reload

### Database errors

```bash
cd carbonsense-backend
rm db.sqlite3
python manage.py migrate
```

---

## Manual Setup (Advanced)

<details>
<summary>Click to expand manual setup instructions</summary>

### Backend Setup

```bash
cd carbonsense-backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup database
python manage.py makemigrations
python manage.py migrate

# Create admin user (optional)
python manage.py createsuperuser

# Start server
python manage.py runserver
```

### Frontend Setup

```bash
cd carbonsense-frontend

# Install dependencies
npm install

# Start dev server
npm run dev
```

</details>

---

## Common Commands

### Backend

```bash
python manage.py makemigrations  # Create migrations
python manage.py migrate         # Apply migrations
python manage.py createsuperuser # Create admin user
python manage.py runserver       # Start server
python manage.py shell           # Open Django shell
```

### Frontend

```bash
npm install        # Install dependencies
npm run dev        # Start dev server
npm run build      # Build for production
npm run check      # Type check
```

---

## Project Links

- Frontend README: `carbonsense-frontend/README.md`
- Backend README: `carbonsense-backend/README.md`
- Scripts Guide: `SCRIPTS.md`

## Contributing

1. Make changes in the appropriate directory
2. Test locally
3. Commit with clear messages
4. Push to your branch

## License

MIT
