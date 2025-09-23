"""
Simple test script for Llama 3.2 integration with FCC
"""

import os
import sys
import requests

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_llama32_connection():
    """Test connection to Llama 3.2"""
    print("Testing Llama 3.2 connection...")
    print("=" * 40)
    
    # Get configuration from environment or use defaults
    base_url = os.getenv('LLAMA_BASE_URL', 'http://localhost:11434/v1')
    model = os.getenv('LLAMA_MODEL', 'llama3.2')
    
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    
    # Check if Ollama is running
    try:
        response = requests.get(f"{base_url}/models", timeout=5)
        if response.status_code == 200:
            print("[SUCCESS] Llama 3.2 server is accessible")
            models = response.json().get("data", [])
            model_names = [model["id"] for model in models]
            print(f"Available models: {model_names}")
            
            if model in model_names or f"{model}:latest" in model_names:
                print(f"[SUCCESS] Model '{model}' is available")
                
                # Test a simple completion
                print("\nTesting completion...")
                payload = {
                    "model": model,  # Ollama will use the latest version automatically
                    "messages": [
                        {"role": "system", "content": "You are a helpful financial assistant."},
                        {"role": "user", "content": "Hello, are you there?"}
                    ],
                    "temperature": 0.7,
                    "max_tokens": 100
                }
                
                response = requests.post(
                    f"{base_url}/chat/completions",
                    json=payload,
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("[SUCCESS] Llama 3.2 is responding to requests")
                    assistant_response = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"Response: {assistant_response}")
                    return True
                else:
                    print(f"[ERROR] Llama 3.2 returned status code {response.status_code}")
                    print(f"Response: {response.text}")
                    return False
            else:
                print(f"[ERROR] Model '{model}' not found")
                print("Please run: ollama pull llama3.2")
                return False
        else:
            print(f"[ERROR] Llama 3.2 server returned status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to Llama 3.2 at the specified URL")
        print("Please make sure Ollama is installed and running")
        print("1. Install Ollama from https://ollama.com/")
        print("2. Run: ollama pull llama3.2")
        print("3. Start Ollama service")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

def test_fcc_integration():
    """Test FCC integration with Llama 3.2"""
    print("\n" + "=" * 40)
    print("Testing FCC integration with Llama 3.2...")
    
    try:
        # Try to import the Llama 3.2 integration
        from fcc_llama32_integration import FCCLlama32Integration
        print("[SUCCESS] FCC Llama 3.2 integration module loaded")
        
        # Test initialization
        # Note: We're not passing a Flask app here, just testing the class
        integration = FCCLlama32Integration(None)
        print(f"[INFO] Integration initialized with client_available: {integration.client_available}")
        
        if integration.client_available:
            print("[SUCCESS] FCC Llama 3.2 integration is ready")
            return True
        else:
            print("[WARNING] FCC Llama 3.2 integration initialized but client not available")
            return False
            
    except ImportError as e:
        print(f"[ERROR] Failed to import FCC Llama 3.2 integration: {e}")
        return False
    except Exception as e:
        print(f"[ERROR] Error testing FCC integration: {e}")
        return False

if __name__ == "__main__":
    print("FCC Llama 3.2 Integration Test")
    print("=" * 40)
    
    success1 = test_llama32_connection()
    success2 = test_fcc_integration()
    
    if success1 and success2:
        print("\n" + "=" * 40)
        print("All tests passed! Llama 3.2 integration is ready to use.")
        print("You can now start the FCC application and use the assistant with Llama 3.2.")
    else:
        print("\n" + "=" * 40)
        if not success1:
            print("Llama 3.2 connection test failed. Please check your Ollama installation.")
        if not success2:
            print("FCC integration test failed. Please check the integration code.")
        print("Please fix the issues before proceeding.")