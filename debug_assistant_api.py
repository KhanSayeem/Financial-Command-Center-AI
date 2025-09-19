#!/usr/bin/env python3
"""
Debug script to test assistant API endpoints
"""

import requests
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_assistant_endpoints():
    """Test assistant API endpoints."""
    base_url = "https://127.0.0.1:8000"

    # Disable SSL warnings for self-signed certificates
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = False

    try:
        # Test 1: Create thread
        logger.info("Testing create thread endpoint...")
        response = session.post(f"{base_url}/assistant/api/create-thread",
                               headers={'Content-Type': 'application/json'})

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Create thread successful: {data}")
            thread_id = data.get('thread_id')
        else:
            logger.error(f"✗ Create thread failed: {response.status_code} - {response.text}")
            return False

        # Test 2: Send message
        logger.info("Testing send message endpoint...")
        message_data = {
            "thread_id": thread_id,
            "message": "Hello, can you help me?"
        }

        response = session.post(f"{base_url}/assistant/api/send-message",
                               headers={'Content-Type': 'application/json'},
                               json=message_data,
                               timeout=30)

        if response.status_code == 200:
            data = response.json()
            logger.info(f"✓ Send message successful: {data}")
        else:
            logger.error(f"✗ Send message failed: {response.status_code} - {response.text}")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Test failed with exception: {e}")
        return False

def test_health_endpoint():
    """Test health endpoint."""
    base_url = "https://127.0.0.1:8000"

    session = requests.Session()
    session.verify = False

    try:
        logger.info("Testing health endpoint...")
        response = session.get(f"{base_url}/health")

        if response.status_code == 200:
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                logger.info(f"✓ Health check successful: {data}")
            else:
                logger.info("✓ Health check returned HTML (normal for browser requests)")
        else:
            logger.error(f"✗ Health check failed: {response.status_code}")

    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")

if __name__ == "__main__":
    logger.info("🔍 Debugging Assistant API Endpoints")
    logger.info("=" * 50)

    # Test health first
    test_health_endpoint()

    print()

    # Test assistant endpoints
    success = test_assistant_endpoints()

    if success:
        logger.info("\n✓ All tests passed!")
    else:
        logger.error("\n✗ Some tests failed!")