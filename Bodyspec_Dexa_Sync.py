import requests
import json
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

# -------------------------------------------------------------------------
# BODYSPEC DEXA SYNC  (v0.11.0 API)
# Docs: /Users/brenttuggle/AntiGravity/GymCoach/API_Documentation/Bodyspec_api-1.json
#
# Purpose: Fetch DEXA scan results from Bodyspec Health REST API and
#          APPEND new results to a persistent history file. Since scans
#          happen every 3-6 months, run this manually after a new scan.
#
# Auth:    Bearer token (personal access token from Bodyspec portal)
#          Set BODYSPEC_ACCESS_TOKEN in .env
#
# Usage:   python3 scripts/Bodyspec_DEXA_Sync.py
#
# Persistent data file: data/bodyspec_dexa_history.json
#   - Never overwritten; only new results are appended by result_id
#   - Safe to re-run at any time -- duplicates are skipped
#
# Real API endpoints (per OpenAPI spec v0.11.0):
#   GET /api/v1/users/me/results/                              list all results
#   GET /api/v1/users/me/results/{result_id}/dexa/scan-info   scan metadata
#   GET /api/v1/users/me/results/{result_id}/dexa/composition  body comp by region
#   GET /api/v1/users/me/results/{result_id}/dexa/bone-density BMD
#   GET /api/v1/users/me/results/{result_id}/dexa/visceral-fat VAT
#   GET /api/v1/users/me/results/{result_id}/dexa/percentiles  age/sex percentiles
#
# NOTE: The /results/ endpoint does NOT return a 'status' field.
#       All records returned already represent completed scans (they have a result_pdf).
# -------------------------------------------------------------------------

load_dotenv()

ACCESS_TOKEN = os.getenv("BODYSPEC_ACCESS_TOKEN")
BASE_URL = "https://app.bodyspec.com"

# Persistent history file -- lives in data/ alongside workouts_master.json
HISTORY_FILE = os.path.join("data", "bodyspec_dexa_history.json")


# -------------------------------------------------------------------------
# REQUEST WRAPPER
# -------------------------------------------------------------------------
def bodyspec_get(path, headers, params=None):
    """GET against BASE_URL + path. Retries once on 429."""
    url = BASE_URL + path
    response = requests.get(url, headers=headers, params=params or {}, timeout=15)
    if response.status_code == 429:
        retry_after = int(response.headers.get("Retry-After", 60))
        print(f"   Rate limit hit. Waiting {retry_after}s...")
        time.sleep(retry_after)
        response = requests.get(url, headers=headers, params=params or {}, timeout=15)
    return response


# -------------------------------------------------------------------------
# API CLIENT
# -------------------------------------------------------------------------
class BodyspecSync:
    def __init__(self, access_token):
        self.headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json",
        }

    def verify_auth(self):
        """Quick auth check -- GET /api/v1/users/me."""
        r = bodyspec_get("/api/v1/users/me", self.headers)
        if r.status_code == 200:
            user = r.json()
            name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            email = user.get("email", "")
            print(f"   Authenticated as: {name} ({email})")
            return True
        print(f"   Auth failed: {r.status_code} -- {r.text}")
        return False

    def list_results(self):
        """GET /api/v1/users/me/results/ -- paginate through all results."""
        all_results = []
        page = 1
        while True:
            r = bodyspec_get(
                "/api/v1/users/me/results/",
                self.headers,
                {"page": page, "page_size": 100},
            )
            if r.status_code != 200:
                print(
                    f"   Failed to list results (page {page}): {r.status_code} -- {r.text}"
                )
                break
            data = r.json()
            results = data.get("results", [])
            all_results.extend(results)
            if not data.get("pagination", {}).get("has_more", False):
                break
            page += 1
        return all_results

    def fetch_scan_info(self, result_id):
        """GET /api/v1/users/me/results/{result_id}/dexa/scan-info"""
        r = bodyspec_get(
            f"/api/v1/users/me/results/{result_id}/dexa/scan-info", self.headers
        )
        return r.json() if r.status_code == 200 else {}

    def fetch_composition(self, result_id):
        """GET /api/v1/users/me/results/{result_id}/dexa/composition"""
        r = bodyspec_get(
            f"/api/v1/users/me/results/{result_id}/dexa/composition", self.headers
        )
        return r.json() if r.status_code == 200 else {}

    def fetch_bone_density(self, result_id):
        """GET /api/v1/users/me/results/{result_id}/dexa/bone-density"""
        r = bodyspec_get(
            f"/api/v1/users/me/results/{result_id}/dexa/bone-density", self.headers
        )
        return r.json() if r.status_code == 200 else {}

    def fetch_visceral_fat(self, result_id):
        """GET /api/v1/users/me/results/{result_id}/dexa/visceral-fat"""
        r = bodyspec_get(
            f"/api/v1/users/me/results/{result_id}/dexa/visceral-fat", self.headers
        )
        return r.json() if r.status_code == 200 else {}

    def fetch_percentiles(self, result_id):
        """GET /api/v1/users/me/results/{result_id}/dexa/percentiles"""
        r = bodyspec_get(
            f"/api/v1/users/me/results/{result_id}/dexa/percentiles", self.headers
        )
        return r.json() if r.status_code == 200 else {}

    def fetch_full_result(self, result_id):
        """Fetch all DEXA sub-sections for a single result_id."""
        print(
            "      Fetching: scan-info, composition, bone-density, visceral-fat, percentiles..."
        )
        return {
            "result_id": result_id,
            "scan_info": self.fetch_scan_info(result_id),
            "composition": self.fetch_composition(result_id),
            "bone_density": self.fetch_bone_density(result_id),
            "visceral_fat": self.fetch_visceral_fat(result_id),
            "percentiles": self.fetch_percentiles(result_id),
        }


