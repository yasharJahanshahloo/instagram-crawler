from elasticsearch_dsl import connections

from inscrawler.elastic import insert_popular,Popular

connections.create_connection(hosts=['localhost'], timeout=20)
Popular.init()
insert_popular(username="amir_mahdi_jule", followers=2500000, checked=False)

