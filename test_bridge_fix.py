#!/usr/bin/env python3
"""
Test script to verify bridge connectivity fixes
"""

import os
import sys
import time
from dotenv import load_dotenv

# Load environment
load_dotenv()

def test_environment():
    """Test environment variable loading"""
    print("🔧 Testing environment variables...")
    
    ip = os.getenv("DEV_MACHINE_IP")
    port = os.getenv("DEV_MACHINE_PORT")
    user = os.getenv("DEV_MACHINE_USER")
    mac = os.getenv("DEV_MACHINE_MAC")
    
    print(f"   IP: {ip}")
    print(f"   Port: {port}")
    print(f"   User: {user}")
    print(f"   MAC: {mac}")
    
    if port != "2222" or user != "vince":
        print("❌ Environment variables not properly configured!")
        return False
    
    print("✅ Environment variables look correct")
    return True

def test_bridge_checker():
    """Test the bridge checker module"""
    print("\n🔍 Testing bridge checker...")
    
    try:
        from tasks.bridge_checker import is_ssh_up, DEV_IP, DEV_PORT, DEV_USER
        
        print(f"   Bridge checker config: {DEV_USER}@{DEV_IP}:{DEV_PORT}")
        
        if DEV_PORT != "2222" or DEV_USER != "vince":
            print("❌ Bridge checker using wrong configuration!")
            return False
            
        print("   Testing SSH connectivity (5 second timeout)...")
        start_time = time.time()
        result = is_ssh_up(DEV_IP)
        elapsed = time.time() - start_time
        
        print(f"   Result: {'✅ Connected' if result else '❌ Not connected'}")
        print(f"   Time taken: {elapsed:.2f} seconds")
        
        if elapsed > 10:
            print("⚠️  Warning: SSH test took longer than expected")
            
        return True
        
    except Exception as e:
        print(f"❌ Bridge checker test failed: {e}")
        return False

def test_bridge_monitor():
    """Test the bridge status monitor"""
    print("\n📊 Testing bridge status monitor...")
    
    try:
        from bridge_status_monitor import BridgeStatusMonitor
        
        monitor = BridgeStatusMonitor()
        
        config = monitor.config
        print(f"   Monitor config: {config['dev_machine_user']}@{config['dev_machine_ip']}:{config['dev_machine_port']}")
        
        if config['dev_machine_port'] != 2222 or config['dev_machine_user'] != "castlebravo":
            print("❌ Bridge monitor using wrong configuration!")
            return False
            
        print("   Testing SSH reachability (5 second timeout)...")
        start_time = time.time()
        result = monitor.is_ssh_reachable()
        elapsed = time.time() - start_time
        
        print(f"   Result: {'✅ Reachable' if result else '❌ Not reachable'}")
        print(f"   Time taken: {elapsed:.2f} seconds")
        
        if elapsed > 10:
            print("⚠️  Warning: Monitor test took longer than expected")
            
        return True
        
    except Exception as e:
        print(f"❌ Bridge monitor test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🧪 Testing Bridge Connectivity Fixes")
    print("=" * 50)
    
    tests = [
        test_environment,
        test_bridge_checker,
        test_bridge_monitor
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    test_names = ["Environment", "Bridge Checker", "Bridge Monitor"]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {name}: {status}")
    
    all_passed = all(results)
    print(f"\nOverall: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    
    if all_passed:
        print("\n🚀 Bridge fixes should now work correctly!")
        print("   Try the curl commands again:")
        print("   curl http://localhost:5000/bridge/status")
        print("   curl -X POST http://localhost:5000/bridge/force_check")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
