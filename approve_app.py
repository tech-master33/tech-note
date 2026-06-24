#!/usr/bin/env python3
"""
approve_app.py - Process App Store submissions from email replies.

Usage:
    python approve_app.py              # Check for pending submissions
    python approve_app.py approve ID   # Approve a submission by ID
    python approve_app.py reject ID    # Reject a submission by ID
    python approve_app.py list         # List all pending submissions

Submissions are stored in ~/.tech-soft/pending_submissions.json
"""

import os
import sys
import json
import datetime

TECH_SOFT = os.path.join(os.path.expanduser("~"), ".tech-soft")
PENDING_FILE = os.path.join(TECH_SOFT, "pending_submissions.json")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CATALOG_FILE = os.path.join(SCRIPT_DIR, "netlify-site", "catalog.json")
APPS_DIR = os.path.join(SCRIPT_DIR, "netlify-site", "apps")
HTML_DIR = os.path.join(SCRIPT_DIR, "netlify-site", "app")


def load_pending():
    if os.path.exists(PENDING_FILE):
        try:
            with open(PENDING_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return []


def save_pending(data):
    os.makedirs(os.path.dirname(PENDING_FILE), exist_ok=True)
    with open(PENDING_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def load_catalog():
    if os.path.exists(CATALOG_FILE):
        try:
            with open(CATALOG_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {"version": 1, "apps": []}


def save_catalog(data):
    with open(CATALOG_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def list_pending():
    pending = load_pending()
    if not pending:
        print("No pending submissions.")
        return
    print(f"\n{len(pending)} pending submission(s):\n")
    for sub in pending:
        print(f"  ID: {sub.get('id', 'unknown')}")
        print(f"  App: {sub.get('name', 'Unknown')}")
        print(f"  Category: {sub.get('category', 'Unknown')}")
        print(f"  Author: {sub.get('author', 'Unknown')}")
        print(f"  Submitted: {sub.get('submitted', 'Unknown')}")
        print(f"  URL: {sub.get('github', 'N/A')}")
        print()


def approve(submission_id):
    pending = load_pending()
    submission = None
    for sub in pending:
        if sub.get('id') == submission_id:
            submission = sub
            break

    if not submission:
        print(f"Submission '{submission_id}' not found.")
        return

    print(f"Approving: {submission.get('name', 'Unknown')}")

    catalog = load_catalog()
    app_id = submission.get('name', 'unknown').lower().replace(' ', '_').replace('-', '_')

    app_entry = {
        "id": app_id,
        "name": submission.get('name', 'Unknown'),
        "description": submission.get('description', 'No description.'),
        "category": submission.get('category', 'Apps'),
        "version": "1.0",
        "filename": app_id + ".py",
        "download_url": f"https://tech-note.surge.sh/apps/{app_id}.py",
        "author": submission.get('author', 'Tech-Note'),
        "features": submission.get('features', []),
        "controls": submission.get('controls', []),
        "added_date": datetime.date.today().isoformat()
    }

    catalog['apps'].append(app_entry)
    save_catalog(catalog)

    pending.remove(submission)
    save_pending(pending)

    print(f"\nDone! '{submission.get('name')}' added to catalog.")
    print(f"Next steps:")
    print(f"  1. Get the .py file from: {submission.get('github', 'N/A')}")
    print(f"  2. Save it to: {APPS_DIR}/{app_id}.py")
    print(f"  3. Create HTML page at: {HTML_DIR}/{app_id}.html")
    print(f"  4. Commit and push to deploy")


def reject(submission_id):
    pending = load_pending()
    for sub in pending[:]:
        if sub.get('id') == submission_id:
            pending.remove(sub)
            save_pending(pending)
            print(f"Rejected: {sub.get('name', 'Unknown')}")
            return
    print(f"Submission '{submission_id}' not found.")


def main():
    if len(sys.argv) < 2:
        list_pending()
        return

    command = sys.argv[1].lower()

    if command == "list":
        list_pending()
    elif command == "approve" and len(sys.argv) >= 3:
        approve(sys.argv[2])
    elif command == "reject" and len(sys.argv) >= 3:
        reject(sys.argv[2])
    else:
        print("Usage:")
        print("  python approve_app.py              # List pending")
        print("  python approve_app.py list         # List pending")
        print("  python approve_app.py approve ID   # Approve")
        print("  python approve_app.py reject ID    # Reject")


if __name__ == "__main__":
    main()
