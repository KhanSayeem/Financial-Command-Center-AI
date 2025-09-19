#!/usr/bin/env python3
"""
Test the API directly to debug the message processing issue
"""

import requests
import json

def test_api():
    base_url = "https://127.0.0.1:8000"

    # Test create thread
    print("Testing create thread...")
    try:
        response = requests.post(f"{base_url}/assistant/api/create-thread",
                               json={},
                               verify=False)
        print(f"Create thread status: {response.status_code}")
        if response.status_code == 200:
            thread_data = response.json()
            print(f"Thread created: {thread_data}")
            thread_id = thread_data.get('thread_id')

            # Test send message
            print("\nTesting send message...")
            message_response = requests.post(f"{base_url}/assistant/api/send-message",
                                           json={
                                               "message": "hello",
                                               "thread_id": thread_id
                                           },
                                           verify=False)
            print(f"Send message status: {message_response.status_code}")
            print(f"Response: {message_response.text}")

        else:
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"Error testing API: {e}")

if __name__ == "__main__":
    test_api()