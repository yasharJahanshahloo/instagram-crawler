from elasticsearch import Elasticsearch
from .settings import settings
import datetime


def insert_post(index = 'posts', dict_post={}, es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=dict_post, id=dict_post["key"])
    # print(res)

def insert_comment(index = 'comments', comment = {} , es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=comment)
    print(res)

def insert_popular(index = 'populars', username = '' , es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=username)
    print(res)