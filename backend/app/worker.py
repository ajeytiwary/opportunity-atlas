import time
from sqlalchemy import select
from .core import Base,engine,SessionLocal,settings,utcnow
from .models import Campaign,Run
from .engine import execute_run,schedule_next
from .structured_ingest import run_priority_adapters
from .predictive import recompute_families
from .predictive_models import AdapterCursor,ProgramFamily,PredictiveAlert
Base.metadata.create_all(engine)
last_structured=None;last_predictive=None
while True:
 now=utcnow()
 if not last_structured or (now-last_structured).total_seconds()>=3600:
  try:run_priority_adapters(incremental=True)
  except Exception:pass
  last_structured=now
 if not last_predictive or (now-last_predictive).total_seconds()>=21600:
  try:recompute_families()
  except Exception:pass
  last_predictive=now
 with SessionLocal() as s:
  queued=s.scalar(select(Run).where(Run.status=='queued').order_by(Run.id))
  if queued:rid=queued.id
  else:
   c=s.scalar(select(Campaign).where(Campaign.enabled==True,Campaign.next_run<=utcnow()).order_by(Campaign.next_run))
   if c:
    r=Run(campaign_id=c.id);s.add(r);c.next_run=schedule_next(c);s.commit();rid=r.id
   else:rid=None
 if rid:execute_run(rid)
 else:time.sleep(settings.worker_poll_seconds)
