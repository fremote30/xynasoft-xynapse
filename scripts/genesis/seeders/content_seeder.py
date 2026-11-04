from datetime import datetime, timedelta
from api.models.user import User
from api.models.sermon import Sermon
from api.models.prayer import Prayer, PrayerReaction, PrayerComment, PrayerBookmark
from scripts.genesis.utils import result

SERMONS=[("Walking by Faith","2 Corinthians 5:7"),("The Power of Prayer","James 5:16"),("Grace for Every Season","2 Corinthians 12:9"),("A Heart of Worship","John 4:23-24"),("Hope That Does Not Disappoint","Romans 5:5"),("Living with Purpose","Ephesians 2:10"),("Forgiveness and Freedom","Colossians 3:13"),("Strength in the Storm","Isaiah 41:10"),("Serving with Humility","Philippians 2:3-4"),("The Great Commission","Matthew 28:18-20")]
PRAYERS=[("Healing","Please pray for healing and renewed strength."),("Family","Please pray for peace and unity in my family."),("Employment","Please pray for an open door for employment."),("Guidance","Please pray for wisdom in an important decision."),("Thanksgiving","I thank God for answered prayer."),("Missions","Please pray for missionaries serving vulnerable communities."),("Students","Please pray for students preparing for examinations."),("Church Growth","Please pray for spiritual growth in our church."),("Grief","Please pray for comfort for a grieving family."),("Marriage","Please pray for restoration and grace in a marriage."),("Children","Please pray for protection and wisdom for our children."),("Finances","Please pray for responsible stewardship and provision."),("Anxiety","Please pray for peace of mind and freedom from fear."),("Community","Please pray for peace and opportunity in our community."),("Ministry","Please pray for strength for church leaders and volunteers.")]


PASTOR_ENCOURAGEMENTS = {
    "Healing": [
        "Praying that God brings healing, renewed strength, and peace through this season.",
        "May the Lord sustain you with strength and surround you with His healing grace.",
        "Standing with you in prayer for restoration, comfort, and renewed health.",
    ],
    "Family": [
        "May God bring patience, understanding, and unity to your family.",
        "Praying for peace in your home and wisdom for every conversation.",
        "May the Lord restore relationships and strengthen your family with grace.",
    ],
    "Employment": [
        "Praying that God opens the right door and gives you wisdom for each opportunity.",
        "May the Lord provide meaningful work and guide you toward the right next step.",
        "Standing with you in prayer for provision, favor, and clarity.",
    ],
    "Guidance": [
        "May God give you clarity, wisdom, and peace as you make this decision.",
        "Praying that the Lord directs your steps and confirms the right path.",
        "May you discern God's leading with confidence and patience.",
    ],
    "Thanksgiving": [
        "We rejoice with you and thank God for His faithfulness.",
        "Praise God for this testimony. May it strengthen the faith of others too.",
        "Giving thanks with you for God's goodness and answered prayer.",
    ],
    "Missions": [
        "Praying for protection, strength, and open doors for those serving in mission.",
        "May God encourage every missionary and provide for the communities they serve.",
        "Standing in prayer for courage, provision, and lasting impact.",
    ],
    "Students": [
        "Praying for focus, confidence, wisdom, and peace during examinations.",
        "May God strengthen every student and help them remember what they have learned.",
        "Praying for discipline, calm minds, and good results.",
    ],
    "Church Growth": [
        "May God deepen discipleship, unity, and spiritual maturity in your church.",
        "Praying that your church grows in faith, love, and service to the community.",
        "May the Lord strengthen your congregation and raise up faithful leaders.",
    ],
    "Grief": [
        "Praying that God's presence brings comfort and strength to your family.",
        "May the Lord hold you close and give you peace in this season of loss.",
        "Standing with you in prayer for comfort, hope, and healing through grief.",
    ],
    "Marriage": [
        "Praying for grace, humility, forgiveness, and restoration in this marriage.",
        "May God renew love, patience, and understanding between you.",
        "Standing with you in prayer for healing, wisdom, and reconciliation.",
    ],
    "Children": [
        "May God protect your children and guide them with wisdom and grace.",
        "Praying for their safety, growth, and strong faith.",
        "May the Lord surround your children with good influences and wise direction.",
    ],
    "Finances": [
        "Praying for provision, wisdom, and faithful stewardship.",
        "May God meet your needs and give you clarity in every financial decision.",
        "Standing with you in prayer for stability, provision, and wise planning.",
    ],
    "Anxiety": [
        "May God's peace guard your heart and mind and replace fear with confidence.",
        "Praying for calm, rest, and freedom from anxiety.",
        "May you experience God's presence and peace one day at a time.",
    ],
    "Community": [
        "Praying for peace, opportunity, justice, and flourishing in your community.",
        "May God raise up wise leaders and strengthen families throughout your community.",
        "Standing in prayer for unity, safety, and new opportunities.",
    ],
    "Ministry": [
        "Praying for renewed strength, wisdom, and joy for every ministry leader and volunteer.",
        "May God sustain those serving and give them fresh vision and endurance.",
        "Praying for healthy leadership, faithful service, and lasting ministry fruit.",
    ],
}

MEMBER_COMMENTS = [
    "Praying with you.",
    "Standing with you in prayer today.",
    "May God give you strength and peace.",
    "Keeping this request in prayer.",
    "Believing with you for God's help and guidance.",
    "You are in my prayers.",
]

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
    out=result()
    users=(
        db.query(User)
        .filter(User.email.ilike("%@genesis.xynafaith.com"))
        .order_by(User.id)
        .all()
    )
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
        for j,u in enumerate(commenters):
            if u.role=="pastor":
                choices=PASTOR_ENCOURAGEMENTS.get(cat, MEMBER_COMMENTS)
                comment_text=choices[(i+j)%len(choices)]
            else:
                comment_text=MEMBER_COMMENTS[(i+j)%len(MEMBER_COMMENTS)]

            db.add(
                PrayerComment(
                    prayer_id=p.id,
                    user_id=u.id,
                    user_name=u.name,
                    comment=comment_text,
                    is_pastor_response=u.role=="pastor",
                    created_at=dt+timedelta(hours=j+2),
                    updated_at=dt+timedelta(hours=j+2)
                )
            )
        for u in reactors[:i%3]: db.add(PrayerBookmark(prayer_id=p.id,user_id=u.id,created_at=dt+timedelta(hours=3)))
        p.prayer_count=sum(1 for j in range(len(reactors)) if j%2==0); p.support_count=len(reactors)-p.prayer_count; p.comment_count=len(commenters); p.share_count=i%5
    if not dry_run: db.flush()
    return out
