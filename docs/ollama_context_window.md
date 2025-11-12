# Ollama Context Window Configuration

## Overview

Ollama supports configurable context window sizes. The default is **4k tokens**, but you can configure it up to **256k tokens** for much better codebase understanding.

## Valid Context Window Sizes

Ollama supports the following context window sizes:
- **4096** (4k) - Default
- **8192** (8k)
- **16384** (16k)
- **32768** (32k)
- **65536** (64k)
- **131072** (128k)
- **262144** (256k) - Maximum

## How to Configure

### Method 1: Environment Variable (Recommended)

Set the `OLLAMA_NUM_CTX` environment variable before starting Ollama:

```bash
export OLLAMA_NUM_CTX=262144  # 256k tokens
ollama serve
```

Or for a specific model:
```bash
OLLAMA_NUM_CTX=262144 ollama run llama3.2
```

### Method 2: Ollama Settings

In Ollama Desktop app:
1. Go to Settings
2. Find "Context Window" or "num_ctx" setting
3. Set to desired value (e.g., 262144 for 256k)

### Method 3: Model-Specific Configuration

Create a Modelfile for your model:

```bash
# Create Modelfile
cat > Modelfile << EOF
FROM llama3.2
PARAMETER num_ctx 262144
EOF

# Create custom model
ollama create llama3.2-256k -f Modelfile
```

Then use `llama3.2-256k` as your model name in Codexa.

## Configuring Codexa

### Via Environment Variable

```bash
export CODEXA_LLM_CONTEXT_WINDOW=262144
uvicorn core.api:app --reload
```

### Via Config File

The context window is saved in `.codexa_config.json`:

```json
{
  "llm": {
    "model": "llama3.2",
    "base_url": "http://localhost:11434",
    "context_window": 262144
  }
}
```

### Via API

```bash
curl -X POST "http://localhost:8000/config/llm" \
  -H "X-API-Key: your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "context_window": 262144
  }'
```

### Via CLI

```bash
codexa llm set llama3.2 --context-window 262144
```

### Via GUI

1. Click "⚙️ Settings"
2. Go to "LLM Settings" tab
3. Select context window from dropdown
4. Click "Save Settings"

## Important Notes

⚠️ **Critical**: The context window in Codexa **must match** Ollama's `num_ctx` setting. If they don't match:
- Codexa may send more context than Ollama can handle
- Ollama may truncate or reject requests
- You may get errors or incomplete responses

### Verification

Check your current Ollama context window:
```bash
# Check Ollama environment
echo $OLLAMA_NUM_CTX

# Or check in Ollama logs when starting
ollama serve
# Look for: "num_ctx: 262144" in the logs
```

Check Codexa's configured context window:
```bash
codexa llm status
# Or
curl http://localhost:8000/config/llm
```

## Recommendations

### For Small Codebases (< 10k LOC)
- **4k-8k tokens**: Sufficient for most queries
- Fast and efficient

### For Medium Codebases (10k-100k LOC)
- **16k-32k tokens**: Good balance
- Can handle most codebase queries

### For Large Codebases (100k+ LOC)
- **64k-128k tokens**: Better coverage
- Can analyze larger code sections

### For Very Large Codebases (500k+ LOC)
- **256k tokens**: Maximum context
- Best for comprehensive analysis
- Requires more memory

## Memory Considerations

Larger context windows require more RAM:
- **4k**: ~2-4 GB RAM
- **8k**: ~4-8 GB RAM
- **16k**: ~8-16 GB RAM
- **32k**: ~16-32 GB RAM
- **64k**: ~32-64 GB RAM
- **128k**: ~64-128 GB RAM
- **256k**: ~128-256 GB RAM

Adjust based on your system's capabilities.

## Troubleshooting

### "Context window mismatch" warnings

If you see warnings about context window mismatches:
1. Check Ollama's `num_ctx`: `echo $OLLAMA_NUM_CTX`
2. Check Codexa's config: `codexa llm status`
3. Ensure they match
4. Restart both Ollama and Codexa if needed

### Out of Memory Errors

If you get OOM errors with large context windows:
- Reduce the context window size
- Close other applications
- Use a smaller model
- Consider using a machine with more RAM

### Incomplete Answers

If answers seem truncated:
- Increase context window
- Ensure Ollama's `num_ctx` matches Codexa's setting
- Check that you have enough RAM

