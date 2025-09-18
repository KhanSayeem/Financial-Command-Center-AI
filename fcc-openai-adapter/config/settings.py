import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# OpenAI Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")

# MCP Server Configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "https://localhost:8000")

# Safety Configuration
MAX_TURNS = 10  # Maximum number of tool call turns to prevent infinite loops

# SSL Configuration for self-signed certificates
SSL_VERIFY = False  # Set to False for self-signed certificates in development