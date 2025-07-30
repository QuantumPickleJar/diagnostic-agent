from flask import Flask, request, jsonify, send_from_directory
from threading import Timer, Thread
import faiss_utils
import memory
import subprocess
import os
import json
import re
import time
import logging
import shutil
import signal
import sys
from datetime import datetime, timedelta
from functools import wraps

# Configure logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('debug.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "agent_memory")
CONFIG_FILE = os.path.join(MEMORY_DIR, "static_config.json")
RECALL_FILE = os.path.join(MEMORY_DIR, "recall_log.jsonl")
ARCHIVE_DIR = os.path.join(MEMORY_DIR, "archived_sessions")
MAX_LOG_SIZE_MB = 50
MAX_LOG_DAYS = 30
LOG_ROTATION_SIZE_MB = 100

# Ensure directories exist
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

app = Flask(__name__)

# Global variables for graceful shutdown
shutdown_flag = False
background_threads = []

# SSH bridge state
ssh_bridge_enabled = False

def error_handler(f):
    """Decorator to handle endpoint errors gracefully"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {f.__name__}: {e}", exc_info=True)
            return jsonify({
                'error': 'Internal server error',
                'endpoint': f.__name__,
                'timestamp': datetime.now().isoformat()
            }), 500
    return wrapper

def init_system():
    """Initialize the diagnostic agent system on startup"""
    logger.info("Initializing Diagnostic Journalist Agent...")
    
    # Don't block startup on model download
    try:
        logger.info("Checking for cached models...")
        # Just check if cache exists, don't force download
        cache_dir = os.path.expanduser("~/.cache/sentence_transformers")
        if os.path.exists(cache_dir) and os.listdir(cache_dir):
            logger.info("Found cached sentence transformer model")
        else:
            logger.info("No cached model found, will download on first use")
    except Exception as e:
        logger.error(f"Model check failed: {e}")
    
    # Initialize FAISS index (this should be fast)
    try:
        logger.info("Initializing FAISS index...")
        count = faiss_utils.reindex()
        logger.info(f"FAISS index initialized with {count} entries")
    except Exception as e:
        logger.error(f"Failed to initialize FAISS index: {e}")
    
    logger.info("System initialization complete")

def cleanup_logs():
    """Clean up old log entries while preserving successful sessions"""
    if not os.path.exists(RECALL_FILE):
        return
    
    try:
        # Check file size
        file_size_mb = os.path.getsize(RECALL_FILE) / (1024 * 1024)
        cutoff_date = datetime.now() - timedelta(days=MAX_LOG_DAYS)
        
        if file_size_mb < MAX_LOG_SIZE_MB:
            return
        
        logger.info(f"Log file size: {file_size_mb:.2f}MB, starting cleanup...")
        
        # Read all entries
        entries = []
        successful_sessions = []
        
        with open(RECALL_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    entry_date = datetime.fromisoformat(entry.get('timestamp', '').replace('Z', '+00:00'))
                    
                    # Check if it's a successful troubleshooting session
                    task = entry.get('task', '').lower()
                    result = entry.get('result', '').lower()
                    
                    is_successful = any(keyword in task + result for keyword in [
                        'resolved', 'fixed', 'successful', 'solution', 'working',
                        'completed', 'troubleshoot', 'network issue resolved'
                    ])
                    
                    if is_successful:
                        successful_sessions.append(entry)
                    elif entry_date > cutoff_date:
                        entries.append(entry)
                        
                except (json.JSONDecodeError, ValueError):
                    continue
        
        # Archive successful sessions
        if successful_sessions:
            archive_file = os.path.join(ARCHIVE_DIR, f"successful_sessions_{int(time.time())}.jsonl")
            with open(archive_file, 'w') as f:
                for session in successful_sessions:
                    f.write(json.dumps(session) + '\n')
            logger.info(f"Archived {len(successful_sessions)} successful sessions")
        
        # Write back filtered entries
        with open(RECALL_FILE, 'w') as f:
            for entry in entries:
                f.write(json.dumps(entry) + '\n')
        
        logger.info(f"Cleaned up logs, kept {len(entries)} recent entries")
          # Reindex after cleanup
        faiss_utils.reindex()
    except Exception as e:
        logger.error(f"Error during log cleanup: {e}")

def rotate_debug_logs():
    """Rotate debug logs if they get too large"""
    debug_log_path = os.path.join(BASE_DIR, 'debug.log')
    if not os.path.exists(debug_log_path):
        return
    
    try:
        file_size_mb = os.path.getsize(debug_log_path) / (1024 * 1024)
        if file_size_mb > LOG_ROTATION_SIZE_MB:
            # Archive current log
            timestamp = int(time.time())
            archived_log = f'debug_{timestamp}.log'
            shutil.move(debug_log_path, os.path.join(BASE_DIR, archived_log))
            logger.info(f"Rotated debug log to {archived_log}")
            
            # Remove old archived logs (keep only last 3)
            log_files = sorted([f for f in os.listdir(BASE_DIR) if f.startswith('debug_') and f.endswith('.log')])
            while len(log_files) > 3:
                oldest_log = log_files.pop(0)
                os.remove(os.path.join(BASE_DIR, oldest_log))
                logger.info(f"Removed old log file: {oldest_log}")
                
    except Exception as e:
        logger.error(f"Error during debug log rotation: {e}")

def simulate_diagnostic_agent(question):
    """Simulate the diagnostic agent's response"""
    timestamp = datetime.now().isoformat()
    
    # Log the question
    memory.log_event(f"User query: {question}", "Processing diagnostic request")
    
    # Simulate some basic diagnostic responses
    if any(keyword in question.lower() for keyword in ['network', 'connection', 'ping', 'dns']):
        response = f"""[{timestamp}] NETWORK DIAGNOSTIC MODE
Query: {question}

Checking network connectivity...
- Interface status: UP
- Gateway reachable: YES
- DNS resolution: TESTING...

Recommendations:
1. Check cable connections
2. Verify IP configuration
3. Test with different DNS servers

Status: Analysis complete. See detailed logs for troubleshooting steps."""
        
        memory.log_event("Network diagnostic", response)
        return response
    
    elif any(keyword in question.lower() for keyword in ['status', 'health', 'system']):
        response = f"""[{timestamp}] SYSTEM STATUS CHECK
Query: {question}

System Health:
- CPU Usage: Normal
- Memory: 65% utilized
- Storage: 23% full
- Temperature: 45°C

Agent Status:
- FAISS Index: Active
- Memory System: Operational
- SSH Bridge: {'Enabled' if ssh_bridge_enabled else 'Disabled'}

Status: All systems operational."""
        
        memory.log_event("System status check", response)
        return response
    
    else:
        # Search for related past experiences
        related = faiss_utils.search(question, top_k=3)
        context = ""
        if related:
            context = "\n\nRelated past experiences:\n"
            for i, entry in enumerate(related, 1):
                context += f"{i}. {entry.get('task', '')}: {entry.get('result', '')[:100]}...\n"
        
        response = f"""[{timestamp}] GENERAL DIAGNOSTIC MODE
Query: {question}

Processing your request using available diagnostic protocols...

Analysis: Based on the query pattern, this appears to be a general diagnostic request. 
I'm equipped to help with network troubleshooting, system monitoring, and technical analysis.

{context}

For specific network issues, please mention 'network', 'connection', or related terms.
For system status, use 'status' or 'health' in your query.

Status: Ready for more specific diagnostic instructions."""
        
        memory.log_event(f"General query: {question}", response)
        return response

