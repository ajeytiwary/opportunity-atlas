import time, random, httpx, xml.etree.ElementTree as ET
from urllib.parse import urljoin,urlparse
from .core import settings
UA={'User-Agent':'OpportunityAtlas/0.4 (+public-opportunity-indexer)'}
class Limiter:
 def __init__(self,min_interval=.6): self.min_interval=min_interval; self.last={}
 def wait(self,host):
  delay=self.min_interval-(time.time()-self.last.get(host,0))
  if delay>0: time.sleep(delay)
  self.last[host]=time.time()
limiter=Limiter()
def request(url,**kw):
 host=urlparse(url).netloc; limiter.wait(host); err=None
 for attempt in range(4):
  try:
   with httpx.Client(timeout=25,follow_redirects=True,headers=UA) as h:
    r=h.get(url,**kw)
    if r.status_code in (429,500,502,503,504): raise RuntimeError(f'HTTP {r.status_code}')
    r.raise_for_status(); return r
  except Exception as e: err=e; time.sleep((2**attempt)+random.random())
 raise err
class SearxAdapter:
 name='searxng'
 def discover(self,q,language='en',time_range=None,pages=2):
  out=[]
  for page in range(1,pages+1):
   p={'q':q,'format':'json','language':language,'safesearch':1,'pageno':page}
   if time_range:p['time_range']=time_range
   out += request(settings.searxng_url+'/search',params=p).json().get('results',[])
  return out
class RSSAdapter:
 name='rss'
 def discover(self,url):
  root=ET.fromstring(request(url).text); out=[]
  for x in root.findall('.//item')+root.findall('.//{http://www.w3.org/2005/Atom}entry'):
   title=x.findtext('title') or x.findtext('{http://www.w3.org/2005/Atom}title') or ''
   link=x.findtext('link'); atom=x.find('{http://www.w3.org/2005/Atom}link')
   if not link and atom is not None: link=atom.attrib.get('href')
   if link: out.append({'title':title,'url':link})
  return out
class SitemapAdapter:
 name='sitemap'
 def discover(self,url,limit=1000):
  root=ET.fromstring(request(url).text); locs=[x.text for x in root.iter() if x.tag.endswith('loc') and x.text]
  return [{'url':x} for x in locs[:limit]]
class JsonAPIAdapter:
 name='json_api'
 def discover(self,url,path=None):
  data=request(url).json()
  for key in (path or '').split('.'):
   if key:data=data.get(key,[])
  return data if isinstance(data,list) else []
def candidate_feeds(base):
 return [urljoin(base,x) for x in ('/feed','/feed.xml','/rss','/rss.xml','/atom.xml','/sitemap.xml','/sitemap_index.xml')]
