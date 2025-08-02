#!/usr/bin/env python3
"""
Smart Agent Frontend - Simple Web Interface
============================================

Provides a clean, simple web interface for the Enhanced Smart Diagnostic Agent.
This is a lightweight frontend focused on user interaction, distinct from the 
full-featured web_agent.py which handles complex backend orchestration.

Features:
- Simple chat-like web interface 
- Direct integration with enhanced_smart_agent.py
- Basic HTTP API endpoints
- Minimal dependencies for lightweight deployment

This complements web_agent.py which provides:
- Memory/FAISS indexing
- Background tasks and monitoring  
- Complex diagnostic orchestration
- SSH bridge and advanced features
"""
import os
import json
import logging
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string

# Import our unified smart agent
try:
    from unified_smart_agent import UnifiedSmartAgent
    SMART_AGENT_AVAILABLE = True
except ImportError:
    SMART_AGENT_AVAILABLE = False

logger = logging.getLogger(__name__)

app = Flask(__name__)

# Initialize agent
agent = UnifiedSmartAgent() if SMART_AGENT_AVAILABLE else None

# Simple HTML template for web interface
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Pi Diagnostic Agent</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }
        .chat-box { border: 1px solid #ddd; height: 400px; overflow-y: auto; padding: 10px; margin: 10px 0; background: #fafafa; }
        .message { margin: 10px 0; padding: 8px; border-radius: 5px; }
        .user { background: #e3f2fd; text-align: right; }
        .agent { background: #f1f8e9; }
        .input-box { display: flex; gap: 10px; }
        input[type="text"] { flex: 1; padding: 10px; border: 1px solid #ddd; border-radius: 5px; }
        button { padding: 10px 20px; background: #2196f3; color: white; border: none; border-radius: 5px; cursor: pointer; }
        button:hover { background: #1976d2; }
        .status { margin: 10px 0; padding: 10px; background: #fff3e0; border-radius: 5px; font-size: 14px; }
        .model-status { color: #ff9800; }
        .model-available { color: #4caf50; }
    </style>
</head>
<body>
    <div class="container">
        <h1> Pi Diagnostic Agent</h1>
        <div class="status">
            <strong>Agent Status:</strong> 
            <span id="agent-status">{{ agent_status }}</span>
            <br>
            <strong>Model:</strong> 
            <span id="model-status" class="{{ model_class }}">{{ model_status }}</span>
        </div>
        
        <div class="chat-box" id="chat-box">
            <div class="message agent">
                <strong>Agent:</strong> Hi! I'm your Pi diagnostic assistant. I can help with system monitoring, network diagnostics, and container management. What would you like to check?
            </div>
        </div>
        
        <div class="input-box">
            <input type="text" id="query-input" placeholder="Ask me about your system..." onkeypress="handleKeyPress(event)">
            <button onclick="sendQuery()">Send</button>
        </div>
        
        <div style="margin-top: 20px; font-size: 12px; color: #666;">
            <strong>Example queries:</strong> "Check network status", "What containers are running?", "System health check", "Who are you?"
        </div>
    </div>

    <script>
        function handleKeyPress(event) {
            if (event.key === 'Enter') {
                sendQuery();
            }
        }

        function sendQuery() {
            const input = document.getElementById('query-input');
            const query = input.value.trim();
            if (!query) return;

            const chatBox = document.getElementById('chat-box');
            
            // Add user message
            const userMsg = document.createElement('div');
            userMsg.className = 'message user';
            userMsg.innerHTML = `<strong>You:</strong> ${query}`;
            chatBox.appendChild(userMsg);
            
            // Clear input
            input.value = '';
            
            // Show thinking message
            const thinkingMsg = document.createElement('div');
            thinkingMsg.className = 'message agent';
            thinkingMsg.innerHTML = '<strong>Agent:</strong> <em>Thinking...</em>';
            thinkingMsg.id = 'thinking-msg';
            chatBox.appendChild(thinkingMsg);
            
            // Scroll to bottom
            chatBox.scrollTop = chatBox.scrollHeight;
            
            // Send request
            fetch('/query', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: query })
            })
            .then(response => response.json())
            .then(data => {
                // Remove thinking message
                const thinking = document.getElementById('thinking-msg');
                if (thinking) thinking.remove();
                
                // Add agent response
                const agentMsg = document.createElement('div');
                agentMsg.className = 'message agent';
                agentMsg.innerHTML = `<strong>Agent:</strong> ${data.response.replace(/\\n/g, '<br>')}`;
                chatBox.appendChild(agentMsg);
                
                // Scroll to bottom
                chatBox.scrollTop = chatBox.scrollHeight;
            })
            .catch(error => {
                // Remove thinking message
                const thinking = document.getElementById('thinking-msg');
                if (thinking) thinking.remove();
                
                // Add error message
                const errorMsg = document.createElement('div');
                errorMsg.className = 'message agent';
                errorMsg.innerHTML = '<strong>Agent:</strong> <em>Sorry, I encountered an error processing your request.</em>';
                chatBox.appendChild(errorMsg);
                
                console.error('Error:', error);
            });
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Main web interface"""
    if agent and agent.model_available:
        model_status = "TinyLlama (Local)"
        model_class = "model-available"
    else:
        model_status = "Fallback Mode"
        model_class = "model-status"
    
    agent_status = "Ready" if SMART_AGENT_AVAILABLE else "Limited (Import Error)"
    
    return render_template_string(HTML_TEMPLATE, 
                                agent_status=agent_status,
                                model_status=model_status,
                                model_class=model_class)

@app.route('/query', methods=['POST'])
def handle_query():
    """Handle agent queries via API"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Missing query parameter'}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({'error': 'Empty query'}), 400
        
        if not agent:
            return jsonify({
                'response': 'Agent not available due to import errors.',
                'timestamp': datetime.now().isoformat()
            })
        
        # Process query with agent
        response = agent.process_query(query)
        
        return jsonify({
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'model_used': 'TinyLlama' if agent.model_available else 'Fallback'
        })
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/status')
def get_status():
    """Get agent status information"""
    if not agent:
        return jsonify({
            'agent_available': False,
            'model_available': False,
            'error': 'Agent import failed'
        })
    
    return jsonify({
        'agent_available': True,
        'model_available': agent.model_available,
        'model_path': agent.local_model_path,
        'conversation_length': len(agent.conversation_history)
    })

@app.route('/health')
def health_check():
    """Simple health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'agent_loaded': agent is not None
    })

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Get configuration from environment
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', 8080))
    debug = os.getenv('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Starting Enhanced Smart Agent Web Interface on {host}:{port}")
    logger.info(f"Agent available: {SMART_AGENT_AVAILABLE}")
    if agent:
        logger.info(f"Model available: {agent.model_available}")
    
    app.run(host=host, port=port, debug=debug)
