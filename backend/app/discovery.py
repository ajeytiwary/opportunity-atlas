import json, httpx
from bs4 import BeautifulSoup
from openai import OpenAI
from dateutil.parser import parse as parse_date
from sqlalchemy import select
from .core import settings, SessionLocal, fingerprint, utcnow
from .models import Opportunity

client=OpenAI(base_url=settings.llm_base_url,api_key=settings.llm_api_key or 'none')
SCHEMA='''Return ONLY JSON object with: relevant(boolean), title, organizer, official_url, kind(one of bounty,competition,challenge,prize,grant,paid_pilot,procurement,tender,accelerator,fellowship,hackathon,research_call,bug_bounty,oss_bounty,data_competition,other), summary, categories(array), skills(array), countries(array), remote(boolean|null), reward(number|null), currency(string|null), deadline(ISO date|null), eligibility, confidence(0..1). Do not invent facts.'''

def search_web(query,language='en',time_range=None):
 params={'q':query,'format':'json','language':language,'safesearch':1}
 if time_range: params['time_range']=time_range
 with httpx.Client(timeout=30,follow_redirects=True) as h:
  r=h.get(f'{settings.searxng_url}/search',params=params); r.raise_for_status()
  return r.json().get('results',[])[:settings.max_results_per_query]

def fetch_text(url):
 with httpx.Client(timeout=20,follow_redirects=True,headers={'User-Agent':'OpportunityAtlas/0.1'}) as h:
  r=h.get(url); r.raise_for_status(); soup=BeautifulSoup(r.text,'html.parser')
  for x in soup(['script','style','nav','footer']): x.decompose()
  return ' '.join(soup.stripped_strings)[:50000],str(r.url)

def extract(url,text):
 prompt=f'{SCHEMA}\nURL:{url}\nPAGE:\n{text[:30000]}'
 r=client.chat.completions.create(model=settings.llm_model,messages=[{'role':'system','content':'You extract and verify public opportunity listings conservatively.'},{'role':'user','content':prompt}],response_format={'type':'json_object'},temperature=0)
 return json.loads(r.choices[0].message.content)

def ingest(url):
 text,final=fetch_text(url); d=extract(final,text)
 if not d.get('relevant') or not d.get('title'): return None
 fp=fingerprint(d['title'],d.get('organizer',''))
 with SessionLocal() as s:
  old=s.scalar(select(Opportunity).where(Opportunity.fingerprint==fp))
  if old: old.last_seen=utcnow(); old.confidence=max(old.confidence,float(d.get('confidence') or 0)); s.commit(); return old.id
  deadline=None
  if d.get('deadline'):
   try: deadline=parse_date(d['deadline'])
   except Exception: pass
  o=Opportunity(fingerprint=fp,title=d['title'],organizer=d.get('organizer') or '',url=final,official_url=d.get('official_url'),kind=d.get('kind') or 'other',summary=d.get('summary') or '',categories=d.get('categories') or [],skills=d.get('skills') or [],countries=d.get('countries') or [],remote=d.get('remote'),reward=d.get('reward'),currency=d.get('currency'),deadline=deadline,eligibility=d.get('eligibility') or '',confidence=float(d.get('confidence') or .5),evidence={'source':final})
  s.add(o); s.commit(); return o.id
