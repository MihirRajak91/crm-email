#!/usr/bin/env python3
"""
End-to-end test script for CRM endpoints:
 - Uploads a PDF to /api/documents/upload
 - Composes an email via /api/email/compose

Usage examples:

  # Minimal (new outreach)
  poetry run python scripts/test_upload_and_compose.py \
    --base-url http://localhost:8001 \
    --file "/home/zeta/Downloads/eng_docuements/pdf/engineering_guides_3 (1).pdf" \
    --status new \
    --past-email "Intro email body"

  # Contacted follow-up
  poetry run python scripts/test_upload_and_compose.py \
    --file "/path/to/file.pdf" \
    --status contacted \
    --past-email "Hi — quick intro..." \
    --latest-email "Looks interesting, do you integrate with HubSpot?"
"""

import argparse
import json
import mimetypes
import os
import sys
import time
from urllib import request, error
from uuid import uuid4


def _http_json(url: str, payload: dict, timeout: int = 120) -> tuple[int, dict | str]:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body)
    except error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = str(e)
        return e.code, body
    except error.URLError as e:
        return 0, f"Connection error: {e.reason}"


def _http_multipart(url: str, field_name: str, file_path: str, timeout: int = 600) -> tuple[int, dict | str]:
    # Build a simple multipart/form-data payload manually (no extra deps)
    boundary = "----CRMFormBoundary" + uuid4().hex

    filename = os.path.basename(file_path)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        with open(file_path, "rb") as f:
            file_bytes = f.read()
    except Exception as e:
        return 0, f"Failed to read file: {e}"

    parts = []
    # File part
    parts.append(f"--{boundary}\r\n".encode("utf-8"))
    parts.append(
        (
            f"Content-Disposition: form-data; name=\"{field_name}\"; filename=\"{filename}\"\r\n"
            f"Content-Type: {content_type}\r\n\r\n"
        ).encode("utf-8")
    )
    parts.append(file_bytes)
    parts.append(b"\r\n")
    # End boundary
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(parts)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
        # Avoid 100-continue stalls on some proxies
        "Expect": "",
    }

    req = request.Request(url, data=body, headers=headers)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            resp_body = resp.read().decode("utf-8")
            # Try JSON first, else return raw text
            try:
                return resp.status, json.loads(resp_body)
            except Exception:
                return resp.status, resp_body
    except error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        return e.code, err_body
    except error.URLError as e:
        return 0, f"Connection error: {e.reason}"


def main() -> None:
    p = argparse.ArgumentParser(description="Upload a PDF and compose an email via CRM API")
    p.add_argument("--base-url", default="http://localhost:8001", help="API base URL (default: http://localhost:8001)")
    p.add_argument("--file", required=True, help="Path to a PDF to upload")
    p.add_argument("--status", default="new", choices=["new", "contacted", "qualified", "lost"], help="Lead status for compose")
    p.add_argument("--past-email", dest="past_email", help="Oldest email body in the thread (optional)")
    p.add_argument("--latest-email", dest="latest_email", help="Most recent email body in the thread (optional)")
    p.add_argument("--recipient-name", dest="recipient_name", help="Recipient name (optional)")
    p.add_argument("--recipient-company", dest="recipient_company", help="Recipient company (optional)")
    p.add_argument("--top-k", type=int, default=6, help="Retrieval top-k (default 6)")

    args = p.parse_args()

    base = args.base_url.rstrip("/")
    upload_url = f"{base}/api/documents/upload"
    compose_url = f"{base}/api/email/compose"

    print(f"[1/2] Uploading PDF to {upload_url} …")
    code, out = _http_multipart(upload_url, "file", args.file)
    print(f"→ HTTP {code}")
    print(out if isinstance(out, str) else json.dumps(out, indent=2))
    if code != 200:
        sys.exit(1)

    time.sleep(1.0)  # small pause before composing

    payload = {"status": args.status}
    thread = []
    if args.past_email:
        thread.append({"subject": None, "body": args.past_email})
    if args.latest_email:
        thread.append({"subject": None, "body": args.latest_email})
    if thread:
        payload["past_emails"] = thread
    if args.recipient_name:
        payload["recipient_name"] = args.recipient_name
    if args.recipient_company:
        payload["recipient_company"] = args.recipient_company
    if args.top_k is not None:
        payload["top_k"] = args.top_k

    print(f"\n[2/2] Composing email via {compose_url} …")
    code, out = _http_json(compose_url, payload)
    print(f"→ HTTP {code}")
    if isinstance(out, str):
        print(out)
        sys.exit(1 if code != 200 else 0)

    print(json.dumps(out, indent=2))
    if code != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
