#!/usr/bin/env python3
"""
Test simple message without MCP tools to isolate the issue
"""

import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_simple_message():
    """Test a simple message to see if it's an MCP or Llama issue."""
    base_url = "https://127.0.0.1:8000"

    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = False

    try:
        # Create thread
        logger.info("Creating thread...")
        response = session.post(f"{base_url}/assistant/api/create-thread",
                               headers={'Content-Type': 'application/json'})

        if response.status_code != 200:
            logger.error(f"Failed to create thread: {response.text}")
            return False

        thread_id = response.json().get('thread_id')
        logger.info(f"Thread created: {thread_id}")

        # Send a very simple message that shouldn't trigger tools
        logger.info("Sending simple message...")
        message_data = {
            "thread_id": thread_id,
            "message": "Hello"
        }

        response = session.post(f"{base_url}/assistant/api/send-message",
                               headers={'Content-Type': 'application/json'},
                               json=message_data,
                               timeout=60)  # Longer timeout

        if response.status_code == 200:
            data = response.json()
            logger.info(f"SUCCESS: {data}")
            return True
        else:
            logger.error(f"FAILED: {response.status_code} - {response.text}")
            return False

    except requests.exceptions.Timeout:
        logger.error("Request timed out - Llama 3.2 is taking too long to respond")
        return False
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False

if __name__ == "__main__":
    logger.info("Testing simple message...")
    success = test_simple_message()

    if not success:
        logger.info("\n🔍 Troubleshooting tips:")
        logger.info("1. Check if Ollama is running: ollama list")
        logger.info("2. Check if llama3.2 model is loaded: ollama show llama3.2")
        logger.info("3. Try loading the model: ollama run llama3.2")
        logger.info("4. Check Ollama logs for errors")