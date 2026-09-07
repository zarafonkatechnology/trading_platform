import os
import json
import time

DASHBOARD_FILE = "C:/Users/sifer/AppData/Roaming/MetaQuotes/Terminal/Common/Files/dashboard_data.json"

if os.path.exists(DASHBOARD_FILE):
    mod_time = os.path.getmtime(DASHBOARD_FILE)
    file_age = time.time() - mod_time
    print(f"✅ File exists")
    print(f"📅 Last modified: {time.ctime(mod_time)}")
    print(f"⏰ Age: {file_age:.1f} seconds ago")
    
    with open(DASHBOARD_FILE, 'r') as f:
        data = json.load(f)
        print(f"📊 Keys in file: {list(data.keys())}")
        if 'prices' in data:
            print(f"📊 Prices: {list(data['prices'].keys())[:5]}...")
        elif 'data' in data and 'prices' in data['data']:
            print(f"📊 Prices: {list(data['data']['prices'].keys())[:5]}...")
        elif 'forex' in data:
            print(f"📊 Forex: {list(data['forex'].keys())[:5]}...")
else:
    print(f"❌ File not found: {DASHBOARD_FILE}")