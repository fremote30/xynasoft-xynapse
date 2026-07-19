from datetime import datetime
from api.core.security import hash_password
from api.models.church import Church
from api.models.user import User
from scripts.genesis.utils import result

def seed_users(db, records, dry_run):
    out = result()
    for r in records:
        email = r["email"].lower()
        if db.query(User).filter(User.email == email).first():
            out["existing"] += 1
            continue
        church = db.query(Church).filter(Church.name == r["church"]).first()
        if not church:
            out["skipped"] += 1
            continue
        out["created"] += 1
        if not dry_run:
            pastor = r["role"] == "pastor"
            db.add(User(name=r["name"], email=email, password=hash_password(r["password"]), role=r["role"], is_verified=True, church_id=church.id, pastor_status="approved" if pastor else "member", pastor_application_date=datetime.utcnow() if pastor else None, pastor_review_date=datetime.utcnow() if pastor else None, pastor_review_notes="Genesis Community seed account" if pastor else None))
    if not dry_run:
        db.flush()
    return out
