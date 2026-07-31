#!/usr/bin/env python3
"""Local-only portable material panel for ChatCut editing workflows."""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import re
import threading
import uuid
from collections import Counter
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm", ".mkv", ".avi", ".m4v", ".ts"}
ROLES = {"", "hook", "try_on", "detail", "motion", "proof", "ending", "transition"}
ANALYSIS_STATUSES = {"queued", "ready", "hold", "rejected"}
SYNC_STATUSES = {"queued", "syncing", "imported", "failed", "unresolved"}
REQUIRED_ROLES = ["hook", "try_on", "detail", "motion", "proof", "ending"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def safe_json_read(path: Path, default: dict) -> dict:
    if not path.exists():
        return default
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default
    return payload if isinstance(payload, dict) else default


def atomic_json_write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def file_fingerprint(path: Path) -> str:
    stat = path.stat()
    identity = f"{path.resolve()}|{stat.st_size}|{stat.st_mtime_ns}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def project_id_from_url(project_url: str) -> str:
    parsed = urlparse(project_url)
    if parsed.scheme != "https" or parsed.netloc.lower() != "app.chatcut.io":
        raise ValueError("ChatCut project URL must use https://app.chatcut.io")
    parts = [part for part in parsed.path.split("/") if part]
    if "editor" not in parts:
        raise ValueError("ChatCut project URL must contain /editor/<project-id>")
    index = parts.index("editor")
    if index + 1 >= len(parts):
        raise ValueError("ChatCut project id is missing")
    return parts[index + 1]


class MaterialStore:
    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()
        self.data_dir = self.root / "data"
        self.library_file = self.data_dir / "material-library.json"
        self.sync_file = self.data_dir / "chatcut-sync.json"
        self.lock = threading.RLock()
        self.initialize()

    def initialize(self) -> None:
        for name in ("data", "analysis", "batches", "uploads", "system"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        with self.lock:
            if not self.library_file.exists():
                atomic_json_write(self.library_file, self.default_library())
            if not self.sync_file.exists():
                atomic_json_write(self.sync_file, self.default_sync())

    def default_library(self) -> dict:
        return {
            "version": 1,
            "updatedAt": now_iso(),
            "activeId": None,
            "filterBatchId": "",
            "filterTag": "",
            "batches": [],
            "items": [],
        }

    def default_sync(self) -> dict:
        return {
            "version": 1,
            "type": "chatcut-material-sync",
            "updatedAt": now_iso(),
            "requests": [],
            "assets": {},
        }

    def read_library(self) -> dict:
        with self.lock:
            return safe_json_read(self.library_file, self.default_library())

    def write_library(self, payload: dict) -> None:
        with self.lock:
            payload["updatedAt"] = now_iso()
            atomic_json_write(self.library_file, payload)

    def read_sync(self) -> dict:
        with self.lock:
            return safe_json_read(self.sync_file, self.default_sync())

    def write_sync(self, payload: dict) -> None:
        with self.lock:
            payload["updatedAt"] = now_iso()
            atomic_json_write(self.sync_file, payload)

    def import_folder(self, folder: str, batch_name: str, recursive: bool) -> dict:
        source_root = Path(folder).expanduser().resolve()
        if not source_root.is_dir():
            raise ValueError(f"Folder is not readable: {source_root}")
        batch_name = batch_name.strip() or source_root.name
        batch_id = stable_id("batch", f"{batch_name}|{source_root}")
        candidates = source_root.rglob("*") if recursive else source_root.glob("*")
        video_paths = sorted(path for path in candidates if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)

        library = self.read_library()
        items = library.setdefault("items", [])
        existing = {item.get("fingerprint"): item for item in items}
        imported = []
        skipped = []
        for path in video_paths:
            fingerprint = file_fingerprint(path)
            if fingerprint in existing:
                skipped.append(existing[fingerprint].get("id"))
                continue
            stat = path.stat()
            item = {
                "id": stable_id("material", fingerprint),
                "name": path.name,
                "sourcePath": str(path),
                "size": stat.st_size,
                "modifiedNs": stat.st_mtime_ns,
                "fingerprint": fingerprint,
                "batchId": batch_id,
                "batchName": batch_name,
                "tags": [],
                "role": "",
                "analysisStatus": "queued",
                "status": "local",
                "createdAt": now_iso(),
                "updatedAt": now_iso(),
            }
            items.append(item)
            existing[fingerprint] = item
            imported.append(item)

        batches = library.setdefault("batches", [])
        if not any(batch.get("id") == batch_id for batch in batches):
            batches.append(
                {
                    "id": batch_id,
                    "name": batch_name,
                    "sourceRoot": str(source_root),
                    "createdAt": now_iso(),
                }
            )
        self.write_library(library)
        return {"imported": imported, "skipped": skipped, "batchId": batch_id, "count": len(imported)}

    def update_item(self, item_id: str, changes: dict) -> dict:
        library = self.read_library()
        item = next((entry for entry in library.get("items", []) if entry.get("id") == item_id), None)
        if not item:
            raise ValueError(f"Unknown material id: {item_id}")
        if "role" in changes:
            role = str(changes.get("role") or "")
            if role not in ROLES:
                raise ValueError(f"Unsupported role: {role}")
            item["role"] = role
        if "analysisStatus" in changes:
            status = str(changes.get("analysisStatus") or "queued")
            if status not in ANALYSIS_STATUSES:
                raise ValueError(f"Unsupported analysis status: {status}")
            item["analysisStatus"] = status
        if "tags" in changes:
            raw_tags = changes.get("tags") or []
            if isinstance(raw_tags, str):
                raw_tags = raw_tags.split(",")
            item["tags"] = sorted({str(tag).strip() for tag in raw_tags if str(tag).strip()})
        item["updatedAt"] = now_iso()
        self.write_library(library)
        return item

    def director_monitor(self) -> dict:
        library = self.read_library()
        ready_items = [item for item in library.get("items", []) if item.get("analysisStatus") == "ready"]
        counts = Counter(item.get("role") for item in ready_items if item.get("role"))
        missing = [role for role in REQUIRED_ROLES if counts.get(role, 0) == 0]
        coverage = len(REQUIRED_ROLES) - len(missing)
        score = round((coverage / len(REQUIRED_ROLES)) * 100) if REQUIRED_ROLES else 100
        return {
            "score": score,
            "readyCount": len(ready_items),
            "roleCounts": dict(counts),
            "missingRequiredRoles": missing,
            "recommendedVersion": "ready-to-cut" if score >= 80 else "needs-review",
            "updatedAt": now_iso(),
        }

    def create_sync_request(self, payload: dict) -> dict:
        project_url = str(payload.get("projectUrl") or "").strip()
        product_key = str(payload.get("productKey") or "").strip()
        item_ids = {str(value) for value in payload.get("itemIds") or []}
        batch_id = str(payload.get("batchId") or "").strip()
        if not product_key:
            raise ValueError("productKey is required")
        project_id = project_id_from_url(project_url)

        library = self.read_library()
        candidates = list(library.get("items", []))
        if item_ids:
            candidates = [item for item in candidates if item.get("id") in item_ids]
            scope = "selected"
        elif batch_id:
            candidates = [item for item in candidates if item.get("batchId") == batch_id]
            scope = "batch"
        else:
            raise ValueError("Select material itemIds or one batchId")
        candidates = [item for item in candidates if item.get("analysisStatus") == "ready"]
        if not candidates:
            raise ValueError("No reviewed ready materials are selected")
        batch_ids = {item.get("batchId") for item in candidates}
        if len(batch_ids) > 1:
            raise ValueError("A sync request cannot mix product batches")

        sync = self.read_sync()
        imported_ledger = sync.setdefault("assets", {}).setdefault(project_id, {})
        active = [item for item in candidates if item.get("fingerprint") not in imported_ledger]
        if not active:
            raise ValueError("Every selected fingerprint is already imported into this project")

        request_items = []
        for item in active[:30]:
            request_items.append(
                {
                    "itemId": item.get("id"),
                    "name": item.get("name"),
                    "sourcePath": item.get("sourcePath"),
                    "size": item.get("size"),
                    "modifiedNs": item.get("modifiedNs"),
                    "fingerprint": item.get("fingerprint"),
                    "batchId": item.get("batchId"),
                    "batchName": item.get("batchName"),
                    "tags": item.get("tags", []),
                    "role": item.get("role"),
                    "analysisStatus": item.get("analysisStatus"),
                    "status": "queued",
                    "chatcutAssetId": "",
                    "error": "",
                    "updatedAt": now_iso(),
                }
            )
        role_counts = Counter(item.get("role") for item in request_items if item.get("role"))
        missing = [role for role in REQUIRED_ROLES if role_counts.get(role, 0) == 0]
        request = {
            "id": f"ccsync-{uuid.uuid4().hex[:16]}",
            "createdAt": now_iso(),
            "updatedAt": now_iso(),
            "createdBy": "portable-material-panel",
            "projectId": project_id,
            "projectUrl": project_url,
            "productKey": product_key,
            "scope": scope,
            "batchId": next(iter(batch_ids)),
            "batchName": active[0].get("batchName"),
            "items": request_items,
            "summary": {
                "selected": len(request_items),
                "roleCounts": dict(role_counts),
                "missingRequiredRoles": missing,
                "recommendedVersion": "ready-to-cut" if len(missing) <= 1 else "needs-review",
            },
            "status": "queued",
        }
        sync.setdefault("requests", []).append(request)
        self.write_sync(sync)
        return request

    def update_sync_request(self, payload: dict) -> dict:
        request_id = str(payload.get("requestId") or "")
        updates = payload.get("updates") or []
        sync = self.read_sync()
        request = next((entry for entry in sync.get("requests", []) if entry.get("id") == request_id), None)
        if not request:
            raise ValueError(f"Unknown request id: {request_id}")
        by_item = {str(update.get("itemId")): update for update in updates if update.get("itemId")}
        by_fingerprint = {str(update.get("fingerprint")): update for update in updates if update.get("fingerprint")}
        ledger = sync.setdefault("assets", {}).setdefault(str(request.get("projectId")), {})
        for item in request.get("items", []):
            update = by_item.get(str(item.get("itemId"))) or by_fingerprint.get(str(item.get("fingerprint")))
            if not update:
                continue
            status = str(update.get("status") or item.get("status") or "queued")
            if status not in SYNC_STATUSES:
                raise ValueError(f"Unsupported sync status: {status}")
            item["status"] = status
            item["chatcutAssetId"] = str(update.get("chatcutAssetId") or item.get("chatcutAssetId") or "")
            item["error"] = str(update.get("error") or "")
            item["updatedAt"] = now_iso()
            if status == "imported" and item["chatcutAssetId"]:
                ledger[item.get("fingerprint")] = item["chatcutAssetId"]
        statuses = [item.get("status") for item in request.get("items", [])]
        if statuses and all(status == "imported" for status in statuses):
            request["status"] = "completed"
        elif any(status == "failed" for status in statuses):
            request["status"] = "partial"
        elif any(status == "syncing" for status in statuses):
            request["status"] = "syncing"
        else:
            request["status"] = "queued"
        request["updatedAt"] = now_iso()
        self.write_sync(sync)
        return request

    def media_path(self, item_id: str) -> Path:
        library = self.read_library()
        item = next((entry for entry in library.get("items", []) if entry.get("id") == item_id), None)
        if not item:
            raise FileNotFoundError(item_id)
        path = Path(str(item.get("sourcePath") or "")).expanduser()
        if not path.is_file():
            raise FileNotFoundError(path)
        return path


class PanelHandler(BaseHTTPRequestHandler):
    server_version = "PortableMaterialPanel/1.0"
    store: MaterialStore
    static_dir: Path

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{now_iso()}] {self.address_string()} {format_string % args}")

    def end_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload: object, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self.send_json({"ok": False, "error": message}, status)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError as error:
            raise ValueError("Invalid Content-Length") from error
        if length <= 0 or length > 2 * 1024 * 1024:
            raise ValueError("JSON body is missing or too large")
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("Invalid JSON body") from error
        if not isinstance(payload, dict):
            raise ValueError("JSON body must be an object")
        return payload

    def serve_static(self, filename: str) -> None:
        path = self.static_dir / filename
        if not path.is_file():
            self.send_error_json("Static file not found", HTTPStatus.NOT_FOUND)
            return
        body = path.read_bytes()
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "application/json"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def serve_media(self, item_id: str) -> None:
        try:
            path = self.store.media_path(item_id)
        except FileNotFoundError:
            self.send_error_json("Media file not found", HTTPStatus.NOT_FOUND)
            return
        size = path.stat().st_size
        start = 0
        end = max(size - 1, 0)
        status = HTTPStatus.OK
        range_header = self.headers.get("Range")
        if range_header:
            match = re.fullmatch(r"bytes=(\d*)-(\d*)", range_header.strip())
            if not match:
                self.send_error_json("Unsupported byte range", HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            if match.group(1):
                start = int(match.group(1))
            if match.group(2):
                end = min(int(match.group(2)), end)
            if start > end or start >= size:
                self.send_error_json("Byte range outside file", HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                return
            status = HTTPStatus.PARTIAL_CONTENT
        length = max(end - start + 1, 0)
        self.send_response(status)
        self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "video/mp4")
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(length))
        if status == HTTPStatus.PARTIAL_CONTENT:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with path.open("rb") as source:
            source.seek(start)
            remaining = length
            while remaining > 0:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    break
                self.wfile.write(chunk)
                remaining -= len(chunk)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/healthz":
            self.send_json({"ok": True, "materialRoot": str(self.store.root), "version": 1})
        elif path in {"/", "/materials", "/materials.html"}:
            self.serve_static("materials.html")
        elif path == "/assets/app.js":
            self.serve_static("app.js")
        elif path == "/assets/styles.css":
            self.serve_static("styles.css")
        elif path == "/api/material-library":
            self.send_json(self.store.read_library())
        elif path == "/api/material-library/director-monitor":
            self.send_json(self.store.director_monitor())
        elif path == "/api/material-library/chatcut-sync":
            self.send_json(self.store.read_sync())
        elif path.startswith("/media/"):
            self.serve_media(unquote(path.removeprefix("/media/")))
        else:
            self.send_error_json("Not found", HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self.read_json()
            if path == "/api/material-library/import-local-folder":
                result = self.store.import_folder(
                    str(payload.get("folder") or ""),
                    str(payload.get("batchName") or ""),
                    bool(payload.get("recursive", False)),
                )
            elif path == "/api/material-library/item/update":
                result = self.store.update_item(str(payload.get("itemId") or ""), payload)
            elif path == "/api/material-library/chatcut-sync/request":
                result = self.store.create_sync_request(payload)
            elif path == "/api/material-library/chatcut-sync/update":
                result = self.store.update_sync_request(payload)
            else:
                self.send_error_json("Not found", HTTPStatus.NOT_FOUND)
                return
        except ValueError as error:
            self.send_error_json(str(error))
            return
        except OSError as error:
            self.send_error_json(str(error), HTTPStatus.INTERNAL_SERVER_ERROR)
            return
        self.send_json({"ok": True, "result": result})


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the portable ChatCut material panel.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8794)
    parser.add_argument(
        "--material-root",
        default=os.environ.get("CHATCUT_MATERIAL_ROOT") or str(Path.home() / "ChatCutMaterials"),
    )
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--init-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
        raise SystemExit("Refusing a non-loopback host without --allow-remote")
    store = MaterialStore(Path(args.material_root))
    if args.init_only:
        print(store.root)
        return
    handler = type(
        "ConfiguredPanelHandler",
        (PanelHandler,),
        {"store": store, "static_dir": Path(__file__).resolve().parent / "static"},
    )
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Portable material panel: http://{args.host}:{args.port}/materials.html")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
