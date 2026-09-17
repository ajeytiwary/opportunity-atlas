"""First-class structured portal adapters."""
from __future__ import annotations
import subprocess,json
import httpx
from dateutil.parser import parse as dtparse
from .adapters_extra import EXTRA_ADAPTERS
UA={"User-Agent":"OpportunityAtlas/0.6 (+public opportunity indexer)"}
def _date(x):
 if not x:return None
 try:return dtparse(str(x)).isoformat()
 except Exception:return None

def grants_gov(keyword:str="",rows:int=100,start:int=0):
 body={"rows":min(rows,1000),"startRecordNum":start,"keyword":keyword,"oppStatuses":"forecasted|posted"}
 with httpx.Client(timeout=45,headers=UA) as h:r=h.post("https://api.grants.gov/v1/api/search2",json=body);r.raise_for_status();data=r.json().get("data",{})
 return [{"external_id":f"grantsgov:{x.get('id') or x.get('number')}","title":x.get("title"),"organizer":x.get("agencyName") or x.get("agencyCode") or "US Government","url":f"https://www.grants.gov/search-results-detail/{x.get('id')}","official_url":f"https://www.grants.gov/search-results-detail/{x.get('id')}","kind":"grant","deadline":_date(x.get("closeDate")),"status":x.get("oppStatus"),"countries":["US"],"source_adapter":"grants_gov","raw":x} for x in data.get("oppHits",[]) if x.get('title')]

def eu_funding_tenders(text:str="",page_size:int=100,page:int=1):
 endpoint="https://api.tech.ec.europa.eu/search-api/prod/rest/search";params={"apiKey":"SEDIA","text":text or "*","pageSize":page_size,"pageNumber":page,"language":"en"}
 with httpx.Client(timeout=60,headers=UA) as h:r=h.get(endpoint,params=params);r.raise_for_status();p=r.json()
 rows=p.get("results") or p.get("response",{}).get("docs") or p.get("documents") or [];out=[]
 for x in rows:
  title=x.get("title") or x.get("content") or x.get("name")
  if not title:continue
  rid=x.get("id") or x.get("reference") or x.get("identifier");url=x.get("url") or x.get("portalUrl") or "https://ec.europa.eu/info/funding-tenders/opportunities/portal/";typ=str(x.get("type") or x.get("typeLabel") or "").lower()
  out.append({"external_id":f"euft:{rid}","title":title,"organizer":"European Commission","url":url,"official_url":url,"kind":"tender" if "tender" in typ else "grant","deadline":_date(x.get("deadlineDate") or x.get("deadline")),"countries":["EU"],"source_adapter":"eu_funding_tenders","raw":x})
 return out

def kaggle_competitions(search:str="",page:int=1):
 cmd=["kaggle","competitions","list","--csv","--page",str(page)]+(["--search",search] if search else [])
 try:p=subprocess.run(cmd,capture_output=True,text=True,timeout=60,check=True)
 except (FileNotFoundError,subprocess.SubprocessError):return []
 import csv,io
 out=[]
 for x in csv.DictReader(io.StringIO(p.stdout)):
  ref=x.get("ref") or x.get("Ref")
  if ref:out.append({"external_id":f"kaggle:{ref}","title":x.get("title") or x.get("Title") or ref,"organizer":"Kaggle","url":f"https://www.kaggle.com/competitions/{ref}","official_url":f"https://www.kaggle.com/competitions/{ref}","kind":"data_competition","deadline":_date(x.get("deadline") or x.get("Deadline")),"reward_text":x.get("reward") or x.get("Reward"),"source_adapter":"kaggle","raw":x})
 return out
ADAPTERS={"grants_gov":grants_gov,"eu_funding_tenders":eu_funding_tenders,"kaggle":kaggle_competitions,**EXTRA_ADAPTERS}
def run_adapter(name:str,query:str="",**kwargs):
 fn=ADAPTERS.get(name)
 if not fn:raise ValueError(f"Unknown adapter: {name}")
 if name=="kaggle":return fn(search=query,**kwargs)
 if name=="eu_funding_tenders":return fn(text=query,**kwargs)
 if name=="grants_gov":return fn(keyword=query,**kwargs)
 return fn(query=query,**kwargs)
