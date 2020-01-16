from time import sleep

from elasticsearch_dsl import connections, Search
from datetime import datetime

from inscrawler.elastic import Target

connections.create_connection(hosts=['localhost'], timeout=20)

while True:
    s = Search(index="targets").query("match", checked=True).delete()
    sleep(24 * 3600)
