#!/bin/bash
# ============================================================
# Monitoring Script for Trading System
# ============================================================

echo "============================================================"
echo "📊 TRADING SYSTEM MONITOR"
echo "============================================================"
echo ""

# Check services
echo "🟢 SERVICE STATUS:"
echo "------------------------"
for service in trading_system telegram_bot nginx postgresql; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service: RUNNING"
    else
        echo "❌ $service: STOPPED"
    fi
done

echo ""
echo "📈 RESOURCE USAGE:"
echo "------------------------"
echo "CPU Usage: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "Memory Usage: $(free -h | awk '/^Mem:/ {print $3 "/" $2}')"
echo "Disk Usage: $(df -h / | awk 'NR==2 {print $5}')"

echo ""
echo "📊 TRADING METRICS (Last 24h):"
echo "------------------------"
if [ -f /opt/trading_system/feature_store.db ]; then
    sqlite3 /opt/trading_system/feature_store.db "SELECT COUNT(*) FROM features WHERE created_at > datetime('now', '-1 day')" 2>/dev/null | xargs echo "Trades today:"
    sqlite3 /opt/trading_system/feature_store.db "SELECT AVG(actual_outcome) FROM features WHERE created_at > datetime('now', '-1 day') AND actual_outcome IS NOT NULL" 2>/dev/null | xargs echo "Avg PnL:"
else
    echo "No feature store data yet"
fi

echo ""
echo "📋 RECENT LOGS (Last 10 lines):"
echo "------------------------"
sudo journalctl -u trading_system -n 10 --no-pager

echo ""
echo "============================================================"
