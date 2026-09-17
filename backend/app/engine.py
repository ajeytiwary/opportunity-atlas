import json
from datetime import timedelta
from openai import OpenAI
from sqlalchemy import select
from .core import SessionLocal, settings, utcnow
from .models import Campaign, Run, Opportunity, Profile, Match
from .discovery import search_web, ingest
client=OpenAI(base_url=settings.llm_base_url,api_key=settings.llm_api_key or 'none')

def expand_queries(c):
 base=c.queries or [c.description]
 prompt='Generate diverse multilingual web searches for this opportunity campaign. Include synonyms: grants, prizes, bounties, open calls, tenders, paid pilots, hackathons, challenges. Return JSON {"queries":[{"q":"...","language":"en"}]}. Campaign: '+c.description+' Seeds:'+json.dumps(base)+' Languages:'+json.dumps(c.languages)
 try:
  r=client.chat.completions.create(model=settings.llm_model,messages=[{'role':'user','content':prompt}],response_format={'type':'json_object'},temperature=.4)
  generated=json.loads(r.choices[0].message.content).get('queries',[])
 except Exception: generated=[]
 return [{'q':q,'language':'en'} for q in base]+generated[:60]

def execute_run(run_id):
 with SessionLocal() as s:
  run=s.get(Run,run_id); c=s.get(Campaign,run.campaign_id); run.status='running'; run.started_at=utcnow(); s.commit()
  stats={'queries':0,'results':0,'ingested':0,'errors':0}
  seen=set()
  try:
   for item in expand_queries(c):
    stats['queries']+=1
    try: results=search_web(item['q'],item.get('language','en'),'month' if c.cadence in ('daily','weekly') else None)
    except Exception: stats['errors']+=1; continue
    for r in results:
     url=r.get('url'); stats['results']+=1
     if not url or url in seen: continue
     seen.add(url)
     try:
      if ingest(url): stats['ingested']+=1
     except Exception: stats['errors']+=1
   run.status='done'
  except Exception as e: run.status='failed'; run.error=str(e)
  run.stats=stats; run.finished_at=utcnow(); s.commit()
  recompute_matches()

def recompute_matches():
 with SessionLocal() as s:
  profiles=s.scalars(select(Profile)).all(); ops=s.scalars(select(Opportunity).where(Opportunity.status=='open')).all()
  for p in profiles:
   for o in ops:
    skill=set(x.lower() for x in p.skills); oskill=set(x.lower() for x in o.skills+o.categories); overlap=skill&oskill
    skill_score=len(overlap)/max(1,len(skill)); reward_score=1 if (o.reward or 0)>=p.min_reward else .2; trust=(o.confidence+o.trust)/2
    score=round(100*(.55*skill_score+.2*reward_score+.25*trust),1)
    m=s.scalar(select(Match).where(Match.profile_id==p.id,Match.opportunity_id==o.id))
    reasons=[f'Matched: {x}' for x in sorted(overlap)][:5]
    if m: m.score=score; m.reasons=reasons
    else: s.add(Match(profile_id=p.id,opportunity_id=o.id,score=score,reasons=reasons))
  s.commit()

def schedule_next(c):
 now=utcnow(); return now+({'daily':timedelta(days=1),'weekly':timedelta(days=7),'monthly':timedelta(days=30)}.get(c.cadence,timedelta(days=7)))
