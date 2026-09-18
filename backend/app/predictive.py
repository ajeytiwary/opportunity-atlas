from __future__ import annotations
import hashlib,re,statistics
from collections import defaultdict
from datetime import timedelta
from sqlalchemy import select
from .core import SessionLocal,utcnow
from .models import Opportunity
from .predictive_models import ProgramFamily,PredictiveAlert

STOP={'2024','2025','2026','2027','call','open','funding','grant','award','competition','challenge','programme','program','round','phase','applications','opportunity'}
def family_name(title):
 s=re.sub(r'\b(19|20)\d{2}\b',' ',title.lower());s=re.sub(r'\b(round|phase|call)\s*\d+\b',' ',s);s=re.sub(r'[^a-z0-9]+',' ',s)
 toks=[x for x in s.split() if x not in STOP and len(x)>2]
 return ' '.join(toks[:12]) or title.lower()[:120]
def family_key(op):
 base=f"{op.organizer.lower().strip()}|{op.kind}|{family_name(op.title)}"
 return hashlib.sha256(base.encode()).hexdigest()
def event_date(o):return o.deadline or o.first_seen
def recompute_families(min_members=2):
 now=utcnow();groups=defaultdict(list)
 with SessionLocal() as s:
  for o in s.scalars(select(Opportunity)).all():groups[family_key(o)].append(o)
  changed=0
  for key,rows in groups.items():
   if len(rows)<min_members:continue
   dates=sorted({event_date(x) for x in rows if event_date(x)})
   if len(dates)<2:continue
   gaps=[(b-a).days for a,b in zip(dates,dates[1:]) if (b-a).days>7]
   if not gaps:continue
   median=statistics.median(gaps);mad=statistics.median([abs(x-median) for x in gaps]) if len(gaps)>1 else median*.2
   periodic=(20<=median<=45) or (70<=median<=120) or (250<=median<=450) or (500<=median<=800)
   if not periodic:continue
   confidence=min(.95,.35+.1*len(dates)+.25*max(0,1-(mad/max(median,1))))
   expected=dates[-1]+timedelta(days=median);half=max(14,min(60,int(max(mad,median*.08))))
   fam=s.scalar(select(ProgramFamily).where(ProgramFamily.key==key))
   vals=dict(name=family_name(rows[-1].title),organizer=rows[-1].organizer,kind=rows[-1].kind,members=len(rows),interval_days=float(median),interval_std_days=float(mad),next_expected=expected,window_start=expected-timedelta(days=half),window_end=expected+timedelta(days=half),confidence=confidence,features={'dates':[d.isoformat() for d in dates[-10:]],'gaps':gaps[-10:]},updated_at=now)
   if fam:
    for k,v in vals.items():setattr(fam,k,v)
   else:s.add(ProgramFamily(key=key,**vals))
   if confidence>=.6 and expected>=now-timedelta(days=30) and expected<=now+timedelta(days=120):
    msg=f"{rows[-1].organizer}: {family_name(rows[-1].title)} is expected around {expected.date()} (historical interval ~{round(median)} days; confidence {round(confidence*100)}%)."
    if not s.scalar(select(PredictiveAlert).where(PredictiveAlert.family_key==key,PredictiveAlert.kind=='expected_reopening',PredictiveAlert.expected_at==expected)):s.add(PredictiveAlert(family_key=key,message=msg,expected_at=expected,confidence=confidence))
   changed+=1
  s.commit();return changed