# -------------------------------------------------------------------------
# PERSISTENT HISTORY MANAGEMENT
# -------------------------------------------------------------------------
def _load_history():
    """Load existing persistent history, or return a fresh shell."""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {
        "schema_version": "2.0",
        "first_synced": datetime.now().isoformat(),
        "last_synced": None,
        "result_count": 0,
        "latest_result": {},
        "results": [],  # Full detail records, newest first, keyed by result_id
    }


def _save_history(history):
    """Atomic write to the persistent history file."""
    tmp = HISTORY_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(history, f, indent=2)
    os.replace(tmp, HISTORY_FILE)


def _strip_result(result):
    """Remove verbose/sensitive fields before persisting to disk."""
    # Signed PDF URL expires -- not useful to store long-term
    pdf = result.get("appt_summary", {}).get("result_pdf", {})
    pdf.pop("url", None)
    # GPS coords and long descriptions are verbose, not needed for analysis
    loc = result.get("appt_summary", {}).get("location", {})
    loc.pop("coordinates", None)
    loc.pop("description", None)
    return result


def _merge_results(existing_results, api_results, sync):
    """Append only new results (by result_id). Fetches full DEXA detail for each new one.
    Returns (merged_list, new_count).

    NOTE: The /results/ endpoint returns only records that represent completed scans
    (they all have a result_pdf). There is NO 'status' field -- do NOT filter on it.
    We filter only on service.name == 'DEXA' to skip any future non-DEXA service types.
    """
    existing_ids = {r.get("result_id", "") for r in existing_results}
    added = 0

    for summary in api_results:
        result_id = summary.get("result_id", "")
        if not result_id or result_id in existing_ids:
            continue

        # Skip any future non-DEXA service types
        service_name = summary.get("service", {}).get("name", "")
        if service_name.upper() != "DEXA":
            continue

        scan_date = summary.get("start_time", "unknown")[:10]
        print(f"   NEW: DEXA result found (ID: {result_id}, date: {scan_date})")
        full = sync.fetch_full_result(result_id)
        full["appt_summary"] = summary
        _strip_result(full)
        existing_results.append(full)  # add then sort below
        existing_ids.add(result_id)
        added += 1

    # Sort newest first by start_time
    existing_results.sort(
        key=lambda r: r.get("appt_summary", {}).get("start_time", ""),
        reverse=True,
    )

    return existing_results, added


# -------------------------------------------------------------------------
# MAIN
# -------------------------------------------------------------------------
def main():
    print("Bodyspec DEXA System Check:")

    if not ACCESS_TOKEN:
        print("   ERROR: BODYSPEC_ACCESS_TOKEN missing from .env")
        print("   Paste your personal access token from the Bodyspec portal:")
        print("   BODYSPEC_ACCESS_TOKEN=<your_token>")
        sys.exit(1)

    sync = BodyspecSync(ACCESS_TOKEN)

    # Verify auth before doing anything else
    if not sync.verify_auth():
        sys.exit(1)

    # Load existing persistent history
    history = _load_history()
    existing_count = len(history["results"])
    print(f"   Loaded {existing_count} existing result(s) from history.")

    print("   Fetching result list from Bodyspec API...")
    api_results = sync.list_results()
    print(f"   Found {len(api_results)} total result(s) on account.")

    print("   Checking for new DEXA results...")
    history["results"], new_count = _merge_results(
        history["results"], api_results, sync
    )

    # Update metadata
    history["last_synced"] = datetime.now().isoformat()
    history["result_count"] = len(history["results"])
    history["latest_result"] = history["results"][0] if history["results"] else {}

    _save_history(history)

    if new_count > 0:
        latest = history["latest_result"]
        scan_date = latest.get("appt_summary", {}).get("start_time", "unknown")[:10]
        print(
            f"SUCCESS! {new_count} new DEXA result(s) added. Total: {history['result_count']} in {HISTORY_FILE}"
        )
        print(f"   Latest scan: {scan_date}")
    elif history["result_count"] > 0:
        print(f"Up to date. {history['result_count']} result(s) in {HISTORY_FILE}")
    else:
        print("No DEXA results found. Check your access token.")


if __name__ == "__main__":
    main()
