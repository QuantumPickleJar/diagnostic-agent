from flask import Flask, request, jsonify, send_from_directory
try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    def load_dotenv(*args, **kwargs):
        pass  # No-op if dotenv not available
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
from semantic_task_scorer import semantic_scorer

# Configure logging with rotation
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/app/logs/debug.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Import diagnostic engines
try:
    from diagnostic_agent import execute_diagnostic
    REAL_DIAGNOSTICS = True
except ImportError:
    REAL_DIAGNOSTICS = False
    logger.warning("Real diagnostic engine not available, using simulation")

# Import smart diagnostic agent
try:
    from unified_smart_agent import process_smart_query, smart_agent
    SMART_AGENT_AVAILABLE = True
    logger.info("Unified smart diagnostic agent loaded successfully")
except ImportError as e:
    SMART_AGENT_AVAILABLE = False
    logger.warning(f"Smart diagnostic agent not available: {e}")

# Import autonomic dispatcher
try:
    from autonomic_dispatcher import (
        dispatch_task,
        test_connectivity,
        get_dispatch_stats,
        get_bridge_status,
        set_wake_on_lan
    )
    AUTONOMIC_DISPATCHER_AVAILABLE = True
    logger.info("Autonomic dispatcher loaded successfully")
    
    # Test connectivity at startup
    connectivity_ok, connectivity_msg = test_connectivity()
    logger.info(f"Remote dev machine connectivity: {connectivity_msg}")
except ImportError as e:
    AUTONOMIC_DISPATCHER_AVAILABLE = False
    logger.warning(f"Autonomic dispatcher not available: {e}")
    
    # Fallback functions
    def dispatch_task(task_text):
        from unified_smart_agent import smart_agent
        return smart_agent.process_query(task_text)
    
    def test_connectivity():
        return False, "Autonomic dispatcher not available"
    
    def get_dispatch_stats():
        return {"error": "Autonomic dispatcher not available"}

    def get_bridge_status():
        return {"status": "unknown", "wake_on_lan_enabled": False, "fallback_used": False, "last_ping_time": None, "disabled_until": 0}

    def set_wake_on_lan(enabled: bool):
        return False

# Import bridge status monitor
try:
    from bridge_status_monitor import (
        start_bridge_monitoring,
        stop_bridge_monitoring,
        get_bridge_status as get_detailed_bridge_status,
        force_bridge_check
    )
    BRIDGE_MONITOR_AVAILABLE = True
    logger.info("Bridge status monitor loaded successfully")
except ImportError as e:
    BRIDGE_MONITOR_AVAILABLE = False
    logger.warning(f"Bridge status monitor not available: {e}")
    
    # Fallback functions
    def start_bridge_monitoring():
        return False
    
    def stop_bridge_monitoring():
        pass
    
    def get_detailed_bridge_status():
        return {"error": "Bridge monitor not available"}
    
    def force_bridge_check():
        return False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_DIR = os.path.join(BASE_DIR, "agent_memory")
CONFIG_FILE = os.path.join(MEMORY_DIR, "static_config.json")
RECALL_FILE = os.path.join(MEMORY_DIR, "recall_log.jsonl")
ARCHIVE_DIR = os.path.join(MEMORY_DIR, "archived_sessions")
MAX_LOG_SIZE_MB = 250
MAX_LOG_DAYS = 30
LOG_ROTATION_SIZE_MB = 100

# Ensure directories exist
os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

app = Flask(__name__)

# Load activation word from optional .env file
if DOTENV_AVAILABLE:
    load_dotenv(os.path.join(BASE_DIR, '.env'))
ACTIVATION_WORD = os.getenv('ACTIVATION_WORD')

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

