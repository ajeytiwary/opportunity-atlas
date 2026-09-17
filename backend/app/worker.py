import time
from sqlalchemy import select
from .core import Base,engine,SessionLocal,settings,utcnow
from .models import Campaign,Run
from .engine import execute_run,schedule_next
Base.metadata.create_all(engine)
while True:
 with SessionLocal() as s:
  queued=s.scalar(select(Run).where(Run.status=='queued').order_by(Run.id))
  if queued: rid=queued.id
  else:
   c=s.scalar(select(Campaign).where(Campaign.enabled==True,Campaign.next_run<=utcnow()).order_by(Campaign.next_run))
   if c:
    r=Run(campaign_id=c.id);s.add(r);c.next_run=schedule_next(c);s.commit();rid=r.id
   else: rid=None
 if rid: execute_run(rid)
 else: time.sleep(settings.worker_poll_seconds)
