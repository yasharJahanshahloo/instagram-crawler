from __future__ import unicode_literals

import glob
import json
import os
import re
import sys
import time
import traceback
from builtins import open
from datetime import datetime
from time import sleep

from tqdm import tqdm

from . import secret
from .browser import Browser
from .exceptions import RetryException
from .fetch import fetch_caption
from .fetch import fetch_comments
from .fetch import fetch_datetime
from .fetch import fetch_imgs
from .fetch import fetch_likers
from .fetch import fetch_likes_plays
from .fetch import fetch_details
from .utils import instagram_int
from .utils import randmized_sleep
from .utils import retry
from .elastic import insert_post, insert_popular


class Logging(object):
    PREFIX = "instagram-crawler"

    def __init__(self):
        try:
            timestamp = int(time.time())
            self.cleanup(timestamp)
            self.logger = open("/tmp/%s-%s.log" %
                               (Logging.PREFIX, timestamp), "w")
            self.log_disable = False
        except Exception:
            self.log_disable = True

    def cleanup(self, timestamp):
        days = 86400 * 7
        days_ago_log = "/tmp/%s-%s.log" % (Logging.PREFIX, timestamp - days)
        for log in glob.glob("/tmp/instagram-crawler-*.log"):
            if log < days_ago_log:
                os.remove(log)

    def log(self, msg):
        if self.log_disable:
            return

        self.logger.write(msg + "\n")
        self.logger.flush()

    def __del__(self):
        if self.log_disable:
            return
        self.logger.close()


