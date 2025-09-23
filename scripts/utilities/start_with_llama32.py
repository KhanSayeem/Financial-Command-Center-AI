#!/usr/bin/env python3
"""
Start the Flask app with Llama 3.2 enabled
"""

from pathlib import Path
import os

REPO_ROOT = Path(__file__).resolve().parents[2]
os.chdir(REPO_ROOT)

import sys

# Add the local LLM adapter to the path
adapter_path = os.path.join(os.path.dirname(__file__), 'fcc-local-llm-adapter')
if os.path.exists(adapter_path) and adapter_path not in sys.path:
    sys.path.insert(0, adapter_path)

# Set environment variables for Llama 3.2
os.environ['USE_LLAMA32'] = 'true'
os.environ['ASSISTANT_MODEL_TYPE'] = 'llama32'

# Import and run the app
if __name__ == "__main__":
    from app_with_setup_wizard import app

    print("Starting Financial Command Center with Llama 3.2...")
    print(f"USE_LLAMA32 = {os.getenv('USE_LLAMA32')}")

    # Run the app
    app.run(host='127.0.0.1', port=8000, debug=True, ssl_context='adhoc')
