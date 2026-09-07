from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from datetime import datetime
import random

load_dotenv()

app = Flask(__name__, template_folder='templates')
CORS(app)

DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'trading_platform')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'lama')

def get_db():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, database=DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
        cursor_factory=psycopg2.extras.RealDictCursor
    )

# ============================================
# MAIN ROUTE
# ============================================

@app.route('/platform2')
def platform2():
    return render_template('platform2.html')

# ============================================
# AGENTS ENDPOINTS
# ============================================

@app.route('/api/platform2/agents')
def api_agents():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT agent_name, agent_type, xp_points, token_balance, trust_weight, vote_accuracy FROM core_agents ORDER BY agent_name")
    agents = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'agents': agents})

@app.route('/api/platform2/add_demo_agent', methods=['POST'])
def api_add_demo_agent():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM core_agents")
    result = cur.fetchone()
    count = result['count']
    new_num = count + 1
    new_name = f"Agent_{chr(64 + new_num)}" if new_num <= 26 else f"Agent_{new_num}"
    cur.execute("""
        INSERT INTO core_agents (agent_name, agent_type, xp_points, token_balance, trust_weight)
        VALUES (%s, %s, %s, %s, %s)
    """, (new_name, 'Demo Agent', 0, 1000, 0.2))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({'success': True, 'agent_name': new_name})

# ============================================
# TELEGRAM SIGNALS
# ============================================

@app.route('/api/platform2/telegram_signals')
def api_telegram_signals():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, asset_type, current_price, confidence_percent, signal_strength, signal_timestamp FROM signals ORDER BY signal_timestamp DESC LIMIT 50")
        signals = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({'success': True, 'signals': signals})
    except Exception as e:
        print(f"Error in telegram_signals: {e}")
        return jsonify({'success': True, 'signals': []})
# ============================================
# SUPERVISOR VOTES
# ============================================

@app.route('/api/platform2/supervisor_votes')
def api_supervisor_votes():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, agent_name, vote_cast, confidence, was_correct, error_type, timestamp FROM supervisor_vote_records ORDER BY timestamp DESC LIMIT 100")
        votes = cur.fetchall()
    except:
        votes = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'votes': votes})

