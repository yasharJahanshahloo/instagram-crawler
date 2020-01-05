from elasticsearch_dsl import connections,Search
from datetime import datetime

from inscrawler.elastic import *

connections.create_connection(hosts=['localhost'], timeout=20)
Post.init()
Comment.init()
Popular.get(id="amir_mahdi_jule").update(checked=True)