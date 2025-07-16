import schedule
import time
import reddit
import asyncio

def job():
    with open("/backend/scheduler.log", "a") as f:
        try:
            start = time.time()
            _ = asyncio.run(redditrun())
            end = time.time()
            f.write(f"Starting at {start} and finished job at {end}\n")
        except:
            t = time.time()
            f.write(f"Error encountered at {t}\n")
        f.write("Starting at \n")

async def redditrun():
    _ = await reddit.getSubredditStatus()
    _ = await reddit.getPostsPerSubreddit()
    return 1

if __name__ == "__main__":
    schedule.every().day.at("10:30").do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
