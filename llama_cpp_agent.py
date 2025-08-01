#!/usr/bin/env python3
"""
Local LLM Agent using llama.cpp for TinyLlama GGUF model
Provides natural language responses while maintaining diagnostic capabilities.
"""

import os
import subprocess
import json
import logging
import tempfile
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class LlamaCppAgent:
    """
    Agent that uses llama.cpp to run local GGUF models for natural language responses
    """
    
    def __init__(self, model_path="/app/models/tinyllama.gguf"):
        self.model_path = model_path
        self.llama_cpp_path = "/usr/local/bin/llama-cli"  # Adjust path as needed
        self.max_tokens = 150
        self.temperature = 0.7
        self.model_available = self._check_model_availability()
        
    def _check_model_availability(self):
        """Check if the model and llama.cpp are available"""
        if not os.path.exists(self.model_path):
            logger.warning(f"TinyLlama model not found at {self.model_path}")
            return False
            
        # Check for llama.cpp binary (try multiple common locations)
        possible_paths = [
            "/usr/local/bin/llama-cli",
            "/usr/bin/llama-cli", 
            "/app/llama.cpp/main",
            "/app/llama.cpp/llama-cli",
            "./llama.cpp/main"
        ]
        
        for path in possible_paths:
            if os.path.exists(path) and os.access(path, os.X_OK):
                self.llama_cpp_path = path
                logger.info(f"Found llama.cpp at {path}")
                return True
                
        logger.warning("llama.cpp binary not found")
        return False
    
    def generate_response(self, query, context=None, system_prompt=None):
        """Generate a natural response using the local TinyLlama model"""
        
        if not self.model_available:
            return self._fallback_response(query, context)
            
        try:
            # Build the prompt
            full_prompt = self._build_prompt(query, context, system_prompt)
            
            # Run llama.cpp
            cmd = [
                self.llama_cpp_path,
                "-m", self.model_path,
                "-p", full_prompt,
                "-n", str(self.max_tokens),
                "--temp", str(self.temperature),
                "--top-k", "40",
                "--top-p", "0.9",
                "--repeat-penalty", "1.1",
                "--ctx-size", "2048",
                "--batch-size", "8",
                "--threads", "4"
            ]
            
            logger.debug(f"Running llama.cpp command: {' '.join(cmd[:4])}...")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd="/app"
            )
            
            if result.returncode == 0:
                response = result.stdout.strip()
                # Clean up the response - remove the input prompt echo
                response = self._clean_response(response, full_prompt)
                return response
            else:
                logger.error(f"llama.cpp failed: {result.stderr}")
                return self._fallback_response(query, context)
                
        except subprocess.TimeoutExpired:
            logger.warning("llama.cpp timed out")
            return self._fallback_response(query, context)
        except Exception as e:
            logger.error(f"Error running llama.cpp: {e}")
            return self._fallback_response(query, context)
    
    def _build_prompt(self, query, context=None, system_prompt=None):
        """Build the prompt for TinyLlama"""
        
        # TinyLlama uses ChatML format
        prompt_parts = []
        
        # System message
        if system_prompt:
            system_msg = system_prompt
        else:
            system_msg = """You are a helpful diagnostic assistant running on a Raspberry Pi. 
You help monitor system health, check Docker containers, troubleshoot network issues, and provide technical support.
Be conversational and helpful. Give specific, actionable responses."""
        
        prompt_parts.append(f"<|system|>\n{system_msg}<|end|>")
        
        # Add context if available
        if context:
            prompt_parts.append(f"<|user|>\nContext: {context}<|end|>")
        
        # User query
        prompt_parts.append(f"<|user|>\n{query}<|end|>")
        
        # Assistant response start
        prompt_parts.append("<|assistant|>\n")
        
        return "\n".join(prompt_parts)
    
    def _clean_response(self, response, original_prompt):
        """Clean up the model response"""
        # Remove the original prompt if it was echoed
        if original_prompt in response:
            response = response.replace(original_prompt, "").strip()
        
        # Remove any trailing special tokens
        response = response.replace("<|end|>", "").strip()
        response = response.replace("<|user|>", "").strip()
        response = response.replace("<|assistant|>", "").strip()
        
        # Split by lines and take the first substantial response
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        if lines:
            # Take the first few lines that form a coherent response
            response_lines = []
            for line in lines:
                response_lines.append(line)
                # Stop at natural breaking points
                if len(response_lines) >= 3 or line.endswith('.') or line.endswith('!') or line.endswith('?'):
                    break
            response = " ".join(response_lines)
        
        return response[:500]  # Limit response length
    
    def _fallback_response(self, query, context=None):
        """Provide a fallback response when the model isn't available"""
        query_lower = query.lower()
        
        # Model/capability queries
        if any(word in query_lower for word in ['model', 'powering', 'responses', 'what are you']):
            return "I'm powered by TinyLlama 1.1B running locally on your Raspberry Pi via llama.cpp. I can help with system diagnostics, Docker container management, and network troubleshooting."
        
        # Container queries
        if any(word in query_lower for word in ['container', 'docker', 'nextcloud', 'running']):
            return "Let me check your Docker containers for you. I can see what's currently running and help troubleshoot any issues."
        
        # System queries
        if any(word in query_lower for word in ['system', 'health', 'status', 'memory', 'cpu']):
            return "I'll analyze your system status including CPU usage, memory consumption, and running processes."
        
        # Network queries  
        if any(word in query_lower for word in ['network', 'connection', 'internet', 'wireguard']):
            return "I can help diagnose network connectivity issues, check your WireGuard tunnel status, and analyze routing configuration."
        
        # Default
        return f"I understand you're asking about {query}. Let me gather some information to help you with that."


# Global instance
llama_agent = LlamaCppAgent()

def generate_smart_response(query, diagnostic_result=None, system_context=None):
    """Generate a smart response using the local LLM"""
    
    # Build context from diagnostic result
    context_parts = []
    if diagnostic_result:
        context_parts.append(f"Diagnostic data: {diagnostic_result}")
    if system_context:
        context_parts.append(f"System context: {system_context}")
    
    context = "; ".join(context_parts) if context_parts else None
    
    return llama_agent.generate_response(query, context)
