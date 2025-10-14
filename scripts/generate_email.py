#!/usr/bin/env python3
"""
Simple CLI to call the CRM email compose endpoint and print the result.

Usage examples:

  # New (cold outreach)
  poetry run python scripts/generate_email.py \
    --base-url http://localhost:8000 \
    --status new \
    --past-email "Intro email body" \
    --recipient-name "Riley" \
    --recipient-company "ExampleCo"

  # Contacted (follow-up)
  poetry run python scripts/generate_email.py \
    --status contacted \
    --past-email "Hi Riley — quick intro to our platform…" \
    --latest-email "Sounds interesting. Do you integrate with HubSpot?"

  # Qualified (assumed interested)
  poetry run python scripts/generate_email.py --status qualified --past-email "Great chatting last week" --latest-email "Can we review pricing?"

  # Lost (polite close)
  poetry run python scripts/generate_email.py --status lost --latest-email "Not a fit right now"
"""

import argparse
import json
import sys
from urllib import request, error


def post_json(url: str, payload: dict, headers: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=data, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body)
    except error.HTTPError as e:
        try:
            err_body = e.read().decode("utf-8")
        except Exception:
            err_body = str(e)
        raise SystemExit(f"HTTP {e.code} {e.reason}: {err_body}")
    except error.URLError as e:
        raise SystemExit(f"Connection error: {e.reason}")


def build_payload(args: argparse.Namespace) -> dict:
    payload: dict = {"status": args.status}

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
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate an email via CRM /api/email/compose")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--status", required=True, choices=["new", "contacted", "qualified", "lost"], help="Lead status")
    parser.add_argument("--past-email", dest="past_email", help="Oldest email body in the thread")
    parser.add_argument("--latest-email", dest="latest_email", help="Most recent email body in the thread")
    parser.add_argument("--recipient-name", dest="recipient_name", help="Recipient name")
    parser.add_argument("--recipient-company", dest="recipient_company", help="Recipient company")
    parser.add_argument("--top-k", type=int, default=6, help="Retrieval top-k (default: 6)")
    parser.add_argument("--verbose", action="store_true", help="Print full JSON response")

    args = parser.parse_args()
    payload = build_payload(args)

    url = args.base_url.rstrip("/") + "/api/email/compose"
    res = post_json(url, payload)

    if args.verbose:
        print(json.dumps(res, indent=2))
        return

    if not isinstance(res, dict) or res.get("status") != "success":
        print("Unexpected response:", json.dumps(res, indent=2), file=sys.stderr)
        sys.exit(1)

    data = res.get("data", {})
    subject = data.get("subject", "")
    body = data.get("body", "")

    print("Subject:\n" + subject)
    print("\nBody:\n" + body)


if __name__ == "__main__":
    main()
