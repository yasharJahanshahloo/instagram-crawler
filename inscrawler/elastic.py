from elasticsearch import Elasticsearch
from .settings import settings


def insert(index, dict_post, es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    print(f"\n*** passed to insert --> index:{index} , body:{dict_post}")
    res = es.index(index=index, doc_type='_doc', body=dict_post, id=dict_post["key"])
    print(res)