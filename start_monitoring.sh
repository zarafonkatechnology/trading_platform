#!/bin/bash
# ============================================================
# Start Monitoring Stack
# ============================================================

echo "============================================================"
echo "📊 Starting Monitoring Stack"
echo "============================================================"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not installed. Installing..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose not installed. Installing..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Start monitoring stack
echo "🚀 Starting Prometheus, Grafana, and exporters..."
docker-compose -f docker-compose.monitoring.yml up -d

echo ""
echo "✅ Monitoring stack started!"
echo ""
echo "📍 Access points:"
echo "   Grafana:      http://localhost:3000 (admin/admin)"
echo "   Prometheus:   http://localhost:9090"
echo "   Node Exporter: http://localhost:9100"
echo "   Postgres Exporter: http://localhost:9187"
echo ""
echo "📊 Your trading metrics are available at: http://localhost:5000/metrics"
echo ""
echo "To stop: docker-compose -f docker-compose.monitoring.yml down"
