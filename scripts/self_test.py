#!/usr/bin/env python3
"""Run an isolated end-to-end test of the portable material bundle."""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen


SKILL_ROOT = Path(__file__).resolve().parent.parent
SERVER = SKILL_ROOT / "panel" / "server.py"
SYNC_TOOL = SKILL_ROOT / "scripts" / "material_sync.py"
DOCTOR = SKILL_ROOT / "scripts" / "doctor.py"
ROLES = ["hook", "try_on", "detail", "motion", "proof", "ending"]


def free_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def request_json(base_url: str, path: str, payload: dict | None = None) -> dict:
    body = None
    headers = {}
    method = "GET"
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json"
        method = "POST"
    request = Request(base_url + path, data=body, headers=headers, method=method)
    with urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def run_tool(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *arguments],
        cwd=SKILL_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="chatcut-hf-test-") as temporary:
        test_root = Path(temporary)
        material_root = test_root / "vault"
        source_root = test_root / "source"
        source_root.mkdir(parents=True)
        for role in ROLES:
            (source_root / f"{role}.mp4").write_bytes(bytes(range(1, 129)))

        port = free_port()
        base_url = f"http://127.0.0.1:{port}"
        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(SERVER),
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--material-root",
                str(material_root),
            ],
            cwd=SKILL_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        try:
            for _ in range(40):
                try:
                    if request_json(base_url, "/healthz").get("ok"):
                        break
                except OSError:
                    time.sleep(0.15)
            else:
                raise RuntimeError("Panel health check timed out")

            imported = request_json(
                base_url,
                "/api/material-library/import-local-folder",
                {"folder": str(source_root), "batchName": "self-test", "recursive": False},
            )["result"]["imported"]
            assert len(imported) == len(ROLES)

            for item, role in zip(imported, ROLES, strict=True):
                request_json(
                    base_url,
                    "/api/material-library/item/update",
                    {
                        "itemId": item["id"],
                        "role": role,
                        "analysisStatus": "ready",
                        "tags": ["可剪辑", "优先混剪"],
                    },
                )

            monitor = request_json(base_url, "/api/material-library/director-monitor")
            assert monitor["score"] == 100

            queued = request_json(
                base_url,
                "/api/material-library/chatcut-sync/request",
                {
                    "projectUrl": "https://app.chatcut.io/zh/editor/11111111-2222-3333-4444-555555555555",
                    "productKey": "SELF-TEST",
                    "itemIds": [item["id"] for item in imported],
                },
            )["result"]
            request_id = queued["id"]

            run_tool(
                [
                    str(SYNC_TOOL),
                    "--material-root",
                    str(material_root),
                    "claim",
                    "--request-id",
                    request_id,
                ]
            )
            manifest_path = test_root / "manifest.json"
            run_tool(
                [
                    str(SYNC_TOOL),
                    "--material-root",
                    str(material_root),
                    "manifest",
                    "--request-id",
                    request_id,
                    "--output",
                    str(manifest_path),
                ]
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            assert len(manifest["items"]) == len(ROLES)
            assert all(item["readable"] for item in manifest["items"])

            updates_path = test_root / "updates.json"
            updates_path.write_text(
                json.dumps(
                    {
                        "updates": [
                            {
                                "itemId": item["itemId"],
                                "fingerprint": item["fingerprint"],
                                "status": "imported",
                                "chatcutAssetId": f"asset-{item['itemId']}",
                                "error": "",
                            }
                            for item in manifest["items"]
                        ]
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            run_tool(
                [
                    str(SYNC_TOOL),
                    "--material-root",
                    str(material_root),
                    "mark",
                    "--request-id",
                    request_id,
                    "--updates-file",
                    str(updates_path),
                ]
            )

            queue = request_json(base_url, "/api/material-library/chatcut-sync")
            final_request = next(entry for entry in queue["requests"] if entry["id"] == request_id)
            assert final_request["status"] == "completed"

            doctor = run_tool(
                [
                    str(DOCTOR),
                    "--material-root",
                    str(material_root),
                    "--panel-url",
                    base_url,
                    "--json",
                ]
            )
            doctor_payload = json.loads(doctor.stdout)
            assert doctor_payload["ok"]

            print(
                json.dumps(
                    {
                        "ok": True,
                        "imported": len(imported),
                        "directorScore": monitor["score"],
                        "requestId": request_id,
                        "syncStatus": final_request["status"],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
