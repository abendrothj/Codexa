# Remote Access & Multi-Device Setup

This guide explains how to set up Codexa for remote access and connect from different devices.

## Overview

Codexa's API key authentication is **optional** but **recommended** for remote access. When enabled, all write and search endpoints require a valid API key.

## How API Keys Work

### Current Implementation

1. **Optional Authentication**: API keys are only enforced if `CODEXA_API_KEY` is set on the server
2. **Simple String Match**: The client sends the key in the `X-API-Key` header, and the server compares it to the environment variable
3. **All-or-Nothing**: If enabled, all protected endpoints require the key

### Protected Endpoints

When `CODEXA_API_KEY` is set, these endpoints require authentication:
- `POST /index` - Index documents
- `POST /index/directory` - Index directory
- `POST /index/web` - Index web content
- `POST /search` - Search documents
- `POST /reindex` - Reindex documents
- `DELETE /documents/{id}` - Delete document
- `POST /config/llm` - Update LLM configuration

**Unprotected endpoints** (no key required):
- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /docs` - API documentation
- `GET /config/llm` - Get LLM configuration (read-only)
- `GET /config/llm/models` - List available models (read-only)

## Setting Up Remote Access

### Step 1: Start the Server with API Key

On your **backend/server machine**:

```bash
# Set a strong API key (use a secure random string)
export CODEXA_API_KEY="your_secure_random_key_here"

# Start the server bound to all interfaces (0.0.0.0)
uvicorn core.api:app --host 0.0.0.0 --port 8000
```

**Important Security Notes:**
- Use a strong, random API key (at least 32 characters)
- Generate with: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- Never commit the key to version control
- Consider using environment files (`.env`) for production

### Step 2: Configure Firewall

Allow incoming connections on port 8000:

```bash
# Linux (ufw)
sudo ufw allow 8000/tcp

# macOS (pfctl) - add to /etc/pf.conf
# Or use System Preferences > Security & Privacy > Firewall

# Windows - configure Windows Firewall to allow port 8000
```

### Step 3: Find Your Server's IP Address

```bash
# Linux/macOS
ip addr show  # or ifconfig

# Windows
ipconfig
```

Note the IP address (e.g., `192.168.1.100` or your public IP if accessing over internet).

### Step 4: Connect from Client Device

On your **client device** (different machine):

#### Option A: Using cURL

```bash
# Set the API key as an environment variable
export CODEXA_API_KEY="your_secure_random_key_here"

# Replace SERVER_IP with your server's IP address
SERVER_IP="192.168.1.100"

# Test connection
curl -X GET "http://${SERVER_IP}:8000/health"

# Index a file
curl -X POST "http://${SERVER_IP}:8000/index" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CODEXA_API_KEY}" \
  -d '{"file_paths": ["/path/to/file.md"]}'

# Search
curl -X POST "http://${SERVER_IP}:8000/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: ${CODEXA_API_KEY}" \
  -d '{"query": "your search query", "top_k": 10}'
```

#### Option B: Using CLI

```bash
# Set environment variables
export CODEXA_API_KEY="your_secure_random_key_here"
export CODEXA_API_URL="http://192.168.1.100:8000"

# Use CLI commands normally
codexa index /path/to/file.md
codexa search "your query"
```

**Or use command-line arguments:**
```bash
codexa --base-url http://192.168.1.100:8000 --api-key "your_key" search "query"
```

#### Option C: Using Desktop GUI

The Desktop GUI reads both `CODEXA_API_KEY` and `CODEXA_API_URL` from environment variables:

```bash
# Set environment variables
export CODEXA_API_KEY="your_secure_random_key_here"
export CODEXA_API_URL="http://192.168.1.100:8000"

# Launch GUI
python desktop/__init__.py
```

The GUI will automatically connect to the remote server using the configured URL and API key.

## Security Considerations

### For Local Network Access

✅ **Safe**: Using API keys on a trusted local network (home/office LAN)
- Still recommended to use API keys to prevent unauthorized access
- Consider firewall rules to restrict access to specific IPs

### For Internet Access

⚠️ **Warning**: Exposing Codexa to the internet requires additional security:

1. **Use HTTPS**: Set up a reverse proxy (nginx, Caddy) with SSL/TLS
2. **Strong API Keys**: Use long, random keys (64+ characters)
3. **Rate Limiting**: Implement rate limiting to prevent abuse
4. **Network Security**: Use VPN or restrict to specific IPs
5. **Regular Key Rotation**: Change API keys periodically

### Example: nginx Reverse Proxy with HTTPS

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### "Invalid API key" Error

- Verify `CODEXA_API_KEY` is set on the server
- Check the key matches exactly (no extra spaces)
- Ensure you're sending it in the `X-API-Key` header

### Connection Refused

- Verify the server is running: `curl http://SERVER_IP:8000/health`
- Check firewall rules allow port 8000
- Verify the server is bound to `0.0.0.0` not just `localhost`

### CORS Issues (Browser/Extension)

If accessing from a browser extension or web app:
- The API has CORS enabled (`allow_origins=["*"]`)
- Ensure the extension sends the `X-API-Key` header
- Check browser console for CORS errors

## Future Improvements

Potential enhancements for better multi-device support:

1. ✅ **Configurable API URL**: CLI and GUI now support `CODEXA_API_URL` environment variable
2. **Multiple API Keys**: Support multiple keys with different permissions
3. **Key Management**: API endpoint to rotate/revoke keys
4. **Token-Based Auth**: JWT tokens with expiration
5. **User Management**: Multi-user support with per-user keys
6. **HTTPS Support**: Built-in SSL/TLS support
7. **GUI Settings**: Add a settings dialog in the GUI to configure API URL without environment variables

## Example: Production Setup

```bash
# Server (backend)
export CODEXA_API_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
export CODEXA_KEY_PATH="/secure/path/to/key.bin"
export CODEXA_LOG_LEVEL="INFO"

# Run as a service (systemd example)
# /etc/systemd/system/codexa.service
[Unit]
Description=Codexa API Server
After=network.target

[Service]
Type=simple
User=codexa
Environment="CODEXA_API_KEY=your_key_here"
ExecStart=/path/to/venv/bin/uvicorn core.api:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Client (different device)
export CODEXA_API_KEY="same_key_as_server"
export CODEXA_API_URL="https://your-domain.com"  # If using HTTPS

codexa search "query"
```

