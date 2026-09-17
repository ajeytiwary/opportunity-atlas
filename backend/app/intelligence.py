import re
from urllib.parse import urlparse,urljoin
from bs4 import BeautifulSoup
from sqlalchemy import select
from .adapters import request,candidate_feeds
from .core import SessionLocal,utcnow
from .models import Source,Opportunity
KEYWORDS=('grant','funding','challenge','competition','prize','bounty','hackathon','open call','call for','tender','procurement','fellowship','accelerator','innovation','award')
PATHS=('opportunities','funding','grants','challenges','competitions','prizes','open-calls','calls','innovation','tenders','procurement','awards')
def host(url): return urlparse(url).netloc.lower().removeprefix('www.')
def recursive_source_candidates(url):
 base=f'{urlparse(url).scheme}://{urlparse(url).netloc}'; found=set(urljoin(base,'/'+p) for p in PATHS)
 try:
  soup=BeautifulSoup(request(url).text,'html.parser')
  for a in soup.select('a[href]'):
   text=(a.get_text(' ',strip=True)+' '+a['href']).lower()
   if any(k in text for k in KEYWORDS):
    u=urljoin(url,a['href'])
    if host(u)==host(url):found.add(u)
 except Exception: pass
 return sorted(found)[:80]
def discover_feed_urls(url):
 found=set(candidate_feeds(url))
 try:
  soup=BeautifulSoup(request(url).text,'html.parser')
  for l in soup.select('link[rel="alternate"]'):
   if 'rss' in (l.get('type') or '') or 'atom' in (l.get('type') or ''):found.add(urljoin(url,l.get('href')))
 except Exception:pass
 return sorted(found)
def verification_score(op,source_text,final_url):
 score=.15; evidence=[]
 if host(final_url)==host(op.official_url or final_url):score+=.25;evidence.append('same-domain')
 text=source_text.lower()
 if op.title and op.title.lower()[:40] in text:score+=.2;evidence.append('title-on-source')
 if op.organizer and op.organizer.lower() in text:score+=.15;evidence.append('organizer-on-source')
 if op.deadline and str(op.deadline.year) in text:score+=.1;evidence.append('deadline-year-on-source')
 if op.reward and any(x in text for x in (str(int(op.reward)),f'{op.reward:,.0f}')):score+=.1;evidence.append('reward-on-source')
 if any(k in text for k in KEYWORDS):score+=.05
 return min(score,1),evidence
def add_recursive_sources(opportunity_url):
 candidates=recursive_source_candidates(opportunity_url); added=0
 with SessionLocal() as s:
  for u in candidates:
   if not s.scalar(select(Source).where(Source.url==u)):
    s.add(Source(name=host(u),url=u,country=None,categories=[],languages=['en'],source_type='discovered',trust=.55));added+=1
  s.commit()
 return added
def recurrence_features(records):
 dates=sorted([x.first_seen for x in records if x.first_seen])
 if len(dates)<2:return {'recurring':False,'confidence':0}
 gaps=[(b-a).days for a,b in zip(dates,dates[1:])]; avg=sum(gaps)/len(gaps)
 recurring=250<=avg<=450 or 20<=avg<=45 or 70<=avg<=120
 return {'recurring':recurring,'average_gap_days':round(avg),'confidence':min(.9,.3+.15*len(gaps))}