class InsCrawler(Logging):
    URL = "https://www.instagram.com"
    RETRY_LIMIT = 10

    def __init__(self, has_screen=False):
        super(InsCrawler, self).__init__()
        self.browser = Browser(has_screen)
        self.page_height = 0

    def _dismiss_login_prompt(self):
        ele_login = self.browser.find_one(".Ls00D .Szr5J")
        if ele_login:
            ele_login.click()

    def login(self):
        browser = self.browser
        url = "%s/accounts/login/" % (InsCrawler.URL)
        browser.get(url)
        u_input = browser.find_one('input[name="username"]')
        u_input.send_keys(secret.username)
        p_input = browser.find_one('input[name="password"]')
        p_input.send_keys(secret.password)

        login_btn = browser.find_one(".L3NKy")
        login_btn.click()

        @retry()
        def check_login():
            if browser.find_one('input[name="username"]'):
                print("wrong username or password")
                raise RetryException()

        check_login()

    def get_user_profile(self, username):
        browser = self.browser
        url = "%s/%s/" % (InsCrawler.URL, username)
        browser.get(url)
        name = browser.find_one(".rhpdm")
        desc = browser.find_one(".-vDIg span")
        photo = browser.find_one("._6q-tv")
        statistics = [ele.text for ele in browser.find(".g47SY")]
        try:
            post_num, follower_num, following_num = statistics
        except:
            return
        return {
            "name": name.text,
            "desc": desc.text if desc else None,
            "photo_url": photo.get_attribute("src"),
            "post_num": post_num,
            "follower_num": follower_num,
            "following_num": following_num,
        }

    def get_user_profile_from_script_shared_data(self, username):
        browser = self.browser
        url = "%s/%s/" % (InsCrawler.URL, username)
        browser.get(url)
        source = browser.driver.page_source
        p = re.compile(
            r"window._sharedData = (?P<json>.*?);</script>", re.DOTALL)
        json_data = re.search(p, source).group("json")
        data = json.loads(json_data)

        user_data = data["entry_data"]["ProfilePage"][0]["graphql"]["user"]

        return {
            "name": user_data["full_name"],
            "desc": user_data["biography"],
            "photo_url": user_data["profile_pic_url_hd"],
            "post_num": user_data["edge_owner_to_timeline_media"]["count"],
            "follower_num": user_data["edge_followed_by"]["count"],
            "following_num": user_data["edge_follow"]["count"],
            "website": user_data["external_url"],
        }

    def get_user_posts(self, username, number=None, detail=False, es=None):
        user_profile = self.get_user_profile(username)
        if not number:
            number = instagram_int(user_profile["post_num"])

        self._dismiss_login_prompt()

        if detail:
            return self._get_posts_full(number, es)
        else:
            return self._get_posts(number)

    def get_latest_posts_by_tag(self, tag, num):
        url = "%s/explore/tags/%s/" % (InsCrawler.URL, tag)
        self.browser.get(url)
        return self._get_posts(num)

    def get_popular_profiles(self, starting_user, es=None):
        user_profile = self.get_user_profile(starting_user)

        browser = self.browser
        followers_btn = browser.find_by_xpath(
            # xpath='//*[@id="react-root"]/section/main/div/header/section/ul/li[2]/a') #by followers
            xpath='//*[@id="react-root"]/section/main/div/header/section/ul/li[3]/a')
        if followers_btn:
            followers_btn.click()
        sleep(0.3)
        followers = browser.find(css_selector=".FPmhX")

        def _is_popular(username, browser):
            url = "%s/%s/" % (InsCrawler.URL, username)
            browser.open_new_tab(url)
            try:
                statistics = [ele.text for ele in browser.find(".g47SY")]
                post_num, follower_num, following_num = statistics
            except ValueError:
                print(f"error finding follow numbers of {username}")
                return 0
            browser.close_current_tab()
            randmized_sleep(0.3)
            return instagram_int(follower_num)

        print("<<scrolling down>>")
        while len(followers) < instagram_int(user_profile["following_num"]) - 10:
            browser.panel_scroll_down(followers[0])
            followers = browser.find(css_selector=".FPmhX")

        def check_followers(start, followers, browser):
            limit = 15000
            for i in range(start, len(followers)):
                randmized_sleep(0.2)
                try:
                    follow_num = _is_popular(followers[i].text, browser)
                except Exception as exp:
                    print("exeption in checking : ", exp)
                    followers = browser.find(css_selector=".FPmhX")
                    check_followers(i, followers, browser)

                if follow_num > limit:
                    print(
                        f"adding {followers[i].text} to elastic with {follow_num} followers")
                    popular_user = {"username": followers[i].text,
                                    "followers": follow_num,
                                    "is_checked": False}
                    insert_popular(username=popular_user, es=es)

        check_followers(0, followers, browser)

    def auto_like(self, tag="", maximum=1000):
        self.login()
        browser = self.browser
        if tag:
            url = "%s/explore/tags/%s/" % (InsCrawler.URL, tag)
        else:
            url = "%s/explore/" % (InsCrawler.URL)
        self.browser.get(url)

        ele_post = browser.find_one(".v1Nh3 a")
        ele_post.click()

        for _ in range(maximum):
            heart = browser.find_one(
                ".dCJp8 .glyphsSpriteHeart__outline__24__grey_9")
            if heart:
                heart.click()
                randmized_sleep(2)

            left_arrow = browser.find_one(".HBoOv")
            if left_arrow:
                left_arrow.click()
                randmized_sleep(2)
            else:
                break

    def _get_posts_full(self, num, es=None):
        @retry()
        def check_next_post(cur_key):
            ele_a_datetime = browser.find_one(".eo2As .c-Yi7")

            # It takes time to load the post for some users with slow network
            if ele_a_datetime is None:
                raise RetryException()

            next_key = ele_a_datetime.get_attribute("href")
            if cur_key == next_key:
                raise RetryException()

        browser = self.browser
        browser.implicitly_wait(1)
        browser.scroll_down()
        ele_post = browser.find_one(".v1Nh3 a")
        ele_post.click()
        dict_posts = {}

        pbar = tqdm(total=num)
        pbar.set_description("fetching")
        cur_key = None

        # Fetching all posts
        for _ in range(num):
            dict_post = {}

            # Fetching post detail
            try:
                check_next_post(cur_key)

                # Fetching datetime and url as key
                username = browser.find_one('.BrX75')
                username = browser.find_one(
                    elem=username, css_selector=".FPmhX").text
                ele_a_datetime = browser.find_one(".eo2As .c-Yi7")
                cur_key = ele_a_datetime.get_attribute("href")
                dict_post["key"] = cur_key
                fetch_datetime(browser, dict_post)
                fetch_imgs(browser, dict_post)
                fetch_likes_plays(browser, dict_post)
                fetch_likers(browser, dict_post)
                fetch_caption(browser, dict_post)
                dict_post["fetched_time"] = datetime.now()
                insert_post(index="posts", dict_post=dict_post, es=es)
                fetch_comments(browser, dict_post, es=es)

            except RetryException:
                sys.stderr.write(
                    "\x1b[1;31m" +
                    "Failed to fetch the post: " +
                    cur_key or 'URL not fetched' +
                    "\x1b[0m" +
                    "\n"
                )
                traceback.print_exc()
                # break TODO

            except Exception:
                sys.stderr.write(
                    "\x1b[1;31m" +
                    "Failed to fetch the post: " +
                    cur_key if isinstance(cur_key, str) else 'URL not fetched' +
                                                             "\x1b[0m" +
                                                             "\n************\n"
                )
                traceback.print_exc()

            self.log(json.dumps(dict_post, ensure_ascii=False, default=str))
            dict_posts[browser.current_url] = dict_post

            pbar.update(1)
            left_arrow = browser.find_one(".HBoOv")
            if left_arrow:
                left_arrow.click()

        pbar.close()
        posts = list(dict_posts.values())
        if posts:
            posts.sort(key=lambda post: post["datetime"], reverse=True)
        return posts

    def _get_posts(self, num):
        """
            To get posts, we have to click on the load more
            button and make the browser call post api.
        """
        TIMEOUT = 600
        browser = self.browser
        key_set = set()
        posts = []
        pre_post_num = 0
        wait_time = 1

        pbar = tqdm(total=num)

        def start_fetching(pre_post_num, wait_time):
            ele_posts = browser.find(".v1Nh3 a")
            for ele in ele_posts:
                key = ele.get_attribute("href")
                if key not in key_set:
                    dict_post = {"key": key}
                    ele_img = browser.find_one(".KL4Bh img", ele)
                    dict_post["caption"] = ele_img.get_attribute("alt")
                    dict_post["img_url"] = ele_img.get_attribute("src")

                    t1 = datetime.now()
                    fetch_details(browser, dict_post)
                    t2 = datetime.now()
                    print("outside of fetch details: ", t2 - t1)

                    key_set.add(key)
                    posts.append(dict_post)

                    if len(posts) == num:
                        break

            if pre_post_num == len(posts):
                pbar.set_description("Wait for %s sec" % (wait_time))
                sleep(wait_time)
                pbar.set_description("fetching")

                wait_time *= 2
                browser.scroll_up(300)
            else:
                wait_time = 1

            pre_post_num = len(posts)
            browser.scroll_down()

            return pre_post_num, wait_time

        pbar.set_description("fetching")
        while len(posts) < num and wait_time < TIMEOUT:
            post_num, wait_time = start_fetching(pre_post_num, wait_time)
            pbar.update(post_num - pre_post_num)
            pre_post_num = post_num

            loading = browser.find_one(".W1Bne")
            if not loading and wait_time > TIMEOUT / 2:
                break

        pbar.close()
        print("Done. Fetched %s posts." % (min(len(posts), num)))
        return posts[:num]
