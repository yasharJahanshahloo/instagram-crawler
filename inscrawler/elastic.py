from elasticsearch import Elasticsearch
from .settings import settings
from datetime import datetime
from elasticsearch_dsl import Document, Date, Integer, Nested, Boolean, \
    analyzer, InnerDoc, Completion, Keyword, Text, connections, Search


def insert_post(index='posts', dict_post={}, es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=dict_post, id=dict_post["key"])
    # print(res)


def insert_comment(index='comments', comment={}, es=None):
    if not settings.elastic:
        return
    if not es:
        es = Elasticsearch([{'host': 'localhost', 'port': 9200}])

    res = es.index(index=index, doc_type='_doc', body=comment)
    print(res)


class Popular(Document):
    username = Text(
        fields={'raw': Keyword()}
    )
    followers = Integer()
    added_at = Date()
    checked = Boolean()

    class Index:
        name = 'populars'

    def save(self, **kwargs):
        self.added_at = datetime.now()
        return super().save(**kwargs)


def insert_popular(username, followers=0, checked=False, doc_id=None):
    if not settings.elastic:
        return

    doc = Popular(username=username, followers=followers, checked=checked)
    doc.meta.id = doc_id if doc_id else username
    doc.save()


def get_unchecked_profiles(number_of_threads):
    s = Search(index="populars").query("match", checked=False)
    total = s.count()
    divider = total // number_of_threads
    hits_list = list()
    for i in range(number_of_threads - 1):
        s = s[i * divider:(i + 1) * divider]
        s.execute()
        hits_list.append(s)
    s = s[(number_of_threads - 1) * divider:total]
    s.execute()
    hits_list.append(s)

    return hits_list


def update_checked_status(username):
    Popular.get(id="username").update(checked=True)