def requires_activation_word(f):
    """Ensure requests supply the correct activation word."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        word = request.headers.get('X-Activate-Word')
        if word is None:
            data = request.get_json(silent=True) or {}
            word = data.get('password')

        if not ACTIVATION_WORD or word != ACTIVATION_WORD:
            return jsonify({'error': 'Invalid activation word'}), 403

        return f(*args, **kwargs)

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
    
    # Start bridge monitoring
    if BRIDGE_MONITOR_AVAILABLE:
        try:
            logger.info("Starting bridge status monitoring...")
            success = start_bridge_monitoring()
            if success:
                logger.info("Bridge status monitoring started successfully")
            else:
                logger.warning("Bridge status monitoring failed to start")
        except Exception as e:
            logger.error(f"Failed to start bridge monitoring: {e}")
    
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
    debug_log_path = '/app/logs/debug.log'
    if not os.path.exists(debug_log_path):
        return
    
    try:
        file_size_mb = os.path.getsize(debug_log_path) / (1024 * 1024)
        if file_size_mb > LOG_ROTATION_SIZE_MB:
            # Archive current log
            timestamp = int(time.time())
            archived_log = f'debug_{timestamp}.log'
            shutil.move(debug_log_path, os.path.join('/app/logs', archived_log))
            logger.info(f"Rotated debug log to {archived_log}")
            
            # Remove old archived logs (keep only last 3)
            log_files = sorted([f for f in os.listdir('/app/logs') if f.startswith('debug_') and f.endswith('.log')])
            while len(log_files) > 3:
                oldest_log = log_files.pop(0)
                os.remove(os.path.join('/app/logs', oldest_log))
                logger.info(f"Removed old log file: {oldest_log}")
                
    except Exception as e:
        logger.error(f"Error during debug log rotation: {e}")

def execute_diagnostic_query(question):
    """Execute diagnostic query using autonomic dispatcher for smart routing"""
    
    # Check if this is a system data query that should return raw data
    system_data_keywords = ['how many containers', 'container count', 'list containers', 'docker ps']
    question_lower = question.lower()
    needs_raw_data = any(keyword in question_lower for keyword in system_data_keywords)
    
    # For system data queries, skip AI interpretation and go straight to raw diagnostics
    if needs_raw_data and REAL_DIAGNOSTICS:
        try:
            logger.info(f"Processing system data query directly: {question[:50]}...")
            raw_result = execute_diagnostic(question)
            
            # Add a note about raw data
            timestamp = datetime.now().isoformat()
            return f"""[{timestamp}] SYSTEM DATA QUERY (RAW OUTPUT)
Query: {question}

{raw_result}

Note: This is raw system data without AI interpretation to ensure accuracy."""
        except Exception as e:
            logger.error(f"Raw diagnostic failed: {e}")
    
    # Use autonomic dispatcher for intelligent task routing (non-system data queries)
    if AUTONOMIC_DISPATCHER_AVAILABLE:
        try:
            logger.info(f"Processing query via autonomic dispatcher: {question[:50]}...")
            return dispatch_task(question)
        except Exception as e:
            logger.error(f"Autonomic dispatcher failed: {e}")
            # Fall back to local smart agent
    
    # Fallback: Use smart agent directly for local processing
    if SMART_AGENT_AVAILABLE:
        try:
            logger.info("Falling back to local smart agent")
            return process_smart_query(question)
        except Exception as e:
            logger.error(f"Smart diagnostic agent failed: {e}")
            # Fall back to traditional methods
    
    # Use diagnostic engine if available
    if REAL_DIAGNOSTICS:
        try:
            logger.info("Falling back to traditional diagnostic engine")
            return execute_diagnostic(question)
        except Exception as e:
            logger.error(f"Diagnostic engine failed: {e}")
    
    # Final fallback - structured response
    timestamp = datetime.now().isoformat()
    response = f"""[{timestamp}] DIAGNOSTIC ERROR
Query: {question}

Unable to process diagnostic request. Available diagnostic engines are not functioning.
Please check system logs and ensure diagnostic capabilities are properly installed.

