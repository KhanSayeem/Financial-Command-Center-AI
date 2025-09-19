"""
Simple script to configure the FCC assistant model type
"""

import os

def set_assistant_model(model_type):
    """Set the assistant model type in the environment file"""
    
    # Check if .env file exists, if not create it
    env_file = ".env"
    env_lines = []
    
    if os.path.exists(env_file):
        with open(env_file, "r") as f:
            env_lines = f.readlines()
    
    # Check if ASSISTANT_MODEL_TYPE is already set
    model_line_found = False
    for i, line in enumerate(env_lines):
        if line.startswith("ASSISTANT_MODEL_TYPE="):
            env_lines[i] = f"ASSISTANT_MODEL_TYPE={model_type}\n"
            model_line_found = True
            break
    
    # If not found, add it
    if not model_line_found:
        env_lines.append(f"ASSISTANT_MODEL_TYPE={model_type}\n")
    
    # Write back to file
    with open(env_file, "w") as f:
        f.writelines(env_lines)
    
    print(f"Assistant model type set to: {model_type}")
    
    # Also print configuration instructions
    if model_type == "openai":
        print("\nFor OpenAI, you also need to set your API key:")
        print("export OPENAI_API_KEY='your_openai_api_key_here'")
        print("or add it to your .env file:")
        print("OPENAI_API_KEY=your_openai_api_key_here")
    elif model_type == "llama32":
        print("\nFor Llama 3.2, make sure you have:")
        print("1. Ollama installed and running")
        print("2. Llama 3.2 model pulled: ollama pull llama3.2")
        print("\nDefault configuration:")
        print("LLAMA_BASE_URL=http://localhost:11434/v1")
        print("LLAMA_MODEL=llama3.2")

def main():
    print("FCC Assistant Model Configuration")
    print("=" * 35)
    
    print("\nAvailable models:")
    print("1. OpenAI (requires API key)")
    print("2. Llama 3.2 (local, free to use)")
    
    choice = input("\nSelect model (1 or 2): ").strip()
    
    if choice == "1":
        set_assistant_model("openai")
    elif choice == "2":
        set_assistant_model("llama32")
    else:
        print("Invalid choice. Please select 1 or 2.")

if __name__ == "__main__":
    main()