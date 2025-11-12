#!/usr/bin/env python3
"""Codexa CLI - Simplified, intuitive interface for your knowledge vault."""

import argparse
import json
import os
import sys
import httpx
from pathlib import Path

# Import config functions
try:
    from core.config import set_llm_config, get_llm_config, get_config_path, get_current_project, set_current_project
except ImportError:
    # Fallback if running outside package context
    set_llm_config = None
    get_llm_config = None
    get_config_path = None
    get_current_project = None
    set_current_project = None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Codexa - Local-first AI knowledge vault",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  codexa s "how to use encryption"          # Search with AI answer
  codexa i file.md                          # Index a file
  codexa i-dir ./docs                       # Index directory
  codexa project create myproject           # Create a new project
  codexa project list                       # List all projects
  codexa llm list                           # List available Ollama models
  codexa llm set llama3.2                   # Set LLM model
        """
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("CODEXA_API_URL", "http://localhost:8000"),
        help="API base URL (default: CODEXA_API_URL env var or http://localhost:8000)"
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("CODEXA_API_KEY"),
        help="X-API-Key header value (default: CODEXA_API_KEY env var)"
    )

    sub = parser.add_subparsers(dest="cmd", required=True)

    # Short aliases for common commands
    idx = sub.add_parser("index", aliases=["i"], help="Index files")
    idx.add_argument("files", nargs="+", help="File paths to index")
    idx.add_argument("-e", "--encrypt", action="store_true", help="Encrypt content")
    idx.add_argument("-p", "--project", default=None, help="Project/workspace name (auto-detected if not set)")

    idxd = sub.add_parser("index-dir", aliases=["i-dir", "dir"], help="Index a directory")
    idxd.add_argument("directory_path", help="Directory path to index")
    idxd.add_argument(
        "-e", "--extensions",
        nargs="*",
        default=[".md", ".py"],
        help="File extensions (default: .md .py)",
    )
    idxd.add_argument("--no-recursive", action="store_true", help="Don't search recursively")
    idxd.add_argument("--encrypt", action="store_true", help="Encrypt content")
    idxd.add_argument("-p", "--project", default=None, help="Project/workspace name (auto-detected if not set)")

    reidx = sub.add_parser("reindex", aliases=["ri"], help="Reindex files")
    reidx.add_argument("files", nargs="+", help="File paths to reindex")
    reidx.add_argument("-e", "--encrypt", action="store_true", help="Encrypt content")

    sea = sub.add_parser("search", aliases=["s"], help="Search documents (AI answers enabled by default)")
    sea.add_argument("query", nargs="?", help="Search query")
    sea.add_argument("-k", "--top-k", type=int, default=10, help="Number of results")
    sea.add_argument("-o", "--offset", type=int, default=0, help="Offset for pagination")
    sea.add_argument("-t", "--file-type", default=None, help="Filter by file type")
    sea.add_argument(
        "-f", "--filter",
        action="append",
        metavar="KEY=VALUE",
        help="Metadata filter (repeatable)",
    )
    sea.add_argument(
        "-p", "--project",
        default=None,
        help="Filter by project (default: current project)",
    )
    sea.add_argument(
        "--no-answer",
        action="store_true",
        help="Disable AI answer generation",
    )

    dele = sub.add_parser("delete", aliases=["d", "del"], help="Delete documents")
    dele_sub = dele.add_subparsers(dest="delete_type", required=True)
    
    dele_id = dele_sub.add_parser("id", help="Delete by document ID")
    dele_id.add_argument("document_id", help="Document ID to delete")
    
    dele_file = dele_sub.add_parser("file", aliases=["f"], help="Delete by file path")
    dele_file.add_argument("file_path", help="File path to delete")
    
    dele_dir = dele_sub.add_parser("dir", aliases=["directory", "d"], help="Delete by directory (recursive)")
    dele_dir.add_argument("directory_path", help="Directory path to delete")
    dele_dir.add_argument("--no-recursive", action="store_true", help="Don't delete files in subdirectories")

    web = sub.add_parser("index-web", aliases=["web", "w"], help="Index web content")
    web.add_argument("--url", required=True, help="Source URL")
    web.add_argument("--title", required=True, help="Page title")
    web.add_argument("--content", required=True, help="Markdown content")
    web.add_argument("--tag", action="append", default=[], help="Add a tag (repeatable)")
    web.add_argument("--meta", action="append", metavar="KEY=VALUE", default=[], help="Metadata (repeatable)")
    web.add_argument("-e", "--encrypt", action="store_true", help="Encrypt content")

    # LLM configuration commands
    llm_parser = sub.add_parser("llm", help="Configure Ollama LLM")
    llm_sub = llm_parser.add_subparsers(dest="llm_cmd", required=True)
    
    llm_list = llm_sub.add_parser("list", aliases=["ls"], help="List available Ollama models")
    
    llm_set = llm_sub.add_parser("set", aliases=["use"], help="Set LLM model and context window")
    llm_set.add_argument("model", help="Model name (e.g., llama3.2)")
    llm_set.add_argument(
        "--context-window",
        type=int,
        choices=[4096, 8192, 16384, 32768, 65536, 131072, 262144],
        help="Context window size in tokens (must match Ollama's num_ctx). "
             "Valid options: 4096, 8192, 16384, 32768, 65536, 131072, 262144. "
             "Default: 4096. Configure Ollama via OLLAMA_NUM_CTX environment variable."
    )
    
    llm_status = llm_sub.add_parser("status", aliases=["info"], help="Show LLM status")
    
    llm_test = llm_sub.add_parser("test", help="Test LLM connection")
    
    llm_test_ctx = llm_sub.add_parser("test-context", aliases=["test-ctx"], help="Test context window configuration")
    llm_test_ctx.add_argument(
        "--context-window",
        type=int,
        choices=[4096, 8192, 16384, 32768, 65536, 131072, 262144],
        help="Context window size to test (default: current config)"
    )

    # Project management commands
    proj_parser = sub.add_parser("project", aliases=["proj", "p"], help="Manage project/workspace")
    proj_sub = proj_parser.add_subparsers(dest="proj_cmd", required=True)
    
    proj_create = proj_sub.add_parser("create", aliases=["new", "add"], help="Create a new project")
    proj_create.add_argument("name", help="Project name")
    
    proj_set = proj_sub.add_parser("set", help="Set current project")
    proj_set.add_argument("name", help="Project name")
    
    proj_get = proj_sub.add_parser("get", aliases=["current"], help="Show current project")
    
    proj_list = proj_sub.add_parser("list", aliases=["ls"], help="List all projects (from indexed documents)")

    args = parser.parse_args()
    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    with httpx.Client(base_url=args.base_url, headers=headers, timeout=30.0) as client:
        if args.cmd in ["index", "i"]:
            abs_files = [os.path.abspath(f) for f in args.files]
            payload = {"file_paths": abs_files, "encrypt": bool(args.encrypt)}
            if args.project is not None:
                payload["project"] = args.project
            resp = client.post("/index", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Indexed {data.get('indexed_count', 0)} file(s)")
                if data.get("failed_count", 0) > 0:
                    print(f"⚠️  {data.get('failed_count')} file(s) failed")
            else:
                print(f"❌ Error: {resp.status_code}")
                print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd in ["index-dir", "i-dir", "dir"]:
            abs_dir = os.path.abspath(args.directory_path)
            payload = {
                "directory_path": abs_dir,
                "extensions": args.extensions,
                "recursive": not args.no_recursive,
                "encrypt": bool(args.encrypt),
            }
            if args.project is not None:
                payload["project"] = args.project
            resp = client.post("/index/directory", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Indexed {data.get('indexed_count', 0)} file(s)")
                if data.get("failed_count", 0) > 0:
                    print(f"⚠️  {data.get('failed_count')} file(s) failed")
            else:
                print(f"❌ Error: {resp.status_code}")
                print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd in ["reindex", "ri"]:
            abs_files = [os.path.abspath(f) for f in args.files]
            resp = client.post("/reindex", json={"file_paths": abs_files, "encrypt": bool(args.encrypt)})
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Reindexed {data.get('indexed_count', 0)} file(s)")
            else:
                print(f"❌ Error: {resp.status_code}")
                print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd in ["search", "s"]:
            query = args.query
            if not query:
                print("❌ Error: Query required. Use: codexa s 'your query'")
                return 1
                
            filters = {}
            if args.filter:
                for kv in args.filter:
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        filters[k] = v
            payload = {
                "query": query,
                "top_k": args.top_k,
                "offset": args.offset,
                "generate_answer": not args.no_answer,  # Default to True
            }
            if args.file_type:
                payload["file_type"] = args.file_type
            if filters:
                payload["filters"] = filters
            # Handle project filter (mandatory - always uses a project)
            if args.project is not None:
                payload["project"] = args.project
            # If not specified, API will use current project from config (always returns a project)
            resp = client.post("/search", json=payload)
            
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                total = data.get("total_results", 0)
                answer = data.get("answer")
                
                # Show answer first if generated
                if answer:
                    print(f"\n🤖 AI Answer:\n")
                    print("─" * 80)
                    # Word wrap the answer
                    words = answer.split()
                    line = ""
                    for word in words:
                        if len(line + word) > 76:
                            print(f"  {line}")
                            line = word + " "
                        else:
                            line += word + " "
                    if line:
                        print(f"  {line}")
                    print("─" * 80)
                    print()
                
                if total == 0:
                    print(f"📭 No results found for: '{query}'")
                else:
                    print(f"🔍 Found {total} result(s):\n")
                    for idx, result in enumerate(results, 1):
                        score = result.get("score", 0.0)
                        file_path = result.get("file_path", "Unknown")
                        file_type = result.get("file_type", "")
                        content = result.get("content", "")
                        
                        # Truncate content for display
                        max_content_len = 200
                        content_preview = content[:max_content_len]
                        if len(content) > max_content_len:
                            content_preview += "..."
                        
                        score_pct = f"{score * 100:.0f}%"
                        print(f"  [{idx}] {file_path} ({file_type}) - {score_pct}")
                        print(f"      {content_preview.replace(chr(10), ' ')}")
                        print()
            else:
                print(f"❌ Error: {resp.status_code}")
                print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd in ["delete", "d", "del"]:
            if args.delete_type == "id":
                resp = client.delete(f"/documents/{args.document_id}")
                if resp.status_code == 204:
                    print(f"✅ Deleted document {args.document_id[:8]}...")
                else:
                    print(f"❌ Error: {resp.status_code}")
                    if resp.status_code != 204:
                        try:
                            print(json.dumps(resp.json(), indent=2))
                        except:
                            print(resp.text)
            elif args.delete_type in ["file", "f"]:
                abs_file_path = os.path.abspath(args.file_path)
                resp = client.delete("/documents/file", json={"file_path": abs_file_path})
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ {data.get('message', 'Deleted')}")
                else:
                    print(f"❌ Error: {resp.status_code}")
                    print(json.dumps(resp.json(), indent=2))
            elif args.delete_type in ["dir", "directory", "d"]:
                abs_dir_path = os.path.abspath(args.directory_path)
                resp = client.delete(
                    "/documents/directory",
                    json={"directory_path": abs_dir_path, "recursive": not args.no_recursive}
                )
                if resp.status_code == 200:
                    data = resp.json()
                    print(f"✅ {data.get('message', 'Deleted')}")
                else:
                    print(f"❌ Error: {resp.status_code}")
                    print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd in ["index-web", "web", "w"]:
            metadata = {}
            for item in args.meta:
                if "=" in item:
                    k, v = item.split("=", 1)
                    metadata[k] = v
            payload = {
                "url": args.url,
                "title": args.title,
                "content": args.content,
                "tags": args.tag,
                "source": args.source,
                "metadata": metadata,
                "encrypt": bool(args.encrypt),
            }
            resp = client.post("/index/web", json=payload)
            if resp.status_code == 201:
                data = resp.json()
                print(f"✅ Indexed web content: {data.get('document_id', 'N/A')[:8]}...")
            else:
                print(f"❌ Error: {resp.status_code}")
                print(json.dumps(resp.json(), indent=2))
                
        elif args.cmd == "llm":
            if args.llm_cmd in ["list", "ls"]:
                # Call Ollama API directly - use config if available
                if get_llm_config:
                    config = get_llm_config()
                    ollama_url = config.get("base_url", "http://localhost:11434")
                else:
                    ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                try:
                    ollama_client = httpx.Client(base_url=ollama_url, timeout=5.0)
                    resp = ollama_client.get("/api/tags")
                    if resp.status_code == 200:
                        models = resp.json().get("models", [])
                        if models:
                            print("📦 Available Ollama models:")
                            for model in models:
                                name = model.get("name", "")
                                size = model.get("size", 0)
                                size_gb = size / (1024**3) if size else 0
                                print(f"  • {name} ({size_gb:.1f} GB)")
                        else:
                            print("📦 No models installed. Run: ollama pull llama3.2")
                    else:
                        print(f"❌ Error connecting to Ollama: {resp.status_code}")
                        print("Make sure Ollama is running: ollama serve")
                except Exception as e:
                    print(f"❌ Error: {e}")
                    print("Make sure Ollama is running: ollama serve")
                    
            elif args.llm_cmd in ["set", "use"]:
                # Set via config file and API
                model = args.model
                
                # First, show available models to help user
                try:
                    resp = client.get("/config/llm/models")
                    if resp.status_code == 200:
                        models_data = resp.json()
                        available = models_data.get("models", [])
                        if available:
                            print("📦 Available models:")
                            for m in available[:10]:  # Show first 10
                                name = m.get("name", "")
                                size = m.get("size_gb", 0)
                                marker = " ← " if name == model or name.startswith(f"{model}:") else ""
                                print(f"  {marker}• {name} ({size} GB)")
                            if len(available) > 10:
                                print(f"  ... and {len(available) - 10} more")
                            print()
                except Exception:
                    pass  # Silently fail - just continue
                
                try:
                    # Prepare payload
                    payload = {"model": model}
                    if args.context_window:
                        payload["context_window"] = args.context_window
                    
                    # Save to config file
                    if set_llm_config:
                        set_llm_config(model, None, args.context_window)
                        print(f"✅ Saved model '{model}' to config file")
                        if args.context_window:
                            print(f"✅ Saved context window: {args.context_window} tokens")
                    else:
                        print(f"⚠️  Config module not available, using API only")
                    
                    # Update via API if server is running
                    try:
                        resp = client.post("/config/llm", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            resolved_model = data.get("model", model)
                            if data.get("available"):
                                if resolved_model != model:
                                    print(f"✅ LLM updated and active: {resolved_model} (resolved from {model})")
                                else:
                                    print(f"✅ LLM updated and active: {model}")
                            else:
                                print(f"⚠️  LLM updated but not available. Make sure Ollama is running: ollama serve")
                                if resolved_model != model:
                                    print(f"   Model resolved to: {resolved_model}")
                                else:
                                    print(f"   Install model: ollama pull {model}")
                        else:
                            print(f"⚠️  Config saved, but API update failed: {resp.status_code}")
                            print(f"   Restart the API server to apply changes")
                    except httpx.ConnectError:
                        print(f"✅ Config saved to file")
                        print(f"⚠️  API server not running - restart it to apply changes")
                    except Exception as e:
                        print(f"✅ Config saved to file")
                        print(f"⚠️  API update failed: {e}")
                    
                    print(f"\n💡 Make sure the model is installed: ollama pull {model}")
                except Exception as e:
                    print(f"❌ Error: {e}")
                
            elif args.llm_cmd in ["status", "info"]:
                # Check LLM status via API and config file
                try:
                    # Get from config file
                    if get_llm_config:
                        config = get_llm_config()
                        config_path = get_config_path()
                        print(f"📁 Config file: {config_path}")
                        print(f"📦 Model: {config['model']}")
                        print(f"🔗 Base URL: {config['base_url']}")
                    
                    # Check API
                    resp = client.get("/config/llm")
                    if resp.status_code == 200:
                        data = resp.json()
                        api_model = data.get('model', 'N/A')
                        config_model = config.get('model', 'N/A') if get_llm_config else 'N/A'
                        print(f"\n🌐 API Status:")
                        print(f"   Model: {api_model}")
                        print(f"   Context Window: {data.get('context_window', 4096)} tokens")
                        if api_model != config_model and config_model != 'N/A':
                            print(f"   (Resolved from: {config_model})")
                        print(f"   Base URL: {data.get('base_url', 'N/A')}")
                        if data.get("available"):
                            print(f"   Status: ✅ Available")
                        else:
                            print(f"   Status: ⚠️  Not available")
                    else:
                        print(f"\n⚠️  API not responding: {resp.status_code}")
                    
                    # Check Ollama directly
                    config = get_llm_config() if get_llm_config else {"base_url": "http://localhost:11434"}
                    ollama_url = config.get("base_url", "http://localhost:11434")
                    try:
                        ollama_client = httpx.Client(base_url=ollama_url, timeout=2.0)
                        ollama_resp = ollama_client.get("/api/tags")
                        if ollama_resp.status_code == 200:
                            print(f"\n🦙 Ollama: ✅ Running at {ollama_url}")
                        else:
                            print(f"\n🦙 Ollama: ⚠️  Not responding at {ollama_url}")
                    except Exception as e:
                        print(f"\n🦙 Ollama: ❌ Connection failed - {e}")
                        print(f"   Make sure Ollama is running: ollama serve")
                except httpx.ConnectError:
                    print("❌ API server not running")
                    if get_llm_config:
                        config = get_llm_config()
                        print(f"📦 Config file shows: {config['model']} at {config['base_url']}")
                        print(f"📏 Context Window: {config.get('context_window', 4096)} tokens")
                        print(f"⚠️  Note: Ensure Ollama's num_ctx is set to {config.get('context_window', 4096)}")
                        print(f"   Valid options: 4096, 8192, 16384, 32768, 65536, 131072, 262144")
                        print(f"   Configure via: OLLAMA_NUM_CTX={config.get('context_window', 4096)}")
                except Exception as e:
                    print(f"⚠️  Error: {e}")
                    
            elif args.llm_cmd == "test":
                # Test LLM by making a search request
                try:
                    resp = client.post("/search", json={"query": "test", "top_k": 1, "generate_answer": True})
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("answer"):
                            print("✅ LLM connection test passed!")
                            print(f"   Answer preview: {data['answer'][:100]}...")
                            if "answer_stats" in data:
                                stats = data["answer_stats"]
                                print(f"   Context usage: {stats.get('context_usage_percent', 0):.1f}%")
                                print(f"   Total tokens: {stats.get('total_tokens', 0):,}")
                        else:
                            print("⚠️  LLM responded but no answer generated")
                    else:
                        print(f"❌ Test failed: {resp.status_code}")
                except Exception as e:
                    print(f"❌ Test error: {e}")
            
            elif args.llm_cmd in ["test-context", "test-ctx"]:
                # Test context window configuration
                try:
                    config = get_llm_config() if get_llm_config else {}
                    payload = {
                        "model": config.get("model", "llama3.2"),
                        "base_url": config.get("base_url", "http://localhost:11434"),
                    }
                    if args.context_window:
                        payload["context_window"] = args.context_window
                    
                    resp = client.post("/config/llm/test", json=payload)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("validated"):
                            print("✅ Context window test passed!")
                            print(f"   Model: {data.get('model')}")
                            print(f"   Context Window: {data.get('context_window')} tokens")
                            if data.get("detected_context_window"):
                                if data["detected_context_window"] == data["context_window"]:
                                    print(f"   ✅ Detected Ollama: {data['detected_context_window']} (matches)")
                                else:
                                    print(f"   ⚠️  Detected Ollama: {data['detected_context_window']} (mismatch!)")
                            if "test_stats" in data:
                                stats = data["test_stats"]
                                print(f"   Usage: {stats.get('context_usage_percent', 0):.1f}%")
                                print(f"   Tokens: {stats.get('total_tokens', 0):,}")
                        else:
                            print(f"❌ Test failed: {data.get('message', 'Unknown error')}")
                    else:
                        print(f"❌ API error: {resp.status_code}")
                except Exception as e:
                    print(f"❌ Test error: {e}")
            
                    
        elif args.cmd in ["project", "proj", "p"]:
            if args.proj_cmd in ["create", "new", "add"]:
                project_name = args.name
                if set_current_project:
                    set_current_project(project_name)
                    print(f"✅ Project '{project_name}' created and set as current")
                    print(f"💡 Documents indexed without --project will use this project")
                else:
                    print(f"✅ Project '{project_name}' created (config module not available)")
                    print(f"💡 Use --project flag when indexing: codexa i --project {project_name} <files>")
                    
            elif args.proj_cmd == "set":
                if set_current_project:
                    set_current_project(args.name)
                    print(f"✅ Current project set to: {args.name}")
                    print(f"💡 Documents indexed without --project will use this project")
                else:
                    print("❌ Config module not available")
                    
            elif args.proj_cmd in ["get", "current"]:
                if get_current_project:
                    project = get_current_project()
                    print(f"📦 Current project: {project}")
                    print(f"💡 Documents indexed without --project will use this project")
                else:
                    print("❌ Config module not available")
                    
            elif args.proj_cmd in ["list", "ls"]:
                # Search for all unique projects
                try:
                    resp = client.post("/search", json={"query": "", "top_k": 1000, "generate_answer": False})
                    if resp.status_code == 200:
                        data = resp.json()
                        results = data.get("results", [])
                        projects = set()
                        for result in results:
                            project = result.get("metadata", {}).get("project")
                            if project:
                                projects.add(project)
                        if projects:
                            print("📦 Projects found in knowledge vault:")
                            for proj in sorted(projects):
                                current_marker = ""
                                if get_current_project:
                                    current = get_current_project()
                                    if current == proj:
                                        current_marker = " (current)"
                                print(f"  • {proj}{current_marker}")
                        else:
                            print("📦 No projects found yet")
                            if get_current_project:
                                current = get_current_project()
                                print(f"💡 Current project: {current}")
                            print("💡 Create a project: codexa project create <name>")
                    else:
                        print(f"❌ Error: {resp.status_code}")
                except Exception as e:
                    print(f"❌ Error: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
