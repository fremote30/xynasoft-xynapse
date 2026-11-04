import argparse, sys
from pathlib import Path
PROJECT_ROOT=Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path: sys.path.insert(0,str(PROJECT_ROOT))
from api.db.database import SessionLocal
import api.models
from scripts.genesis.utils import load_json
from scripts.genesis.seeders.church_seeder import seed_churches
from scripts.genesis.seeders.user_seeder import seed_users
from scripts.genesis.seeders.content_seeder import seed_sermons, seed_prayers
from scripts.genesis.seeders.follow_seeder import seed_follows

def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--commit",action="store_true"); args=parser.parse_args(); dry=not args.commit
    print("XynaFaith Genesis Community — Wave 1"); print("MODE:","DRY RUN" if dry else "COMMIT")
    db=SessionLocal()
    try:
        results={}
        results["Churches"]=seed_churches(db,load_json("churches.json"),dry)
        if not dry: db.flush()
        results["Users"]=seed_users(db,load_json("pastors.json")+load_json("members.json"),dry)
        if not dry: db.flush()
        results["Sermons"]=seed_sermons(db,dry); results["Prayers"]=seed_prayers(db,dry); results["Follows"]=seed_follows(db,dry)
        for name,r in results.items(): print(f"{name}: created={r['created']}, existing={r['existing']}, skipped={r['skipped']}")
        if dry: db.rollback(); print("Dry run complete. No records were written.")
        else: db.commit(); print("Genesis Community created successfully.")
    except Exception:
        db.rollback(); raise
    finally: db.close()
if __name__=="__main__": main()
