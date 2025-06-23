import asyncio
import os
from dotenv import load_dotenv
from twikit import Client

class Twitter():
    def __init__(self):
        self.client = Client('en-US')
        load_dotenv()
        asyncio.run(self.login())

    async def login(self):
        await self.client.login(
            auth_info_1=os.getenv("TWITTER_USERNAME"),
            auth_info_2=os.getenv("TWITTER_EMAIL"),
            password=os.getenv("TWITTER_PASSWORD"),
            cookies_file='cookies.json'
        )

        