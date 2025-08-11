#!/usr/bin/env python3
"""
Statistical Dashboard for Diagnostic Agent Routing
==================================================

Terminal-themed ASCII dashboard for monitoring routing performance and timing analysis.
Tracks Pi vs Dev machine response times to identify optimization opportunities.
"""

import os
import json
import time
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, render_template_string
from threading import Lock
import statistics
from collections import deque, defaultdict

app = Flask(__name__)

# Thread-safe storage for statistics
stats_lock = Lock()
query_stats = deque(maxlen=1000)  # Keep last 1000 queries
routing_stats = defaultdict(list)
performance_stats = {
    'pi_times': deque(maxlen=100),
    'dev_times': deque(maxlen=100),
    'total_queries': 0,
    'routed_to_dev': 0,
    'routed_to_pi': 0,
    'timeouts': 0,
    'errors': 0
}

# ASCII Art and Terminal Styling
TERMINAL_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Diagnostic Agent Stats - Terminal</title>
    <meta charset="UTF-8">
    <style>
        body {
            background: #000;
            color: #00ff00;
            font-family: 'Courier New', monospace;
            margin: 0;
            padding: 20px;
            overflow-x: auto;
        }
        .terminal {
            background: #000;
            border: 2px solid #00ff00;
            border-radius: 5px;
            padding: 15px;
            margin: 10px 0;
            white-space: pre;
            font-size: 14px;
            line-height: 1.2;
        }
        .header {
            color: #00ffff;
            text-align: center;
            border-bottom: 1px solid #00ff00;
            padding-bottom: 10px;
            margin-bottom: 15px;
        }
        .section {
            margin: 20px 0;
            border: 1px solid #444;
            padding: 10px;
        }
        .metric-good { color: #00ff00; }
        .metric-warn { color: #ffff00; }
        .metric-bad { color: #ff0000; }
        .graph-char { color: #00ffff; }
        .timestamp { color: #888; font-size: 12px; }
        .ascii-art { color: #00ff00; text-align: center; }
        .blink {
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0; }
            100% { opacity: 1; }
        }
        .progress-bar {
            display: inline-block;
            width: 40px;
        }
        .route-indicator {
            display: inline-block;
            width: 3px;
            height: 15px;
            margin: 0 1px;
            vertical-align: middle;
        }
        .route-pi { background: #00ff00; }
        .route-dev { background: #ffff00; }
        .route-timeout { background: #ff0000; }
        .refresh-button {
            background: #000;
            color: #00ff00;
            border: 1px solid #00ff00;
            padding: 5px 10px;
            cursor: pointer;
            font-family: 'Courier New', monospace;
        }
        .refresh-button:hover {
            background: #00ff00;
            color: #000;
        }
    </style>
</head>
<body>
    <div class="terminal">
        <div class="header">
            <div class="ascii-art">
╔══════════════════════════════════════════════════════════════════════════════╗
║                    DIAGNOSTIC AGENT ROUTING STATISTICS                      ║
║                          Pi ←→ Dev Machine Analytics                         ║
╚══════════════════════════════════════════════════════════════════════════════╝
            </div>
            <div class="timestamp">Last Updated: {{ timestamp }} | <button class="refresh-button" onclick="window.location.reload()">REFRESH</button></div>
        </div>

        <div class="section">
            <div style="color: #00ffff;">▓▓▓ PERFORMANCE OVERVIEW ▓▓▓</div>
            
Total Queries: {{ stats.total_queries }}
Routed to Pi:  {{ stats.routed_to_pi }} ({{ pi_percentage }}%)  {{ pi_bar }}
Routed to Dev: {{ stats.routed_to_dev }} ({{ dev_percentage }}%) {{ dev_bar }}
Timeouts:      {{ stats.timeouts }} ({{ timeout_percentage }}%) {{ timeout_bar }}
Errors:        {{ stats.errors }} ({{ error_percentage }}%)   {{ error_bar }}

{{ routing_visual }}
        </div>

        <div class="section">
            <div style="color: #00ffff;">▓▓▓ RESPONSE TIME ANALYSIS ▓▓▓</div>
            
Pi Response Times:
  Average: {{ pi_avg }}ms | Median: {{ pi_median }}ms | Max: {{ pi_max }}ms
  {{ pi_time_graph }}
  
Dev Machine Response Times:
  Average: {{ dev_avg }}ms | Median: {{ dev_median }}ms | Max: {{ dev_max }}ms
  {{ dev_time_graph }}
  
Performance Comparison:
  Dev machine is {{ performance_factor }}x {{ performance_direction }} than Pi
  {% if performance_factor > 1.5 %}
  <span class="metric-bad">⚠️  DEV MACHINE SLOWER THAN EXPECTED</span>
  Recommendation: Check OpenHermes model loading and n_ctx settings
  {% elif performance_factor < 0.8 %}
  <span class="metric-good">✅ Dev machine performing well</span>
  {% else %}
  <span class="metric-warn">△ Performance acceptable but room for improvement</span>
  {% endif %}
        </div>

        <div class="section">
            <div style="color: #00ffff;">▓▓▓ SEMANTIC SCORING DISTRIBUTION ▓▓▓</div>
            
{{ score_distribution }}
            
Routing Accuracy: {{ routing_accuracy }}%
{% if routing_accuracy < 80 %}
<span class="metric-bad">⚠️  Low routing accuracy - check semantic scorer</span>
{% else %}
<span class="metric-good">✅ Routing accuracy acceptable</span>
{% endif %}
        </div>

        <div class="section">
            <div style="color: #00ffff;">▓▓▓ RECENT QUERY LOG ▓▓▓</div>
            
{{ recent_queries }}
        </div>

        <div class="section">
            <div style="color: #00ffff;">▓▓▓ OPTIMIZATION RECOMMENDATIONS ▓▓▓</div>
            
{{ recommendations }}
        </div>

        <div class="section">
            <div style="color: #888; font-size: 12px;">
Auto-refresh: <span class="blink">●</span> | Data retention: Last 1000 queries
Pi timeout: 60s | Dev timeout: 120s | Update interval: 5s
            </div>
        </div>
    </div>

    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => window.location.reload(), 30000);
        
        // Add some subtle terminal effects
        document.addEventListener('DOMContentLoaded', () => {
            // Random cursor blink simulation
            const indicators = document.querySelectorAll('.blink');
            indicators.forEach(indicator => {
                setInterval(() => {
                    indicator.style.opacity = indicator.style.opacity === '0' ? '1' : '0';
                }, 500 + Math.random() * 500);
            });
        });
    </script>
</body>
</html>
"""

def log_query_stats(query, score, routed_to, start_time, end_time, error=None):
    """Log query statistics for dashboard analysis"""
    with stats_lock:
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        
        entry = {
            'timestamp': datetime.now().isoformat(),
            'query': query[:100],  # Truncate long queries
            'score': score,
            'routed_to': routed_to,
            'response_time': response_time,
            'error': error,
            'timeout': response_time > (120000 if routed_to == 'dev' else 60000)
        }
        
        query_stats.append(entry)
        
        # Update performance stats
        performance_stats['total_queries'] += 1
        
        if error:
            performance_stats['errors'] += 1
        elif entry['timeout']:
            performance_stats['timeouts'] += 1
        elif routed_to == 'dev':
            performance_stats['routed_to_dev'] += 1
            performance_stats['dev_times'].append(response_time)
        else:
            performance_stats['routed_to_pi'] += 1
            performance_stats['pi_times'].append(response_time)

def create_ascii_bar(value, max_value, width=20, char='█', empty_char='░'):
    """Create ASCII progress bar"""
    if max_value == 0:
        filled = 0
    else:
        filled = int((value / max_value) * width)
    return char * filled + empty_char * (width - filled)

def create_time_graph(times, width=50):
    """Create ASCII graph of response times"""
    if not times:
        return "No data available"
    
    max_time = max(times)
    min_time = min(times)
    
    if max_time == min_time:
        return "All responses: {}ms".format(int(max_time))
    
    graph = ""
    for i, time_val in enumerate(list(times)[-width:]):
        height = int(((time_val - min_time) / (max_time - min_time)) * 10)
        if height == 0:
            graph += "▁"
        elif height <= 2:
            graph += "▂"
        elif height <= 4:
            graph += "▄"
        elif height <= 6:
            graph += "▆"
        else:
            graph += "█"
    
    return f"{graph}\nRange: {int(min_time)}ms - {int(max_time)}ms"

def generate_recommendations():
    """Generate optimization recommendations based on performance data"""
    recommendations = []
    
    with stats_lock:
        pi_times = list(performance_stats['pi_times'])
        dev_times = list(performance_stats['dev_times'])
        
        # Check if dev machine is slower than expected
        if dev_times:
            avg_dev = statistics.mean(dev_times)
            if avg_dev > 30000:  # More than 30 seconds
                recommendations.append("🔧 Dev machine responses > 30s - Consider reducing n_ctx in OpenHermes")
            elif avg_dev > 15000:  # More than 15 seconds
                recommendations.append("⚡ Dev machine responses > 15s - Check model loading overhead")
        
        # Check Pi performance
        if pi_times:
            avg_pi = statistics.mean(pi_times)
            if avg_pi > 10000:  # More than 10 seconds
                recommendations.append("🔧 Pi responses slow - Check TinyLlama model size/settings")
        
        # Check routing accuracy
        total = performance_stats['total_queries']
        if total > 10:
            timeout_rate = performance_stats['timeouts'] / total
            if timeout_rate > 0.1:
                recommendations.append("⚠️  High timeout rate - Review timeout settings")
        
        # Check for delegation effectiveness
        if pi_times and dev_times:
            avg_pi = statistics.mean(pi_times)
            avg_dev = statistics.mean(dev_times)
            if avg_dev > avg_pi * 2:
                recommendations.append("📊 Dev delegation not improving performance - Review query complexity threshold")
    
    if not recommendations:
        recommendations.append("✅ System performing within acceptable parameters")
    
    return "\n".join(f"  {rec}" for rec in recommendations)

@app.route('/stats')
def stats_dashboard():
    """Main statistics dashboard"""
    with stats_lock:
        # Calculate summary statistics
        pi_times = list(performance_stats['pi_times'])
        dev_times = list(performance_stats['dev_times'])
        total = performance_stats['total_queries'] or 1
        
        # Calculate percentages
        pi_percentage = round((performance_stats['routed_to_pi'] / total) * 100, 1)
        dev_percentage = round((performance_stats['routed_to_dev'] / total) * 100, 1)
        timeout_percentage = round((performance_stats['timeouts'] / total) * 100, 1)
        error_percentage = round((performance_stats['errors'] / total) * 100, 1)
        
        # Create progress bars
        pi_bar = create_ascii_bar(performance_stats['routed_to_pi'], total)
        dev_bar = create_ascii_bar(performance_stats['routed_to_dev'], total)
        timeout_bar = create_ascii_bar(performance_stats['timeouts'], total)
        error_bar = create_ascii_bar(performance_stats['errors'], total)
        
        # Calculate response time stats
        pi_avg = round(statistics.mean(pi_times), 1) if pi_times else 0
        pi_median = round(statistics.median(pi_times), 1) if pi_times else 0
        pi_max = round(max(pi_times), 1) if pi_times else 0
        
        dev_avg = round(statistics.mean(dev_times), 1) if dev_times else 0
        dev_median = round(statistics.median(dev_times), 1) if dev_times else 0
        dev_max = round(max(dev_times), 1) if dev_times else 0
        
        # Performance comparison
        if pi_avg > 0 and dev_avg > 0:
            performance_factor = round(dev_avg / pi_avg, 1)
            performance_direction = "slower" if performance_factor > 1 else "faster"
        else:
            performance_factor = 1.0
            performance_direction = "equivalent"
        
        # Recent queries
        recent_queries = ""
        for entry in list(query_stats)[-10:]:
            timestamp = datetime.fromisoformat(entry['timestamp']).strftime('%H:%M:%S')
            route_symbol = "→Dev" if entry['routed_to'] == 'dev' else "→Pi "
            status = "TIMEOUT" if entry['timeout'] else "ERROR" if entry['error'] else "OK"
            recent_queries += f"{timestamp} | {route_symbol} | {entry['response_time']:6.0f}ms | {status:7} | {entry['query'][:50]}\n"
        
        # Routing visualization
        routing_visual = "Last 50 queries: "
        for entry in list(query_stats)[-50:]:
            if entry['error']:
                routing_visual += "🔴"
            elif entry['timeout']:
                routing_visual += "🟠"
            elif entry['routed_to'] == 'dev':
                routing_visual += "🟡"
            else:
                routing_visual += "🟢"
        
        # Score distribution
        scores = [entry['score'] for entry in query_stats]
        score_distribution = "Score distribution:\n"
        if scores:
            score_ranges = [(0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)]
            for low, high in score_ranges:
                count = sum(1 for s in scores if low <= s < high)
                bar = create_ascii_bar(count, len(scores), width=20)
                score_distribution += f"  {low:.1f}-{high:.1f}: {bar} ({count:3d})\n"
        
        # Calculate routing accuracy
        correct_routes = 0
        total_routes = 0
        for entry in query_stats:
            if not entry['error'] and not entry['timeout']:
                total_routes += 1
                # Simple heuristic: complex queries (score >= 0.7) should go to dev
                should_go_to_dev = entry['score'] >= 0.7
                actually_went_to_dev = entry['routed_to'] == 'dev'
                if should_go_to_dev == actually_went_to_dev:
                    correct_routes += 1
        
        routing_accuracy = round((correct_routes / total_routes * 100), 1) if total_routes > 0 else 100
        
        return render_template_string(TERMINAL_TEMPLATE,
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stats=performance_stats,
            pi_percentage=pi_percentage,
            dev_percentage=dev_percentage,
            timeout_percentage=timeout_percentage,
            error_percentage=error_percentage,
            pi_bar=pi_bar,
            dev_bar=dev_bar,
            timeout_bar=timeout_bar,
            error_bar=error_bar,
            routing_visual=routing_visual,
            pi_avg=pi_avg,
            pi_median=pi_median,
            pi_max=pi_max,
            dev_avg=dev_avg,
            dev_median=dev_median,
            dev_max=dev_max,
            pi_time_graph=create_time_graph(pi_times),
            dev_time_graph=create_time_graph(dev_times),
            performance_factor=performance_factor,
            performance_direction=performance_direction,
            score_distribution=score_distribution,
            routing_accuracy=routing_accuracy,
            recent_queries=recent_queries,
            recommendations=generate_recommendations()
        )

@app.route('/log_query', methods=['POST'])
def log_query():
    """API endpoint to log query statistics"""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    try:
        log_query_stats(
            query=data.get('query', ''),
            score=data.get('score', 0.0),
            routed_to=data.get('routed_to', 'unknown'),
            start_time=data.get('start_time', time.time()),
            end_time=data.get('end_time', time.time()),
            error=data.get('error')
        )
        return jsonify({'status': 'logged'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats')
def api_stats():
    """JSON API for statistics data"""
    with stats_lock:
        return jsonify({
            'performance': dict(performance_stats),
            'recent_queries': list(query_stats)[-20:],
            'pi_times': list(performance_stats['pi_times']),
            'dev_times': list(performance_stats['dev_times'])
        })

if __name__ == '__main__':
    # Generate some sample data for testing
    import random
    for i in range(50):
        log_query_stats(
            query=f"Sample query {i}",
            score=random.random(),
            routed_to='dev' if random.random() > 0.6 else 'pi',
            start_time=time.time() - random.randint(1, 30),
            end_time=time.time(),
            error=None if random.random() > 0.1 else "Sample error"
        )
    
    app.run(host='0.0.0.0', port=5001, debug=True)
