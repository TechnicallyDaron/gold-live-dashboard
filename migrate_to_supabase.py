"""
ONE-TIME migration: JSON files → Supabase. Run LOCALLY from repo root:
  SUPABASE_URL=... SUPABASE_SERVICE_KEY=... OPERATOR_USER_ID=<your-auth-uuid> \
  python3 migrate_to_supabase.py
Find your auth uuid: Supabase → Authentication → Users → your row → UID.
Idempotent-ish: skips watchlist names that already exist for the user.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api import db  # noqa: E402

UID = os.getenv("OPERATOR_USER_ID", "")

def main():
    if not db.enabled() or not UID:
        sys.exit("Set SUPABASE_URL, SUPABASE_SERVICE_KEY, OPERATOR_USER_ID first.")

    existing = {r["display_name"] for r in db.select("watchlists", {"user_id": UID})}
    wl = json.load(open("watchlist.json"))
    added = 0
    for i, (name, d) in enumerate(wl.items()):
        if name in existing:
            continue
        db.insert("watchlists", {"user_id": UID, "display_name": name,
                                 "ticker": d["ticker"], "unit": d.get("unit", "/sh"),
                                 "priority": i})
        added += 1
    print(f"watchlist: {added} inserted, {len(existing)} already present")

    pos = json.load(open("positions.json"))
    for pid, p in pos.items():
        ep = p.get("entry_premium") or p.get("premium_paid") or p.get("entry")
        if not (ep and p.get("entry_date")):
            print(f"SKIP {pid}: needs entry_premium + entry_date")
            continue
        db.insert("positions", {
            "user_id": UID, "asset": p.get("asset", "?"),
            "contract_type": p.get("type", "call"), "strike": p.get("strike", 0),
            "entry_premium": ep, "entry_date": p["entry_date"],
            "expiration": p.get("expiration"), "premium_stop": p.get("premium_stop"),
            "time_stop": p.get("time_stop"),
            "invalidation_above": p.get("invalidation_above"),
            "invalidation_below": p.get("invalidation_below"),
        })
        print(f"position migrated: {pid}")
    print("Done. The database is now the source of truth.")

if __name__ == "__main__":
    main()
