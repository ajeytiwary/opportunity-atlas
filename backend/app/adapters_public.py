"""Verified public-data and official-page adapters."""
from __future__ import annotations
import re
from urllib.parse import urljoin
import httpx
from bs4 import BeautifulSoup
UA={"User-Agent":"OpportunityAtlas/0.7 (+public opportunity indexer)"}
def _rows(p):
 if isinstance(p,list):return p
 if not isinstance(p,dict):return []
 for k in ('items','results','data','subsidies','regelingen','opportunities','records'):
  v=p.get(k)
  if isinstance(v,list):return v
  if isinstance(v,dict):
   for kk in ('items','results','records'):
    if isinstance(v.get(kk),list):return v[kk]
 return []
def rvo(query:str='',limit:int=500):
 with httpx.Client(timeout=60,headers=UA,follow_redirects=True) as h:r=h.get('https://www.rvo.nl/api/v1/opendata/subsidies');r.raise_for_status();rows=_rows(r.json())
 out=[]
 for x in rows[:limit]:
  title=x.get('title') or x.get('titel') or x.get('name') or x.get('naam')
  if not title:continue
  blob=' '.join(str(v) for v in x.values() if isinstance(v,(str,int,float)))
  if query and query.lower() not in blob.lower():continue
  link=x.get('url') or x.get('link') or x.get('uri') or 'https://www.rvo.nl/subsidies-financiering'
  if isinstance(link,str) and link.startswith('/'):link=urljoin('https://www.rvo.nl',link)
  rid=x.get('id') or x.get('uuid') or x.get('slug') or link
  out.append({'external_id':f'rvo:{rid}','title':title,'organizer':'RVO','url':link,'official_url':link,'kind':'grant','countries':['NL'],'source_adapter':'rvo','raw':x})
 return out
def nwo_projects(query:str='',limit:int=250):
 params={'summary':query} if query else {}
 with httpx.Client(timeout=60,headers=UA,follow_redirects=True) as h:r=h.get('https://nwopen-api.nwo.nl/NWOpen-API/api/Projects',params=params);r.raise_for_status();rows=_rows(r.json())
 out=[]
 for x in rows[:limit]:
  title=x.get('title') or x.get('projectTitle') or x.get('Title')
  if title:out.append({'external_id':f"nwo-project:{x.get('id') or x.get('projectId') or title}",'title':title,'organizer':'NWO','url':'https://data.nwo.nl/','official_url':'https://data.nwo.nl/','kind':'historical_grant','summary':x.get('summary') or '','countries':['NL'],'source_adapter':'nwo_projects','raw':x})
 return out
def nsf_awards(query:str='',limit:int=100):
 params={'printFields':'id,title,agency,awardeeName,date,expDate,fundsObligatedAmt,abstractText','offset':1,'rpp':min(limit,100)}
 if query:params['keyword']=query
 with httpx.Client(timeout=60,headers=UA,follow_redirects=True) as h:r=h.get('https://api.nsf.gov/services/v1/awards.json',params=params);r.raise_for_status();p=r.json()
 rows=p.get('response',{}).get('award',[]) or p.get('award',[]);out=[]
 for x in rows:
  rid=x.get('id');title=x.get('title')
  if title:out.append({'external_id':f'nsf-award:{rid}','title':title,'organizer':'National Science Foundation','url':f'https://www.nsf.gov/awardsearch/showAward?AWD_ID={rid}','official_url':f'https://www.nsf.gov/awardsearch/showAward?AWD_ID={rid}','kind':'historical_grant','reward_text':x.get('fundsObligatedAmt'),'countries':['US'],'summary':x.get('abstractText') or '','source_adapter':'nsf_awards','raw':x})
 return out
def _official(page,query,organizer,kind,adapter,limit=100):
 with httpx.Client(timeout=60,headers=UA,follow_redirects=True) as h:r=h.get(page);r.raise_for_status();s=BeautifulSoup(r.text,'html.parser')
 out=[];seen=set()
 for a in s.select('a[href]'):
  title=' '.join(a.stripped_strings).strip();href=urljoin(str(r.url),a.get('href'));context=' '.join((a.parent.get_text(' ',strip=True) if a.parent else title).split())
  if len(title)<8 or href in seen or (query and query.lower() not in (title+' '+context).lower()):continue
  if not re.search(r'(?i)\b(challenge|competition|prize|opportunity|solicitation|call|funding|grant|apply|proposal)\b',title+' '+context):continue
  seen.add(href);out.append({'external_id':f'{adapter}:{href}','title':title[:500],'organizer':organizer,'url':href,'official_url':href,'kind':kind,'summary':context[:2000],'source_adapter':adapter,'raw':{'page':page,'context':context}})
  if len(out)>=limit:break
 return out
def nasa(query:str='',limit:int=100):return _official('https://www.nasa.gov/coeci-opportunities/',query,'NASA','challenge','nasa',limit)
def nasa_stmd(query:str='',limit:int=100):return _official('https://www.nasa.gov/stmd-solicitations-and-opportunities/',query,'NASA STMD','research_call','nasa_stmd',limit)
PUBLIC_ADAPTERS={'rvo':rvo,'nwo_projects':nwo_projects,'nsf_awards':nsf_awards,'nasa':nasa,'nasa_stmd':nasa_stmd}
