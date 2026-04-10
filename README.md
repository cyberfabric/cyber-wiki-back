# CyberWiki Backend

Django-based REST API backend for CyberWiki - a collaborative documentation platform with Git integration.

## Architecture

Based on the [Backend Design Specification](../../docs/specs/backend/DESIGN.md), this backend implements:

- **Django 5.2.9** + **Django REST Framework 3.16.1**
- **Modular app structure**: users, wiki, git_provider, source_provider, enrichment_provider
- **SQLite** (dev) / **PostgreSQL** (production)
- **OpenAPI/Swagger** documentation via drf-spectacular

## Quick Start

### 1. Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env.dev
# Edit .env.dev with your settings
```

### 4. Run Migrations

```bash
python manage.py migrate
```

### 5. Create Superuser

```bash
python manage.py createsuperuser
```

### 6. Run Development Server

```bash
python manage.py runserver
```

The API will be available at:
- **API**: http://localhost:8000/api/
- **Admin**: http://localhost:8000/admin/
- **API Docs**: http://localhost:8000/api/docs/
- **OpenAPI Schema**: http://localhost:8000/api/schema/

## Running from Main Repo

From the main `cyber-wiki` repository root:

```bash
./scripts/run-local.sh
```

This script will:
1. Start the backend on port 8000
2. Start the frontend on port 3000 (if available)
3. Auto-create admin user (admin/admin)

## Project Structure

```
.
├── src/                       # Source code directory
│   ├── config/                # Django project settings
│   │   ├── settings.py        # Main configuration
│   │   ├── urls.py            # Root URL routing
│   │   └── wsgi.py            # WSGI application
│   ├── users/                 # User management & auth
│   ├── wiki/                  # Wiki/document management
│   ├── git_provider/          # Git provider abstraction
│   ├── source_provider/       # Source addressing layer
│   └── enrichment_provider/   # Enrichment system
├── data/                      # Runtime data (SQLite, etc.)
├── venv/                      # Virtual environment (not in git)
├── manage.py                  # Django management script
├── requirements.txt           # Python dependencies
└── requirements-prod.txt      # Production dependencies (PostgreSQL)
```

## API Endpoints

### Users
- `GET /api/users/health/` - Health check

### Wiki
- `GET /api/wiki/spaces/` - List spaces

### Git Provider
- `GET /api/git/repositories/` - List repositories

### Source Provider
- `GET /api/source/get/` - Get source content

### Enrichment Provider
- `GET /api/enrichment/list/` - List enrichments

## Testing

```bash
pytest
```

## Development

### Adding a New App

```bash
python manage.py startapp myapp
```

Then add to `INSTALLED_APPS` in `config/settings.py`.

### Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

### Shell Access

```bash
python manage.py shell
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `DJANGO_SECRET_KEY` - Django secret key (required)
- `DEBUG` - Debug mode (default: True)
- `ALLOWED_HOSTS` - Comma-separated list of allowed hosts
- `CORS_ALLOWED_ORIGINS` - Comma-separated list of CORS origins
- `DATABASE_URL` - PostgreSQL connection string (optional)

## Next Steps

This is a minimal stub implementation. See the [Backend Design Specification](../../docs/specs/backend/DESIGN.md) for the full architecture and implementation roadmap
