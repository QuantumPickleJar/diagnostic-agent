from flask import Flask, request, jsonify
import subprocess
from threading import Timer
import faiss_utils

app = Flask(__name__)

@app.route('/ask', methods=['POST'])
def ask():
    question = request.json.get('question')
    output = subprocess.run(['python3', 'agent_cli.py', question], capture_output=True, text=True)
    return jsonify({'response': output.stdout})

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

if __name__ == '__main__':
    # reindex every 5 minutes
    _periodic_reindex(300)
    app.run(host='0.0.0.0', port=5000)
