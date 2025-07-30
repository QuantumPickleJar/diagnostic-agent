#!/usr/bin/env python3
"""
CLI interface for the Diagnostic Agent
Allows sending prompts directly to the agent via command line
"""

import argparse
import requests
import json
import sys
import os
from datetime import datetime

# Default configuration
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5000
DEFAULT_ENDPOINT = "/ask"

# Remote host configuration (can be overridden by environment variables)
REMOTE_HOST = os.getenv('DIAGNOSTIC_AGENT_HOST', DEFAULT_HOST)
REMOTE_PORT = int(os.getenv('DIAGNOSTIC_AGENT_PORT', DEFAULT_PORT))

def send_prompt(question, host=DEFAULT_HOST, port=DEFAULT_PORT, activation_word=None, verbose=False):
    """Send a prompt to the diagnostic agent and return the response"""
    
    url = f"http://{host}:{port}{DEFAULT_ENDPOINT}"
    
    # Prepare the request data
    data = {"question": question}
    
    # Add activation word if provided
    if activation_word:
        data["password"] = activation_word
    
    headers = {"Content-Type": "application/json"}
    
    # Add activation word to headers if provided
    if activation_word:
        headers["X-Activate-Word"] = activation_word
    
    if verbose:
        print(f"[DEBUG] Sending request to: {url}")
        print(f"[DEBUG] Data: {json.dumps(data, indent=2)}")
        print(f"[DEBUG] Headers: {json.dumps(headers, indent=2)}")
        print()
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=30)
        
        if verbose:
            print(f"[DEBUG] Response status: {response.status_code}")
            print(f"[DEBUG] Response headers: {dict(response.headers)}")
            print()
        
        if response.status_code == 200:
            result = response.json()
            return True, result.get("response", "No response received")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", f"HTTP {response.status_code}")
            except:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
            return False, error_msg
            
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to diagnostic agent at {host}:{port}. Is it running?"
    except requests.exceptions.Timeout:
        return False, f"Request timed out after 30 seconds"
    except requests.exceptions.RequestException as e:
        return False, f"Request failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

def get_agent_status(host=DEFAULT_HOST, port=DEFAULT_PORT, verbose=False):
    """Get the status of the diagnostic agent"""
    
    url = f"http://{host}:{port}/status"
    
    if verbose:
        print(f"[DEBUG] Checking status at: {url}")
    
    try:
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            return True, response.json()
        else:
            return False, f"Status check failed: HTTP {response.status_code}"
            
    except requests.exceptions.ConnectionError:
        return False, f"Cannot connect to diagnostic agent at {host}:{port}"
    except Exception as e:
        return False, f"Status check error: {str(e)}"

def interactive_mode(host=DEFAULT_HOST, port=DEFAULT_PORT, activation_word=None, verbose=False):
    """Start interactive CLI mode"""
    
    print("🚀 Diagnostic Agent CLI - Interactive Mode")
    print(f"Connected to: {host}:{port}")
    print("Type 'exit', 'quit', or press Ctrl+C to exit")
    print("Type 'status' to check agent status")
    print("Type 'help' for available commands")
    print("-" * 50)
    
    # Check agent status first
    success, status_data = get_agent_status(host, port, verbose)
    if success:
        print(f"✅ Agent Status: {status_data.get('status', 'Unknown')}")
        if status_data.get('ssh_bridge'):
            print("🔗 SSH Bridge: Enabled")
        print(f"📊 FAISS Entries: {status_data.get('faiss_entries', 0)}")
    else:
        print(f"⚠️  Status check failed: {status_data}")
    
    print("-" * 50)
    
    while True:
        try:
            # Get user input
            question = input("\n🤖 Ask > ").strip()
            
            if not question:
                continue
            
            # Handle special commands
            if question.lower() in ['exit', 'quit']:
                print("👋 Goodbye!")
                break
            elif question.lower() == 'status':
                success, status_data = get_agent_status(host, port, verbose)
                if success:
                    print(f"📊 Agent Status: {json.dumps(status_data, indent=2)}")
                else:
                    print(f"❌ Status Error: {status_data}")
                continue
            elif question.lower() == 'help':
                print("""
Available commands:
  status     - Check agent status
  help       - Show this help message
  exit/quit  - Exit interactive mode
  
Or type any question to send to the diagnostic agent.
                """)
                continue
            
            # Send the question to the agent
            print("⏳ Processing...")
            success, response = send_prompt(question, host, port, activation_word, verbose)
            
            print("\n" + "="*60)
            if success:
                print("🔍 Agent Response:")
                print(response)
            else:
                print("❌ Error:")
                print(response)
            print("="*60)
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except EOFError:
            print("\n👋 Goodbye!")
            break

