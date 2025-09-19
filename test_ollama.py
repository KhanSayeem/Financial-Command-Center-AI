"""
Simple test script for Ollama connection
"""
import requests
import json

def test_ollama():
    """Test connection to Ollama"""
    print("Testing Ollama connection...")
    print("=" * 40)
    
    # Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            print("[SUCCESS] Ollama server is running")
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            print(f"Available models: {model_names}")
            
            # Check for llama3.2 (with or without :latest)
            llama32_available = any("llama3.2" in name for name in model_names)
            if llama32_available:
                print("[SUCCESS] Llama 3.2 model is available")
                
                # Test a simple completion
                print("\nTesting completion...")
                payload = {
                    "model": "llama3.2",  # Ollama will use the latest version
                    "prompt": "Hello, are you there?",
                    "stream": False
                }
                
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json=payload
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("[SUCCESS] Ollama is responding to requests")
                    print(f"Response: {result.get('response', '')[:100]}...")
                    return True
                else:
                    print(f"[ERROR] Ollama returned status code {response.status_code}")
                    return False
            else:
                print("[ERROR] Llama 3.2 model not found")
                print("Please run: ollama pull llama3.2")
                return False
        else:
            print("[ERROR] Ollama server is not accessible")
            return False
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Cannot connect to Ollama at http://localhost:11434")
        print("Please make sure Ollama is installed and running")
        return False
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama()
    if success:
        print("\n" + "=" * 40)
        print("Ollama is ready to use!")
        print("You can now test the local LLM adapter")
    else:
        print("\n" + "=" * 40)
        print("Please fix the Ollama connection before proceeding")