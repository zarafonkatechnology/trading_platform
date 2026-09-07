#!/bin/bash
cd /home/mohammed/Downloads/trading_platform/backend/agents

# List of agents to create (I through W)
for agent in I J K L M N O P Q R S T U V W; do
    cat > agent_${agent,,}.py << EOF
\"\"\"
Agent_${agent} - ${AGENT_ROLE}
\"\"\"

from datetime import datetime
from .base_agent import BaseAgent
import random

class Agent${agent}(BaseAgent):
    def __init__(self):
        super().__init__("Agent_${agent}", "${AGENT_TYPE}")
        self.role = "${AGENT_ROLE}"
        self.timeframe = "${AGENT_TIMEFRAME}"
    
    def analyze(self, signal_data):
        # Simulate analysis - replace with real logic later
        vote = random.choice(['BUY', 'SELL', 'HOLD'])
        confidence = random.randint(50, 95)
        reasoning = f"${AGENT_ROLE} analysis: ${vote} signal"
        
        return {
            'agent': self.name,
            'type': self.agent_type,
            'role': self.role,
            'vote': vote,
            'confidence': confidence,
            'reasoning': reasoning,
            'timestamp': datetime.now().isoformat()
        }
EOF
done

echo "✅ All agent classes created"
