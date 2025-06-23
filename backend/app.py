from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

rigins = [
    "http://localhost",
    "http://localhost:3000"
]

@asynccontextmanager
async def lifespan(app):
    global db
    await db.connect()
    yield
    await db.disconnect()

app = FastAPI(lifespan=lifespan)