@app.route('/')
@error_handler
def index():
    """Serve the main interface"""
    return send_from_directory('.', 'index.html')

@app.route('/status')
@error_handler
def status():
    """Get agent status"""
    faiss_entries = 0
    try:
        if hasattr(faiss_utils, '_load_entries'):
            faiss_entries = len(faiss_utils._load_entries())
    except Exception as e:
        logger.warning(f"Could not get FAISS entry count: {e}")
    
    return jsonify({
        'status': 'OPERATIONAL',
        'ssh_bridge': ssh_bridge_enabled,
        'faiss_entries': faiss_entries,
        'timestamp': datetime.now().isoformat(),
        'memory_dir': MEMORY_DIR,
        'uptime': time.time() - start_time if 'start_time' in globals() else 0
    })

@app.route('/ask', methods=['POST'])
@error_handler
def ask():
    """Main chat endpoint"""
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400
    
    question = data['question'].strip()
    if not question:
        return jsonify({'error': 'Empty question'}), 400
    
    # Process the question through our diagnostic agent
    response = simulate_diagnostic_agent(question)
    
    return jsonify({'response': response})

@app.route('/search', methods=['POST'])
@error_handler
def search():
    """Search past experiences using FAISS"""
    data = request.get_json()
    query = data.get('query', '') if data else ''
    top_k = int(data.get('top_k', 5)) if data else 5
    
    if not query:
        return jsonify({'error': 'No query provided'}), 400
    
    results = faiss_utils.search(query, top_k=top_k)
    return jsonify({'results': results})

