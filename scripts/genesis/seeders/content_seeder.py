from datetime import datetime, timedelta
from api.models.user import User
from api.models.sermon import Sermon
from api.models.prayer import Prayer, PrayerReaction, PrayerComment, PrayerBookmark
from scripts.genesis.utils import result

SERMONS=[("Walking by Faith","2 Corinthians 5:7"),("The Power of Prayer","James 5:16"),("Grace for Every Season","2 Corinthians 12:9"),("A Heart of Worship","John 4:23-24"),("Hope That Does Not Disappoint","Romans 5:5"),("Living with Purpose","Ephesians 2:10"),("Forgiveness and Freedom","Colossians 3:13"),("Strength in the Storm","Isaiah 41:10"),("Serving with Humility","Philippians 2:3-4"),("The Great Commission","Matthew 28:18-20")]
PRAYERS=[("Healing","Please pray for healing and renewed strength."),("Family","Please pray for peace and unity in my family."),("Employment","Please pray for an open door for employment."),("Guidance","Please pray for wisdom in an important decision."),("Thanksgiving","I thank God for answered prayer."),("Missions","Please pray for missionaries serving vulnerable communities."),("Students","Please pray for students preparing for examinations."),("Church Growth","Please pray for spiritual growth in our church."),("Grief","Please pray for comfort for a grieving family."),("Marriage","Please pray for restoration and grace in a marriage."),("Children","Please pray for protection and wisdom for our children."),("Finances","Please pray for responsible stewardship and provision."),("Anxiety","Please pray for peace of mind and freedom from fear."),("Community","Please pray for peace and opportunity in our community."),("Ministry","Please pray for strength for church leaders and volunteers.")]

def seed_sermons(db, dry_run):
    out=result(); pastors=db.query(User).filter(User.role=="pastor").order_by(User.id).all()
    if dry_run and not pastors: return result(created=100)
    for pi,p in enumerate(pastors[:10]):
        for si,(base,verse) in enumerate(SERMONS):
            title=f"{base} — {p.name}"
            if db.query(Sermon).filter(Sermon.author_id==p.id,Sermon.title==title).first(): out["existing"]+=1; continue
            out["created"]+=1
            if not dry_run:
                dt=datetime.utcnow()-timedelta(days=pi*3+si*2)
                content=f"{base}\n\nPrimary Scripture: {verse}\n\nGod is faithful. Faith grows through obedience, prayer, love, and service.\n\nApplication: take one concrete step of faith this week."
                db.add(Sermon(title=title,scripture=verse,content=content,sermon_data={"genesis_seed":True},author_id=p.id,is_public=1,created_at=dt,updated_at=dt,views=20+(pi+1)*(si+3),shares=(pi+si)%8))
    if not dry_run: db.flush()
    return out

def seed_prayers(db, dry_run):
    out=result(); users=db.query(User).order_by(User.id).all()
    if dry_run and not users: return result(created=75)
    if not users: return result(skipped=75)
    for i in range(75):
        owner=users[i%len(users)]; cat,msg=PRAYERS[i%len(PRAYERS)]; message=f"{msg} [Genesis #{i+1:03d}]"
        if db.query(Prayer).filter(Prayer.user_id==owner.id,Prayer.message==message).first(): out["existing"]+=1; continue
        out["created"]+=1
        if dry_run: continue
        dt=datetime.utcnow()-timedelta(days=i%35,hours=i%20); answered=i%11==0
        p=Prayer(user_id=owner.id,user_name=owner.name,message=message,category=cat,visibility="community",status="answered" if answered else "still_praying",is_anonymous=i%13==0,created_at=dt,updated_at=dt,answered_at=dt+timedelta(days=4) if answered else None,answer_testimony="God provided encouragement and a clear next step." if answered else None,testimony_shared_at=dt+timedelta(days=4) if answered else None)
        db.add(p); db.flush()
        reactors=[u for u in users if u.id!=owner.id][:2+(i%4)]
        for j,u in enumerate(reactors): db.add(PrayerReaction(prayer_id=p.id,user_id=u.id,reaction_type="pray" if j%2==0 else "support",created_at=dt+timedelta(hours=j+1)))
        commenters=reactors[:1+(i%3)]
        for j,u in enumerate(commenters): db.add(PrayerComment(prayer_id=p.id,user_id=u.id,user_name=u.name,comment="Praying with you. May God give you peace and strength.",is_pastor_response=u.role=="pastor",created_at=dt+timedelta(hours=j+2),updated_at=dt+timedelta(hours=j+2)))
        for u in reactors[:i%3]: db.add(PrayerBookmark(prayer_id=p.id,user_id=u.id,created_at=dt+timedelta(hours=3)))
        p.prayer_count=sum(1 for j in range(len(reactors)) if j%2==0); p.support_count=len(reactors)-p.prayer_count; p.comment_count=len(commenters); p.share_count=i%5
    if not dry_run: db.flush()
    return out
