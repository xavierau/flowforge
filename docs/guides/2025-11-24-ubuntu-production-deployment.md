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

```bash
# Create PostgreSQL database and user
sudo -u postgres psql << EOF
CREATE DATABASE ai_document_processing;
CREATE USER ai_doc_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE ai_document_processing TO ai_doc_user;
\q
EOF

# Run migrations
source .venv/bin/activate
alembic upgrade head
```

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

**Last Updated:** 2025-11-24
**Version:** 1.0
