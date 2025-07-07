"""
Methods to read from the database
"""

async def getSubreddits(db):
    async with db.getPool().acquire() as connection:
        query = "SELECT s_id FROM subreddit;"
        res = await connection.fetch(query)
    return res

async def getSubredditStatus(db, lb, rb):
    async with db.getPool().acquire() as connection:
        query = "SELECT new_post_id, hot_post_id FROM subreddit_status WHERE access_time >= $1 AND access_time <= $2;"
        res = await connection.fetch(query, lb, rb)
    return res