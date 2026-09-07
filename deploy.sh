#!/bin/bash
# ============================================================
# Complete VPS Deployment Script for Trading System
# Supports: Ubuntu 22.04/24.04 LTS
# ============================================================

set -e

echo "============================================================"
echo "🚀 TRADING SYSTEM VPS DEPLOYMENT"
echo "============================================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/trading_system"
PYTHON_VERSION="3.10"
SYSTEM_USER="$(whoami)"

echo -e "${GREEN}📦 Updating system packages...${NC}"
sudo apt update && sudo apt upgrade -y

echo -e "${GREEN}🔧 Installing dependencies...${NC}"
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    build-essential \
    libpq-dev \
    libssl-dev \
    libffi-dev

echo -e "${GREEN}🐍 Setting up Python virtual environment...${NC}"
cd /opt
sudo mkdir -p $APP_DIR
sudo chown $SYSTEM_USER:$SYSTEM_USER $APP_DIR
cd $APP_DIR

python3 -m venv venv
source venv/bin/activate

echo -e "${GREEN}📦 Installing Python packages...${NC}"
pip install --upgrade pip
pip install \
    flask \
    flask-cors \
    psycopg2-binary \
    requests \
    python-dotenv \
    schedule \
    telebot \
    pyttsx3 \
    numpy \
    pandas \
    scikit-learn \
    torch \
    websocket-client \
    oandapyV20

echo -e "${GREEN}🗄️ Setting up PostgreSQL...${NC}"
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE trading_platform;
CREATE USER trading_user WITH PASSWORD 'lama';
GRANT ALL PRIVILEGES ON DATABASE trading_platform TO trading_user;
ALTER USER trading_user CREATEDB;
EOF

echo -e "${GREEN}📁 Creating directory structure...${NC}"
mkdir -p $APP_DIR/logs
mkdir -p $APP_DIR/backups
mkdir -p $APP_DIR/data
mkdir -p $APP_DIR/models

echo -e "${GREEN}⚙️ Creating environment file...${NC}"
cat > $APP_DIR/.env << 'EOF'
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_platform
DB_USER=trading_user
DB_PASSWORD=lama

# OANDA (replace with your actual keys)
OANDA_API_KEY=your_oanda_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=practice

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_token_here
TELEGRAM_CHAT_ID=your_chat_id_here

# Flask
FLASK_APP=app_code.py
FLASK_ENV=production
SECRET_KEY=your_secret_key_here
EOF

echo -e "${YELLOW}⚠️ Please edit $APP_DIR/.env with your actual API keys${NC}"

echo -e "${GREEN}🛠️ Creating systemd service...${NC}"
sudo cat > /etc/systemd/system/trading_system.service << 'EOF'
[Unit]
Description=Trading System Multi-Agent
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/trading_system
Environment="PATH=/opt/trading_system/venv/bin"
Environment="FLASK_APP=app_code.py"
Environment="FLASK_ENV=production"
ExecStart=/opt/trading_system/venv/bin/python3 /opt/trading_system/app_code.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/trading_system/logs/system.log
StandardError=append:/opt/trading_system/logs/error.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}🤖 Creating Telegram bot service...${NC}"
sudo cat > /etc/systemd/system/telegram_bot.service << 'EOF'
[Unit]
Description=Trading System Telegram Bot
After=network.target trading_system.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/opt/trading_system
Environment="PATH=/opt/trading_system/venv/bin"
ExecStart=/opt/trading_system/venv/bin/python3 /opt/trading_system/telegram.py
Restart=always
RestartSec=10
StandardOutput=append:/opt/trading_system/logs/telegram.log
StandardError=append:/opt/trading_system/logs/telegram_error.log

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}📊 Creating Nginx configuration...${NC}"
sudo cat > /etc/nginx/sites-available/trading_system << 'EOF'
server {
    listen 80;
    server_name _;
    
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static {
        alias /opt/trading_system/static;
    }
    
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5000/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/trading_system /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

echo -e "${GREEN}🔧 Setting up log rotation...${NC}"
sudo cat > /etc/logrotate.d/trading_system << 'EOF'
/opt/trading_system/logs/*.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 0644 ubuntu ubuntu
}
EOF

echo -e "${GREEN}🔄 Creating backup cron job...${NC}"
sudo cat > /etc/cron.daily/trading_backup << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/trading_system/backups"
DATE=$(date +%Y%m%d_%H%M%S)
sudo -u postgres pg_dump trading_platform > "$BACKUP_DIR/backup_$DATE.sql"
find "$BACKUP_DIR" -name "backup_*.sql" -mtime +7 -delete
EOF
sudo chmod +x /etc/cron.daily/trading_backup

echo -e "${GREEN}✅ Reloading services...${NC}"
sudo systemctl daemon-reload
sudo systemctl enable trading_system
sudo systemctl enable telegram_bot
sudo systemctl enable nginx

echo -e "${GREEN}============================================================${NC}"
echo -e "${GREEN}✅ DEPLOYMENT COMPLETE!${NC}"
echo -e "${GREEN}============================================================${NC}"
echo ""
echo -e "${YELLOW}📋 Next steps:${NC}"
echo "1. Edit $APP_DIR/.env with your actual API keys"
echo "2. Copy your application code to $APP_DIR"
echo "3. Start services:"
echo "   sudo systemctl start trading_system"
echo "   sudo systemctl start telegram_bot"
echo "   sudo systemctl start nginx"
echo ""
echo "4. Check status:"
echo "   sudo systemctl status trading_system"
echo "   sudo journalctl -u trading_system -f"
echo ""
echo "5. Access dashboard: http://YOUR_VPS_IP"
echo ""
echo -e "${YELLOW}⚠️ Don't forget to configure firewall:${NC}"
echo "   sudo ufw allow 22"
echo "   sudo ufw allow 80"
echo "   sudo ufw allow 443"
echo "   sudo ufw enable"
echo ""
