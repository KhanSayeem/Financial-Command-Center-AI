import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Local LLM Configuration
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")  # or "lmstudio"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")  # Default for Ollama OpenAI API
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")  # Default model

# MCP Server Configuration - Keep consistent with existing setup
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://127.0.0.1:8000")

# Safety Configuration
MAX_TURNS = 10  # Maximum number of tool call turns to prevent infinite loops

# SSL Configuration for self-signed certificates
SSL_VERIFY = False  # Set to False for self-signed certificates in development