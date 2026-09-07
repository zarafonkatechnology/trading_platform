# ============================================================
# priority_queue.py - Opportunity Ranking & Priority Queue
# ============================================================
# Ranks assets by opportunity and allocates computing power
# ============================================================

import heapq
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class OpportunityQueue:
    """
    Priority queue for trading opportunities.
    
    Allocates 80% of computing power to top 3 assets.
    """
    
    def __init__(self, top_n: int = 3):
        self.top_n = top_n
        self.opportunities = {}  # symbol -> opportunity_data
        self.ranked_symbols = []
        self.last_rank_update = None
        self.rank_interval = 5  # seconds
        
        logger.info(f"✅ OpportunityQueue initialized (top {top_n})")
    
    def update_opportunity(self, symbol: str, z_score: float, volatility: float, liquidity: float):
        """Update opportunity data for a symbol."""
        self.opportunities[symbol] = {
            'symbol': symbol,
            'z_score': abs(z_score),
            'volatility': volatility,
            'liquidity': liquidity,
            'timestamp': datetime.now()
        }
    
    def calculate_priority_score(self, opportunity: Dict) -> float:
        """Calculate priority score for an asset."""
        z_score = opportunity.get('z_score', 0)
        volatility = opportunity.get('volatility', 0.001)
        liquidity = opportunity.get('liquidity', 0.5)
        
        # Weighted score
        score = (
            z_score * 0.6 +           # Z-score magnitude (highest weight)
            volatility * 0.3 +        # Volatility opportunity
            liquidity * 0.1           # Liquidity confirmation
        )
        
        return score
    
    def rank_opportunities(self) -> List[str]:
        """Rank all opportunities by priority score."""
        if not self.opportunities:
            return []
        
        # Calculate scores
        scored = []
        for symbol, data in self.opportunities.items():
            score = self.calculate_priority_score(data)
            scored.append((score, symbol))
        
        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        self.ranked_symbols = [symbol for _, symbol in scored]
        self.last_rank_update = datetime.now()
        
        # Log top opportunities
        if self.ranked_symbols:
            top_symbols = self.ranked_symbols[:self.top_n]
            top_scores = [scored[i][0] for i in range(min(self.top_n, len(scored)))]
            
            logger.debug(f"📊 Top {len(top_symbols)} opportunities:")
            for i, (sym, score) in enumerate(zip(top_symbols, top_scores)):
                logger.debug(f"   #{i+1}: {sym} (score: {score:.3f})")
        
        return self.ranked_symbols
    
    def get_top_n(self, n: int = None) -> List[str]:
        """Get top N symbols to analyze."""
        if n is None:
            n = self.top_n
        
        if not self.ranked_symbols or not self._should_update():
            self.rank_opportunities()
        
        return self.ranked_symbols[:n]
    
    def _should_update(self) -> bool:
        """Check if ranks should be updated."""
        if self.last_rank_update is None:
            return True
        
        elapsed = (datetime.now() - self.last_rank_update).seconds
        return elapsed >= self.rank_interval
    
    def get_allocation(self, symbols: List[str]) -> Dict[str, float]:
        """
        Get computing power allocation for symbols.
        80% to top 3, 20% to others.
        """
        if not symbols:
            return {}
        
        ranked = self.get_top_n()
        if not ranked:
            return {symbol: 1.0 / len(symbols) for symbol in symbols}
        
        allocation = {}
        
        # Top N get 80%
        top_n = ranked[:self.top_n]
        for symbol in top_n:
            if symbol in symbols:
                allocation[symbol] = 0.8 / self.top_n
        
        # Others get 20%
        remaining_symbols = [s for s in symbols if s not in top_n]
        if remaining_symbols:
            for symbol in remaining_symbols:
                allocation[symbol] = 0.2 / len(remaining_symbols)
        
        return allocation
    
    def get_status(self) -> Dict:
        """Get queue status."""
        return {
            'total_opportunities': len(self.opportunities),
            'top_n': self.top_n,
            'ranked_symbols': self.ranked_symbols[:5],
            'last_update': self.last_rank_update.isoformat() if self.last_rank_update else None
        }