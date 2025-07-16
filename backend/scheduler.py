from reddit import Reddit
import schedule
import time
import asyncio

def job():
    with open("/backend/scheduler.log", "a") as f:
        try:
            start = time.time()
            _ = asyncio.run(redditrun())
            end = time.time()
            f.write(f"Starting at {start} and finished job at {end}\n")
        except Exception as e :
            t = time.time()
            f.write(f"Error encountered at {t}\n")
            f.write(str(e))

async def redditrun():
    source = Reddit()
    _ = await source.getSubredditStatus()
    _ = await source.getPostsPerSubreddit()
    return 1

if __name__ == "__main__":
    schedule.every().day.at("1:00").do(job)
    # schedule.every(1).minutes.do(job)
    while True:
        schedule.run_pending()
        time.sleep(1)
