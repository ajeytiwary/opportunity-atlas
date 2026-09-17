import os, hashlib, re
from datetime import datetime, timezone
from pydantic_settings import BaseSettings
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

class Settings(BaseSettings):
    database_url:str=os.getenv('DATABASE_URL','sqlite:///./atlas.db')
    llm_base_url:str=os.getenv('LLM_BASE_URL','https://api.openai.com/v1')
    llm_api_key:str=os.getenv('LLM_API_KEY','')
    llm_model:str=os.getenv('LLM_MODEL','gpt-5-mini')
    searxng_url:str=os.getenv('SEARXNG_URL','http://localhost:8080')
    max_results_per_query:int=int(os.getenv('MAX_RESULTS_PER_QUERY','20'))
    worker_poll_seconds:int=int(os.getenv('WORKER_POLL_SECONDS','60'))
settings=Settings()
class Base(DeclarativeBase): pass
engine=create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal=sessionmaker(engine, expire_on_commit=False)
def utcnow(): return datetime.now(timezone.utc)
def fingerprint(title:str, organizer:str=''):
    x=re.sub(r'[^a-z0-9]+',' ',f'{title} {organizer}'.lower()).strip()
    return hashlib.sha256(x.encode()).hexdigest()
