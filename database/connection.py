from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from config import MONGODB_URI

client = None
db = None

def connect_db():
    global client, db
    try:
        client = MongoClient(MONGODB_URI)
        # Test the connection
        client.admin.command('ping')
        db = client["interviewPilot"]
        print("✅ MongoDB connected successfully!")
        return db
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise e

def get_db():
    global db
    if db is None:
        connect_db()
    return db

def close_db():
    global client

    if client:
        client.close()
        print("🔒 MongoDB connection closed")