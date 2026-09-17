from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select,desc,func
from .core import Base,engine,SessionLocal,utcnow
from .models import *
from .advanced_models import Snapshot,QueryMetric,Watchlist,Alert
from .search import build_query
from .seeds import SOURCES
from .portal_registry import PORTALS
from .portal_adapters import ADAPTERS
from .structured_ingest import ingest_adapter
app=FastAPI(title='Opportunity Atlas',version='0.5.0');app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
@app.on_event('startup')
def startup():Base.metadata.create_all(engine);seed()
class CampaignIn(BaseModel):name:str;description:str='';cadence:str='weekly';queries:list[str]=[];languages:list[str]=['en'];filters:dict={}
class ProfileIn(BaseModel):name:str;skills:list[str]=[];interests:list[str]=[];countries:list[str]=[];min_reward:float=0;hours_per_week:int=10
class WatchIn(BaseModel):name:str;profile_id:int|None=None;filters:dict={}
@app.get('/health')
def health():return {'ok':True,'version':'0.5.0','structured_adapters':list(ADAPTERS)}
@app.get('/opportunities')
def opportunities(q:str|None=None,kind:str|None=None,country:str|None=None,min_reward:float|None=None,min_confidence:float|None=None,remote:bool|None=None,status:str='open',sort:str='confidence',limit:int=100,offset:int=0):
 with SessionLocal() as s:return s.scalars(build_query(q,kind,country,min_reward,min_confidence,remote,status,sort).offset(offset).limit(min(limit,500))).all()
@app.get('/opportunities/{oid}/history')
def history(oid:int):
 with SessionLocal() as s:return s.scalars(select(Snapshot).where(Snapshot.opportunity_id==oid).order_by(desc(Snapshot.captured_at))).all()
@app.get('/sources')
def sources(limit:int=1000):
 with SessionLocal() as s:return s.scalars(select(Source).order_by(desc(Source.trust)).limit(limit)).all()
@app.get('/portals')
def portals():return PORTALS
@app.post('/portals/{adapter}/sync')
def sync_portal(adapter:str,q:str=''):
 if adapter not in ADAPTERS:raise HTTPException(404,'No structured adapter with that name')
 return ingest_adapter(adapter,q)
@app.get('/campaigns')
def campaigns():
 with SessionLocal() as s:return s.scalars(select(Campaign)).all()
@app.post('/campaigns')
def create_campaign(x:CampaignIn):
 with SessionLocal() as s:c=Campaign(**x.model_dump(),next_run=utcnow());s.add(c);s.commit();s.refresh(c);return c
@app.post('/campaigns/{cid}/run')
def run(cid:int):
 with SessionLocal() as s:
  if not s.get(Campaign,cid):raise HTTPException(404)
  r=Run(campaign_id=cid);s.add(r);s.commit();s.refresh(r);return r
@app.get('/campaigns/{cid}/queries')
def query_metrics(cid:int):
 with SessionLocal() as s:return s.scalars(select(QueryMetric).where(QueryMetric.campaign_id==cid).order_by(desc(QueryMetric.score)).limit(500)).all()
@app.get('/runs')
def runs():
 with SessionLocal() as s:return s.scalars(select(Run).order_by(desc(Run.id)).limit(100)).all()
@app.post('/profiles')
def profile(x:ProfileIn):
 with SessionLocal() as s:p=Profile(**x.model_dump());s.add(p);s.commit();s.refresh(p);return p
@app.get('/profiles/{pid}/matches')
def matches(pid:int,limit:int=100):
 with SessionLocal() as s:rows=s.execute(select(Match,Opportunity).join(Opportunity,Opportunity.id==Match.opportunity_id).where(Match.profile_id==pid).order_by(desc(Match.score)).limit(limit)).all();return [{'score':m.score,'reasons':m.reasons,'opportunity':o} for m,o in rows]
@app.post('/watchlists')
def watch(x:WatchIn):
 with SessionLocal() as s:w=Watchlist(**x.model_dump());s.add(w);s.commit();s.refresh(w);return w
@app.get('/watchlists')
def watches():
 with SessionLocal() as s:return s.scalars(select(Watchlist)).all()
@app.get('/alerts')
def alerts(unread:bool=False,limit:int=200):
 with SessionLocal() as s:
  stmt=select(Alert).order_by(desc(Alert.created_at));stmt=stmt.where(Alert.read==False) if unread else stmt;return s.scalars(stmt.limit(limit)).all()
@app.get('/stats')
def stats():
 with SessionLocal() as s:return {'opportunities':s.scalar(select(func.count()).select_from(Opportunity)),'sources':s.scalar(select(func.count()).select_from(Source)),'campaigns':s.scalar(select(func.count()).select_from(Campaign)),'runs':s.scalar(select(func.count()).select_from(Run)),'alerts':s.scalar(select(func.count()).select_from(Alert)),'portals':len(PORTALS),'structured_adapters':len(ADAPTERS)}
def seed():
 with SessionLocal() as s:
  for name,url,country,cats in SOURCES:
   if not s.scalar(select(Source).where(Source.url==url)):s.add(Source(name=name,url=url,country=country,categories=cats,languages=['en'],trust=.85))
  if not s.scalar(select(Campaign).limit(1)):
   seeds=[('Global Opportunity Discovery','Worldwide grants prizes bounties hackathons innovation challenges paid pilots tenders and research calls','daily',['innovation challenge cash prize deadline','open call grant applications','developer bounty hackathon prize']),('EU & Netherlands','EU and Dutch innovation grants procurement challenges pilots climate AI research and startup opportunities','weekly',['site:europa.eu open call innovation','site:rvo.nl innovatie subsidie challenge']),('AI & Open Source','AI ML data science agent developer and open-source paid opportunities','daily',['AI competition prize','machine learning challenge cash prize','open source bounty developer']),('Climate Nature EO','Biodiversity climate Earth observation remote sensing nature-tech opportunities','daily',['biodiversity innovation challenge','Earth observation competition grant','remote sensing open call climate']),('India Innovation','Indian startup research AI technology and government innovation programs','weekly',['India innovation challenge grant startup','MeitY AI challenge','DST research open call'])]
   for name,desc,cad,q in seeds:s.add(Campaign(name=name,description=desc,cadence=cad,queries=q,languages=['en','nl','de','fr','hi'],next_run=utcnow()))
  s.commit()
