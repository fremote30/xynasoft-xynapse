from importlib import import_module
from api.models.user import User
from scripts.genesis.utils import result

def get_model():
    for module in ["api.models.pastor_member","api.models.pastormember","api.models.follow"]:
        try: return getattr(import_module(module), "PastorMember")
        except (ImportError, AttributeError): pass
    raise ImportError("PastorMember model file not found. Add its module path in follow_seeder.py")

def seed_follows(db, dry_run):
    Model=get_model(); out=result(); pastors=db.query(User).filter(User.role=="pastor").order_by(User.id).all(); members=db.query(User).filter(User.role=="member").order_by(User.id).all()
    if dry_run and (not pastors or not members): return result(created=150)
    for i,m in enumerate(members[:50]):
        for p in {x.id:x for x in [pastors[i%len(pastors)],pastors[(i+3)%len(pastors)],pastors[(i+6)%len(pastors)]]}.values():
            if db.query(Model).filter(Model.pastor_id==p.id,Model.member_id==m.id).first(): out["existing"]+=1; continue
            out["created"]+=1
            if not dry_run: db.add(Model(pastor_id=p.id,member_id=m.id))
    if not dry_run: db.flush()
    return out
