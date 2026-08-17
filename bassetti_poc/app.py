"""Dependency-light local HTTP application for the interview POC."""

from __future__ import annotations

import argparse
import cgi
import json
import logging
import mimetypes
import os
import re
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .exporter import ApprovalError, export_docx, export_json
from .extractor import InputError, parse_document
from .schema import FIELD_ORDER
from .storage import SessionStore


BASE_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = BASE_DIR / "static"
SAMPLE_DIR = BASE_DIR / "samples"
STORE = SessionStore(BASE_DIR / "data" / "sessions")
LOG = logging.getLogger("bassetti_poc")


def json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False).encode("utf-8")


class AppHandler(BaseHTTPRequestHandler):
    server_version = "BassettiPOC/1.0"

    def log_message(self, fmt, *args):
        LOG.info("%s %s", self.client_address[0], fmt % args)

    def security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'")
        self.send_header("Cache-Control", "no-store")

    def send_body(self, body: bytes, content_type: str, status=200, disposition: str | None = None):
        self.send_response(status)
        self.security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers(); self.wfile.write(body)

    def send_json(self, value, status=200):
        self.send_body(json_bytes(value), "application/json; charset=utf-8", status)

    def error_json(self, message: str, status=400):
        LOG.warning("request_error status=%s message=%s", status, message)
        self.send_json({"error": message}, status)

    def do_GET(self):
        try:
            self._do_GET()
        except KeyError as exc:
            self.error_json(str(exc), 404)
        except Exception:
            LOG.exception("unhandled GET error")
            self.error_json("Unexpected local server error.", 500)

    def _do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/":
            return self.serve_file(STATIC_DIR / "index.html")
        if path.startswith("/static/"):
            return self.serve_file(STATIC_DIR / path.removeprefix("/static/"))
        if path == "/api/samples":
            items = []
            for sample in sorted(SAMPLE_DIR.glob("*.pdf")):
                items.append({"id": sample.stem, "name": sample.name, "size": sample.stat().st_size})
            return self.send_json({"samples": items})
        if path == "/api/metrics":
            fixture_path = BASE_DIR / "fixtures" / "validation_summary.json"
            fixture_metrics = json.loads(fixture_path.read_text(encoding="utf-8")) if fixture_path.exists() else {}
            return self.send_json({"label": "demo measurement", "fixture": fixture_metrics, "runtime": STORE.stats()})
        match = re.fullmatch(r"/api/sessions/([a-zA-Z0-9]+)", path)
        if match:
            return self.send_json(STORE.get(match.group(1)))
        match = re.fullmatch(r"/api/sessions/([a-zA-Z0-9]+)/export/(json|docx)", path)
        if match:
            session = STORE.get(match.group(1)); fmt = match.group(2)
            try:
                # Check the gate before stamping approval; a failed attempt must not
                # leave behind a misleading approval timestamp.
                from .exporter import assert_exportable
                assert_exportable(session)
                if not session.get("approved_at"):
                    session["approved_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                    session["audit"].append({"timestamp": session["approved_at"], "field": "*", "old_value": None, "new_value": "human_approved", "old_status": None, "new_status": "approved", "action": "approve_export"})
                    STORE.save(session)
                body = export_json(session) if fmt == "json" else export_docx(session)
            except ApprovalError as exc:
                return self.error_json(str(exc), 409)
            mime = "application/json; charset=utf-8" if fmt == "json" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            filename = f"candidate_profile_{session['id']}.{fmt}"
            return self.send_body(body, mime, disposition=f'attachment; filename="{filename}"')
        self.error_json("Route not found", 404)

    def do_POST(self):
        try:
            self._do_POST()
        except (InputError, ValueError) as exc:
            self.error_json(str(exc), 400)
        except KeyError as exc:
            self.error_json(str(exc), 404)
        except Exception:
            LOG.exception("unhandled POST error")
            self.error_json("Unexpected local server error.", 500)

    def _do_POST(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/parse":
            content_type = self.headers.get("Content-Type", "")
            if content_type.startswith("multipart/form-data"):
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type})
                item = form["file"] if "file" in form else None
                if item is None or not getattr(item, "filename", None):
                    raise InputError("Choose a PDF or DOCX file.")
                filename, data = Path(item.filename).name, item.file.read(10 * 1024 * 1024 + 1)
            else:
                payload = self.read_json()
                sample_id = payload.get("sample_id", "")
                if not re.fullmatch(r"[a-zA-Z0-9_-]+", sample_id):
                    raise InputError("Invalid sample selection.")
                sample_path = SAMPLE_DIR / f"{sample_id}.pdf"
                if not sample_path.exists():
                    raise InputError("Sample not found.")
                filename, data = sample_path.name, sample_path.read_bytes()
            result = parse_document(filename, data)
            session = STORE.create(result)
            LOG.info("parse_complete session=%s file=%s duration_ms=%s", session["id"], filename, result["processing_ms"])
            return self.send_json(session, 201)

        match = re.fullmatch(r"/api/sessions/([a-zA-Z0-9]+)/fields", path)
        if match:
            payload = self.read_json()
            field_path, action = payload.get("field"), payload.get("action")
            if field_path not in FIELD_ORDER:
                raise ValueError("Unknown schema field")
            return self.send_json(STORE.update_field(match.group(1), field_path, payload.get("value"), action))
        match = re.fullmatch(r"/api/sessions/([a-zA-Z0-9]+)/reset-review", path)
        if match:
            return self.send_json(STORE.reset_review(match.group(1)))
        self.error_json("Route not found", 404)

    def read_json(self) -> dict:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Invalid request length") from exc
        if length > 1024 * 1024:
            raise ValueError("Request is too large")
        try:
            value = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            raise ValueError("Malformed JSON request") from exc
        if not isinstance(value, dict):
            raise ValueError("JSON object expected")
        return value

    def serve_file(self, path: Path):
        try:
            safe = path.resolve(strict=True)
        except FileNotFoundError:
            return self.error_json("File not found", 404)
        if STATIC_DIR.resolve() not in safe.parents and safe != STATIC_DIR.resolve():
            return self.error_json("File not found", 404)
        mime = mimetypes.guess_type(str(safe))[0] or "application/octet-stream"
        self.send_body(safe.read_bytes(), mime + ("; charset=utf-8" if mime.startswith("text/") else ""))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run the local Bassetti CV Parser POC")
    parser.add_argument("--host", default=os.getenv("BASSETTI_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("BASSETTI_PORT", "8765")))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Bassetti CV Parser POC running at http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
