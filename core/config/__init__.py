"""Configuration management for Codexa."""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


def get_config_path() -> Path:
    """Get the path to the Codexa config file."""
    # Try project root first, then home directory
    project_root = Path.cwd()
    project_config = project_root / ".codexa_config.json"
    if project_config.exists():
        return project_config
    
    home_config = Path.home() / ".codexa_config.json"
    return home_config


def load_config() -> Dict[str, Any]:
    """Load configuration from file."""
    config_path = get_config_path()
    if not config_path.exists():
        return {}
    
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return {}


def save_config(config: Dict[str, Any]) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        logger.info(f"Configuration saved to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")
        raise


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration, checking env vars first, then config file."""
    config = load_config()
    llm_config = config.get("llm", {})
    
    # Environment variables take precedence
    model = os.getenv("CODEXA_LLM_MODEL") or llm_config.get("model", "llama3.2")
    base_url = os.getenv("OLLAMA_BASE_URL") or llm_config.get("base_url", "http://localhost:11434")
    context_window = os.getenv("CODEXA_LLM_CONTEXT_WINDOW")
    if context_window:
        context_window = int(context_window)
    else:
        context_window = llm_config.get("context_window", 4096)  # Default 4k (Ollama's default)
    
    return {
        "model": model,
        "base_url": base_url,
        "context_window": context_window,
    }


def set_llm_config(model: str, base_url: Optional[str] = None, context_window: Optional[int] = None) -> None:
    """Set LLM configuration in config file."""
    config = load_config()
    if "llm" not in config:
        config["llm"] = {}
    
    config["llm"]["model"] = model
    if base_url is not None:
        config["llm"]["base_url"] = base_url
    if context_window is not None:
        config["llm"]["context_window"] = context_window
    
    save_config(config)
    logger.info(f"LLM config updated: model={model}, base_url={base_url or 'default'}, context_window={context_window or 'default'}")


def get_api_config() -> Dict[str, Any]:
    """Get API configuration."""
    config = load_config()
    return config.get("api", {})


def set_api_config(**kwargs) -> None:
    """Set API configuration."""
    config = load_config()
    if "api" not in config:
        config["api"] = {}
    
    config["api"].update(kwargs)
    save_config(config)


def get_current_project() -> str:
    """Get current project name from config, auto-detect, or create default."""
    # Check config file first
    config = load_config()
    project = config.get("project")
    if project:
        return project
    
    # Auto-detect from git repo
    try:
        from pathlib import Path
        import subprocess
        cwd = Path.cwd()
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            repo_path = Path(result.stdout.strip())
            detected = repo_path.name
            # Save auto-detected project
            set_current_project(detected)
            return detected
    except Exception:
        pass
    
    # Fallback to directory name
    try:
        from pathlib import Path
        detected = Path.cwd().name
        if detected:
            # Save auto-detected project
            set_current_project(detected)
            return detected
    except Exception:
        pass
    
    # Last resort: create and use default project
    default_project = "default"
    logger.info(f"No project found, using default project: {default_project}")
    set_current_project(default_project)
    return default_project


def set_current_project(project: str) -> None:
    """Set current project name in config."""
    config = load_config()
    config["project"] = project
    save_config(config)
    logger.info(f"Current project set to: {project}")


def get_usage_history() -> List[Dict[str, Any]]:
    """Get context window usage history."""
    config = load_config()
    return config.get("usage_history", [])


def add_usage_entry(stats: Dict[str, Any]) -> None:
    """Add a usage entry to history (keeps last 100 entries)."""
    config = load_config()
    if "usage_history" not in config:
        config["usage_history"] = []
    
    # Add timestamp
    from datetime import datetime
    entry = {
        "timestamp": datetime.now().isoformat(),
        **stats,
    }
    
    config["usage_history"].append(entry)
    
    # Keep only last 100 entries
    if len(config["usage_history"]) > 100:
        config["usage_history"] = config["usage_history"][-100:]
    
    save_config(config)


def get_smart_recommendation() -> Optional[Dict[str, Any]]:
    """
    Generate smart recommendation based on usage history.
    
    Returns:
        Recommendation dict with size and reason, or None
    """
    history = get_usage_history()
    if len(history) < 5:
        return None  # Need more data
    
    # Analyze usage patterns
    high_usage_count = 0
    truncation_count = 0
    avg_usage = 0.0
    
    for entry in history[-20:]:  # Last 20 entries
        usage_pct = entry.get("context_usage_percent", 0)
        avg_usage += usage_pct
        if usage_pct > 90:
            high_usage_count += 1
        if entry.get("context_truncated", False):
            truncation_count += 1
    
    avg_usage /= len(history[-20:])
    
    # Get current context window
    llm_config = get_llm_config()
    current_window = llm_config.get("context_window", 4096)
    
    # Generate recommendation
    valid_sizes = [4096, 8192, 16384, 32768, 65536, 131072, 262144]
    
    # If frequently hitting limits, recommend increase
    if high_usage_count > 5 or truncation_count > 3:
        # Find next size up
        for size in valid_sizes:
            if size > current_window:
                return {
                    "size": size,
                    "reason": f"High usage detected ({high_usage_count} queries >90%, {truncation_count} truncated). "
                             f"Average usage: {avg_usage:.1f}%. Consider increasing to {size} tokens.",
                    "confidence": "high" if high_usage_count > 10 else "medium",
                }
    
    # If consistently low usage, could recommend decrease (but be conservative)
    if avg_usage < 30 and current_window > 4096:
        # Find next size down
        for size in reversed(valid_sizes):
            if size < current_window:
                return {
                    "size": size,
                    "reason": f"Low average usage ({avg_usage:.1f}%). Could reduce to {size} tokens to save memory.",
                    "confidence": "low",  # Conservative recommendation
                }
    
    return None

