import asyncpraw 
import time
# from encoding import TokenModel
import os
import asyncprawcore.exceptions
from datetime import datetime, timedelta
from database.database import DBManager
import database.migration as migrate
import database.query as dq
import asyncio
from summa import keywords
import sys

SUBMISSION_PER_SUBREDDIT = 1
COMMENT_PER_SUBMISSION = 3
MAX_RETRY = 3

db = DBManager()

class Reddit():
    def __init__(self):
        # self.reddit = asyncpraw.Reddit(
        #         client_id= os.getenv("REDDIT_CLIENT_ID"),
        #         client_secret= os.getenv("REDDIT_SECRET"),
        #         user_agent="ReadAgent",
        #     )
        placeholder = 0
        # self.emotion_model = TokenModel(type_info="emotion")
        # self.category_model = TokenModel(type_info="category")
    
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
                subred_keywords = [item[0] for item in keywords.keywords(sr.public_description, scores=True)[0:5]]
                if(sr.id not in seen_key):
                    subreddit.append((sr.id, sr.display_name, sr.over18, sr.public_description.strip(), category, sr.subreddit_type, subred_keywords, sr.created_utc))
                    seen_key.add(sr.id)
        _ = await migrate.populateSubreddit(db, subreddit)
        await db.disconnect()
        # return subreddit
    
    # Get the subreddit information at the latest time stamp
    async def getSubredditStatus(self):
        global db
        await db.connect()
        try:
            unprocessed_ids = await dq.getSubreddits(db)
            ids = [item["s_id"] for item in unprocessed_ids]
            s_id = [f"t5_{id_s}" for id_s in ids]
            async with asyncpraw.Reddit(
                        client_id= "4j5eA9rff-hGW2vh4ktNFQ",
                        client_secret= "YYzSC02w1DyDR58oONtVbhsUJ60DsQ",
                        user_agent="ReadAgent",
                    ) as source:
                enum_idx = 0
                async for sub in source.info(fullnames=s_id):
                    submissions = []
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
                            for submission in sub.new(limit=SUBMISSION_PER_SUBREDDIT): 
                                utcPostTime = submission.created
                                if(access_time - utcPostTime < 1800):
                                    new_posts = new_posts + 1
                                    new_posts_id.append(submission.id)
                                else:
                                    break
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(60)  # conservative sleep
                            retry_new += 1 
                        except:
                            print("Error occured exiting")
                    fetch_hot_submission_failed = True
                    hot_posts_id = []
                    retry_hot = 0
                    while fetch_hot_submission_failed and retry_hot < MAX_RETRY:
                        try:
                            for hot in sub.hot(limit=SUBMISSION_PER_SUBREDDIT//2):
                                hot_posts_id.append(hot.id)
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(60)  # conservative sleep
                            retry_hot += 1
                        except:
                            print("Error occured exiting")
                    key = str(access_time) + "_" + cur_s_id
                    submissions.append((key, cur_s_id, subscribers, new_posts, access_timestamp, new_posts_id, hot_posts_id))
                    _ = await migrate.populateSubredditStatus(submissions)
                    enum_idx = enum_idx + 1
                    time.sleep(1)
        except KeyboardInterrupt:
                sys.exit()
        except Exception as e:
            print(e)
            print("Other error occured. Exiting early")
        await db.disconnect()
        # return 1
    
    #Process the posts and then return it
    def __process_post(self, new_posts, hot_posts):
            new_posts_id = [id_s[2:len(id_s)-2].split("', '") for id_s in new_posts.to_list()]
            flatten_new = ["t3_"+x for xs in new_posts_id for x in xs if x]
            hot_posts_id = [id_s[2:len(id_s)-2].split("', '") for id_s in hot_posts.to_list()]
            flatten_hot = ["t3_"+x  for xs in hot_posts_id for x in xs if x]
            posts = flatten_new + flatten_hot
            return posts 
    
    # Get the hot/new posts information per subreddit
    # Get comment per posts
    async def getPostsPerSubreddit(self):
        global db
        await db.connect()
        try:
            rb_time = datetime.now().date()  # today's date
            lb_time = rb_time - timedelta(days=2)  # two days ago
            sr = await dq.getSubredditStatus(db, lb_time, rb_time) ################# Not sure if these two lines will work
            posts = self.__process_post(sr["new_post_id"], sr["hot_post_id"])#######
            num_fit = (len(posts) + 99) // 100
            for iteration in range(num_fit + 1):
                submissions = []
                submission_status = []
                start = iteration * 100
                end = min((iteration + 1) * 100, len(posts))
                iter_posts = posts[start:end]
                post_info_failed = True
                retry_post = 0
                async with asyncpraw.Reddit(
                        client_id= "4j5eA9rff-hGW2vh4ktNFQ",
                        client_secret= "YYzSC02w1DyDR58oONtVbhsUJ60DsQ",
                        user_agent="ReadAgent",
                    ) as source:
                    while post_info_failed and retry_post < MAX_RETRY:
                        try:
                            posts_info = source.info(fullnames=iter_posts)
                            post_info_failed = False
                        except asyncprawcore.exceptions.TooManyRequests as e:
                            print("429 Too Many Requests: Sleeping before retrying...")
                            time.sleep(60)  # conservative sleep
                            retry_post += 1
                    idx = 0
                    for sub in posts_info:
                        # Entries for the submissions
                        if not sub.selftext.strip():
                            continue
                        await sub.load() #fetch the subreddit object and its content
                        subreddit_obj = sub.subreddit
                        await subreddit_obj.load()
                        subreddit_id = subreddit_obj.id

                        access_time = int(time.time())
                        acess_timestamp = datetime.fromtimestamp(access_time).date()
                        submission_key = subreddit_id + "_" + str(idx)
                        status_key = str(access_time) + "_" + submission_key
                        # sentiment = self.emotion_model.query([sub.selftext.strip()])[0]
                        sentiment = "sad"
                        replace_failed = True
                        retry_replace = 0
                        while replace_failed and retry_replace < MAX_RETRY:
                            try:
                                await sub.comments.replace_more(limit=5)
                                replace_failed = False
                            except asyncprawcore.exceptions.TooManyRequests as e:
                                print("429 Too Many Requests: Sleeping before retrying...")
                                time.sleep(60)  # conservative sleep
                                retry_replace += 1
                        fetch_comment_failed = True
                        retry_comment = 0
                        comments_list = []
                        while fetch_comment_failed and retry_comment < MAX_RETRY:
                            try:
                                for cidx, comment in enumerate(sub.comments.list()[:COMMENT_PER_SUBMISSION]):
                                    # comments for each submissions
                                    # comment_sentiment = self.emotion_model.query([comment.body.strip()])[0]
                                    comment_sentiment = "sad"
                                    comment_key = status_key + "_" + submission_key + str(cidx)
                                    comment_keywords = [item[0] for item in keywords.keywords(comment.body.strip(), scores=True)[0:5]]
                                    comments_list.append((submission_key, comment_key, comment.author.name if comment.author else "[deleted]",
                                        comment.body.strip(),
                                        comment.score,
                                        comment_keywords,
                                        comment_sentiment,
                                        comment.created_utc))
                                fetch_comment_failed = False
                            except asyncprawcore.exceptions.TooManyRequests as e:
                                print("429 Too Many Requests: Sleeping before retrying...")
                                time.sleep(60)  # conservative sleep
                                retry_comment += 1
                        _ = migrate.populateComment(db, comments_list) # populate in batches as the program runs
                        submission_keyword = [item[0] for item in keywords.keywords(sub.selftext.strip(), scores=True)[0:5]]
                        submissions.append((submission_key, subreddit_id, sub.name, sub.over_18, sub.selftext.strip(), sentiment, submission_keyword, sub.created_utc))
                        submission_status.append((submission_key, status_key, sub.score, sub.upvote_ratio, sub.num_comments, acess_timestamp))
                        idx = idx + 1
                    time.sleep(2)
                _ = migrate.populateSubmission(db, submissions) # populate in batches as the program runs
                _ = migrate.populateSubmissionStatus(db, submission_status) # populate in batches as the program runs
        except KeyboardInterrupt:
            sys.exit()
        except Exception as e:
            print(e)
            print("Other error occured. Exiting early")
        await db.disconnect()
        return 0

if __name__ == "__main__":
    reddit = Reddit()
    # columns = ["s_id", "name", "over18", "description", "category", "type", "created_utc"]
    # subred = asyncio.run(reddit.getSubreddit(top=51))
    # print(subred)

    res = asyncio.run(reddit.getSubredditStatus())

    # columns1 = ["id", "s_id", "subscribers", "new_post_past_30minutes", "date_access_utc", "new_post_id", "hot_post_id"]
    # status = reddit.getSubredditStatus("subreddit.csv")
    # df1 = pd.DataFrame(status, columns=columns1).reset_index(drop=True)
    # df1.to_csv("subreddit_status.csv")

    # columns2 = ["s_id", "p_id", "title", "over18", "content", "sentiment", "created_utc"]
    # submissions, submission_status, comment = reddit.getPostsPerSubreddit("subreddit_status.csv")
    # df2 = pd.DataFrame(submissions, columns=columns2).reset_index(drop=True)
    # df2.to_csv("submission.csv")

    # colums3 = ["p_id", "id", "score", "upvote_ratio", "num_comments", "date_access_utc"]
    # df3 = pd.DataFrame(submission_status, columns=colums3).reset_index(drop=True)
    # df3.to_csv("submission_status.csv")

    # columns4 = ["p_id", "c_id", "author", "body", "score", "sentiment", "created_utc"]
    # df4 = pd.DataFrame(comment, columns=columns4).reset_index(drop=True)
    # df4.to_csv("comment.csv")
