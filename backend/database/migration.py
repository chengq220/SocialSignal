"""
Methods to populate the database
"""
async def populateSubreddit(db, subreddits):
    async with db.getPool().acquire() as connection:
        res = await connection.executemany("""
                INSERT INTO Subreddit VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7, $8); """, subreddits)
    return res

async def populateSubredditStatus(db, status):
    async with db.getPool().acquire() as connection:
        res = await connection.executemany("""
                INSERT INTO subreddit_status VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7); """, status)
    return res

async def populateSubmission(db, submissions):
    async with db.getPool().acquire() as connection:
        res = await connection.executemany("""
                INSERT INTO submission VALUES (
                    $1,$2,$3,$4,
                    $5, $6, $7, $8); """, submissions)
    return res

async def populateSubmissionStatus(db, status):
    async with db.getPool().acquire() as connection:
        res = await connection.executemany("""
                INSERT INTO submission VALUES (
                    $1,$2,$3,$4,
                    $5, $6); """, status)
    return res

async def populateComment(db, comments):
    async with db.getPool().acquire() as connection:
        res = await connection.executemany("""
                INSERT INTO comment VALUES (
                    $1,$2,$3,$4,
                    $5, $6, $7, $&); """, comments)
    return res