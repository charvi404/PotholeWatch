# test_mongo.py
import os, asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

async def test():
    uri = os.environ.get("MONGO_URL")
    dbname = os.environ.get("DB_NAME", "pothole_detection")
    print("Using URI:", "..." + uri[-40:])  # show tail only
    client = AsyncIOMotorClient(uri)
    try:
        # list databases (simple call to verify auth & connectivity)
        dbs = await client.list_database_names()
        print("Connected OK. Databases:", dbs)
        # check create/read test collection
        db = client[dbname]
        res = await db.test_connection.insert_one({"ok": True, "ts": __import__('datetime').datetime.utcnow().isoformat()})
        print("Inserted test doc id:", res.inserted_id)
        doc = await db.test_connection.find_one({"_id": res.inserted_id})
        print("Read back doc:", doc)
        # cleanup
        await db.test_connection.delete_one({"_id": res.inserted_id})
    except Exception as e:
        print("Connection test failed:", e)
    finally:
        client.close()

asyncio.run(test())
