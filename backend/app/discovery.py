import json,hashlib
from bs4 import BeautifulSoup
from openai import OpenAI
from dateutil.parser import parse as parse_date
from sqlalchemy import select
from .core import settings,SessionLocal,fingerprint,utcnow
from .models import Opportunity
from .advanced_models import Snapshot
from .adapters import SearxAdapter,request
from .intelligence import verification_score,add_recursive_sources
client=OpenAI(base_url=settings.llm_base_url,api_key=settings.llm_api_key or 'none');searx=SearxAdapter()
SCHEMA='''Return ONLY JSON object with: relevant(boolean), title, organizer, official_url, kind(one of bounty,competition,challenge,prize,grant,paid_pilot,procurement,tender,accelerator,fellowship,hackathon,research_call,bug_bounty,oss_bounty,data_competition,other), summary, categories(array), skills(array), countries(array), remote(boolean|null), reward(number|null), currency(string|null), deadline(ISO date|null), eligibility, confidence(0..1). Do not invent facts. Prefer facts explicitly present on this page.'''
def search_web(query,language='en',time_range=None):return searx.discover(query,language,time_range,pages=2)[:settings.max_results_per_query]
def fetch_text(url):
 r=request(url);soup=BeautifulSoup(r.text,'html.parser')
 for x in soup(['script','style','nav','footer']):x.decompose()
 return ' '.join(soup.stripped_strings)[:60000],str(r.url)
def extract(url,text):
 prompt=f'{SCHEMA}\nURL:{url}\nPAGE:\n{text[:35000]}';r=client.chat.completions.create(model=settings.llm_model,messages=[{'role':'system','content':'Extract public opportunity listings conservatively. Unknown facts must be null/empty.'},{'role':'user','content':prompt}],response_format={'type':'json_object'},temperature=0);return json.loads(r.choices[0].message.content)
def snapshot(s,o):
 data={'title':o.title,'organizer':o.organizer,'kind':o.kind,'reward':o.reward,'currency':o.currency,'deadline':o.deadline.isoformat() if o.deadline else None,'status':o.status,'confidence':o.confidence,'official_url':o.official_url};raw=json.dumps(data,sort_keys=True);h=hashlib.sha256(raw.encode()).hexdigest();last=s.scalar(select(Snapshot).where(Snapshot.opportunity_id==o.id).order_by(Snapshot.id.desc()).limit(1))
 if not last or last.content_hash!=h:s.add(Snapshot(opportunity_id=o.id,content_hash=h,data=data))
def ingest(url):
 text,final=fetch_text(url);d=extract(final,text)
 if not d.get('relevant') or not d.get('title'):return None
 fp=fingerprint(d['title'],d.get('organizer',''));deadline=None
 if d.get('deadline'):
  try:deadline=parse_date(d['deadline'])
  except Exception:pass
 with SessionLocal() as s:
  old=s.scalar(select(Opportunity).where(Opportunity.fingerprint==fp))
  if old:
   old.last_seen=utcnow();old.confidence=max(old.confidence,float(d.get('confidence') or 0));snapshot(s,old);s.commit();return old.id
  o=Opportunity(fingerprint=fp,title=d['title'],organizer=d.get('organizer') or '',url=final,official_url=d.get('official_url'),kind=d.get('kind') or 'other',summary=d.get('summary') or '',categories=d.get('categories') or [],skills=d.get('skills') or [],countries=d.get('countries') or [],remote=d.get('remote'),reward=d.get('reward'),currency=d.get('currency'),deadline=deadline,eligibility=d.get('eligibility') or '',confidence=float(d.get('confidence') or .5),evidence={'source':final})
  score,evidence=verification_score(o,text,final);o.trust=score;o.evidence={'source':final,'verification':evidence};s.add(o);s.flush();snapshot(s,o);oid=o.id;s.commit()
 try:add_recursive_sources(final)
 except Exception:pass
 return oid
