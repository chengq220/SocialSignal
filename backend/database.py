import asyncpg
import os
from dotenv import load_dotenv


class DBManager():
    def __init__(self):
        self.pool = None
    
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(DBManager, cls).__new__(cls)
        return cls.instance

    async def connect(self):
        load_dotenv()
        dburl = os.getenv("DB_URL")
        try:
            self.pool = await asyncpg.create_pool(
                dsn=dburl, min_size=1, max_size=10
            )
        except Exception as e:
            print("Error occured when trying to initialized a connection to database") 

    
    async def disconnect(self):
        if self.pool is not None:
            try:
                await self.pool.close()
            except Exception as e:
                print("Error occured when trying to close pool")

    def getPool(self):
        return self.pool