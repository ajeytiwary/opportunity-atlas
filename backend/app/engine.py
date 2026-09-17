import json
from datetime import timedelta
from openai import OpenAI
from sqlalchemy import select
from .core import SessionLocal,settings,utcnow
from .models import Campaign,Run,Opportunity,Profile,Match
from .advanced_models import QueryMetric
from .discovery import search_web,ingest
from .source_factory import registry_queries
from .portal_registry import discovery_queries
from .structured_ingest import run_priority_adapters
from .watch import evaluate_watchlists
client=OpenAI(base_url=settings.llm_base_url,api_key=settings.llm_api_key or 'none')
def expand_queries(c):
 base=[{'q':q,'language':'en'} for q in (c.queries or [c.description])]
 prompt='Generate diverse multilingual searches for grants prizes bounties open calls tenders paid pilots hackathons and challenges. Return JSON {"queries":[{"q":"...","language":"en"}]}. Campaign:'+c.description+' Seeds:'+json.dumps(c.queries)+' Languages:'+json.dumps(c.languages)
 try:
  r=client.chat.completions.create(model=settings.llm_model,messages=[{'role':'user','content':prompt}],response_format={'type':'json_object'},temperature=.4);gen=json.loads(r.choices[0].message.content).get('queries',[])
 except Exception:gen=[]
 extra=registry_queries() if 'Global' in c.name else []
 portal=discovery_queries() if ('Global' in c.name or 'Opportunity' in c.name) else []
 with SessionLocal() as s:
  metrics=s.scalars(select(QueryMetric).where(QueryMetric.campaign_id==c.id).order_by(QueryMetric.score.desc()).limit(50)).all();learned=[{'q':m.query,'language':m.language} for m in metrics]
 seen=set();out=[]
 for x in base+learned+gen[:80]+portal+extra[:900]:
  k=(x.get('q'),x.get('language','en'))
  if k[0] and k not in seen:seen.add(k);out.append(x)
 return out
def metric(cid,q,lang,results,new,errors):
 with SessionLocal() as s:
  m=s.scalar(select(QueryMetric).where(QueryMetric.campaign_id==cid,QueryMetric.query==q,QueryMetric.language==lang))
  if not m:m=QueryMetric(campaign_id=cid,query=q,language=lang);s.add(m)
  m.runs+=1;m.results+=results;m.new_items+=new;m.errors+=errors;m.last_run=utcnow();m.score=max(.05,min(1,(m.new_items+1)/(m.results+5)*(1/(1+m.errors/max(1,m.runs)))));s.commit()
def execute_run(run_id):
 with SessionLocal() as s:run=s.get(Run,run_id);c=s.get(Campaign,run.campaign_id);run.status='running';run.started_at=utcnow();s.commit()
 stats={'queries':0,'results':0,'ingested':0,'errors':0,'structured':[]};seen=set()
 try:
  # Structured official APIs run first; these records receive high provenance/trust scores.
  if 'Global' in c.name:
   stats['structured']=run_priority_adapters(['','AI','climate','biodiversity','innovation'])
   stats['ingested']+=sum(x.get('upserted',0) for x in stats['structured'])
   stats['errors']+=sum(x.get('errors',0) for x in stats['structured'])
  for item in expand_queries(c):
   q=item['q'];lang=item.get('language','en');stats['queries']+=1;qr=qn=qe=0
   try:results=search_web(q,lang,'month' if c.cadence in ('daily','weekly') else None);qr=len(results)
   except Exception:stats['errors']+=1;metric(c.id,q,lang,0,0,1);continue
   for r in results:
    url=r.get('url');stats['results']+=1
    if not url or url in seen:continue
    seen.add(url)
    try:
     if ingest(url):stats['ingested']+=1;qn+=1
    except Exception:stats['errors']+=1;qe+=1
   metric(c.id,q,lang,qr,qn,qe)
  run.status='done'
 except Exception as e:run.status='failed';run.error=str(e)
 with SessionLocal() as s:run=s.get(Run,run_id);run.stats=stats;run.finished_at=utcnow();s.commit()
 recompute_matches();evaluate_watchlists()
def recompute_matches():
 with SessionLocal() as s:
  profiles=s.scalars(select(Profile)).all();ops=s.scalars(select(Opportunity).where(Opportunity.status=='open')).all()
  for p in profiles:
   for o in ops:
    skill=set(x.lower() for x in p.skills);oskill=set(x.lower() for x in o.skills+o.categories);overlap=skill&oskill;skill_score=len(overlap)/max(1,len(skill));reward_score=1 if (o.reward or 0)>=p.min_reward else .2;trust=(o.confidence+o.trust)/2;score=round(100*(.55*skill_score+.2*reward_score+.25*trust),1);m=s.scalar(select(Match).where(Match.profile_id==p.id,Match.opportunity_id==o.id));reasons=[f'Matched: {x}' for x in sorted(overlap)][:5]
    if m:m.score=score;m.reasons=reasons
    else:s.add(Match(profile_id=p.id,opportunity_id=o.id,score=score,reasons=reasons))
  s.commit()
def schedule_next(c):return utcnow()+({'daily':timedelta(days=1),'weekly':timedelta(days=7),'monthly':timedelta(days=30)}.get(c.cadence,timedelta(days=7)))
