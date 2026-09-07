<!DOCTYPE html>
<html>
<head>
    <title>Platform 1 – Trading & Learning</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: Arial, sans-serif; background: #0a0e27; color: #e0e0e0; padding: 20px; }
        .container { max-width: 1400px; margin: auto; }
        .header { background: #1a1f3a; padding: 20px; border-radius: 12px; margin-bottom: 20px; text-align: center; }
        .stats { display: flex; gap: 20px; justify-content: center; margin-top: 10px; }
        .stat { background: #0f1322; padding: 10px 20px; border-radius: 10px; }
        .stat-value { font-size: 24px; font-weight: bold; color: #ffd700; }
        .two-columns { display: flex; gap: 20px; margin-bottom: 20px; }
        .panel { flex: 1; background: #0f1322; padding: 20px; border-radius: 12px; }
        .panel h3 { color: #ffd700; margin-bottom: 15px; }
        .agent-item { background: #1a1f3a; padding: 10px; margin: 8px 0; border-radius: 8px; cursor: pointer; display: flex; justify-content: space-between; }
        .agent-item:hover { background: #2a2f4a; }
        .knowledge-item { background: #1a1f3a; padding: 10px; margin: 8px 0; border-radius: 8px; }
        input, select, textarea { width: 100%; padding: 10px; margin: 5px 0 15px; background: #1a1f3a; border: 1px solid #2a2f4a; border-radius: 6px; color: white; }
        button { background: #ffd700; color: #0a0e27; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; font-weight: bold; margin: 5px; }
        button:hover { opacity: 0.9; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.8); justify-content: center; align-items: center; }
        .modal-content { background: #1a1f3a; padding: 30px; border-radius: 12px; max-width: 500px; width: 90%; }
        .auto-save { position: fixed; bottom: 20px; right: 20px; font-size: 12px; background: #0f1322; padding: 5px 10px; border-radius: 20px; }
    </style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🤖 Platform 1 – Trading Agent Dashboard</h1>
        <div class="stats" id="stats">
            <div class="stat">🤖 Agents: <span id="agentCount">0</span></div>
            <div class="stat">💰 Total XP: <span id="totalXP">0</span></div>
            <div class="stat">🎴 Total Tokens: <span id="totalTokens">0</span></div>
        </div>
    </div>
    
    <div class="two-columns">
        <div class="panel">
            <h3>🤖 Agents</h3>
            <div id="agentsList"></div>
            <button onclick="addDemoAgent()">➕ Add Demo Agent</button>
        </div>
        <div class="panel">
            <h3>📚 Knowledge Exchange</h3>
            <div id="knowledgeFeed" style="max-height: 400px; overflow-y: auto;"></div>
        </div>
    </div>
    
    <div class="panel">
        <h3>📖 Teach Agents</h3>
        <select id="teachAgent">
            <option value="Agent_A">Agent_A</option>
            <option value="Agent_B">Agent_B</option>
            <option value="Agent_C">Agent_C</option>
            <option value="Agent_D">Agent_D</option>
            <option value="Agent_E">Agent_E</option>
            <option value="ALL">📢 ALL AGENTS</option>
        </select>
        <input type="text" id="topic" placeholder="Topic">
        <textarea id="content" rows="2" placeholder="Knowledge content..."></textarea>
        <button onclick="teach()">🎓 Teach (+50 XP)</button>
        <button onclick="saveAll()">💾 Save All Data</button>
    </div>
    
    <div class="panel">
        <h3>💬 Agent Conversation</h3>
        <select id="fromAgent"><option>Agent_A</option><option>Agent_B</option><option>Agent_C</option><option>Agent_D</option><option>Agent_E</option></select>
        <select id="toAgent"><option>Agent_A</option><option>Agent_B</option><option>Agent_C</option><option>Agent_D</option><option>Agent_E</option></select>
        <input type="text" id="message" placeholder="Type your message...">
        <button onclick="sendMessage()">💬 Send</button>
    </div>
</div>

<div id="agentModal" class="modal"><div class="modal-content" id="modalContent"></div><button onclick="closeModal()">Close</button></div>
<div class="auto-save">💾 Auto-saving every 30 seconds</div>

<script>
    async function loadAgents() {
        const res = await fetch('/api/agents');
        const data = await res.json();
        if (data.success) {
            const agents = data.agents;
            let html = '';
            let totalXP = 0, totalTokens = 0;
            agents.forEach(a => {
                totalXP += a.xp_points;
                totalTokens += a.token_balance;
                html += `<div class="agent-item" onclick="showAgent('${a.name}')">
                            <div><strong>${a.name}</strong><br><small>${a.type}</small></div>
                            <div>⚡${a.xp_points} 🎴${a.token_balance}<br>📊${a.vote_accuracy}%</div>
                         </div>`;
            });
            document.getElementById('agentsList').innerHTML = html;
            document.getElementById('agentCount').innerText = agents.length;
            document.getElementById('totalXP').innerText = totalXP;
            document.getElementById('totalTokens').innerText = totalTokens;
            
            // Update dropdowns
            const opts = agents.map(a => `<option value="${a.name}">${a.name}</option>`).join('');
            document.getElementById('teachAgent').innerHTML = `<option value="ALL">📢 ALL AGENTS</option>${opts}`;
            document.getElementById('fromAgent').innerHTML = opts;
            document.getElementById('toAgent').innerHTML = opts;
        }
    }
    
    async function loadKnowledge() {
        const res = await fetch('/api/knowledge');
        const data = await res.json();
        if (data.success && data.exchanges) {
            let html = '';
            data.exchanges.forEach(e => {
                html += `<div class="knowledge-item">
                            <div><strong>${e.from}</strong> → ${e.to}</div>
                            <div>📖 ${e.topic}</div>
                            <div><small>${e.content?.substring(0, 100)}</small></div>
                            <div style="color:#4caf50;">+${e.xp} XP, +${e.tokens} Tokens</div>
                            <div style="font-size:11px;">${e.time}</div>
                         </div>`;
            });
            document.getElementById('knowledgeFeed').innerHTML = html;
        }
    }
    
    async function teach() {
        const agent = document.getElementById('teachAgent').value;
        const topic = document.getElementById('topic').value;
        const content = document.getElementById('content').value;
        if (!topic || !content) { alert('Enter topic and content'); return; }
        
        if (agent === 'ALL') {
            await fetch('/api/teach_all', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({topic, content})});
        } else {
            await fetch('/api/teach', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({agent_name: agent, topic, content})});
        }
        document.getElementById('topic').value = '';
        document.getElementById('content').value = '';
        loadAgents();
        loadKnowledge();
    }
    
    async function sendMessage() {
        const fromAgent = document.getElementById('fromAgent').value;
        const toAgent = document.getElementById('toAgent').value;
        const message = document.getElementById('message').value;
        if (!message) return;
        await fetch('/api/conversation', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({from_agent: fromAgent, to_agent: toAgent, message})});
        document.getElementById('message').value = '';
        loadKnowledge();
    }
    
    async function saveAll() {
        await fetch('/api/save_all', {method: 'POST'});
        alert('Saved!');
    }
    
    async function addDemoAgent() {
        await fetch('/api/add_demo_agent', {method: 'POST'});
        loadAgents();
    }
    
    async function showAgent(name) {
        const res = await fetch('/api/agents');
        const data = await res.json();
        const agent = data.agents.find(a => a.name === name);
        if (agent) {
            document.getElementById('modalContent').innerHTML = `
                <h3>${agent.name}</h3>
                <p>Type: ${agent.type}</p>
                <p>Specialization: ${agent.specialization}</p>
                <p>⚡ XP: ${agent.xp_points}</p>
                <p>🎴 Tokens: ${agent.token_balance}</p>
                <p>📊 Accuracy: ${agent.vote_accuracy}%</p>
                <p>🎯 Trust Weight: ${(agent.trust_weight * 100).toFixed(1)}%</p>
                <p>📚 Knowledge Shared: ${agent.knowledge_shared_count}</p>
                <hr>
                <input type="text" id="teachTopic" placeholder="Topic">
                <textarea id="teachContent" rows="2" placeholder="Content"></textarea>
                <button onclick="teachAgent('${agent.name}')">🎓 Teach (+50 XP)</button>
            `;
            document.getElementById('agentModal').style.display = 'flex';
        }
    }
    
    async function teachAgent(name) {
        const topic = document.getElementById('teachTopic').value;
        const content = document.getElementById('teachContent').value;
        if (!topic || !content) return;
        await fetch('/api/teach', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({agent_name: name, topic, content})});
        closeModal();
        loadAgents();
        loadKnowledge();
    }
    
    function closeModal() { document.getElementById('agentModal').style.display = 'none'; }
    
    loadAgents();
    loadKnowledge();
    setInterval(() => { loadAgents(); loadKnowledge(); }, 10000);
</script>
</body>
</html>
