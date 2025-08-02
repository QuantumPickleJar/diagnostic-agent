#!/usr/bin/env python3
"""
Unified Smart Diagnostic Agent
Hardware Requirements: Raspberry Pi 4 (4GB+ RAM recommended)
Package Requirements: llama-cpp-python>=0.2.27, sentence-transformers>=3.0.0, psutil>=5.9.0

Combines TinyLlama GGUF local inference with system diagnostics.
Uses sentence-transformers for embeddings and llama.cpp for natural language responses.
"""

import os
import sys
import logging
import subprocess
import json
import psutil
from datetime import datetime
from pathlib import Path

# Try to import required packages
try:
    from llama_cpp import Llama
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    print("Warning: llama-cpp-python not available, using fallback responses")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class UnifiedSmartAgent:
    """
    Unified smart diagnostic agent with natural language processing capabilities.
    
    Hardware Requirements:
    - Raspberry Pi 4 with 4GB+ RAM (2GB may work with reduced context)
    - ~1GB storage for models
    
    Package Requirements:
    - llama-cpp-python>=0.2.27 (for local TinyLlama inference)
    - sentence-transformers>=3.0.0 (for embeddings)
    - psutil>=5.9.0 (for system monitoring)
    """
    
    def __init__(self):
        """Initialize the unified smart diagnostic agent"""
        # Model paths - corrected for your actual setup
        self.model_path = "/home/diagnostic-agent/models/tinyllama.gguf"
        self.embeddings_model_path = "/home/diagnostic-agent/models/all-MiniLM-L6-v2"
        
        # Model instances
        self.llama_model = None
        self.sentence_model = None
        self.model_available = False
        
        # Conversation tracking
        self.conversation_history = []
        
        # System context for responses
        self.system_context = """You are a helpful diagnostic assistant running locally on a Raspberry Pi. 
You help users monitor system health, check Docker containers, and troubleshoot issues.
Be conversational, helpful, and concise. Give specific answers based on the diagnostic data provided."""
        
        # Initialize models
        self._initialize_models()
        
        logger.info("Unified Smart Agent initialized")
    
    def _initialize_models(self):
        """Initialize both language models"""
        # Initialize TinyLlama for natural language responses
        if LLAMA_CPP_AVAILABLE and os.path.exists(self.model_path):
            try:
                logger.info(f"Loading TinyLlama model from {self.model_path}")
                self.llama_model = Llama(
                    model_path=self.model_path,
                    n_ctx=1024,  # Context window
                    n_threads=2,  # Conservative for Pi 4
                    n_gpu_layers=0,  # CPU only
                    verbose=False
                )
                self.model_available = True
                logger.info("TinyLlama model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load TinyLlama model: {e}")
                self.model_available = False
        else:
            if not LLAMA_CPP_AVAILABLE:
                logger.warning("llama-cpp-python not available")
            elif not os.path.exists(self.model_path):
                logger.warning(f"TinyLlama model not found: {self.model_path}")
            self.model_available = False
        
        # Initialize sentence transformer for embeddings  
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                # Try local model first, fallback to download
                if os.path.exists(self.embeddings_model_path):
                    logger.info(f"Loading local sentence transformer from {self.embeddings_model_path}")
                    self.sentence_model = SentenceTransformer(self.embeddings_model_path)
                else:
                    logger.info("Loading sentence transformer (will download if needed)")
                    self.sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Sentence transformer loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load sentence transformer: {e}")
                self.sentence_model = None
        else:
            logger.warning("sentence-transformers not available")
            self.sentence_model = None
    
    def process_query(self, query):
        """Process a user query with diagnostics and natural language response"""
        timestamp = datetime.now().isoformat()
        
        # Log the interaction
        self.conversation_history.append({
            'timestamp': timestamp,
            'query': query,
            'type': 'user'
        })
        
        try:
            # Extract diagnostic intent
            intent = self._extract_diagnostic_intent(query)
            
            # Run diagnostics if needed
            diagnostic_result = None
            if intent != 'general':
                diagnostic_result = self.run_diagnostics(intent)
            
            # Generate natural language response
            response = self._generate_response(query, diagnostic_result)
            
            # Log the response
            self.conversation_history.append({
                'timestamp': timestamp,
                'response': response,
                'diagnostic_result': diagnostic_result,
                'type': 'assistant'
            })
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-20:]
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return f"I encountered an error while processing your request: {str(e)}"
    
    def _generate_response(self, query, diagnostic_result=None):
        """Generate natural language response using TinyLlama"""
        if not self.model_available:
            return self._fallback_response(query, diagnostic_result)
        
        try:
            # Build context for the model
            context_parts = [self.system_context]
            
            # Include diagnostic results if available
            if diagnostic_result:
                context_parts.append(f"System diagnostic data: {diagnostic_result}")
            
            # Build the prompt using TinyLlama's chat format
            full_prompt = f"""<|system|>
{' '.join(context_parts)}<|end|>
<|user|>
{query}<|end|>
<|assistant|>
"""
            
            # Generate response using llama.cpp
            response = self.llama_model(
                full_prompt,
                max_tokens=150,
                temperature=0.7,
                top_p=0.9,
                stop=["<|end|>", "<|user|>", "<|system|>"],
                echo=False
            )
            
            generated_text = response['choices'][0]['text'].strip()
            return generated_text if generated_text else self._fallback_response(query, diagnostic_result)
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return self._fallback_response(query, diagnostic_result)
    
    def _fallback_response(self, query, diagnostic_result=None):
        """Generate fallback response when LLM is not available"""
        query_lower = query.lower()
        
        # Container queries
        if any(word in query_lower for word in ['container', 'nextcloud', 'docker']):
            if diagnostic_result:
                return f"Here's what I found about your containers:\n{diagnostic_result}"
            return "I can check container status. Docker may not be available in this environment."
        
        # System status queries
        if any(word in query_lower for word in ['status', 'health', 'running', 'system']):
            if diagnostic_result:
                return f"Current system status:\n{diagnostic_result}"
            return "I can check system health including memory, CPU, and disk usage."
        
        # Model/capability queries
        if any(word in query_lower for word in ['model', 'powering', 'how do you work']):
            if self.model_available:
                return "I'm powered by TinyLlama 1.1B running locally on your Pi via llama.cpp, combined with system diagnostic tools."
            else:
                return "I'm running locally on your Pi using structured diagnostic protocols. I can help monitor system health and troubleshoot issues."
        
        # Network queries
        if any(word in query_lower for word in ['network', 'connection', 'internet', 'wireguard']):
            if diagnostic_result:
                return f"Network status:\n{diagnostic_result}"
            return "I can check network connectivity, interface status, and routing information."
        
        # Default response
        base_response = f"I understand you're asking about: {query}."
        if diagnostic_result:
            return f"{base_response}\n\nHere's what I found:\n{diagnostic_result}"
        return f"{base_response} Let me gather some information to help you."
    
    def _extract_diagnostic_intent(self, query):
        """Extract the diagnostic intent from user query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['container', 'docker', 'nextcloud', 'service']):
            return 'container_status'
        elif any(word in query_lower for word in ['memory', 'ram', 'cpu', 'load', 'system']):
            return 'system_status'
        elif any(word in query_lower for word in ['network', 'connection', 'internet', 'ping', 'wireguard']):
            return 'network_check'
        elif any(word in query_lower for word in ['process', 'running', 'pid']):
            return 'process_list'
        elif any(word in query_lower for word in ['disk', 'space', 'storage']):
            return 'disk_usage'
        else:
            return 'general'
    
    def run_diagnostics(self, intent):
        """Run appropriate diagnostic based on intent"""
        try:
            if intent == 'container_status':
                return self._check_container_status()
            elif intent == 'system_status':
                return self._check_system_status()
            elif intent == 'network_check':
                return self._check_network()
            elif intent == 'process_list':
                return self._get_process_list()
            elif intent == 'disk_usage':
                return self._check_disk_usage()
            else:
                return self._get_general_status()
        except Exception as e:
            logger.error(f"Diagnostic error: {e}")
            return f"Error running diagnostics: {e}"
    
    def _check_container_status(self):
        """
        Check Docker container status
        Requirements: docker command available, user in docker group
        """
        try:
            result = subprocess.run(['docker', 'ps', '-a', '--format', 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return f"Container status:\n{result.stdout}"
            else:
                return "Docker not available or permission denied"
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError) as e:
            return f"Cannot check containers: {e}"
    
    def _check_system_status(self):
        """
        Check system memory, CPU, and load
        Requirements: /proc filesystem (standard on Linux)
        """
        status_parts = []
        
        # Memory usage using psutil
        try:
            memory = psutil.virtual_memory()
            status_parts.append(f"Memory: {memory.percent}% used ({memory.used // (1024**3):.1f}GB / {memory.total // (1024**3):.1f}GB)")
        except Exception as e:
            status_parts.append(f"Memory: unavailable ({e})")
        
        # CPU usage
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            status_parts.append(f"CPU: {cpu_percent}% usage")
        except Exception as e:
            status_parts.append(f"CPU: unavailable ({e})")
        
        # Load average
        try:
            load_avg = os.getloadavg()[0]
            status_parts.append(f"Load: {load_avg:.2f}")
        except Exception as e:
            status_parts.append(f"Load: unavailable ({e})")
        
        # CPU temperature (Pi specific)
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp_millidegree = int(f.read().strip())
                temp_celsius = temp_millidegree / 1000
                status_parts.append(f"CPU temp: {temp_celsius:.1f}°C")
        except Exception:
            pass  # Temperature not critical for status
        
        return "\n".join(status_parts)
    
    def _check_network(self):
        """
        Check network connectivity
        Requirements: ping, ip commands available
        """
        results = []
        
        # Check interfaces
        try:
            result = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                interfaces = [line for line in result.stdout.split('\n') if 'state UP' in line]
                results.append(f"Active interfaces: {len(interfaces)}")
        except Exception as e:
            results.append(f"Interface check failed: {e}")
        
        # Ping test
        try:
            result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                results.append("Internet connectivity: OK")
            else:
                results.append("Internet connectivity: Failed")
        except Exception as e:
            results.append(f"Ping test failed: {e}")
        
        # Check WireGuard if available
        try:
            result = subprocess.run(['wg', 'show'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                results.append("WireGuard: Active")
            else:
                results.append("WireGuard: Not active")
        except Exception:
            results.append("WireGuard: Not available")
        
        return "\n".join(results)
    
    def _get_process_list(self):
        """
        Get list of running processes
        Requirements: ps command or psutil
        """
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    if proc.info['cpu_percent'] > 5 or proc.info['memory_percent'] > 5:
                        processes.append(f"{proc.info['name']} (PID {proc.info['pid']}): CPU {proc.info['cpu_percent']:.1f}%, RAM {proc.info['memory_percent']:.1f}%")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if processes:
                return f"High resource processes:\n" + "\n".join(processes[:10])
            else:
                return "No high resource usage processes found"
        except Exception as e:
            return f"Process check failed: {e}"
    
    def _check_disk_usage(self):
        """
        Check disk usage
        Requirements: df command or psutil
        """
        try:
            disk_usage = psutil.disk_usage('/')
            used_percent = (disk_usage.used / disk_usage.total) * 100
            return f"Disk usage: {used_percent:.1f}% used ({disk_usage.used // (1024**3):.1f}GB / {disk_usage.total // (1024**3):.1f}GB)"
        except Exception as e:
            return f"Disk check failed: {e}"
    
    def _get_general_status(self):
        """Get general system overview"""
        status_parts = []
        
        # Hostname
        try:
            hostname = os.uname().nodename
            status_parts.append(f"System: {hostname}")
        except Exception:
            pass
        
        # Uptime
        try:
            uptime_seconds = psutil.boot_time()
            uptime_hours = (datetime.now().timestamp() - uptime_seconds) / 3600
            status_parts.append(f"Uptime: {uptime_hours:.1f} hours")
        except Exception:
            pass
        
        # Quick memory check
        try:
            memory = psutil.virtual_memory()
            status_parts.append(f"Available RAM: {memory.available // (1024**3):.1f}GB")
        except Exception:
            pass
        
        return "\n".join(status_parts) if status_parts else "System information available"


# Global instance for use by web_agent.py
smart_agent = UnifiedSmartAgent()

def process_smart_query(query):
    """Main entry point for processing smart queries"""
    return smart_agent.process_query(query)


def main():
    """Main entry point for testing"""
    agent = UnifiedSmartAgent()
    
    print("Unified Smart Agent initialized!")
    print(f"TinyLlama available: {agent.model_available}")
    print(f"Sentence transformer available: {agent.sentence_model is not None}")
    
    # Test queries
    test_queries = [
        "What model is powering your responses?",
        "How many containers are running?", 
        "What's the system status?",
        "Check network connectivity"
    ]
    
    for query in test_queries:
        print(f"\n🤖 Query: {query}")
        response = agent.process_query(query)
        print(f"📋 Response: {response}")


if __name__ == "__main__":
    main()
