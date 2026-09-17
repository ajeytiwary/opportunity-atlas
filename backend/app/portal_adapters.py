"""First-class structured portal adapters.

Adapters return normalized candidate dictionaries. Detail pages are still passed through
Opportunity Atlas verification/extraction where useful, preserving provenance.
"""
from __future__ import annotations
import os, subprocess, json
from datetime import datetime
from typing import Iterable
import httpx
from dateutil.parser import parse as dtparse

UA={"User-Agent":"OpportunityAtlas/0.5 (+public opportunity indexer)"}

def _date(x):
    if not x:return None
    try:return dtparse(str(x)).isoformat()
    except Exception:return None

def grants_gov(keyword:str="", rows:int=100, start:int=0)->list[dict]:
    """Official Grants.gov search2 API; public search needs no auth."""
    body={"rows":min(rows,1000),"startRecordNum":start,"keyword":keyword,"oppStatuses":"forecasted|posted"}
    with httpx.Client(timeout=45,headers=UA) as h:
        r=h.post("https://api.grants.gov/v1/api/search2",json=body);r.raise_for_status();data=r.json().get("data",{})
    out=[]
    for x in data.get("oppHits",[]):
        oid=x.get("id"); num=x.get("number")
        out.append({"external_id":f"grantsgov:{oid or num}","title":x.get("title"),"organizer":x.get("agencyName") or x.get("agencyCode") or "US Government","url":f"https://www.grants.gov/search-results-detail/{oid}" if oid else "https://www.grants.gov/search-results-detail/","official_url":f"https://www.grants.gov/search-results-detail/{oid}" if oid else None,"kind":"grant","deadline":_date(x.get("closeDate")),"status":x.get("oppStatus"),"countries":["US"],"source_adapter":"grants_gov","raw":x})
    return out

def eu_funding_tenders(text:str="", page_size:int=100, page:int=1)->list[dict]:
    """Official EC corporate Search API used by Funding & Tenders Portal."""
    endpoint="https://api.tech.ec.europa.eu/search-api/prod/rest/search"
    params={"apiKey":"SEDIA","text":text or "*","pageSize":page_size,"pageNumber":page,"language":"en"}
    with httpx.Client(timeout=60,headers=UA) as h:
        r=h.get(endpoint,params=params);r.raise_for_status();payload=r.json()
    records=payload.get("results") or payload.get("response",{}).get("docs") or payload.get("documents") or []
    out=[]
    for x in records:
        title=x.get("title") or x.get("content") or x.get("name")
        if not title:continue
        rid=x.get("id") or x.get("reference") or x.get("identifier")
        url=x.get("url") or x.get("portalUrl") or "https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
        typ=str(x.get("type") or x.get("typeLabel") or "").lower()
        kind="tender" if "tender" in typ else "grant"
        out.append({"external_id":f"euft:{rid}","title":title,"organizer":"European Commission","url":url,"official_url":url,"kind":kind,"deadline":_date(x.get("deadlineDate") or x.get("deadline")),"countries":["EU"],"source_adapter":"eu_funding_tenders","raw":x})
    return out

def kaggle_competitions(search:str="", page:int=1)->list[dict]:
    """Kaggle's supported CLI is used when credentials/CLI are available."""
    cmd=["kaggle","competitions","list","--csv","--page",str(page)]
    if search:cmd += ["--search",search]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=60,check=True)
    except (FileNotFoundError,subprocess.SubprocessError):return []
    import csv,io
    out=[]
    for x in csv.DictReader(io.StringIO(p.stdout)):
        ref=x.get("ref") or x.get("Ref");
        if not ref:continue
        out.append({"external_id":f"kaggle:{ref}","title":x.get("title") or x.get("Title") or ref,"organizer":"Kaggle","url":f"https://www.kaggle.com/competitions/{ref}","official_url":f"https://www.kaggle.com/competitions/{ref}","kind":"data_competition","deadline":_date(x.get("deadline") or x.get("Deadline")),"reward_text":x.get("reward") or x.get("Reward"),"source_adapter":"kaggle","raw":x})
    return out

ADAPTERS={"grants_gov":grants_gov,"eu_funding_tenders":eu_funding_tenders,"kaggle":kaggle_competitions}

def run_adapter(name:str, query:str="", **kwargs):
    fn=ADAPTERS.get(name)
    if not fn:raise ValueError(f"Unknown adapter: {name}")
    key="search" if name=="kaggle" else ("text" if name=="eu_funding_tenders" else "keyword")
    return fn(**{key:query},**kwargs)
