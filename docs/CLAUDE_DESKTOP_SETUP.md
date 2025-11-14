# Claude Desktop MCP Configuration Guide

## 🎯 **How Path Detection Works**

Your Financial Command Center automatically detects your specific setup and generates a Claude Desktop configuration tailored to YOUR environment.

## 🔍 **What Gets Detected**

### **Python Executable Detection**
The system checks for Python in this order:
1. **`.venv\Scripts\python.exe`** (Windows virtual environment)
2. **`.venv\bin\python`** (Mac/Linux virtual environment) 
3. **`venv\Scripts\python.exe`** (Alternative Windows venv)
4. **`venv\bin\python`** (Alternative Mac/Linux venv)
5. **`python`** (System Python fallback)
6. **`python3`** (System Python3 fallback)

### **Project Directory Detection**
- Uses the directory where you're running Financial Command Center
- All MCP server script paths are relative to this directory
- Automatically finds `mcp_server.py`, `stripe_mcp.py`, etc.

## 💻 **Example Configurations for Different Users**

### **User 1: Windows with Virtual Environment**
```json
{
  "mcpServers": {
    "financial-command-center": {
      "command": "C:\\Users\\Alice\\Documents\\Financial-Command-Center-AI\\.venv\\Scripts\\python.exe",
      "args": ["C:\\Users\\Alice\\Documents\\Financial-Command-Center-AI\\mcp_server.py"]
    }
  }
}
```

### **User 2: Mac with Virtual Environment**
```json
{
  "mcpServers": {
    "financial-command-center": {
      "command": "/Users/bob/projects/Financial-Command-Center-AI/.venv/bin/python",
      "args": ["/Users/bob/projects/Financial-Command-Center-AI/mcp_server.py"]
    }
  }
}
```

### **User 3: Linux with System Python**
```json
{
  "mcpServers": {
    "financial-command-center": {
      "command": "python3",
      "args": ["/home/charlie/Financial-Command-Center-AI/mcp_server.py"]
    }
  }
}
```

## 📋 **Setup Instructions for Different Users**

### **For Individual Users**
1. **Clone/download** Financial Command Center to your preferred directory
2. **Run setup**: `ultimate_cert_fix.cmd` (Windows) or `python app_with_setup_wizard.py` (Mac/Linux)
3. **Configure credentials** in the web UI setup wizard
4. **Generate config**: Visit `https://127.0.0.1:8000/claude/setup`
5. **Close Claude Desktop completely** (Task Manager → “End task” on Windows, Force Quit / Activity Monitor on macOS)
6. **Click “Connect automatically”** so FCC writes the JSON to the Claude Desktop folder (a backup is created automatically)
7. **Download** a copy if you want to store the JSON elsewhere

### **For Teams/Organizations**
Each team member should:

1. **Get their own copy** of the Financial Command Center codebase
2. **Install in their preferred location** (their Documents folder, project directory, etc.)
3. **Run their own setup** with shared credentials or individual accounts
4. **Generate their own Claude config** - paths will be customized for their system
5. **Quit Claude Desktop before connecting** (Task Manager / Activity Monitor) to avoid locked files
6. **Use “Connect automatically”** so FCC writes to `%APPDATA%\Claude` on Windows or `~/Library/Application Support/Claude` on macOS
7. **Never share config files** - they contain hardcoded paths specific to each person

## 🔧 **Troubleshooting Path Issues**

### **"Python executable not found"**
1. **Check Python installation**: Ensure Python 3.8+ is installed
2. **Virtual environment**: Run `python -m venv .venv` in project directory
3. **Regenerate config**: Delete old config and generate new one
4. **Manual path**: Edit config file and update Python path manually

### **"MCP server scripts not found"**
1. **Check project directory**: Ensure all `.py` files are present
2. **Correct location**: Make sure you're in the right project folder
3. **File permissions**: Ensure scripts are readable
4. **Reconnect automatically**: Click “Generate config” then “Connect automatically” to ensure Claude’s folder is in sync

### **"Config works on my machine but not others"**
This is expected! Each user needs their own config because:
- **Different operating systems** (Windows vs Mac vs Linux)
- **Different directory structures** (C:\Users\Alice vs /Users/bob)
- **Different Python installations** (venv vs system vs conda)
- **Different project locations** (Documents vs Desktop vs custom folder)

## 🚀 **Best Practices**

### **For Individual Use**
- ✅ Generate config from your actual project directory
- ✅ Close Claude Desktop first, then use “Connect automatically” for the one-click copy (backups are created for you)
- ✅ Test with a simple command first: "What's our financial health?"
- ✅ Keep your project in a stable location (don't move folders after setup)

### **For Team Use**
- ✅ Share the project code, not the config files
- ✅ Document your team's preferred project location
- ✅ Remind teammates to quit Claude Desktop first, then click “Connect automatically”
- ✅ Include setup instructions in team documentation

### **For Client Deployment**
- ✅ Provide setup script that generates config automatically
- ✅ Include path verification steps
- ✅ Demonstrate the one-click connect on a clean machine before delivery
- ✅ Document fallback to system Python if needed

## 📞 **Getting Help**

If you're having path-related issues:

1. **Check the generated config** - open `claude_desktop_config.json` and verify paths exist
2. **Test Python path** - run the Python executable path from command line
3. **Test script paths** - ensure you can find the `.py` files in your project
4. **Regenerate if needed** - delete config and generate fresh one
5. **Use absolute paths** - edit config manually if automatic detection fails

## 🎉 **Success Indicators**

You'll know it's working when:
- ✅ Claude Desktop shows "Financial Command Center" in available tools
- ✅ You can ask: "Show me our financial health" and get a response
- ✅ No error messages about missing files or Python executables
- ✅ All 5 MCP servers (financial, stripe, xero, plaid, compliance) are available

Your configuration is **customized for YOUR setup** - and that's exactly how it should be! 🎊
