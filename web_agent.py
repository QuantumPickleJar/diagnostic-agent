from flask import Flask, request, jsonify
from threading import Timer
import faiss_utils
import subprocess
import os


MEMORY_DIR = os.path.join(BASE_DIR, "agent_memory")
CONFIG_FILE = os.path.join(MEMORY_DIR, "static_config.json")

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question")
    output = subprocess.run(["python3", "agent_cli.py", question], capture_output=True, text=True)
    return jsonify({"response": output.stdout})

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}


def save_config(cfg):
    os.makedirs(MEMORY_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)


def valid_key(key):
    pattern = re.compile(r"^[A-Za-z0-9_\.]+$")
    return bool(pattern.match(key))


@app.route("/recall", methods=["GET"])
def recall():
    date_filter = request.args.get("date")
    keyword = request.args.get("keyword", "")
    if date_filter and not re.match(r"^\d{4}-\d{2}-\d{2}$", date_filter):
        return jsonify({"status": "error", "error": "invalid date"}), 400
    if len(keyword) > 100:
        return jsonify({"status": "error", "error": "keyword too long"}), 400

    entries = []
    if os.path.exists(RECALL_FILE):
        with open(RECALL_FILE) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if date_filter and not entry.get("timestamp", "").startswith(date_filter):
                    continue
                if keyword and keyword.lower() not in json.dumps(entry).lower():
                    continue
                entries.append(entry)
    return jsonify({"status": "ok", "entries": entries})

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '')
    top_k = int(request.json.get('top_k', 5))
    results = faiss_utils.search(query, top_k=top_k)
    return jsonify({'results': results})

@app.route('/reindex', methods=['POST'])
def reindex_endpoint():
    faiss_utils.reindex()
    return jsonify({'status': 'reindexed'})

def _periodic_reindex(interval):
    faiss_utils.reindex()
    Timer(interval, _periodic_reindex, [interval]).start()

@app.route("/config", methods=["GET", "POST"])
def config():
    if request.method == "GET":
        key = request.args.get("key")
        cfg = load_config()
        if not key:
            return jsonify({"status": "ok", "config": cfg})
        if not valid_key(key):
            return jsonify({"status": "error", "error": "invalid key"}), 400
        parts = key.split(".")
        val = cfg
        for p in parts:
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return jsonify({"status": "error", "error": "key not found"}), 404
        return jsonify({"status": "ok", "value": val})

    # POST => update
    data = request.get_json(silent=True) or {}
    key = data.get("key")
    new_value = data.get("value")
    if not key or not valid_key(key):
        return jsonify({"status": "error", "error": "invalid key"}), 400
    cfg = load_config()
    parts = key.split(".")
    current = cfg
    for p in parts[:-1]:
        if p not in current or not isinstance(current[p], dict):
            current[p] = {}
        current = current[p]
    current[parts[-1]] = new_value
    try:
        save_config(cfg)
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500
    return jsonify({"status": "ok", "value": new_value})

if __name__ == '__main__':
    # reindex every 5 minutes
    _periodic_reindex(300)
    app.run(host='0.0.0.0', port=5000)