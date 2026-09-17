from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from .core import SessionLocal
from .models import Opportunity
from .advanced_models import Watchlist,Alert
def matches(o,f):
 if f.get('kinds') and o.kind not in f['kinds']:return False
 if f.get('min_reward') and (o.reward or 0)<float(f['min_reward']):return False
 if f.get('min_confidence') and o.confidence<float(f['min_confidence']):return False
 if f.get('remote') is True and o.remote is not True:return False
 cats=set(x.lower() for x in o.categories+o.skills)
 if f.get('keywords') and not cats.intersection(x.lower() for x in f['keywords']):return False
 if f.get('countries') and o.countries and not set(f['countries']).intersection(o.countries):return False
 return True
def evaluate_watchlists():
 with SessionLocal() as s:
  lists=s.scalars(select(Watchlist).where(Watchlist.enabled==True)).all();ops=s.scalars(select(Opportunity).where(Opportunity.status=='open')).all();n=0
  for w in lists:
   for o in ops:
    if matches(o,w.filters):
     a=Alert(watchlist_id=w.id,opportunity_id=o.id,message=f'{o.title} matches {w.name}')
     s.add(a)
     try:s.flush();n+=1
     except IntegrityError:s.rollback()
  s.commit();return n
