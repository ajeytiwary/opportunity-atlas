# Registry expansion without pretending generated URLs are verified sources.
# These are search targets; discovered URLs become Source rows only after successful retrieval.
COUNTRIES=['Netherlands','Belgium','Germany','France','Spain','Portugal','Italy','Austria','Switzerland','Denmark','Sweden','Norway','Finland','Ireland','Poland','Czech Republic','Estonia','Latvia','Lithuania','Romania','Greece','United Kingdom','United States','Canada','India','Singapore','Japan','South Korea','Australia','New Zealand','Brazil','Mexico','South Africa','Kenya','Nigeria','UAE','Saudi Arabia']
DOMAINS=['AI','machine learning','data science','open source','cybersecurity','robotics','space','Earth observation','remote sensing','biodiversity','nature restoration','climate','energy','grid','agriculture','water','oceans','health','biotech','materials','manufacturing','mobility','smart cities','education','fintech','quantum','semiconductors','creative technology','social impact','development','mathematics','science','startup']
TERMS=['grant','innovation challenge','cash prize competition','open call','research funding','startup accelerator','paid pilot','procurement challenge','hackathon','developer bounty','fellowship','award','tender']
def registry_queries():
 out=[]
 for c in COUNTRIES:
  for term in TERMS:out.append({'q':f'"{term}" {c} deadline applications','language':'en','family':'geography'})
 for d in DOMAINS:
  for term in TERMS:out.append({'q':f'"{d}" "{term}" applications deadline','language':'en','family':'domain'})
 return out
