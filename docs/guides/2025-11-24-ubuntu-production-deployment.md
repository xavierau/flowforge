# Ubuntu Production Deployment Guide

Complete guide for deploying AI Document Processing on Ubuntu production server with two options: PM2 or systemd.

## Prerequisites

### System Requirements
- Ubuntu 20.04 LTS or 22.04 LTS
- Python 3.11 or 3.12
- PostgreSQL 14+ (local installation)
- Redis 6+ (local installation)
- Node.js 18+ (for PM2 option)
- 4GB+ RAM recommended

### Install Required Packages

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Install Redis
sudo apt install -y redis-server

# Install Python dependencies
sudo apt install -y python3-pip python3-venv python3-dev

# Install Node.js (for PM2)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install build tools
sudo apt install -y build-essential libpq-dev
```

---

## Option 1: PM2 (Recommended for Easy Management)

### 1. Install PM2

```bash
sudo npm install -g pm2
```

### 2. Setup Application

```bash
# Clone/copy application to server
cd /var/www
sudo git clone <your-repo> ai_document_processing
cd ai_document_processing

# Set ownership
sudo chown -R $USER:$USER /var/www/ai_document_processing

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install uv and dependencies
pip install uv
uv sync
```

### 3. Configure Environment

```bash
# Copy and edit .env file
cp .env.example .env
nano .env

# Required settings:
# DATABASE_URL=postgresql://user:password@localhost:5432/ai_document_processing
# CELERY_BROKER_URL=redis://localhost:6379/0
# CELERY_RESULT_BACKEND=redis://localhost:6379/0
# GOOGLE_API_KEY=your_key_here
```

### 4. Setup Database

**Option A: Automatic (Recommended)**

```bash
# Run the database setup script
./setup-database.sh

# This script will:
# - Parse DATABASE_URL from .env
# - Check if database exists
# - Create database if needed
# - Optionally run migrations
```

**Option B: Manual**

```bash
# Create PostgreSQL database and user
sudo -u postgres psql << EOF
CREATE DATABASE doc_processing;
CREATE USER postgres WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE doc_processing TO postgres;
ALTER USER postgres CREATEDB;
\q
EOF

# Run migrations
source .venv/bin/activate
alembic upgrade head
```

**Note:** The `start-production.sh` script now automatically checks and creates the database if it doesn't exist.

### 5. Update PM2 Configuration

Edit `ecosystem.config.js` to use correct paths:

```javascript
const path = require('path');

const projectRoot = '/var/www/ai_document_processing';
const venvPython = path.join(projectRoot, '.venv', 'bin', 'python');

module.exports = {
  apps: [
    {
      name: 'ai-document-processing-api',
      script: venvPython,
      args: '-m uvicorn app.main:app --host 0.0.0.0 --port 8000',
      cwd: projectRoot,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      env: {
        NODE_ENV: 'production',
        VIRTUAL_ENV: path.join(projectRoot, '.venv'),
        PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
      },
      error_file: './logs/uvicorn-error.log',
      out_file: './logs/uvicorn-out.log',
      log_file: './logs/uvicorn-combined.log',
      time: true,
    },
    {
      name: 'ai-document-processing-celery-worker',
      script: venvPython,
      args: '-m celery -A app.tasks.celery_app worker --loglevel=info',
      cwd: projectRoot,
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production',
        VIRTUAL_ENV: path.join(projectRoot, '.venv'),
        PATH: `${path.join(projectRoot, '.venv', 'bin')}:${process.env.PATH}`,
      },
      error_file: './logs/celery-error.log',
      out_file: './logs/celery-out.log',
      log_file: './logs/celery-combined.log',
      time: true,
    },
  ],
};
```

### 6. Start with PM2

```bash
# Start services
./start-production.sh

# Or manually:
pm2 start ecosystem.config.js
pm2 save

# Setup auto-start on boot
pm2 startup systemd
# Follow the command it outputs (requires sudo)
pm2 save
```

### PM2 Management Commands

```bash
# View status
pm2 status

# View logs
pm2 logs
pm2 logs ai-document-processing-api
pm2 logs ai-document-processing-celery-worker

# Restart services
pm2 restart all
pm2 restart ai-document-processing-api

# Stop services
pm2 stop all

# Monitor in real-time
pm2 monit

