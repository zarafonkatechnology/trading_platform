"""
Agent_R - Supply & Demand Expert
Tracks support/resistance zones and identifies breakouts
"""
from price_cache_manager import get_price_for_agent, get_any_price
from price_helper import get_price_with_fallback, get_price_with_details
import psycopg2
from datetime import datetime, timedelta
from collections import deque
from .base_agent import BaseAgent

class SupplyDemandExpert(BaseAgent):
    """
    Agent R - Identifies and tracks Supply/Demand zones
    Uses database to store historical zones and their strength
    """
    
    def __init__(self):
        super().__init__(
            name="Agent_R",
            agent_type="Identifies and tracks Supply/Demand zones",
            specialization= "Uses database to store historical zones and their strength"
        )
        
        # In-memory cache of active zones
        self.supply_zones = []   # Resistance (sell zones)
        self.demand_zones = []   # Support (buy zones)
        
        # Load zones from database
        self._load_zones_from_db()
        
        print(f"🏔️ {self.name} initialized - Tracking {len(self.supply_zones)} supply / {len(self.demand_zones)} demand zones")
    
    def analyze(self, signal_data):
        """
        Analyze price position relative to Supply/Demand zones
        """
        price = get_price_with_fallback(symbol, self.name)
    
        if price <= 0:
            return {'decision': 'HOLD', 'reason': 'No price available'}
        ticker = signal_data.get('pair', 'EURUSD')
        current_price = signal_data.get('price', 100.0)
        
        # 1. Find nearest zones
        nearest_supply = self._find_nearest_supply(current_price)
        nearest_demand = self._find_nearest_demand(current_price)
        
        # 2. Check for zone breaks
        supply_broken = self._check_supply_break(current_price, nearest_supply)
        demand_broken = self._check_demand_break(current_price, nearest_demand)
        
        # 3. Identify fresh zones (newly formed)
        new_zones = self._identify_fresh_zones(signal_data)
        
        # 4. Make decision
        return self._make_decision(current_price, nearest_supply, nearest_demand, supply_broken, demand_broken, new_zones)
    
    def _load_zones_from_db(self):
        """Load active zones from PostgreSQL"""
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="trading_platform",
                user="postgres",
                password="lama"
            )
            cur = conn.cursor()
            
            # Load supply zones (resistance)
            cur.execute("""
                SELECT zone_level, strength, zone_high, zone_low 
                FROM supply_demand_zones 
                WHERE zone_type = 'SUPPLY' AND strength > 0
                ORDER BY zone_level DESC
            """)
            self.supply_zones = [{'level': row[0], 'strength': row[1], 'high': row[2], 'low': row[3]} for row in cur.fetchall()]
            
            # Load demand zones (support)
            cur.execute("""
                SELECT zone_level, strength, zone_high, zone_low 
                FROM supply_demand_zones 
                WHERE zone_type = 'DEMAND' AND strength > 0
                ORDER BY zone_level ASC
            """)
            self.demand_zones = [{'level': row[0], 'strength': row[1], 'high': row[2], 'low': row[3]} for row in cur.fetchall()]
            
            cur.close()
            conn.close()
            
        except Exception as e:
            print(f"Error loading zones: {e}")
    
    def _find_nearest_supply(self, current_price):
        """Find nearest supply zone above current price"""
        for zone in self.supply_zones:
            if zone['level'] > current_price:
                return zone
        return None
    
    def _find_nearest_demand(self, current_price):
        """Find nearest demand zone below current price"""
        for zone in reversed(self.demand_zones):
            if zone['level'] < current_price:
                return zone
        return None
    
    def _check_supply_break(self, current_price, supply_zone):
        """Check if price broke above a supply zone"""
        if supply_zone and current_price > supply_zone['high']:
            return {'broken': True, 'zone': supply_zone}
        return {'broken': False, 'zone': None}
    
    def _check_demand_break(self, current_price, demand_zone):
        """Check if price broke below a demand zone"""
        if demand_zone and current_price < demand_zone['low']:
            return {'broken': True, 'zone': demand_zone}
        return {'broken': False, 'zone': None}
    
    def _identify_fresh_zones(self, signal_data):
        """
        Identify new Supply/Demand zones from recent price action
        A fresh zone forms after a strong move and consolidation
        """
        # In production: Analyze recent candles
        # For demo: Simulate zone detection
        
        import random
        new_zones = []
        
        # 20% chance of new zone formation
        if random.random() < 0.2:
            is_supply = random.choice([True, False])
            zone_level = signal_data.get('price', 100.0) * (1 + random.uniform(-0.01, 0.01))
            
            new_zones.append({
                'type': 'SUPPLY' if is_supply else 'DEMAND',
                'level': round(zone_level, 3),
                'strength': 1
            })
            
            # Store in database
            self._save_zone_to_db(new_zones[-1])
        
        return new_zones
    
    def _save_zone_to_db(self, zone):
        """Save new zone to database"""
        try:
            conn = psycopg2.connect(
                host="localhost",
                port=5432,
                database="trading_platform",
                user="postgres",
                password="lama"
            )
            cur = conn.cursor()
            
            cur.execute("""
                INSERT INTO supply_demand_zones (symbol, zone_type, zone_level, strength)
                VALUES (%s, %s, %s, %s)
            """, ('EURUSD', zone['type'], zone['level'], zone['strength']))
            
            conn.commit()
            cur.close()
            conn.close()
            
            print(f"✅ New {zone['type']} zone saved at {zone['level']}")
            
        except Exception as e:
            print(f"Error saving zone: {e}")
    
    def _update_zone_strength(self, zone_level, zone_type):
        """Increase zone strength when tested again"""
        # Zone gets stronger each time it holds
        pass
    
    def _make_decision(self, current_price, nearest_supply, nearest_demand, supply_broken, demand_broken, new_zones):
        """
        Make trading decision based on Supply/Demand analysis
        """
        # Case 1: Price broke above supply (resistance becomes support)
        if supply_broken['broken']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'BUY',
                'confidence': 85,
                'reasoning': f"✅ SUPPLY BREAK: Price broke above {supply_broken['zone']['level']:.3f}. Resistance became support. Bullish.",
                'zone_data': {
                    'nearest_supply': nearest_supply['level'] if nearest_supply else None,
                    'nearest_demand': nearest_demand['level'] if nearest_demand else None,
                    'new_zones': new_zones
                },
                'timestamp': datetime.now().isoformat()
            }
        
        # Case 2: Price broke below demand (support becomes resistance)
        if demand_broken['broken']:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'SELL',
                'confidence': 85,
                'reasoning': f"❌ DEMAND BREAK: Price broke below {demand_broken['zone']['level']:.3f}. Support became resistance. Bearish.",
                'zone_data': {
                    'nearest_supply': nearest_supply['level'] if nearest_supply else None,
                    'nearest_demand': nearest_demand['level'] if nearest_demand else None,
                    'new_zones': new_zones
                },
                'timestamp': datetime.now().isoformat()
            }
        
        # Case 3: Price near demand zone (support) - potential bounce
        if nearest_demand and abs(current_price - nearest_demand['level']) / current_price < 0.005:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'BUY',
                'confidence': min(75, 50 + nearest_demand['strength'] * 5),
                'reasoning': f"📈 NEAR DEMAND ZONE: Price at support {nearest_demand['level']:.3f}. Zone strength: {nearest_demand['strength']}/5. Potential bounce.",
                'zone_data': {
                    'nearest_supply': nearest_supply['level'] if nearest_supply else None,
                    'nearest_demand': nearest_demand['level'] if nearest_demand else None,
                    'new_zones': new_zones
                },
                'timestamp': datetime.now().isoformat()
            }
        
        # Case 4: Price near supply zone (resistance) - potential rejection
        if nearest_supply and abs(current_price - nearest_supply['level']) / current_price < 0.005:
            return {
                'agent': self.name,
                'type': self.agent_type,
                'vote': 'SELL',
                'confidence': min(75, 50 + nearest_supply['strength'] * 5),
                'reasoning': f"📉 NEAR SUPPLY ZONE: Price at resistance {nearest_supply['level']:.3f}. Zone strength: {nearest_supply['strength']}/5. Potential rejection.",
                'zone_data': {
                    'nearest_supply': nearest_supply['level'] if nearest_supply else None,
                    'nearest_demand': nearest_demand['level'] if nearest_demand else None,
                    'new_zones': new_zones
                },
                'timestamp': datetime.now().isoformat()
            }
        
        # Case 5: No clear zone interaction
        return {
            'agent': self.name,
            'type': self.agent_type,
            'vote': 'HOLD',
            'confidence': 40,
            'reasoning': f"⚖️ No active Supply/Demand zones near price ({current_price:.3f}). Waiting for zone interaction.",
            'zone_data': {
                'nearest_supply': nearest_supply['level'] if nearest_supply else None,
                'nearest_demand': nearest_demand['level'] if nearest_demand else None,
                'new_zones': new_zones
            },
            'timestamp': datetime.now().isoformat()
        }
