import praw
import os
from dotenv import load_dotenv

class Reddit():
    def __init__(self):
        load_dotenv()
        self.reddit = praw.Reddit(
                        client_id= os.getenv("REDDIT_CLIENT_ID"),
                        client_secret= os.getenv("REDDIT_SECRET"),
                        user_agent="ReadAgent",
                    )
        
    def read_from_reddit(self):
        for submission in self.reddit.subreddit("test").hot(limit=10):
            print(submission.title)