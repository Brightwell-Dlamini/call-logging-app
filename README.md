# CallLog Pro – Call Logging Application

A production-ready call logging system for organizations to track customer calls, support requests, incidents, and follow-ups with role-based access control (Admin, Agent, Manager).

## Features

- **Authentication & Authorization**: Flask-Login, bcrypt-style password hashing, role-based decorators, session timeout, login rate limiting.
- **Dashboard**: Statistics cards, Chart.js visualizations (status doughnut, daily bar, department bar), recent calls.
- **Call Logging**: Create, list (search/filter/sort/paginate), detail view, status updates, notes, assignment, activity audit trail.
- **Reports**: Daily log, monthly summary, agent performance, department breakdown; Excel & PDF export.
- **Admin**: User management, department management, system-wide audit log.
- **REST API**: JSON endpoints for calls, users, dashboard stats, and daily reports.
- **Security**: CSRF protection, ORM-based queries, input validation, XSS-safe templates, audit logging.

## Technology Stack

- Backend: Flask 3.x, SQLAlchemy, Flask-Login, Flask-WTF, Flask-Migrate, Flask-Caching, Flask-Limiter
- Database: SQLite (development) / MySQL (production)
- Frontend: Bootstrap 5, Chart.js, DataTables, Font Awesome
- Export: openpyxl (Excel), ReportLab (PDF)

## Quick Start (Development)

```bash
# Clone and enter directory
cd call-logging-app

# Create virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env and set a strong SECRET_KEY

# Initialize database and seed sample data
python -c "from scripts.seed import seed; seed()"

# Run the application
python run.py
```

Open http://127.0.0.1:5000

**Default credentials**

| Username | Password   | Role    |
|----------|------------|---------|
| admin    | admin123   | Admin   |
| agent1   | password123| Agent   |
| manager1 | password123| Manager |

## Production Deployment

### Docker Compose

```bash
export SECRET_KEY=$(openssl rand -hex 32)
docker-compose up -d --build
```

Application available at http://localhost:8000

### Gunicorn

```bash
gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 run:app
```

### Nginx (example reverse proxy)

```nginx
server {
    listen 80;
    server_name calllog.example.com;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## API Endpoints

All endpoints require an authenticated session.

| Method | Endpoint                | Description              |
|--------|-------------------------|--------------------------|
| GET    | /api/calls              | List calls (filters)     |
| POST   | /api/calls              | Create call              |
| GET    | /api/calls/<id>         | Call details             |
| PUT    | /api/calls/<id>         | Update call              |
| GET    | /api/users              | List agents              |
| GET    | /api/dashboard/stats    | Dashboard statistics     |
| GET    | /api/reports/daily      | Daily report data        |

## Project Structure

```
call-logging-app/
├── app/
│   ├── blueprints/     # auth, calls, dashboard, admin, reports, api
│   ├── forms/
│   ├── models/
│   ├── templates/
│   ├── static/
│   └── utils/
├── scripts/seed.py
├── tests/
├── config.py
├── run.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Testing

```bash
pip install pytest pytest-flask
pytest tests/ -v
```

## License

MIT
