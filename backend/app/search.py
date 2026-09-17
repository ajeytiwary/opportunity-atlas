from sqlalchemy import select,or_,desc
from .models import Opportunity
def build_query(q=None,kind=None,country=None,min_reward=None,min_confidence=None,remote=None,status='open',sort='confidence'):
 stmt=select(Opportunity)
 if status:stmt=stmt.where(Opportunity.status==status)
 if q:
  x=f'%{q}%';stmt=stmt.where(or_(Opportunity.title.ilike(x),Opportunity.organizer.ilike(x),Opportunity.summary.ilike(x),Opportunity.eligibility.ilike(x)))
 if kind:stmt=stmt.where(Opportunity.kind==kind)
 if min_reward is not None:stmt=stmt.where(Opportunity.reward>=min_reward)
 if min_confidence is not None:stmt=stmt.where(Opportunity.confidence>=min_confidence)
 if remote is not None:stmt=stmt.where(Opportunity.remote==remote)
 if country:stmt=stmt.where(Opportunity.countries.contains([country]))
 order={'confidence':Opportunity.confidence,'reward':Opportunity.reward,'deadline':Opportunity.deadline,'newest':Opportunity.first_seen}.get(sort,Opportunity.confidence)
 return stmt.order_by(desc(order))
