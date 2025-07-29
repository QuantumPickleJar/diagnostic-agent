from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    question = request.json.get("question")
    output = subprocess.run(["python3", "agent_cli.py", question], capture_output=True, text=True)
    return jsonify({"response": output.stdout})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)