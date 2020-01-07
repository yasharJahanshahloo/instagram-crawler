from elasticsearch_dsl import connections, Search
from datetime import datetime

from inscrawler.elastic import *

connections.create_connection(hosts=['localhost'], timeout=20)
# s = Search().query('range', added_at={"lte": "now-2d","missing":"now-1y"})
# s.execute()
# for hit in s:
#     print(hit)

res = Post.get(id='https://www.instagram.com/p/B1z_P_-lm7t/',ignore=404)
print(res)