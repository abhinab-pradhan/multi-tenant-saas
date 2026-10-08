from pymongo import AsyncMongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL=os.getenv("MONGODB_URL")
DATABASE_NAME=os.getenv("DATABASE_NAME")

client=AsyncMongoClient(MONGODB_URL)

db=client[DATABASE_NAME]