@app.route('/reindex', methods=['POST'])
@error_handler
def reindex_endpoint():
    """Reindex the FAISS database"""
    count = faiss_utils.reindex()
    return jsonify({'status': 'reindexed', 'entries': count})

@app.route('/toggle-ssh', methods=['POST'])
@error_handler
def toggle_ssh():
    """Toggle SSH bridge mode"""
    global ssh_bridge_enabled
    ssh_bridge_enabled = not ssh_bridge_enabled
    logger.info(f"SSH bridge {'enabled' if ssh_bridge_enabled else 'disabled'}")
    return jsonify({'ssh_bridge': ssh_bridge_enabled})

@app.route('/recall', methods=['GET'])
@error_handler
def recall():
    """Get recall log entries with optional filtering"""
    date_filter = request.args.get('date')
    keyword = request.args.get('keyword', '')
    
    if date_filter and not re.match(r'^\d{4}-\d{2}-\d{2}$', date_filter):
        return jsonify({'error': 'Invalid date format'}), 400
    
    if len(keyword) > 100:
        return jsonify({'error': 'Keyword too long'}), 400
    
    entries = []
    if os.path.exists(RECALL_FILE):
        with open(RECALL_FILE, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if date_filter and not entry.get('timestamp', '').startswith(date_filter):
                        continue
                    if keyword and keyword.lower() not in json.dumps(entry).lower():
                        continue
                    entries.append(entry)
                except json.JSONDecodeError:
                    continue
    
    return jsonify({'entries': entries})

@app.route('/config', methods=['GET', 'POST'])
@error_handler
def config():
    """Handle configuration management"""
    if request.method == 'GET':
        key = request.args.get('key')
        cfg = load_config()
        
        if not key:
            return jsonify({'config': cfg})
        
        if not valid_key(key):
            return jsonify({'error': 'Invalid key'}), 400
        
        parts = key.split('.')
        val = cfg
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return jsonify({'error': 'Key not found'}), 404
        
        return jsonify({'value': val})
    
    # POST - update config
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    key = data.get('key')
    new_value = data.get('value')
    
    if not key or not valid_key(key):
        return jsonify({'error': 'Invalid key'}), 400
    
    cfg = load_config()
    parts = key.split('.')
    current = cfg
    
    for p in parts[:-1]:
        if p not in current or not isinstance(current[p], dict):
            current[p] = {}
        current = current[p]
    
    current[parts[-1]] = new_value
    save_config(cfg)
    
    return jsonify({'value': new_value})

@app.route('/health')
@error_handler
def health():
    """Health check endpoint for container orchestration"""
    # Don't trigger model download in health check
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'memory_accessible': os.path.exists(MEMORY_DIR),
        'endpoints_active': True
    }
    return jsonify(health_status)

