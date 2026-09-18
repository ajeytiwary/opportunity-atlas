from __future__ import annotations
from datetime import timedelta
from sqlalchemy import select
from .core import SessionLocal,utcnow
from .predictive_models import AdapterCursor
from .structured_ingest import ingest_adapter

DEFAULT_LOOKBACK_DAYS=3
def cursor_for(adapter,query=''):
 with SessionLocal() as s:
  c=s.scalar(select(AdapterCursor).where(AdapterCursor.adapter==adapter,AdapterCursor.query==query))
  if not c:c=AdapterCursor(adapter=adapter,query=query,cursor={});s.add(c);s.commit();s.refresh(c)
  return {'id':c.id,'cursor':c.cursor or {},'last_success':c.last_success}
def run_incremental(adapter,query=''):
 state=cursor_for(adapter,query);now=utcnow()
 with SessionLocal() as s:
  c=s.get(AdapterCursor,state['id']);c.last_started=now;s.commit()
 try:
  stats=ingest_adapter(adapter,query)
  with SessionLocal() as s:
   c=s.get(AdapterCursor,state['id']);c.last_success=utcnow();c.last_error=None;c.consecutive_errors=0;c.cursor={'last_success':c.last_success.isoformat(),'lookback_days':DEFAULT_LOOKBACK_DAYS};s.commit()
  return stats|{'incremental':True}
 except Exception as e:
  with SessionLocal() as s:
   c=s.get(AdapterCursor,state['id']);c.last_error=str(e);c.consecutive_errors+=1;s.commit()
  raise
def due(adapter,query='',hours=24):
 state=cursor_for(adapter,query);return not state['last_success'] or state['last_success']<=utcnow()-timedelta(hours=hours)
