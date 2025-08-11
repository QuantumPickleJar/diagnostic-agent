#!/usr/bin/env python3
"""
Statistics Logger for Performance Analytics
Tracks response times, routing decisions, and performance metrics
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict, deque

class StatsLogger:
    """Thread-safe statistics logger for tracking query performance"""
    
    def __init__(self, memory_dir=None):
        self.memory_dir = Path(memory_dir or Path(__file__).parent / "agent_memory")
        self.memory_dir.mkdir(exist_ok=True)
        self.stats_file = self.memory_dir / "performance_stats.jsonl"
        self.lock = threading.Lock()
        
        # In-memory stats for quick access (last 1000 entries)
        self.recent_queries = deque(maxlen=1000)
        self.session_start = time.time()
        
        # Enhanced performance thresholds for optimization analysis
        self.pi_timeout = 30  # Pi should respond quickly
        self.dev_timeout = 120  # Dev machine timeout
        self.pi_target = 5  # Target response time for Pi (seconds)
        self.dev_target = 15  # Target response time for dev machine (seconds)
        
        # Performance tracking for optimization
        self.slow_queries = deque(maxlen=100)  # Track slow queries for analysis
        self.timeout_queries = deque(maxlen=50)  # Track timeouts
        
        # Load historical data
        self._load_historical_data()
        
    def _load_historical_data(self):
        """Load any existing historical data"""
        # For now, just initialize - could load from persistent storage later
        pass
        
    def log_query_start(self, query_id, query_text, expected_destination):
        """Log the start of a query processing"""
        entry = {
            "query_id": query_id,
            "query_text": query_text,
            "expected_destination": expected_destination,
            "start_time": time.time(),
            "timestamp": datetime.now().isoformat()
        }
        
        with self.lock:
            self.recent_queries.append(entry)
        
        return entry
    
    def log_query_complete(self, query_id, actual_destination, response_length, success=True, error_msg=None):
        """Log the completion of a query processing"""
        end_time = time.time()
        
        with self.lock:
            # Find the matching start entry
            start_entry = None
            for entry in reversed(self.recent_queries):
                if entry.get("query_id") == query_id and "duration" not in entry:
                    start_entry = entry
                    break
            
            if start_entry:
                duration = end_time - start_entry["start_time"]
                
                # Update the entry with completion data
                start_entry.update({
                    "actual_destination": actual_destination,
                    "duration": duration,
                    "response_length": response_length,
                    "success": success,
                    "error_msg": error_msg,
                    "completed_at": datetime.now().isoformat(),
                    "performance_category": self._categorize_performance(duration, actual_destination)
                })
                
                # Write to persistent log
                self._write_to_file(start_entry)
                
                return start_entry
        
        return None
    
    def _categorize_performance(self, duration, destination):
        """Categorize performance based on destination and duration"""
        if destination == "local":
            if duration < 5:
                return "excellent"
            elif duration < 15:
                return "good"
            elif duration < self.pi_timeout:
                return "acceptable"
            else:
                return "slow"
        else:  # dev machine
            if duration < 10:
                return "excellent"
            elif duration < 30:
                return "good"  
            elif duration < 60:
                return "acceptable"
            elif duration < self.dev_timeout:
                return "slow"
            else:
                return "timeout_risk"
    
    def _write_to_file(self, entry):
        """Write entry to persistent log file"""
        try:
            with open(self.stats_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"Failed to write stats: {e}")
    
    def get_recent_stats(self, hours=24):
        """Get statistics for recent queries"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            # Filter recent queries
            recent = [entry for entry in self.recent_queries 
                     if entry.get("start_time", 0) > cutoff_time and "duration" in entry]
        
        if not recent:
            return self._empty_stats()
        
        # Calculate statistics
        total_queries = len(recent)
        local_queries = [q for q in recent if q.get("actual_destination") == "local"]
        dev_queries = [q for q in recent if q.get("actual_destination") == "dev"]
        
        stats = {
            "summary": {
                "total_queries": total_queries,
                "local_queries": len(local_queries),
                "dev_queries": len(dev_queries),
                "success_rate": sum(1 for q in recent if q.get("success", False)) / total_queries * 100,
                "session_uptime": time.time() - self.session_start
            },
            "performance": {
                "local": self._calculate_performance_stats(local_queries),
                "dev": self._calculate_performance_stats(dev_queries)
            },
            "routing_accuracy": self._calculate_routing_accuracy(recent),
            "performance_distribution": self._get_performance_distribution(recent),
            "recent_queries": recent[-10:]  # Last 10 queries for debugging
        }
        
        return stats
    
    def _calculate_performance_stats(self, queries):
        """Calculate performance statistics for a set of queries"""
        if not queries:
            return {"count": 0, "avg_duration": 0, "min_duration": 0, "max_duration": 0, "median_duration": 0}
        
        durations = [q["duration"] for q in queries if "duration" in q]
        durations.sort()
        
        return {
            "count": len(queries),
            "avg_duration": sum(durations) / len(durations),
            "min_duration": min(durations),
            "max_duration": max(durations),
            "median_duration": durations[len(durations)//2] if durations else 0,
            "success_rate": sum(1 for q in queries if q.get("success", False)) / len(queries) * 100
        }
    
    def _calculate_routing_accuracy(self, queries):
        """Calculate how often queries were routed to their expected destination"""
        if not queries:
            return {"total": 0, "correct": 0, "accuracy": 0}
        
        total = len(queries)
        correct = sum(1 for q in queries 
                     if q.get("expected_destination") == q.get("actual_destination"))
        
        return {
            "total": total,
            "correct": correct,
            "accuracy": correct / total * 100 if total > 0 else 0
        }
    
    def _get_performance_distribution(self, queries):
        """Get distribution of performance categories"""
        distribution = defaultdict(int)
        for query in queries:
            category = query.get("performance_category", "unknown")
            distribution[category] += 1
        
        return dict(distribution)
    
    def _empty_stats(self):
        """Return empty stats structure"""
        return {
            "summary": {"total_queries": 0, "local_queries": 0, "dev_queries": 0, "success_rate": 0, "session_uptime": 0},
            "performance": {"local": {"count": 0}, "dev": {"count": 0}},
            "routing_accuracy": {"total": 0, "correct": 0, "accuracy": 0},
            "performance_distribution": {},
            "recent_queries": []
        }
    
    def get_ascii_chart(self, data, width=40, height=10):
        """Generate ASCII bar chart for terminal display"""
        if not data:
            return ["No data available"]
        
        max_val = max(data.values()) if data.values() else 1
        lines = []
        
        # Chart title
        lines.append("Performance Distribution")
        lines.append("=" * width)
        
        # Bars
        for label, value in data.items():
            bar_length = int((value / max_val) * (width - 15)) if max_val > 0 else 0
            bar = "█" * bar_length + "░" * (width - 15 - bar_length)
            lines.append(f"{label:10} |{bar}| {value:3}")
        
        return lines
    
    def analyze_dev_machine_performance(self, hours=24):
        """Analyze dev machine performance bottlenecks"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            dev_queries = [entry for entry in self.recent_queries 
                          if (entry.get("start_time", 0) > cutoff_time and 
                              entry.get("actual_destination") == "dev" and 
                              "duration" in entry)]
        
        if not dev_queries:
            return {"error": "No dev machine queries in the specified time range"}
        
        # Analyze response times
        durations = [q["duration"] for q in dev_queries]
        slow_queries = [q for q in dev_queries if q["duration"] > self.dev_target]
        timeout_risk = [q for q in dev_queries if q["duration"] > 60]
        
        analysis = {
            "total_dev_queries": len(dev_queries),
            "avg_response_time": sum(durations) / len(durations),
            "median_response_time": sorted(durations)[len(durations)//2],
            "max_response_time": max(durations),
            "min_response_time": min(durations),
            "slow_queries_count": len(slow_queries),
            "timeout_risk_count": len(timeout_risk),
            "performance_breakdown": {
                "excellent": len([q for q in dev_queries if q.get("performance_category") == "excellent"]),
                "good": len([q for q in dev_queries if q.get("performance_category") == "good"]),
                "acceptable": len([q for q in dev_queries if q.get("performance_category") == "acceptable"]),
                "slow": len([q for q in dev_queries if q.get("performance_category") == "slow"]),
                "timeout_risk": len([q for q in dev_queries if q.get("performance_category") == "timeout_risk"])
            },
            "optimization_recommendations": self._generate_optimization_recommendations(dev_queries),
            "slowest_queries": sorted(dev_queries, key=lambda x: x["duration"], reverse=True)[:5]
        }
        
        return analysis
    
    def _generate_optimization_recommendations(self, dev_queries):
        """Generate optimization recommendations based on performance data"""
        recommendations = []
        
        if not dev_queries:
            return ["No data available for recommendations"]
        
        avg_duration = sum(q["duration"] for q in dev_queries) / len(dev_queries)
        slow_queries = [q for q in dev_queries if q["duration"] > self.dev_target]
        
        if avg_duration > self.dev_target:
            recommendations.append(f"⚠️  Average dev machine response time ({avg_duration:.1f}s) exceeds target ({self.dev_target}s)")
        
        if len(slow_queries) > len(dev_queries) * 0.3:  # More than 30% slow
            recommendations.append("🔧 Consider optimizing OpenHermes model settings:")
            recommendations.append("   • Reduce n_ctx if using large context windows")
            recommendations.append("   • Decrease max_tokens for faster responses")
            recommendations.append("   • Optimize n_threads for your CPU")
        
        long_queries = [q for q in dev_queries if len(q.get("query", "")) > 200]
        if long_queries:
            recommendations.append("📝 Long queries detected - consider query preprocessing")
        
        if any(q["duration"] > 60 for q in dev_queries):
            recommendations.append("⏰ Some queries exceed 60s - implement query chunking")
        
        # SSH/network analysis
        ssh_slow = [q for q in dev_queries if q["duration"] > 45]
        if len(ssh_slow) > 0:
            recommendations.append("🌐 Network/SSH latency may be contributing to slow responses")
            recommendations.append("   • Check SSH connection stability")
            recommendations.append("   • Consider connection pooling")
        
        if not recommendations:
            recommendations.append("✅ Dev machine performance is within acceptable ranges")
        
        return recommendations
    
    def get_performance_insights(self, hours=24):
        """Get comprehensive performance insights for dashboard"""
        cutoff_time = time.time() - (hours * 3600)
        
        with self.lock:
            recent = [entry for entry in self.recent_queries 
                     if entry.get("start_time", 0) > cutoff_time and "duration" in entry]
        
        if not recent:
            return {"error": "No data available"}
        
        local_queries = [q for q in recent if q.get("actual_destination") == "local"]
        dev_queries = [q for q in recent if q.get("actual_destination") == "dev"]
        
        insights = {
            "efficiency_comparison": {
                "local_avg": sum(q["duration"] for q in local_queries) / len(local_queries) if local_queries else 0,
                "dev_avg": sum(q["duration"] for q in dev_queries) / len(dev_queries) if dev_queries else 0,
                "efficiency_ratio": None
            },
            "routing_effectiveness": {
                "total_time_saved": 0,  # Estimate time saved by routing to dev machine
                "delegation_overhead": 0  # Time cost of delegation vs local processing
            },
            "performance_trends": self._calculate_performance_trends(recent),
            "bottleneck_analysis": {
                "primary_bottleneck": self._identify_primary_bottleneck(recent),
                "suggestions": []
            }
        }
        
        # Calculate efficiency ratio
        if dev_queries and local_queries:
            insights["efficiency_comparison"]["efficiency_ratio"] = (
                insights["efficiency_comparison"]["local_avg"] / 
                insights["efficiency_comparison"]["dev_avg"]
            )
        
        return insights
    
    def _calculate_performance_trends(self, queries):
        """Calculate performance trends over time"""
        if len(queries) < 10:
            return {"trend": "insufficient_data"}
        
        # Sort by time
        sorted_queries = sorted(queries, key=lambda x: x["start_time"])
        
        # Split into two halves for trend analysis
        mid_point = len(sorted_queries) // 2
        first_half = sorted_queries[:mid_point]
        second_half = sorted_queries[mid_point:]
        
        first_avg = sum(q["duration"] for q in first_half) / len(first_half)
        second_avg = sum(q["duration"] for q in second_half) / len(second_half)
        
        trend_direction = "improving" if second_avg < first_avg else "degrading"
        trend_magnitude = abs(second_avg - first_avg) / first_avg * 100
        
        return {
            "trend": trend_direction,
            "magnitude": trend_magnitude,
            "first_half_avg": first_avg,
            "second_half_avg": second_avg
        }
    
    def _identify_primary_bottleneck(self, queries):
        """Identify the primary performance bottleneck"""
        local_queries = [q for q in queries if q.get("actual_destination") == "local"]
        dev_queries = [q for q in queries if q.get("actual_destination") == "dev"]
        
        local_avg = sum(q["duration"] for q in local_queries) / len(local_queries) if local_queries else 0
        dev_avg = sum(q["duration"] for q in dev_queries) / len(dev_queries) if dev_queries else 0
        
        slow_local = len([q for q in local_queries if q["duration"] > self.pi_target])
        slow_dev = len([q for q in dev_queries if q["duration"] > self.dev_target])
        
        if dev_avg > self.dev_target * 2:
            return "dev_machine_processing"
        elif local_avg > self.pi_target * 2:
            return "pi_processing"
        elif slow_dev > slow_local:
            return "dev_machine_optimization_needed"
        elif slow_local > slow_dev:
            return "pi_optimization_needed"
        else:
            return "acceptable_performance"

# Global instance
stats_logger = StatsLogger()
