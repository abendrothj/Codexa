#!/usr/bin/env python3
import argparse
import json
import sys
import httpx


def main() -> int:
    parser = argparse.ArgumentParser(description="Codexa CLI")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--api-key", default=None, help="X-API-Key header value")

    sub = parser.add_subparsers(dest="cmd", required=True)

    idx = sub.add_parser("index", help="Index files")
    idx.add_argument("files", nargs="+", help="File paths to index")
    idx.add_argument("--encrypt", action="store_true", help="Encrypt content")

    idxd = sub.add_parser("index-dir", help="Index a directory")
    idxd.add_argument("directory_path", help="Directory path to index")
    idxd.add_argument(
        "--extensions",
        nargs="*",
        default=[".md", ".py"],
        help="File extensions to include (default: .md .py)",
    )
    idxd.add_argument("--no-recursive", action="store_true", help="Do not search recursively")
    idxd.add_argument("--encrypt", action="store_true", help="Encrypt content")

    reidx = sub.add_parser("reindex", help="Reindex files")
    reidx.add_argument("files", nargs="+", help="File paths to reindex")
    reidx.add_argument("--encrypt", action="store_true", help="Encrypt content")

    sea = sub.add_parser("search", help="Search documents")
    sea.add_argument("--query", required=True, help="Search query")
    sea.add_argument("--top-k", type=int, default=10, help="Number of results")
    sea.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    sea.add_argument("--file-type", default=None, help="Filter by file type")
    sea.add_argument(
        "--filter",
        action="append",
        metavar="KEY=VALUE",
        help="Additional metadata filter (can repeat)",
    )

    dele = sub.add_parser("delete", help="Delete a document")
    dele.add_argument("document_id", help="Document ID to delete")

    web = sub.add_parser("index-web", help="Index web content")
    web.add_argument("--url", required=True, help="Source URL")
    web.add_argument("--title", required=True, help="Page title")
    web.add_argument("--content", required=True, help="Markdown content")
    web.add_argument("--tag", action="append", default=[], help="Add a tag (repeatable)")
    web.add_argument("--source", default="web", help="Source identifier")
    web.add_argument(
        "--meta",
        action="append",
        metavar="KEY=VALUE",
        default=[],
        help="Additional metadata key=value (repeatable)",
    )
    web.add_argument("--encrypt", action="store_true", help="Encrypt content")

    args = parser.parse_args()
    headers = {}
    if args.api_key:
        headers["X-API-Key"] = args.api_key

    with httpx.Client(base_url=args.base_url, headers=headers, timeout=30.0) as client:
        if args.cmd == "index":
            resp = client.post(
                "/index", json={"file_paths": args.files, "encrypt": bool(args.encrypt)}
            )
            print(resp.status_code, json.dumps(resp.json(), indent=2))
        elif args.cmd == "index-dir":
            resp = client.post(
                "/index/directory",
                json={
                    "directory_path": args.directory_path,
                    "extensions": args.extensions,
                    "recursive": not args.no_recursive,
                    "encrypt": bool(args.encrypt),
                },
            )
            print(resp.status_code, json.dumps(resp.json(), indent=2))
        elif args.cmd == "reindex":
            resp = client.post(
                "/reindex", json={"file_paths": args.files, "encrypt": bool(args.encrypt)}
            )
            print(resp.status_code, json.dumps(resp.json(), indent=2))
        elif args.cmd == "search":
            filters = {}
            if args.filter:
                for kv in args.filter:
                    if "=" in kv:
                        k, v = kv.split("=", 1)
                        filters[k] = v
            payload = {
                "query": args.query,
                "top_k": args.top_k,
                "offset": args.offset,
            }
            if args.file_type:
                payload["file_type"] = args.file_type
            if filters:
                payload["filters"] = filters
            resp = client.post("/search", json=payload)
            print(resp.status_code, json.dumps(resp.json(), indent=2))
        elif args.cmd == "delete":
            resp = client.delete(f"/documents/{args.document_id}")
            print(resp.status_code)
        elif args.cmd == "index-web":
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
            print(resp.status_code, json.dumps(resp.json(), indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())

