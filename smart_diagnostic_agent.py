#!/usr/bin/env python3
"""
Smart Diagnostic Agent with Natural Language Processing
Provides organic, conversational responses while maintaining diagnostic capabilities.

This agent uses a local LLM to provide natural responses and then executes
appropriate diagnostic tasks based on the conversation context.
"""

import os
import json
import subprocess
import time
import logging
from datetime import datetime
from pathlib import Path

# Try to import transformers for local LLM
try:
    from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    import torch
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False

# Import existing diagnostic capabilities
from diagnostic_agent import DiagnosticAgent

logger = logging.getLogger(__name__)

class SmartDiagnosticAgent:
    """
    An intelligent diagnostic agent that combines natural language understanding
    with system diagnostic capabilities.
    """
    
    def __init__(self, memory_dir="/app/agent_memory"):
        self.memory_dir = memory_dir
        self.diagnostic_agent = DiagnosticAgent(memory_dir)
        self.model = None
        self.tokenizer = None
        self.conversation_history = []
        
        # Model configuration - use local TinyLlama model
        self.local_model_path = "/home/diagnostic-agent/models/tinyllama.gguf"
        self.huggingface_model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        self.max_tokens = 256
        self.temperature = 0.7
        
        self._initialize_model()
        
    def _initialize_model(self):
        """Initialize the local language model - prioritize local GGUF model"""
        # First try to use local GGUF model with llama.cpp
        if os.path.exists(self.local_model_path):
            logger.info(f"Using local GGUF model: {self.local_model_path}")
            self.use_gguf = True
            return
            
        # Fallback to transformers if available
        if not TRANSFORMERS_AVAILABLE:
            logger.warning("Neither local GGUF model nor transformers available, using structured responses")
            self.use_gguf = False
            return
            
        try:
            logger.info(f"Loading transformers model: {self.huggingface_model_name}")
            
            # Use CPU-optimized settings for Pi
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.huggingface_model_name, 
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.huggingface_model_name,
                torch_dtype=torch.float32,  # Use float32 for CPU
                device_map="cpu",
                trust_remote_code=True,
                low_cpu_mem_usage=True
            )
            
            self.use_gguf = False
            logger.info("Transformers model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load transformers model: {e}")
            self.model = None
            self.tokenizer = None
            self.use_gguf = False

    def _generate_natural_response(self, query, diagnostic_result=None):
        """Generate a natural language response using the local LLM"""
        if hasattr(self, 'use_gguf') and self.use_gguf and os.path.exists(self.local_model_path):
            return self._generate_gguf_response(query, diagnostic_result)
        elif self.model and self.tokenizer:
            return self._generate_transformers_response(query, diagnostic_result)
        else:
            return self._fallback_response(query, diagnostic_result)
    
    def _generate_gguf_response(self, query, diagnostic_result=None):
        """Generate response using local GGUF model via llama.cpp"""
        try:
            # Build context for the model
            system_prompt = """You are a helpful diagnostic assistant running on a Raspberry Pi. 
You help users understand their system status in a conversational, friendly way. 
Be concise but informative. If you don't have specific information, say so honestly."""
            
            # Include diagnostic results in context if available
            context = ""
            if diagnostic_result:
                context = f"\n\nDiagnostic information: {diagnostic_result}"
            
            # Format the conversation
            full_prompt = f"{system_prompt}\n\nUser: {query}{context}\n\nAssistant:"
            
            # Use llama.cpp to generate response
            llama_cpp_path = "/home/diagnostic-agent/llama.cpp/main"  # Adjust path as needed
            if not os.path.exists(llama_cpp_path):
                # Try alternative paths
                for alt_path in ["/app/llama.cpp/main", "./llama.cpp/main", "llama.cpp"]:
                    if os.path.exists(alt_path):
                        llama_cpp_path = alt_path
                        break
                else:
                    logger.warning("llama.cpp not found, falling back")
                    return self._fallback_response(query, diagnostic_result)
            
            # Run llama.cpp with the model
            cmd = [
                llama_cpp_path,
                "-m", self.local_model_path,
                "-p", full_prompt,
                "-n", str(self.max_tokens),
                "--temp", str(self.temperature),
                "-c", "1024"  # context size
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                # Extract just the assistant's response
                output = result.stdout.strip()
                if "Assistant:" in output:
                    response = output.split("Assistant:")[-1].strip()
                else:
                    response = output.strip()
                return response
            else:
                logger.error(f"llama.cpp failed: {result.stderr}")
                return self._fallback_response(query, diagnostic_result)
                
        except Exception as e:
            logger.error(f"GGUF response generation failed: {e}")
            return self._fallback_response(query, diagnostic_result)
    
    def _generate_transformers_response(self, query, diagnostic_result=None):
        """Generate response using transformers library"""
        try:
            # Build context for the model
            system_prompt = """You are a helpful diagnostic assistant running on a Raspberry Pi. 
You help users understand their system status in a conversational, friendly way. 
Be concise but informative. If you don't have specific information, say so honestly."""
            
            # Include diagnostic results in context if available
            context = ""
            if diagnostic_result:
                context = f"\n\nDiagnostic information: {diagnostic_result}"
            
            # Format the conversation
            full_prompt = f"{system_prompt}\n\nUser: {query}{context}\n\nAssistant:"
            
            # Generate response
            inputs = self.tokenizer.encode(full_prompt, return_tensors="pt")
            
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs,
                    max_length=inputs.shape[1] + self.max_tokens,
                    temperature=self.temperature,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id,
                    attention_mask=torch.ones_like(inputs)
                )
            
            # Decode response
            full_response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = full_response.split("Assistant:")[-1].strip()
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return self._fallback_response(query, diagnostic_result)
    
    def _fallback_response(self, query, diagnostic_result=None):
        """Fallback response when LLM is not available"""
        query_lower = query.lower()
        
        # Container queries
        if any(word in query_lower for word in ['container', 'nextcloud', 'docker']):
            if diagnostic_result and 'ERR: Docker command not found' in diagnostic_result:
                return "It looks like Docker isn't available in this environment. Are you running this from outside the Pi, or is Docker not installed?"
            elif diagnostic_result:
                return f"Let me check the container status... {diagnostic_result}"
            else:
                return "I'll check the container status for you."
        
        # System status queries
        if any(word in query_lower for word in ['status', 'health', 'running']):
            return "Let me gather the current system information for you."
        
        # Model/capability queries
        if any(word in query_lower for word in ['model', 'powering', 'how do you work']):
            model_info = f"I'm running locally on your Pi using {self.model_name if self.model else 'structured diagnostic protocols'}. I can help you monitor system health, check services, and troubleshoot network issues."
            return model_info
        
        # Network queries
        if any(word in query_lower for word in ['network', 'connection', 'internet']):
            return "I'll check your network connectivity and configuration."
        
        # Default response
        return f"I understand you're asking about: {query}. Let me see what I can find out for you."

    def _extract_diagnostic_intent(self, query):
        """Extract what kind of diagnostic action is needed"""
        query_lower = query.lower()
        
        # Map query patterns to diagnostic types
        if any(word in query_lower for word in ['container', 'docker', 'nextcloud', 'service']):
            return 'containers'
        elif any(word in query_lower for word in ['network', 'connection', 'internet', 'wifi']):
            return 'network'
        elif any(word in query_lower for word in ['system', 'status', 'health', 'memory', 'cpu']):
            return 'system'
        elif any(word in query_lower for word in ['process', 'running', 'ps']):
            return 'processes'
        elif any(word in query_lower for word in ['log', 'error', 'problem']):
            return 'logs'
        else:
            return 'general'

    def process_query(self, query):
        """Process a user query with natural language response and diagnostics"""
        timestamp = datetime.now().isoformat()
        
        # Log the interaction
        self.conversation_history.append({
            'timestamp': timestamp,
            'query': query,
            'type': 'user'
        })
        
        try:
            # Determine what diagnostic action is needed
            diagnostic_intent = self._extract_diagnostic_intent(query)
            
            # Run appropriate diagnostics in background
            diagnostic_result = None
            if diagnostic_intent != 'general':
                try:
                    diagnostic_result = self.diagnostic_agent.execute_diagnostic(query)
                except Exception as e:
                    logger.error(f"Diagnostic error: {e}")
                    diagnostic_result = f"Had trouble running diagnostics: {str(e)}"
            
            # Generate natural language response
            response = self._generate_natural_response(query, diagnostic_result)
            
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

    def get_system_summary(self):
        """Get a quick system summary"""
        try:
            # Get basic system info
            hostname = os.uname().nodename
            
            # Check if we're in a container
            in_container = os.path.exists('/.dockerenv')
            
            summary = f"I'm running on {hostname}"
            if in_container:
                summary += " (inside a container)"
            
            if self.model:
                summary += f" using {self.model_name} for natural language processing"
            else:
                summary += " with structured diagnostic protocols"
            
            return summary
            
        except Exception as e:
            return f"I'm your diagnostic assistant, though I'm having trouble getting system details: {e}"

# Global instance for the web interface
smart_agent = SmartDiagnosticAgent()

def process_smart_query(question):
    """Process a query through the smart diagnostic agent"""
    return smart_agent.process_query(question)
