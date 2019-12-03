from elasticsearch import Elasticsearch


def insert(index, dict_post, es=None):
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=dict_post)