def main():
    parser = argparse.ArgumentParser(
        description="CLI interface for the Diagnostic Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "What is the system status?"
  %(prog)s --interactive
  %(prog)s --host 192.168.1.100 "Check network connectivity"
  %(prog)s --activation-word secret123 "Run system diagnostic"
  %(prog)s --status
        """
    )
    
    parser.add_argument(
        "question",
        nargs="?",
        help="Question to ask the diagnostic agent (if not using interactive mode)"
    )
    
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Host where the diagnostic agent is running (default: {DEFAULT_HOST})"
    )
    
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port where the diagnostic agent is listening (default: {DEFAULT_PORT})"
    )
    
    parser.add_argument(
        "--activation-word", "-a",
        help="Activation word for protected endpoints"
    )
    
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Start interactive mode"
    )
    
    parser.add_argument(
        "--status", "-s",
        action="store_true",
        help="Check agent status and exit"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output (debug information)"
    )
    
    parser.add_argument(
        "--output-format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    args = parser.parse_args()
    
    # Load activation word from environment if not provided
    if not args.activation_word:
        args.activation_word = os.getenv('ACTIVATION_WORD')
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if args.verbose:
        print(f"[DEBUG] {timestamp} - Starting CLI with args: {vars(args)}")
    
    # Status check mode
    if args.status:
        success, result = get_agent_status(args.host, args.port, args.verbose)
        
        if args.output_format == "json":
            if success:
                print(json.dumps(result, indent=2))
            else:
                print(json.dumps({"error": result}, indent=2))
        else:
            if success:
                print(f"✅ Agent Status: {result.get('status', 'Unknown')}")
                print(f"🌐 Host: {args.host}:{args.port}")
                print(f"🔗 SSH Bridge: {'Enabled' if result.get('ssh_bridge') else 'Disabled'}")
                print(f"📊 FAISS Entries: {result.get('faiss_entries', 0)}")
                print(f"⏰ Timestamp: {result.get('timestamp', 'Unknown')}")
            else:
                print(f"❌ Status Error: {result}")
        
        sys.exit(0 if success else 1)
    
    # Interactive mode
    if args.interactive:
        interactive_mode(args.host, args.port, args.activation_word, args.verbose)
        sys.exit(0)
    
    # Single question mode
    if not args.question:
        print("❌ Error: Please provide a question or use --interactive mode")
        parser.print_help()
        sys.exit(1)
    
    if args.verbose:
        print(f"[DEBUG] Sending question: {args.question}")
    
    success, response = send_prompt(args.question, args.host, args.port, args.activation_word, args.verbose)
    
    if args.output_format == "json":
        result = {
            "success": success,
            "question": args.question,
            "timestamp": timestamp,
            "host": f"{args.host}:{args.port}"
        }
        
        if success:
            result["response"] = response
        else:
            result["error"] = response
        
        print(json.dumps(result, indent=2))
    else:
        print(f"🤖 Question: {args.question}")
        print("="*60)
        
        if success:
            print("🔍 Agent Response:")
            print(response)
        else:
            print("❌ Error:")
            print(response)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
