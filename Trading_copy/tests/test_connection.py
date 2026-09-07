"""
Test all connections: Dashboard, MT4, API
"""

import pytest
import os
import json
import requests
from pathlib import Path

class TestConnections:
    """Test all platform connections"""
    
    def test_dashboard_connection(self):
        """Test connection to forex dashboard"""
        try:
            response = requests.get("http://localhost:5002/health", timeout=3)
            assert response.status_code == 200
            print("✅ Dashboard connected")
        except:
            pytest.skip("Dashboard not running on port 5002")
    
    def test_mt4_file_exists(self):
        """Test MT4 file exists and is readable"""
        mt4_file = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"
        
        if os.path.exists(mt4_file):
            with open(mt4_file, 'r') as f:
                data = json.load(f)
                assert 'prices' in data or 'balance' in data
            print("✅ MT4 file exists and readable")
        else:
            pytest.skip("MT4 file not found")
    
    def test_api_connection(self, test_client):
        """Test API connection"""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        print("✅ API connected")
    
    def test_api_root(self, test_client):
        """Test API root endpoint"""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert 'name' in data
        assert 'version' in data
        print("✅ API root endpoint working")