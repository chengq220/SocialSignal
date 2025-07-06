import asyncpg
import os
from dotenv import load_dotenv


class DBManager():
    _instance = None
    _pool = None
    
    def __new__(cls):
        if cls._instance == None:
            cls._instance = super(DBManager, cls).__new__(cls)
        return cls._instance

    async def connect(self):
        load_dotenv()
        dburl = os.getenv("DB_URL")
        try:
            self._pool = await asyncpg.create_pool(
                dsn=dburl, min_size=1, max_size=10
            )
        except Exception as e:
            print("Error occured when trying to initialized a connection to database") 

    
    async def disconnect(self):
        if self._pool is not None:
            try:
                await self._pool.close()
            except Exception as e:
                print("Error occured when trying to close pool")

    def getPool(self):
        return self._pool