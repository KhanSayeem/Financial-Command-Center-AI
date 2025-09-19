"""
Utility script to check if the local LLM is running and accessible
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
import requests
import json
from config.settings import LLM_PROVIDER, LLM_BASE_URL, LLM_MODEL

def check_local_llm():
    """Check if the local LLM is running and accessible"""
    print(f"Checking {LLM_PROVIDER} connection...")
    print(f"Base URL: {LLM_BASE_URL}")
    print(f"Model: {LLM_MODEL}")
    
    try:
        # For Ollama, we can check if the model is available
        if LLM_PROVIDER.lower() == "ollama":
            # Check if Ollama is running (tags endpoint - non-OpenAI API)
            response = requests.get("http://localhost:11434/api/tags", timeout=10)
            if response.status_code == 200:
                print("[SUCCESS] Ollama server is running")
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                if any(LLM_MODEL in name for name in model_names):
                    print(f"[SUCCESS] Model '{LLM_MODEL}' is available")
                else:
                    print(f"[WARNING] Model '{LLM_MODEL}' is not available. Available models: {model_names}")
                    return False
            else:
                print("[ERROR] Ollama server is not accessible")
                return False
                
        # For LM Studio, we can check the models endpoint
        elif LLM_PROVIDER.lower() == "lmstudio":
            response = requests.get(f"{LLM_BASE_URL}/models", timeout=10)
            if response.status_code == 200:
                print("[SUCCESS] LM Studio server is running")
                models = response.json().get("data", [])
                if models:
                    print(f"[SUCCESS] {len(models)} models available")
                else:
                    print("[WARNING] No models available in LM Studio")
            else:
                print("[ERROR] LM Studio server is not accessible")
                return False
        
        # Test a simple completion using the OpenAI-compatible endpoint
        print("Testing completion...")
        
        payload = {
            "model": LLM_MODEL,
            "messages": [
                {"role": "user", "content": "Hello, are you there?"}
            ],
            "max_tokens": 50
        }
        
        headers = {
            "Content-Type": "application/json"
        }
        
        # Use the OpenAI-compatible endpoint for both providers
        api_endpoint = f"{LLM_BASE_URL}/chat/completions"
        
        response = requests.post(
            api_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            print("[SUCCESS] Local LLM is responding to requests")
            result = response.json()
            response_text = result["choices"][0]["message"]["content"] if "choices" in result and len(result["choices"]) > 0 else ""
            print(f"Sample response: {response_text[:100]}...")
            return True
        else:
            print(f"[ERROR] Local LLM returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to {LLM_PROVIDER} at {LLM_BASE_URL}")
        print("Please make sure:")
        if LLM_PROVIDER.lower() == "ollama":
            print("1. Ollama is installed and running")
            print("2. The model is pulled: ollama pull llama3.2")
        elif LLM_PROVIDER.lower() == "lmstudio":
            print("1. LM Studio is installed and running")
            print("2. A model is loaded and the server is started")
        return False
    except Exception as e:
        print(f"[ERROR] Error checking {LLM_PROVIDER}: {e}")
        return False

if __name__ == "__main__":
    success = check_local_llm()
    if success:
        print("\nLocal LLM is ready for use with the Financial Command Center!")
    else:
        print("\nPlease resolve the connection issues before proceeding.")
    sys.exit(0 if success else 1)