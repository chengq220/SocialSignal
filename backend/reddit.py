import asyncpraw 
import time
from encoding import TokenModel
import os
import asyncprawcore.exceptions
from datetime import datetime, timedelta
from database.database import DBManager
import database.migration as migrate
import database.query as dq
import asyncio
from summa import keywords
import sys
import argparse

SUBMISSION_PER_SUBREDDIT = 1
COMMENT_PER_SUBMISSION = 3
MAX_RETRY = 3
NUM_KEYWORD = 5

db = DBManager()

class Reddit():
    def __init__(self):
        self.emotion_model = TokenModel(type_info="emotion")
        self.category_model = TokenModel(type_info="category")
    
    # Should only be run once to get the top 100 subreddits
    async def getSubreddit(self, top=50):
        global db
        await db.connect()
        subreddit = []
        seen_key = set()
        async with asyncpraw.Reddit(
                client_id= os.getenv("REDDIT_CLIENT_ID"),
                client_secret= os.getenv("REDDIT_SECRET"),
                user_agent="ReadAgent",
            ) as source:
            async for sr in source.subreddits.popular(limit=top):
                category = self.category_model.query([sr.public_description])[0]
                subred_keywords = ','.join(item for item in [item[0] for item in keywords.keywords(sr.public_description, scores=True)[0:NUM_KEYWORD]])
                if(sr.id not in seen_key):
                    dttime = datetime.fromtimestamp(sr.created_utc).date()
                    subreddit.append((sr.id, sr.display_name, sr.over18, sr.public_description.strip(), category, sr.subreddit_type, dttime, subred_keywords))
                    seen_key.add(sr.id)
        _ = await migrate.populateSubreddit(db, subreddit)
        await db.disconnect()
        return 1
    
    # Get the subreddit information at the latest time stamp
    async def getSubredditStatus(self):
        global db
        await db.connect()
        try:
            unprocessed_ids = await dq.getSubreddits(db)
            ids = [item["s_id"] for item in unprocessed_ids]
            s_id = [f"t5_{id_s}" for id_s in ids]
            async with asyncpraw.Reddit(
                        client_id= os.getenv("REDDIT_CLIENT_ID"),
                        client_secret= os.getenv("REDDIT_SECRET"),
                        user_agent="ReadAgent",
                    ) as source:
                enum_idx = 0
                async for sub in source.info(fullnames=s_id):
                    cur_s_id = s_id[enum_idx]
                    access_time = int(time.time())
                    access_timestamp = datetime.fromtimestamp(access_time).date()
                    subscribers = sub.subscribers
                    new_posts = 0
                    new_posts_id = []
                    fetch_submission_failed = True
                    retry_new = 0
                    while fetch_submission_failed and retry_new < MAX_RETRY:
                        try:
                            async for submission in sub.new(limit=SUBMISSION_PER_SUBREDDIT): 
                                utcPostTime = submission.created
                                if(access_time - utcPostTime < 1800):
                                    new_posts = new_posts + 1
                                    new_posts_id.append(submission.id)
                                else:
                                    break
                            fetch_submission_failed = False
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(10)  # conservative sleep
                            retry_new += 1 
                        except:
                            print("Error occured exiting")
                    fetch_hot_submission_failed = True
                    hot_posts_id = []
                    retry_hot = 0
                    while fetch_hot_submission_failed and retry_hot < MAX_RETRY:
                        try:
                            async for hot in sub.hot(limit=SUBMISSION_PER_SUBREDDIT//2):
                                hot_posts_id.append(hot.id)
                            fetch_hot_submission_failed = False
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(10)  # conservative sleep
                            retry_hot += 1
                        except:
                            print("Error occured exiting")
                    key = str(access_time) + "_" + cur_s_id
                    new_posts_id = ','.join(item for item in new_posts_id)
                    hot_posts_id = ','.join(item for item in hot_posts_id)
                    entry = [(key, cur_s_id[3:], subscribers, new_posts, access_timestamp, new_posts_id, hot_posts_id)]
                    enum_idx = enum_idx + 1
                    _ = await migrate.populateSubredditStatus(db, entry)
                    time.sleep(1)
        except KeyboardInterrupt:
                sys.exit()
        except Exception as e:
            print(e)
            print("Other error occured. Exiting early")
        await db.disconnect()
        return 1 
    
    # Get the hot/new posts information per subreddit
    # Get comment per posts
    async def getPostsPerSubreddit(self):
        global db
        await db.connect()
        try:
            rb_time = datetime.now().date()  # today's date
            lb_time = rb_time - timedelta(days=2)  # two days ago
            unprocessed_ids = await dq.getSubredditStatus(db, lb_time, rb_time) ################# Not sure if these two lines will work
            new_ids = ["t3_" + item["new_post_id"] for item in unprocessed_ids if item["new_post_id"]]
            hot_ids = ["t3_" + item["hot_post_id"] for item in unprocessed_ids if item["hot_post_id"]]
            posts = new_ids + hot_ids
            num_fit = (len(posts) + 99) // 100
            for iteration in range(num_fit):
                submissions = []
                submission_status = []
                start = iteration * 100
                end = min((iteration + 1) * 100, len(posts))
                iter_posts = posts[start:end]
                post_info_failed = True
                retry_post = 0
                async with asyncpraw.Reddit(
                        client_id= os.getenv("REDDIT_CLIENT_ID"),
                        client_secret= os.getenv("REDDIT_SECRET"),
                        user_agent="ReadAgent",
                    ) as source:
                    while post_info_failed and retry_post < MAX_RETRY:
                        try:
                            posts_info = source.info(fullnames=iter_posts)
                            post_info_failed = False
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(10)  # conservative sleep
                            retry_post += 1
                    idx = 0
                    async for sub in posts_info:
                        # Entries for the submissions
                        if not sub.selftext.strip():
                            continue
                        await sub.load() #fetch the subreddit object and its content
                        subreddit_obj = sub.subreddit
                        await subreddit_obj.load()
                        subreddit_id = subreddit_obj.id
                        access_time = int(time.time())
                        acess_timestamp = datetime.fromtimestamp(access_time).date()
                        submission_key = subreddit_id + "_" + str(access_time) + "_" + str(idx)
                        status_key = str(access_time) + "_" + submission_key
                        sentiment = self.emotion_model.query([sub.selftext.strip()])[0]
                        replace_failed = True
                        retry_replace = 0
                        while replace_failed and retry_replace < MAX_RETRY:
                            try:
                                await sub.comments.replace_more(limit=5)
                                replace_failed = False
                            except asyncprawcore.exceptions.TooManyRequests as e:
                                print("429 Too Many Requests: Sleeping before retrying...")
                                time.sleep(10)  # conservative sleep
                                retry_replace += 1
                        fetch_comment_failed = True
                        retry_comment = 0
                        comments_list = []
                        while fetch_comment_failed and retry_comment < MAX_RETRY:
                            try:
                                cidx = 0
                                for comment in sub.comments.list()[:COMMENT_PER_SUBMISSION]:
                                    # comments for each submissions
                                    comment_sentiment = self.emotion_model.query([comment.body.strip()])[0]
                                    comment_key = status_key + "_" + submission_key + str(cidx)
                                    comment_keywords =  ','.join(item for item in [item[0] for item in keywords.keywords(comment.body.strip(), scores=True)[0:NUM_KEYWORD]])
                                    comments_list.append((submission_key, comment_key, comment.author.name if comment.author else "[deleted]",
                                        comment.body.strip(),
                                        comment.score,
                                        comment_sentiment,
                                        datetime.fromtimestamp(comment.created_utc).date(),
                                        comment_keywords))
                                    cidx = cidx + 1
                                fetch_comment_failed = False
                            except asyncprawcore.exceptions.TooManyRequests as e:
                                print("429 Too Many Requests: Sleeping before retrying...")
                                time.sleep(10)  # conservative sleep
                                retry_comment += 1
                        submission_keyword =  ','.join(item for item in[item[0] for item in keywords.keywords(sub.selftext.strip(), scores=True)[0:NUM_KEYWORD]])
                        submissions.append((subreddit_id, submission_key, sub.name, sub.over_18, sub.selftext.strip(), sentiment, datetime.fromtimestamp(sub.created_utc).date(), submission_keyword))
                        submission_status.append((submission_key, status_key, sub.score, sub.upvote_ratio, sub.num_comments, acess_timestamp))
                        idx = idx + 1
                    time.sleep(2)
                _ = await migrate.populateSubmission(db, submissions) # populate in batches as the program runs
                _ = await migrate.populateSubmissionStatus(db, submission_status) # populate in batches as the program runs
                _ = await migrate.populateComment(db, comments_list) # populate in batches as the program runs
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            print(e)
            print("Other error occured. Exiting early")
        await db.disconnect()
        return 1

parser = argparse.ArgumentParser()
parser.add_argument("-o", "--option", type=int, default=1, choices=[1,2,3],
                     help = "1: Get most popular subrredit\n2: Get current status of popular subrredit\n3: Get submissions and comments from subreddit")

if __name__ == "__main__":
    reddit = Reddit()
    args = parser.parse_args()
    if args.option:
        if args.option == 1: 
            res = asyncio.run(reddit.getSubreddit(top=11))
        elif args.option == 2: 
            res = asyncio.run(reddit.getSubredditStatus())
        else:
            res = asyncio.run(reddit.getPostsPerSubreddit())
