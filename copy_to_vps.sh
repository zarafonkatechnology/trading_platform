#!/bin/bash
# ============================================================
# Copy trading system files to VPS
# ============================================================

VPS_IP="${1:-your_vps_ip}"
VPS_USER="${2:-ubuntu}"

if [ "$VPS_IP" == "your_vps_ip" ]; then
    echo "Usage: ./copy_to_vps.sh <VPS_IP> [VPS_USER]"
    echo "Example: ./copy_to_vps.sh 123.456.789.0 ubuntu"
    exit 1
fi

echo "============================================================"
echo "📁 Copying trading system files to VPS"
echo "   VPS: $VPS_USER@$VPS_IP"
echo "============================================================"

# Create directory on VPS
ssh $VPS_USER@$VPS_IP "sudo mkdir -p /opt/trading_system && sudo chown $VPS_USER:$VPS_USER /opt/trading_system"

# Copy all Python files
scp -r \
    app_code.py \
    telegram.py \
    backend/ \
    templates/ \
    static/ \
    requirements.txt \
    $VPS_USER@$VPS_IP:/opt/trading_system/

# Copy deployment script
scp deploy.sh $VPS_USER@$VPS_IP:/opt/trading_system/

echo "✅ Files copied successfully!"

echo ""
echo "Next steps:"
echo "1. ssh $VPS_USER@$VPS_IP"
echo "2. cd /opt/trading_system"
echo "3. ./deploy.sh"
echo "4. Edit .env with your API keys"