# Remove from PM2
pm2 delete all
```

---

## Option 2: systemd (Native Linux Service Management)

### 1. Setup Application (same as PM2 steps 2-4)

Follow steps 2-4 from the PM2 section above.

### 2. Install systemd Service Files

```bash
# Copy service files
sudo cp systemd/*.service /etc/systemd/system/

# Update paths in service files if needed
sudo nano /etc/systemd/system/ai-document-api.service
sudo nano /etc/systemd/system/ai-document-worker.service
sudo nano /etc/systemd/system/ai-document-flower.service

# Key paths to verify:
# - WorkingDirectory=/var/www/ai_document_processing
# - EnvironmentFile=/var/www/ai_document_processing/.env
# - ExecStart=/var/www/ai_document_processing/.venv/bin/...
# - User=www-data (or your user)
```

### 3. Create User and Set Permissions

```bash
# Create www-data user if not exists (usually exists by default)
sudo useradd -r -s /bin/false www-data 2>/dev/null || true

# Set ownership
sudo chown -R www-data:www-data /var/www/ai_document_processing

# Ensure storage directories exist
sudo -u www-data mkdir -p /var/www/ai_document_processing/storage/documents
sudo -u www-data mkdir -p /var/www/ai_document_processing/storage/pages
sudo -u www-data mkdir -p /var/www/ai_document_processing/logs
```

### 4. Enable and Start Services

```bash
# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services (auto-start on boot)
sudo systemctl enable ai-document-api
sudo systemctl enable ai-document-worker
sudo systemctl enable ai-document-flower  # Optional monitoring

# Start services
sudo systemctl start ai-document-api
sudo systemctl start ai-document-worker
sudo systemctl start ai-document-flower

# Check status
sudo systemctl status ai-document-api
sudo systemctl status ai-document-worker
```

### systemd Management Commands

```bash
# View status
sudo systemctl status ai-document-api
sudo systemctl status ai-document-worker

# View logs
sudo journalctl -u ai-document-api -f
sudo journalctl -u ai-document-worker -f
sudo journalctl -u ai-document-api --since "1 hour ago"

# Restart services
sudo systemctl restart ai-document-api
sudo systemctl restart ai-document-worker

# Stop services
sudo systemctl stop ai-document-api
sudo systemctl stop ai-document-worker

# Disable auto-start
sudo systemctl disable ai-document-api
sudo systemctl disable ai-document-worker

# Reload configuration after editing service files
sudo systemctl daemon-reload
sudo systemctl restart ai-document-api
```

---

## Setup PostgreSQL and Redis

### PostgreSQL Configuration

```bash
# Edit PostgreSQL config (if needed)
sudo nano /etc/postgresql/14/main/postgresql.conf

# Ensure these settings:
# listen_addresses = 'localhost'
# max_connections = 100

# Restart PostgreSQL
sudo systemctl restart postgresql

# Enable auto-start
sudo systemctl enable postgresql

# Test connection
psql -h localhost -U ai_doc_user -d ai_document_processing
```

### Redis Configuration

```bash
# Edit Redis config (if needed)
sudo nano /etc/redis/redis.conf

# Recommended settings:
# bind 127.0.0.1
# maxmemory 1gb
# maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis-server

# Enable auto-start
sudo systemctl enable redis-server

# Test connection
redis-cli ping  # Should return PONG
```

---

## Nginx Reverse Proxy (Optional)

### Install Nginx

```bash
sudo apt install -y nginx
```

### Configure Nginx

Create `/etc/nginx/sites-available/ai-document-processing`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # API endpoints
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Flower monitoring (optional, restrict access!)
    location /flower/ {
        proxy_pass http://localhost:5555/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;

        # Basic auth protection
        auth_basic "Restricted";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

### Enable Site

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/ai-document-processing /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
sudo systemctl enable nginx
```

---

## Firewall Configuration

```bash
# Install UFW (if not installed)
sudo apt install -y ufw

# Allow SSH (IMPORTANT - do this first!)
sudo ufw allow ssh

# Allow HTTP/HTTPS (if using Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Or allow specific port (if not using Nginx)
sudo ufw allow 8000/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

---

## SSL/TLS with Let's Encrypt (Optional)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured by default
# Test renewal:
sudo certbot renew --dry-run
```

---

## Monitoring and Maintenance

### Health Checks

```bash
# Check API health
curl http://localhost:8000/health

# Check service status (PM2)
pm2 status

# Check service status (systemd)
sudo systemctl status ai-document-api
sudo systemctl status ai-document-worker

# Check PostgreSQL
sudo systemctl status postgresql
psql -h localhost -U ai_doc_user -d ai_document_processing -c "SELECT 1;"

# Check Redis
sudo systemctl status redis-server
redis-cli ping
```

### View Logs

**PM2:**
```bash
pm2 logs
pm2 logs ai-document-processing-api --lines 100
```

**systemd:**
```bash
sudo journalctl -u ai-document-api -f
sudo journalctl -u ai-document-worker --since "1 hour ago"
```

**PostgreSQL:**
```bash
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

**Redis:**
```bash
sudo tail -f /var/log/redis/redis-server.log
```

### Database Backup

```bash
# Create backup script
cat > /var/www/ai_document_processing/backup-db.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/ai_document_processing"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR
pg_dump -h localhost -U ai_doc_user ai_document_processing | gzip > $BACKUP_DIR/backup_$DATE.sql.gz
# Keep only last 7 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete
EOF

chmod +x /var/www/ai_document_processing/backup-db.sh

# Add to crontab (daily at 2 AM)
(crontab -l 2>/dev/null; echo "0 2 * * * /var/www/ai_document_processing/backup-db.sh") | crontab -
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check logs
sudo journalctl -u ai-document-api -n 50
pm2 logs ai-document-processing-api --lines 50

# Check port conflicts
sudo lsof -i :8000
sudo lsof -i :5432
sudo lsof -i :6379

# Check permissions
ls -la /var/www/ai_document_processing
ls -la /var/www/ai_document_processing/.venv
```

### Database Connection Issues

```bash
# Test connection
psql -h localhost -U ai_doc_user -d ai_document_processing

# Check PostgreSQL is listening
sudo netstat -plnt | grep 5432

# Check pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Ensure: local   all   ai_doc_user   md5
```

### Celery Worker Issues

```bash
# Check Redis connection
redis-cli ping

# Check Celery can connect to Redis
source /var/www/ai_document_processing/.venv/bin/activate
python -c "from app.tasks.celery_app import celery_app; print(celery_app.connection().as_uri())"

# Check active tasks
celery -A app.tasks.celery_app inspect active
```

---

## Deployment Checklist

- [ ] PostgreSQL installed and running
- [ ] Redis installed and running
- [ ] Application code deployed to `/var/www/ai_document_processing`
- [ ] Virtual environment created and dependencies installed
- [ ] `.env` file configured with correct credentials
- [ ] Database created and migrations applied
- [ ] Storage directories created with correct permissions
- [ ] Services started (PM2 or systemd)
- [ ] Auto-start on boot enabled
- [ ] Firewall configured
- [ ] Nginx reverse proxy configured (optional)
- [ ] SSL certificate installed (optional)
- [ ] Database backup scheduled
- [ ] Health checks passing

---

## Quick Reference

### Start/Stop Services

**PM2:**
```bash
./start-production.sh              # Start all
pm2 restart all                    # Restart all
pm2 stop all                       # Stop all
pm2 status                         # Check status
```

**systemd:**
```bash
sudo systemctl start ai-document-api ai-document-worker
sudo systemctl restart ai-document-api ai-document-worker
sudo systemctl stop ai-document-api ai-document-worker
sudo systemctl status ai-document-api
```

### Update Application

```bash
cd /var/www/ai_document_processing
git pull
source .venv/bin/activate
uv sync
alembic upgrade head

# Restart services
pm2 restart all                                        # PM2
# OR
sudo systemctl restart ai-document-api ai-document-worker  # systemd
```

---

## Appendix: Migration Conflict Fix (2025-11-24)

### Problem: Migration Failure on Production

Production migration failed with error:
```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedColumn) column "tenant_id" does not exist
[SQL: CREATE INDEX idx_extraction_jobs_tenant_id ON extraction_jobs (tenant_id)]
```

### Root Cause

Migration conflict due to incorrect auto-generated migration:

1. Migration `d8f7226ad686` (2025-11-06) added `tenant_id` column and index
2. Migration `b61940e9e225` (2025-11-16) **accidentally removed** the column (auto-generated without review)
3. Migration `922d747266dd` (2025-11-17) tried to recreate the index, but column was gone

### Solution Applied Locally

**Files Modified:**

1. **`alembic/versions/2025-11-16_b61940e9e225_add_preprocessed_image_path_to_document_.py`**
   - Removed incorrect `drop_column('extraction_jobs', 'tenant_id')`
   - Removed incorrect `drop_index('idx_extraction_jobs_tenant_id')`
   - Removed incorrect `drop_constraint('extraction_jobs_tenant_id_fkey')`

2. **`alembic/versions/2025-11-17_922d747266dd_add_index_extraction_jobs_tenant_id.py`**
   - **DELETED** (duplicate of index in `d8f7226ad686`)

3. **`alembic/versions/2025-11-17_67afd920ae17_add_markdown_pipeline_support.py`**
   - Updated `down_revision` from `'922d747266dd'` to `'add_constraint_20251117'`

### Production Deployment Steps

#### Step 1: Deploy Fixed Migrations

```bash
# On local machine (already done)
git add alembic/versions/
git commit -m "Fix migration conflict: remove duplicate tenant_id operations"
git push origin develop

# On production server
cd /home/forge/flowforge-app.phbsolution.com
git pull origin develop
```

#### Step 2: Check Current Migration State

```bash
# Check alembic_version table
source .venv/bin/activate
alembic current

# OR manually check database
PGPASSWORD=your_password psql -U postgres -d ai_document_processing -c "SELECT * FROM alembic_version;"
```

#### Step 3: Handle Failed Migration State

**If migration failed BEFORE updating alembic_version (most likely):**

```bash
# Just run upgrade with fixed migrations
source .venv/bin/activate
alembic upgrade head
```

**If stuck at '922d747266dd' in alembic_version:**

```bash
# Connect to database
PGPASSWORD=your_password psql -U postgres -d ai_document_processing

# Manually update version to parent of deleted migration
UPDATE alembic_version SET version_num = 'add_constraint_20251117';

# Exit and run upgrade
\q
alembic upgrade head
```

#### Step 4: Verify Database Schema

```bash
# Connect to database
PGPASSWORD=your_password psql -U postgres -d ai_document_processing

# Check extraction_jobs has tenant_id
\d extraction_jobs

# Should show:
# - tenant_id column (UUID, not null)
# - idx_extraction_jobs_tenant_id index
# - extraction_jobs_tenant_id_fkey foreign key

# Check final migration state
\q
alembic current
# Should show: 67afd920ae17 (head)
```

#### Step 5: Start Production Services

```bash
# Use production start script
./start-production.sh

# OR manually with PM2
pm2 restart all

# OR with systemd
sudo systemctl restart ai-document-api ai-document-worker
```

#### Step 6: Verify Services

```bash
# Check API health
curl http://localhost:8000/health

# Check service status
pm2 status
# OR
sudo systemctl status ai-document-api

# Check logs for errors
pm2 logs
# OR
sudo journalctl -u ai-document-api -f
```

### Prevention: Migration Best Practices

1. **Always Review Auto-Generated Migrations**
   ```bash
   # After generating migration
   alembic revision --autogenerate -m "description"

   # ALWAYS review before committing
   git diff alembic/versions/
   ```

2. **Test Migrations in Staging First**
   ```bash
   # Create test database
   createdb test_migrations
   DATABASE_URL=postgresql://postgres:password@localhost:5432/test_migrations alembic upgrade head
   psql -d test_migrations -c "\d extraction_jobs"
   dropdb test_migrations
   ```

3. **Document Migration Dependencies**
   ```python
   """
   DEPENDENCIES:
       - Requires migration xyz (adds tenant_id column)

   CRITICAL:
       Do not modify without checking migration xyz
   """
   ```

### Current Migration Chain (Post-Fix)

```
<base> → 001 → ... → d8f7226ad686 (adds tenant_id) → b2491e5a4876
→ b61940e9e225 (fixed) → ... → add_constraint_20251117
→ 67afd920ae17 (head)
```

### Verification Commands

```bash
# Check migration chain
alembic history | grep -E "(tenant_id|extraction_jobs)"

# Verify current migration
alembic current

# Check for any pending migrations
alembic heads
```

---

**Last Updated:** 2025-11-24
**Version:** 1.1 (Added migration conflict fix appendix)
