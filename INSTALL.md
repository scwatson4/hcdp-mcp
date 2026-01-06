# HCDP MCP Server Installation Guide

## Quick Installation

```bash
# Clone and install
git clone https://github.com/yourusername/hcdp-mcp.git
cd hcdp-mcp
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your HCDP API token
```

## Detailed Installation Steps

### 1. System Requirements

- **Python 3.9+** (Python 3.11+ recommended)
- **pip** package manager
- **HCDP API Token** (get from [hcdp.ikewai.org](https://www.hcdp.ikewai.org/))

### 2. Get HCDP API Token

1. Visit https://www.hcdp.ikewai.org/
2. Create account or sign in
3. Navigate to Profile → API Keys
4. Generate new API token
5. Copy the token (you'll need it for configuration)

### 3. Install Python Package

**Option A: Development Installation (Recommended)**
```bash
git clone https://github.com/yourusername/hcdp-mcp.git
cd hcdp-mcp
pip install -e .
```

**Option B: PyPI Installation (When available)**
```bash
pip install hcdp-mcp-server
```

**Option C: Direct from GitHub**
```bash
pip install git+https://github.com/yourusername/hcdp-mcp.git
```

### 4. Configure Environment

Create `.env` file in the project directory:

```bash
cp .env.example .env
```

Edit `.env` with your API token:
```bash
HCDP_API_TOKEN=your_actual_token_here
HCDP_BASE_URL=https://api.hcdp.ikewai.org
```

### 5. Verify Installation

Test the MCP server:
```bash
hcdp-mcp-server
```

You should see the server start and wait for connections.

## Desktop Application Setup

### Claude Code

1. **Find your Claude Code configuration directory:**
   - macOS: `~/.claude/`
   - Windows: `%APPDATA%/Claude/`
   - Linux: `~/.claude/`

2. **Create/edit `mcp_servers.json`:**
   ```json
   {
     "mcpServers": {
       "hcdp": {
         "command": "hcdp-mcp-server",
         "env": {
           "HCDP_API_TOKEN": "your_token_here"
         }
       }
     }
   }
   ```

3. **Alternative: Use working directory approach:**
   ```json
   {
     "mcpServers": {
       "hcdp": {
         "command": "hcdp-mcp-server",
         "cwd": "/path/to/hcdp-mcp"
       }
     }
   }
   ```

4. **Restart Claude Code**

### Cursor

1. **Create MCP configuration file:**
   
   **Project-level:** Create `.cursor/mcp_servers.json` in your project
   ```json
   {
     "mcpServers": {
       "hcdp-climate-data": {
         "command": "hcdp-mcp-server",
         "env": {
           "HCDP_API_TOKEN": "your_token_here"
         }
       }
     }
   }
   ```

   **Global configuration:** Add to Cursor global settings

2. **Restart Cursor**

### Visual Studio Code

1. **Install MCP extension** (if available)

2. **Add to `settings.json`:**
   ```json
   {
     "mcp.servers": {
       "hcdp": {
         "command": "hcdp-mcp-server",
         "env": {
           "HCDP_API_TOKEN": "your_token_here"
         }
       }
     }
   }
   ```

## Troubleshooting Installation

### Common Issues

**1. Python Version Error**
```bash
# Check Python version
python --version
# Should be 3.9+

# If using older version, install newer Python
# Or use python3 specifically
python3 -m pip install -e .
```

**2. Package Not Found**
```bash
# Verify installation
pip list | grep hcdp

# If not found, try:
pip install -e . --force-reinstall
```

**3. Command Not Found: hcdp-mcp-server**
```bash
# Check if it's in PATH
which hcdp-mcp-server

# Try running directly
python -m hcdp_mcp_server.server

# Or add to PATH (add to your shell config):
export PATH="$PATH:$(python -m site --user-base)/bin"
```

**4. Permission Errors**
```bash
# Use --user flag for user installation
pip install --user -e .

# Or use virtual environment
python -m venv hcdp-env
source hcdp-env/bin/activate  # Linux/Mac
# hcdp-env\Scripts\activate   # Windows
pip install -e .
```

**5. MCP Server Connection Issues**

Check that the server starts correctly:
```bash
# Test server startup
hcdp-mcp-server
# Should show: Server running...

# Test with verbose output
HCDP_DEBUG=true hcdp-mcp-server
```

**6. API Token Issues**
```bash
# Verify token is loaded
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Token loaded:', bool(os.getenv('HCDP_API_TOKEN')))"

# Test API access
curl -H "Authorization: Bearer YOUR_TOKEN" "https://api.hcdp.ikewai.org/stations?q={}&limit=1"
```

### Environment-Specific Setup

**Windows:**
```powershell
# Use PowerShell
git clone https://github.com/yourusername/hcdp-mcp.git
cd hcdp-mcp
python -m pip install -e .

# Set environment variable
$env:HCDP_API_TOKEN="your_token_here"
```

**macOS:**
```bash
# Install with Homebrew Python if needed
brew install python@3.11

# Then follow standard installation
pip3 install -e .
```

**Linux (Ubuntu/Debian):**
```bash
# Install Python development tools
sudo apt update
sudo apt install python3-dev python3-pip python3-venv

# Continue with standard installation
pip3 install -e .
```

## Development Installation

For developers wanting to contribute or modify the code:

```bash
# Clone repository
git clone https://github.com/yourusername/hcdp-mcp.git
cd hcdp-mcp

# Install with development dependencies
pip install -e ".[dev]"

# Verify development setup
pytest  # Run tests
black hcdp_mcp_server/  # Format code
ruff check hcdp_mcp_server/  # Lint code
```

## Verification

After installation, verify everything works:

```bash
# 1. Check package installation
pip show hcdp-mcp-server

# 2. Test MCP server startup
hcdp-mcp-server &
# Should start without errors

# 3. Test API connectivity (in another terminal)
python -c "
import asyncio
from hcdp_mcp_server.client import HCDPClient

async def test():
    client = HCDPClient()
    print('API configured:', bool(client.api_token))
    print('Base URL:', client.base_url)

asyncio.run(test())
"

# 4. Test in your AI assistant
# Ask: "Are there any HCDP tools available?"
```

If all steps complete successfully, the HCDP MCP server is ready to use!