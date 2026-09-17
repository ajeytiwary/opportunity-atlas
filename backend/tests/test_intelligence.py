from app.core import fingerprint
from app.intelligence import host,recurrence_features
from app.watch import matches
from types import SimpleNamespace
from datetime import datetime,timezone,timedelta
def test_fingerprint_stable():assert fingerprint('AI Prize','NASA')==fingerprint('AI Prize','NASA')
def test_host():assert host('https://www.example.org/x')=='example.org'
def test_watch_filters():
 o=SimpleNamespace(kind='grant',reward=10000,confidence=.9,remote=True,categories=['AI'],skills=['Python'],countries=['NL'])
 assert matches(o,{'kinds':['grant'],'min_reward':5000,'keywords':['python']})
def test_recurrence_yearly():
 now=datetime.now(timezone.utc);rows=[SimpleNamespace(first_seen=now-timedelta(days=730)),SimpleNamespace(first_seen=now-timedelta(days=365)),SimpleNamespace(first_seen=now)]
 assert recurrence_features(rows)['recurring'] is True
