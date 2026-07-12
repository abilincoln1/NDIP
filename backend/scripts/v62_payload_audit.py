import sys,time,json
sys.path.insert(0,'/app')
import redis
r=redis.Redis(host='redis',port=6379,decode_responses=True)
from app.db.database import SessionLocal
db=SessionLocal()
auth={"email":"admin@agora.rtifn.org"}

def audit(name,fn):
    [r.delete(k) for k in r.keys("agora:*")]
    t=time.time()
    result=fn()
    bt=time.time()-t
    st=time.time()
    payload=json.dumps(result,default=str)
    st=time.time()-st
    kb=len(payload.encode())/1024
    print(f"{name}: backend={bt:.2f}s serialise={st*1000:.1f}ms payload={kb:.0f}KB keys={len(result) if isinstance(result,dict) else len(result)}")
    return result

from app.api.routes.leadership_pack import leadership_pack
lp=audit("Leadership Pack",lambda: leadership_pack(days=30,db=db,_=auth))
from app.services.narrative_intelligence import generate_situation_room
audit("Situation Room",lambda: generate_situation_room(db,days=30))
from app.api.routes.strategic_outcome import strategic_outcome_dashboard
audit("SOI Dashboard",lambda: strategic_outcome_dashboard(days=30,db=db,_=auth))
db.close()
