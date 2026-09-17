from app.portal_adapters import ADAPTERS
from app.portal_registry import PORTALS

def test_structured_adapters_registered():
 for name in ['grants_gov','eu_funding_tenders','kaggle','ted','ukri','github_issues']:
  assert name in ADAPTERS

def test_no_retired_challenge_gov_adapter():
 p=[x for x in PORTALS if x['name']=='Challenge.gov']
 assert not p

def test_structured_portals_have_adapter():
 for p in PORTALS:
  if p['mode']=='structured': assert p['adapter'] in ADAPTERS
