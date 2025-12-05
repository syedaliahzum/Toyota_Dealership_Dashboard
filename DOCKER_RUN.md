# Running Toyota Dashboard with Docker

## Prerequisites
- Docker and Docker Compose installed
- Port 3000 (Frontend), 8000 (Backend), 3307 (MySQL) available

## Quick Start

### 1. Start All Services
```bash
docker-compose up -d
```

### 2. Access the Application
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000
- **PHPMyAdmin:** http://localhost:8080

### 3. Generate Test Data (First Time)
```bash
python generate_500_rows_data.py
```

## Common Commands

**View logs:**
```bash
docker-compose logs -f
```

**Stop services:**
```bash
docker-compose down
```

**Rebuild services:**
```bash
docker-compose up -d --build
```

**Restart services:**
```bash
docker-compose restart
```

## Database Access
- **Host:** localhost:3307
- **Username:** toyota_user
- **Password:** toyota_password
- **Database:** toyota_db

---
That's it! The dashboard should be running and ready to use.
