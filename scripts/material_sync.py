#!/usr/bin/env python3
"""Operate the portable material panel's ChatCut sync queue."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def default_root() -> Path:
    configured = os.environ.get("CHATCUT_MATERIAL_ROOT")
    if configured:
        return Path(configured).expanduser()
    config_path = Path.home() / ".codex" / "chatcut-hyperframes" / "config.json"
    if config_path.exists():
        try:
            payload = json.loads(config_path.read_text(encoding="utf-8"))
            if payload.get("materialRoot"):
                return Path(payload["materialRoot"]).expanduser()
        except (OSError, json.JSONDecodeError):
            pass
    return Path.home() / "ChatCutMaterials"


def queue_path(root: Path) -> Path:
    return root / "data" / "chatcut-sync.json"


def read_queue(root: Path) -> dict:
    path = queue_path(root)
    if not path.exists():
        return {"version": 1, "type": "chatcut-material-sync", "updatedAt": now_iso(), "requests": [], "assets": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def write_queue(root: Path, payload: dict) -> None:
    path = queue_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload["updatedAt"] = now_iso()
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def find_request(payload: dict, request_id: str) -> dict:
    for request in payload.get("requests", []):
        if request.get("id") == request_id:
            return request
    raise SystemExit(f"Unknown request id: {request_id}")


def refresh_status(request: dict) -> None:
    statuses = [item.get("status", "queued") for item in request.get("items", [])]
    if statuses and all(status == "imported" for status in statuses):
        request["status"] = "completed"
    elif any(status == "failed" for status in statuses):
        request["status"] = "partial"
    elif any(status == "syncing" for status in statuses):
        request["status"] = "syncing"
    else:
        request["status"] = "queued"
    request["updatedAt"] = now_iso()


def command_next(args: argparse.Namespace, payload: dict) -> None:
    requests = [request for request in payload.get("requests", []) if request.get("status") in {"queued", "partial"}]
    requests.sort(key=lambda request: request.get("createdAt", ""), reverse=args.latest)
    print(json.dumps(requests[0] if requests else None, ensure_ascii=False, indent=2))


def command_claim(args: argparse.Namespace, payload: dict, root: Path) -> None:
    request = find_request(payload, args.request_id)
    for item in request.get("items", []):
        if item.get("status") in {"queued", "failed", "unresolved"}:
            item["status"] = "syncing"
            item["error"] = ""
            item["updatedAt"] = now_iso()
    refresh_status(request)
    write_queue(root, payload)
    print(json.dumps(request, ensure_ascii=False, indent=2))


def command_manifest(args: argparse.Namespace, payload: dict) -> None:
    request = find_request(payload, args.request_id)
    items = []
    for item in request.get("items", []):
        if item.get("status") not in {"queued", "syncing", "failed", "unresolved"}:
            continue
        source = Path(item.get("sourcePath", "")).expanduser()
        items.append(
            {
                "itemId": item.get("itemId") or item.get("id"),
                "name": item.get("name"),
                "sourcePath": str(source),
                "readable": source.is_file(),
                "fingerprint": item.get("fingerprint"),
                "role": item.get("role"),
                "tags": item.get("tags", []),
            }
        )
    manifest = {
        "requestId": request.get("id"),
        "projectId": request.get("projectId"),
        "projectUrl": request.get("projectUrl"),
        "productKey": request.get("productKey"),
        "items": items,
    }
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


def command_mark(args: argparse.Namespace, payload: dict, root: Path) -> None:
    request = find_request(payload, args.request_id)
    updates = json.loads(Path(args.updates_file).read_text(encoding="utf-8"))
    updates = updates.get("updates", updates) if isinstance(updates, dict) else updates
    by_item = {str(update.get("itemId")): update for update in updates if update.get("itemId")}
    by_fingerprint = {str(update.get("fingerprint")): update for update in updates if update.get("fingerprint")}
    for item in request.get("items", []):
        update = by_item.get(str(item.get("itemId") or item.get("id"))) or by_fingerprint.get(str(item.get("fingerprint")))
        if not update:
            continue
        item["status"] = update.get("status", item.get("status"))
        item["chatcutAssetId"] = update.get("chatcutAssetId", item.get("chatcutAssetId", ""))
        item["error"] = update.get("error", "")
        item["updatedAt"] = now_iso()
        if item["status"] == "imported" and item.get("chatcutAssetId"):
            project_id = str(request.get("projectId") or "unknown-project")
            payload.setdefault("assets", {}).setdefault(project_id, {})[item.get("fingerprint")] = item["chatcutAssetId"]
    refresh_status(request)
    write_queue(root, payload)
    print(json.dumps(request, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Operate portable ChatCut sync requests.")
    parser.add_argument("--material-root", default=str(default_root()), help="Portable material root.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    next_parser = subparsers.add_parser("next", help="Print the next queued request.")
    next_parser.add_argument("--latest", action="store_true")

    claim_parser = subparsers.add_parser("claim", help="Mark active request items syncing.")
    claim_parser.add_argument("--request-id", required=True)

    manifest_parser = subparsers.add_parser("manifest", help="Create an upload manifest.")
    manifest_parser.add_argument("--request-id", required=True)
    manifest_parser.add_argument("--output")

    mark_parser = subparsers.add_parser("mark", help="Write import results back to the queue.")
    mark_parser.add_argument("--request-id", required=True)
    mark_parser.add_argument("--updates-file", required=True)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    root = Path(args.material_root).expanduser().resolve()
    payload = read_queue(root)
    if args.command == "next":
        command_next(args, payload)
    elif args.command == "claim":
        command_claim(args, payload, root)
    elif args.command == "manifest":
        command_manifest(args, payload)
    elif args.command == "mark":
        command_mark(args, payload, root)


if __name__ == "__main__":
    main()
