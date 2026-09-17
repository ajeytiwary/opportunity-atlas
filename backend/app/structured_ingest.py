from __future__ import annotations
import re
from sqlalchemy import select
from .core import SessionLocal,fingerprint,utcnow
from .models import Opportunity
from .portal_adapters import run_adapter

def _reward(text):
 if not text:return (None,None)
 s=str(text).replace(',','');m=re.search(r'([$€£])\s*([0-9]+(?:\.\d+)?)\s*([kKmM]?)',s)
 if m:return float(m.group(2))*({'k':1e3,'m':1e6}.get(m.group(3).lower(),1)),{'$':'USD','€':'EUR','£':'GBP'}[m.group(1)]
 m=re.search(r'([0-9]+(?:\.\d+)?)',s)
 return (float(m.group(1)),None) if m else (None,None)
def upsert_candidate(x):
 if not x.get('title') or not x.get('url'):return None
 fp=fingerprint(x['title'],x.get('organizer',''))
 with SessionLocal() as s:
  o=s.scalar(select(Opportunity).where(Opportunity.fingerprint==fp));reward,currency=_reward(x.get('reward_text'))
  confidence=.97 if x.get('kind')!='historical_grant' else .99
  if o:
   o.last_seen=utcnow();o.official_url=o.official_url or x.get('official_url');o.confidence=max(o.confidence,confidence);o.trust=max(o.trust,.97);ev=dict(o.evidence or {});sources=list(ev.get('structured_sources',[]));sources.append({'adapter':x.get('source_adapter'),'external_id':x.get('external_id'),'raw':x.get('raw',{})});ev['structured_sources']=sources[-10:];o.evidence=ev;s.commit();return o.id
  status='historical' if x.get('kind')=='historical_grant' else x.get('status') or 'open'
  o=Opportunity(fingerprint=fp,title=x['title'],organizer=x.get('organizer') or '',url=x['url'],official_url=x.get('official_url'),kind=x.get('kind') or 'other',summary=x.get('summary') or '',categories=x.get('categories') or [],skills=x.get('skills') or [],countries=x.get('countries') or [],reward=reward,currency=currency,eligibility=x.get('eligibility') or '',confidence=confidence,trust=.97,status=status,evidence={'structured_sources':[{'adapter':x.get('source_adapter'),'external_id':x.get('external_id'),'raw':x.get('raw',{})}]});s.add(o);s.commit();return o.id
def ingest_adapter(name,query=''):
 stats={'adapter':name,'query':query,'found':0,'upserted':0,'errors':0}
 try:rows=run_adapter(name,query)
 except Exception as e:stats.update(error=str(e),errors=1);return stats
 stats['found']=len(rows)
 for x in rows:
  try:
   if upsert_candidate(x):stats['upserted']+=1
  except Exception:stats['errors']+=1
 return stats
def run_priority_adapters(queries=None):
 queries=queries or ['','AI','climate','biodiversity','innovation','technology','remote sensing'];result=[]
 plans={'grants_gov':queries,'eu_funding_tenders':queries,'rvo':['','innovatie','duurzaamheid','AI','biodiversiteit'],'kaggle':['','AI','climate'],'ukri':['','AI','climate','biodiversity'],'github_issues':['bounty reward','paid bounty','reward prize'],'ted':['publication-date >= 20260101'],'nasa':['','challenge'],'nasa_stmd':['','opportunity'],'nwo_projects':['climate','biodiversity','AI'],'nsf_awards':['climate','biodiversity','artificial intelligence']}
 for name,qs in plans.items():
  for q in qs:result.append(ingest_adapter(name,q))
 return result
