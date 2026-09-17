from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from sqlalchemy import select,desc
from .core import Base,engine,SessionLocal,utcnow
from .models import *
app=FastAPI(title='Opportunity Atlas',version='0.3.0')
@app.on_event('startup')
def startup(): Base.metadata.create_all(engine); seed()
class CampaignIn(BaseModel): name:str; description:str=''; cadence:str='weekly'; queries:list[str]=[]; languages:list[str]=['en']; filters:dict={}
class ProfileIn(BaseModel): name:str; skills:list[str]=[]; interests:list[str]=[]; countries:list[str]=[]; min_reward:float=0; hours_per_week:int=10
@app.get('/health')
def health(): return {'ok':True}
@app.get('/opportunities')
def opportunities(limit:int=100,status:str='open'):
 with SessionLocal() as s: return s.scalars(select(Opportunity).where(Opportunity.status==status).order_by(desc(Opportunity.confidence)).limit(limit)).all()
@app.get('/sources')
def sources():
 with SessionLocal() as s:return s.scalars(select(Source)).all()
@app.get('/campaigns')
def campaigns():
 with SessionLocal() as s:return s.scalars(select(Campaign)).all()
@app.post('/campaigns')
def create_campaign(x:CampaignIn):
 with SessionLocal() as s: c=Campaign(**x.model_dump(),next_run=utcnow());s.add(c);s.commit();s.refresh(c);return c
@app.post('/campaigns/{cid}/run')
def run(cid:int):
 with SessionLocal() as s:
  if not s.get(Campaign,cid): raise HTTPException(404)
  r=Run(campaign_id=cid);s.add(r);s.commit();s.refresh(r);return r
@app.get('/runs')
def runs():
 with SessionLocal() as s:return s.scalars(select(Run).order_by(desc(Run.id)).limit(100)).all()
@app.post('/profiles')
def profile(x:ProfileIn):
 with SessionLocal() as s:p=Profile(**x.model_dump());s.add(p);s.commit();s.refresh(p);return p
@app.get('/profiles/{pid}/matches')
def matches(pid:int,limit:int=100):
 with SessionLocal() as s:return s.scalars(select(Match).where(Match.profile_id==pid).order_by(desc(Match.score)).limit(limit)).all()
@app.get('/stats')
def stats():
 with SessionLocal() as s:return {'opportunities':len(s.scalars(select(Opportunity)).all()),'sources':len(s.scalars(select(Source)).all()),'campaigns':len(s.scalars(select(Campaign)).all()),'runs':len(s.scalars(select(Run)).all())}
def seed():
 with SessionLocal() as s:
  if not s.scalar(select(Campaign).limit(1)):
   seeds=[('Global Opportunity Discovery','Worldwide grants prizes bounties hackathons innovation challenges paid pilots tenders and research calls','daily',['innovation challenge cash prize deadline','open call grant applications','developer bounty hackathon prize']),('EU & Netherlands','EU and Dutch innovation grants procurement challenges pilots climate AI research and startup opportunities','weekly',['site:europa.eu open call innovation','site:rvo.nl innovatie subsidie challenge']),('AI & Open Source','AI ML data science agent developer and open-source paid opportunities','daily',['AI competition prize','machine learning challenge cash prize','open source bounty developer']),('Climate Nature EO','Biodiversity climate Earth observation remote sensing nature-tech opportunities','daily',['biodiversity innovation challenge','Earth observation competition grant','remote sensing open call climate']),('India Innovation','Indian startup research AI technology and government innovation programs','weekly',['India innovation challenge grant startup','MeitY AI challenge','DST research open call'])]
   for name,desc,cad,q in seeds:s.add(Campaign(name=name,description=desc,cadence=cad,queries=q,languages=['en','nl','de','fr','hi'],next_run=utcnow()))
   s.commit()