def load_config():
    """Load configuration from file"""
    if not os.path.exists(CONFIG_FILE):
        return {}
    try:
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}

def save_config(cfg):
    """Save configuration to file"""
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(cfg, f, indent=2)

def valid_key(key):
    """Validate configuration key format"""
    pattern = re.compile(r'^[A-Za-z0-9_\.]+$')
    return bool(pattern.match(key))

def _periodic_reindex():
    """Periodically reindex FAISS database"""
    global shutdown_flag
    while not shutdown_flag:
        try:
            time.sleep(300)  # 5 minutes
            if not shutdown_flag:
                faiss_utils.reindex()
                logger.info("Periodic reindex completed")
        except Exception as e:
            logger.error(f"Periodic reindex failed: {e}")

def _periodic_cleanup():
    """Periodically clean up logs"""
    global shutdown_flag
    while not shutdown_flag:
        try:
            time.sleep(3600)  # 1 hour
            if not shutdown_flag:
                cleanup_logs()
                rotate_debug_logs()
        except Exception as e:
            logger.error(f"Periodic cleanup failed: {e}")

def _periodic_health_check():
    """Periodically check system health and log status"""
    global shutdown_flag
    while not shutdown_flag:
        try:
            time.sleep(600)  # 10 minutes
            if not shutdown_flag:
                # Check memory usage, disk space, etc.
                memory_entries = len(faiss_utils._load_entries()) if hasattr(faiss_utils, '_load_entries') else 0
                logger.info(f"System health check - Memory entries: {memory_entries}, SSH: {ssh_bridge_enabled}")
        except Exception as e:
            logger.error(f"Health check failed: {e}")

def _periodic_isa_scripts():
    """Periodically run ISA scripts"""
    global shutdown_flag
    scripts = [
        os.path.join(BASE_DIR, "collect_self_facts.py"),
        os.path.join(BASE_DIR, "check_connectivity.py"),
        os.path.join(BASE_DIR, "scan_processes.py"),
    ]
    while not shutdown_flag:
        for script in scripts:
            try:
                subprocess.run(["python3", script], check=True)
            except Exception as e:
                logger.error(f"ISA script failed: {script} - {e}")
        for _ in range(300):
            if shutdown_flag:
                break
            time.sleep(1)

def signal_handler(signum, frame):
    """Handle graceful shutdown"""
    global shutdown_flag
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_flag = True
    
    # Wait for background threads to finish
    for thread in background_threads:
        if thread.is_alive():
            thread.join(timeout=5)
    
    logger.info("Graceful shutdown complete")
    sys.exit(0)

if __name__ == '__main__':
    # Set start time for uptime tracking
    start_time = time.time()
    
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize system
    init_system()
    
    # Start background tasks
    reindex_thread = Thread(target=_periodic_reindex, daemon=True)
    cleanup_thread = Thread(target=_periodic_cleanup, daemon=True)
    health_thread = Thread(target=_periodic_health_check, daemon=True)
    isa_thread = Thread(target=_periodic_isa_scripts, daemon=True)
    
    background_threads.extend([reindex_thread, cleanup_thread, health_thread, isa_thread])
    app.config["ISA_THREAD"] = isa_thread
    
    reindex_thread.start()
    cleanup_thread.start()
    health_thread.start()
    isa_thread.start()
    
    logger.info("Starting Diagnostic Journalist Agent web server on port 5000")
    logger.info(f"Memory directory: {MEMORY_DIR}")
    logger.info("All endpoints are active and monitoring initiated")
    
    try:
        # Run Flask app with proper error handling
        app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
    except Exception as e:
        logger.error(f"Flask application error: {e}")
        signal_handler(signal.SIGTERM, None)
