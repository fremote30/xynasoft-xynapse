from api.models.church import Church
from scripts.genesis.utils import result

def seed_churches(db, records, dry_run):
    out = result()
    for r in records:
        row = db.query(Church).filter(Church.name == r["name"]).first()
        if row:
            out["existing"] += 1
            continue
        out["created"] += 1
        if not dry_run:
            db.add(Church(name=r["name"], location=r.get("location")))
    if not dry_run:
        db.flush()
    return out
