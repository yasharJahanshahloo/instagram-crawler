import random

from elasticsearch import Elasticsearch
from .settings import settings
from datetime import datetime
from elasticsearch_dsl import Document, Date, Integer, Nested, Boolean, \
    analyzer, InnerDoc, Completion, Keyword, Text, connections, Search


class Post(Document):
    username = Text(
        fields={'raw': Keyword()}
    )
    key = Text(
        fields={'raw': Keyword()}
    )
    img_urls = Text(
        fields={'raw': Keyword()}
    )
    hashtags = Text(
        fields={'raw': Keyword()}
    )
    mentions = Text(
        fields={'raw': Keyword()}
    )
    location = Text(
        fields={'raw': Keyword()}
    )
    caption = Text()
    added_at = Date()
    published_at = Date()
    last_update = Date()

    class Index:
        name = 'posts'

    def save(self, **kwargs):
        self.added_at = datetime.now()
        self.last_update = datetime.now()
        return super().save(**kwargs)


def insert_post(dict_post):
    if not settings.elastic:
        return

    doc = Post(username=dict_post.get("username", "unknown"), key=dict_post["key"], img_urls=dict_post["img_urls"],
               hashtags=dict_post.get("hashtags", []), mentions=dict_post.get("mentions", []),
               location=dict_post.get("location", []),
               caption=dict_post.get("caption", ""), published_at=dict_post.get("published_at", ""))
    doc.meta.id = dict_post["key"]
    doc.save()


class Comment(Document):
    post_id = Text(
        fields={'raw': Keyword()}
    )
    author = Text(
        fields={'raw': Keyword()}
    )
    comment = Text(
        fields={'raw': Keyword()}
    )
    hashtags = Text(
        fields={'raw': Keyword()}
    )
    mentions = Text(
        fields={'raw': Keyword()}
    )
    added_at = Date()
    published_at = Date()

    class Index:
        name = 'comments'

    def save(self, **kwargs):
        self.added_at = datetime.now()
        return super().save(**kwargs)


def insert_comment(comment_obj):
    if not settings.elastic:
        return

    doc = Comment(post_id=comment_obj["post_id"], author=comment_obj["author"], comment=comment_obj["comment"],
                  hashtags=comment_obj.get("hashtags", []), mentions=comment_obj.get("mentions", []),
                  published_at=comment_obj.get("published_at", ""))
    doc.meta.id = comment_obj["post_id"] + '|' \
                  + comment_obj["author"] + '|' \
                  + comment_obj.get("published_at", random.randint(0, 100))
    doc.save()


class Popular(Document):
    username = Text(
        fields={'raw': Keyword()}
    )
    followers = Integer()
    added_at = Date()
    last_update = Date()
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


def update_checked_status(username, index_class):
    index_class.get(id=username).update(checked=True)


class Target(Document):
    username = Text(
        fields={'raw': Keyword()}
    )
    checked = Boolean()

    class Index:
        name = 'targets'

    def save(self, **kwargs):
        return super().save(**kwargs)


def insert_target(username, checked=False, doc_id=None):
    if not settings.elastic:
        return

    doc = Target(username=username, checked=checked)
    doc.meta.id = doc_id if doc_id else username
    doc.save()


def get_unchecked_targets(number_of_threads):
    s = Search(index="targets").query("match", checked=False)
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