Status: Error - diagnostic engines unavailable."""
    
    # Log the error
    try:
        import memory
        memory.log_event(f"Diagnostic error for query: {question}", response)
    except:
        pass
        
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
    
    # Get dispatch stats if available
    dispatch_stats = get_dispatch_stats() if AUTONOMIC_DISPATCHER_AVAILABLE else None
    
    # Test remote connectivity
    remote_connectivity = None
    if AUTONOMIC_DISPATCHER_AVAILABLE:
        try:
            success, message = test_connectivity()
            remote_connectivity = {'success': success, 'message': message}
        except Exception as e:
            remote_connectivity = {'success': False, 'message': f'Connectivity test failed: {e}'}
    
    return jsonify({
        'status': 'OPERATIONAL',
        'ssh_bridge': ssh_bridge_enabled,
        'faiss_entries': faiss_entries,
        'timestamp': datetime.now().isoformat(),
        'memory_dir': MEMORY_DIR,
        'uptime': time.time() - start_time if 'start_time' in globals() else 0,
        'autonomic_dispatcher': {
            'available': AUTONOMIC_DISPATCHER_AVAILABLE,
            'stats': dispatch_stats,
            'remote_connectivity': remote_connectivity
        },
        'agents': {
            'smart_agent': SMART_AGENT_AVAILABLE,
            'real_diagnostics': REAL_DIAGNOSTICS,
            'autonomic_dispatcher': AUTONOMIC_DISPATCHER_AVAILABLE
        }
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
    response = execute_diagnostic_query(question)
    
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
@requires_activation_word
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

@app.route('/system_info', methods=['GET'])
@error_handler
@requires_activation_word
def system_info():
    """Return latest ISA script outputs"""
    files = {
        'system_facts': os.path.join(MEMORY_DIR, 'system_facts.json'),
        'connectivity': os.path.join(MEMORY_DIR, 'connectivity.json'),
        'process_status': os.path.join(MEMORY_DIR, 'process_status.json'),
    }
    info = {}
    for key, path in files.items():
        if os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    info[key] = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
                info[key] = 'unavailable'
        else:
            info[key] = 'unavailable'
    return jsonify(info)

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

@app.route('/dispatch/stats', methods=['GET'])
@error_handler
def dispatch_stats():
    """Get autonomic dispatcher statistics"""
    stats = get_dispatch_stats()
    return jsonify(stats)

@app.route('/dispatch/connectivity', methods=['GET'])
@error_handler
def dispatch_connectivity():
    """Test connectivity to the remote dev machine"""
    success, message = test_connectivity()
    return jsonify({
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat()
    })

@app.route('/dispatch/force', methods=['POST'])
@error_handler
def dispatch_force():
    """Force a task to execute locally or remotely"""
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400
    
    question = data['question'].strip()
    if not question:
        return jsonify({'error': 'Empty question'}), 400
    
    force_local = data.get('force_local', False)
    force_remote = data.get('force_remote', False)
    
    if force_local and force_remote:
        return jsonify({'error': 'Cannot force both local and remote execution'}), 400
    
    try:
        if AUTONOMIC_DISPATCHER_AVAILABLE:
            response = dispatch_task(question, force_local=force_local, force_remote=force_remote)
        else:
            # Fallback to regular processing
            response = execute_diagnostic_query(question)
        
        return jsonify({
            'response': response,
            'execution_type': 'local' if force_local else 'remote' if force_remote else 'auto'
        })
        
    except Exception as e:
        logger.error(f"Forced dispatch failed: {e}")
        return jsonify({'error': f'Dispatch failed: {str(e)}'}), 500


@app.route('/semantic/status', methods=['GET'])
@error_handler
def semantic_status():
    """Get semantic scoring status and recent tasks"""
    return jsonify(semantic_scorer.status())


@app.route('/semantic/enable', methods=['POST'])
@error_handler
def semantic_enable():
    """Enable or disable semantic task scoring"""
    data = request.get_json() or {}
    semantic_scorer.set_enabled(bool(data.get('enabled')))
    return jsonify(semantic_scorer.status())


@app.route('/semantic/threshold', methods=['POST'])
@error_handler
def semantic_threshold():
    """Update semantic scoring delegation threshold"""
    data = request.get_json() or {}
    try:
        semantic_scorer.set_threshold(float(data.get('threshold')))
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid threshold'}), 400
    return jsonify(semantic_scorer.status())


@app.route('/bridge_status', methods=['GET'])
@error_handler
def bridge_status():
    """Return current SSH bridge status"""
    return jsonify(get_bridge_status())


@app.route('/bridge/detailed_status', methods=['GET'])
@error_handler
def bridge_detailed_status():
    """Return detailed bridge status from monitor"""
    if BRIDGE_MONITOR_AVAILABLE:
        return jsonify(get_detailed_bridge_status())
    else:
        return jsonify({'error': 'Bridge monitor not available'}), 503


@app.route('/bridge/force_check', methods=['POST'])
@error_handler
def bridge_force_check():
    """Force immediate bridge status check"""
    if BRIDGE_MONITOR_AVAILABLE:
        success = force_bridge_check()
        return jsonify({
            'success': success,
            'message': 'Bridge check completed' if success else 'Bridge check failed',
            'timestamp': datetime.now().isoformat()
        })
    else:
        return jsonify({'error': 'Bridge monitor not available'}), 503


@app.route('/bridge/wake_on_lan', methods=['POST'])
@error_handler
def bridge_wake_on_lan():
    """Enable or disable Wake-on-LAN attempts"""
    data = request.get_json() or {}
    state = set_wake_on_lan(bool(data.get('enabled')))
    return jsonify({'wake_on_lan_enabled': state})

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
        os.path.join(BASE_DIR, "tasks", "collect_self_facts.py"),
        os.path.join(BASE_DIR, "tasks", "check_connectivity.py"),
        os.path.join(BASE_DIR, "tasks", "scan_processes.py"),
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
    
    # Stop bridge monitoring
    if BRIDGE_MONITOR_AVAILABLE:
        try:
            logger.info("Stopping bridge status monitoring...")
            stop_bridge_monitoring()
        except Exception as e:
            logger.error(f"Error stopping bridge monitoring: {e}")
    
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