@app.route('/api/platform2/vote_accuracy')
def api_vote_accuracy():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT agent_name, 
                   COUNT(*) as total_votes,
                   SUM(CASE WHEN was_correct THEN 1 ELSE 0 END) as correct_votes,
                   ROUND(SUM(CASE WHEN was_correct THEN 1 ELSE 0 END)::DECIMAL / COUNT(*) * 100, 2) as accuracy
            FROM supervisor_vote_records
            GROUP BY agent_name
            ORDER BY accuracy DESC
        """)
        accuracy = cur.fetchall()
    except:
        accuracy = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'accuracy': accuracy})

# ============================================
# AGENT ERRORS
# ============================================

@app.route('/api/platform2/agent_errors')
def api_agent_errors():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, agent_name, error_category, error_description, root_cause, severity, is_fixed, created_at FROM agent_errors ORDER BY created_at DESC LIMIT 100")
        errors = cur.fetchall()
        cur.close()
        conn.close()
        
        result = []
        for row in errors:
            result.append({
                'id': row[0],
                'agent_name': row[1],
                'error_category': row[2],
                'error_description': row[3],
                'root_cause': row[4],
                'severity': row[5],
                'is_fixed': row[6],
                'created_at': row[7].isoformat() if row[7] else None
            })
        
        return jsonify({'success': True, 'errors': result})
    except Exception as e:
        print(f"Error in agent_errors: {e}")
        return jsonify({'success': True, 'errors': []})
@app.route('/api/platform2/correct_agent_error', methods=['POST'])
def api_correct_agent_error():
    data = request.json
    error_id = data.get('error_id')
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE agent_errors SET is_fixed = TRUE WHERE id = %s", (error_id,))
        conn.commit()
    except:
        pass
    cur.close()
    conn.close()
    return jsonify({'success': True})

# ============================================
# ML TRAINING CYCLES
# ============================================
@app.route('/api/platform2/training_cycles')
def api_training_cycles():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT cycle_number, started_at, completed_at, pre_training_accuracy, post_training_accuracy, status FROM ml_training_cycles ORDER BY cycle_number DESC")
        cycles = cur.fetchall()
        cur.close()
        conn.close()
        
        # Convert to list of dicts for JSON
        result = []
        for row in cycles:
            result.append({
                'cycle_number': row[0],
                'started_at': row[1].isoformat() if row[1] else None,
                'completed_at': row[2].isoformat() if row[2] else None,
                'pre_training_accuracy': float(row[3]) if row[3] else None,
                'post_training_accuracy': float(row[4]) if row[4] else None,
                'status': row[5]
            })
        
        return jsonify({'success': True, 'cycles': result})
    except Exception as e:
        print(f"Error in training_cycles: {e}")
        return jsonify({'success': True, 'cycles': []})

# ============================================
# GATEKEEPER AUDIT
# ============================================

@app.route('/api/platform2/gatekeeper_audit')
def api_gatekeeper_audit():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id, agent_name, pillar1_identity_passed, pillar2_logic_passed, pillar3_resource_passed, gate_status, block_reason, timestamp FROM gatekeeper_full_audit ORDER BY timestamp DESC LIMIT 50")
        rows = cur.fetchall()
        cur.close()
        conn.close()
        
        audits = []
        for row in rows:
            audits.append({
                'id': row[0],
                'agent_name': row[1],
                'pillar1_identity_passed': row[2],
                'pillar2_logic_passed': row[3],
                'pillar3_resource_passed': row[4],
                'gate_status': row[5],
                'block_reason': row[6],
                'timestamp': row[7].isoformat() if row[7] else None
            })
        
        return jsonify({'success': True, 'audits': audits})
    except Exception as e:
        print(f"Gatekeeper audit error: {e}")
        return jsonify({'success': True, 'audits': []})

@app.route('/api/platform2/gatekeeper_stats')
def api_gatekeeper_stats():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as total, SUM(CASE WHEN gate_status = 'OPEN' THEN 1 ELSE 0 END) as opened, SUM(CASE WHEN gate_status != 'OPEN' THEN 1 ELSE 0 END) as blocked FROM gatekeeper_full_audit")
        row = cur.fetchone()
        cur.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_checks': row[0] if row else 0,
                'gates_opened': row[1] if row else 0,
                'gates_blocked': row[2] if row else 0
            }
        })
    except Exception as e:
        print(f"Gatekeeper stats error: {e}")
        return jsonify({'success': True, 'stats': {'total_checks': 0, 'gates_opened': 0, 'gates_blocked': 0}})
# ============================================
# SENTINEL STATUS
# ============================================

@app.route('/api/platform2/sentinel_status')
def api_sentinel_status():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT metric_name, current_value, target_value FROM sentinel_mastery")
        mastery = cur.fetchall()
        cur.execute("SELECT COUNT(*) as veto_count FROM sentinel_veto_log")
        veto_count = cur.fetchone()['veto_count'] if cur.fetchone() else 0
    except:
        mastery = []
        veto_count = 0
    cur.close()
    conn.close()
    return jsonify({'success': True, 'mastery': mastery, 'veto_count': veto_count})

@app.route('/api/platform2/sentinel_veto_log')
def api_sentinel_veto_log():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT veto_type, target_agent, veto_reason, timestamp FROM sentinel_veto_log ORDER BY timestamp DESC LIMIT 30")
        vetos = cur.fetchall()
    except:
        vetos = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'vetos': vetos})

# ============================================
# KNOWLEDGE EXCHANGE & CONVERSATIONS
# ============================================

@app.route('/api/platform2/knowledge')
def api_knowledge():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, from_agent, to_agent, topic, xp_reward, timestamp FROM knowledge_exchange ORDER BY id DESC LIMIT 30")
        knowledge = cur.fetchall()
    except:
        knowledge = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'knowledge': knowledge})

@app.route('/api/platform2/conversations')
def api_conversations():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, from_agent, to_agent, message, timestamp FROM agent_conversations ORDER BY id DESC LIMIT 30")
        conversations = cur.fetchall()
    except:
        conversations = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'conversations': conversations})

# ============================================
# COLLABORATION METRICS
# ============================================

@app.route('/api/platform2/collaboration_metrics')
def api_collaboration_metrics():
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id, consensus_percentage, teamwork_score, zero_error_contribution, timestamp FROM collaboration_metrics ORDER BY timestamp DESC LIMIT 30")
        metrics = cur.fetchall()
    except:
        metrics = []
    cur.close()
    conn.close()
    return jsonify({'success': True, 'metrics': metrics})


# ============================================
# HEALTH CHECK
# ============================================

@app.route('/api/platform2/health')
def api_health():
    return jsonify({'success': True, 'status': 'healthy'})

# ============================================
# RUN APP
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("📊 PLATFORM 2 - FULL DASHBOARD")
    print("URL: http://localhost:5001/platform2")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5001, debug=True)
