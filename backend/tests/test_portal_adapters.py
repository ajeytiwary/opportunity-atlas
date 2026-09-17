from app.portal_registry import PORTALS,discovery_queries
from app.portal_adapters import ADAPTERS
from app.structured_ingest import _reward

def test_structured_adapters_registered():
    assert {'grants_gov','eu_funding_tenders','kaggle'} <= set(ADAPTERS)

def test_portal_registry_has_fallbacks():
    assert len(PORTALS)>=30
    assert len(discovery_queries())>=30

def test_reward_parser():
    assert _reward('$50k')==(50000.0,'USD')
    assert _reward('€1.5M')==(1500000.0,'EUR')
    assert _reward(None)==(None,None)
