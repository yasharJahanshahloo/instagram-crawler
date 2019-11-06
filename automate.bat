@echo off
for /f %%d in (%1) do python crawler.py hashtag -t iran -n 50 -o ./%%d --fetch_details --fetch_comments %2