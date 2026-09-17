"""Additional high-recall portal adapters with conservative fallbacks."""
from __future__ import annotations
import os,re
from urllib.parse import quote_plus
import httpx,feedparser
from bs4 import BeautifulSoup
from dateutil.parser import parse as dtparse
UA={"User-Agent":"OpportunityAtlas/0.6 (+public opportunity indexer)"}

def _date(x):
 try:return dtparse(str(x)).isoformat() if x else None
 except Exception:return None

def ted(query:str="",limit:int=100,page:int=1):
 """TED Search API v3. Anonymous search of published procurement notices."""
 body={"query":query or "publication-date >= 20260101","fields":["publication-number","notice-title","buyer-name","deadline-receipt-tender-date-lot","estimated-value-lot","estimated-value-lot-currency","place-of-performance"],"page":page,"limit":min(limit,250),"scope":"ALL","checkQuerySyntax":False,"paginationMode":"PAGE_NUMBER"}
 with httpx.Client(timeout=60,headers=UA) as h:
  r=h.post("https://api.ted.europa.eu/v3/notices/search",json=body);r.raise_for_status();p=r.json()
 rows=p.get("notices") or p.get("results") or [] ;out=[]
 for x in rows:
  num=x.get("publication-number") or x.get("publicationNumber") or x.get("notice-id")
  title=x.get("notice-title") or x.get("title") or f"TED notice {num}"
  if isinstance(title,list):title=title[0] if title else None
  buyer=x.get("buyer-name") or x.get("buyerName") or "EU public buyer"
  if isinstance(buyer,list):buyer=buyer[0] if buyer else "EU public buyer"
  url=f"https://ted.europa.eu/en/notice/-/detail/{num}" if num else "https://ted.europa.eu/"
  out.append({"external_id":f"ted:{num}","title":title,"organizer":buyer,"url":url,"official_url":url,"kind":"tender","deadline":_date(x.get("deadline-receipt-tender-date-lot")),"countries":["EU"],"source_adapter":"ted","raw":x})
 return out

def ukri(query:str="",limit:int=100):
 """UKRI funding finder RSS/HTML. RSS is preferred because UKRI publishes it explicitly."""
 feeds=["https://www.ukri.org/opportunity/feed/"]
 out=[]
 for u in feeds:
  f=feedparser.parse(u)
  for e in f.entries[:limit]:
   title=e.get("title");link=e.get("link")
   if query and query.lower() not in (title+' '+e.get('summary','')).lower():continue
   out.append({"external_id":f"ukri:{e.get('id') or link}","title":title,"organizer":"UK Research and Innovation","url":link,"official_url":link,"kind":"grant","summary":BeautifulSoup(e.get("summary",''),"html.parser").get_text(' ',strip=True),"deadline":None,"countries":["UK"],"source_adapter":"ukri","raw":dict(e)})
 return out

def github_issues(query:str="bounty reward prize",limit:int=100):
 """GitHub public Issues search. Optional GITHUB_TOKEN raises rate limits."""
 token=os.getenv("GITHUB_TOKEN");headers={**UA,"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}
 if token:headers["Authorization"]=f"Bearer {token}"
 q=f"{query} is:issue is:open archived:false"
 with httpx.Client(timeout=45,headers=headers) as h:
  r=h.get("https://api.github.com/search/issues",params={"q":q,"per_page":min(limit,100),"sort":"updated","order":"desc"});r.raise_for_status();rows=r.json().get("items",[])
 out=[]
 for x in rows:
  text=(x.get("title") or '')+' '+(x.get("body") or '')
  if not re.search(r'(?i)\b(bounty|reward|prize|paid|\$\s?\d|€\s?\d|£\s?\d)\b',text):continue
  repo=(x.get("repository_url") or '').split('/repos/')[-1]
  out.append({"external_id":f"github:{x.get('id')}","title":x.get("title"),"organizer":repo,"url":x.get("html_url"),"official_url":x.get("html_url"),"kind":"oss_bounty","deadline":None,"source_adapter":"github_issues","raw":x})
 return out

def rss_generic(url:str,query:str="",kind:str="other",organizer:str=""):
 f=feedparser.parse(url);out=[]
 for e in f.entries:
  text=(e.get('title','')+' '+e.get('summary',''))
  if query and query.lower() not in text.lower():continue
  link=e.get('link');out.append({"external_id":f"rss:{e.get('id') or link}","title":e.get('title'),"organizer":organizer,"url":link,"official_url":link,"kind":kind,"summary":BeautifulSoup(e.get('summary',''),'html.parser').get_text(' ',strip=True),"source_adapter":"rss_generic","raw":dict(e)})
 return out

EXTRA_ADAPTERS={"ted":ted,"ukri":ukri,"github_issues":github_issues}
