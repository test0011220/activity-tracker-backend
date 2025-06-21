from bson.objectid import ObjectId
from datetime import datetime

class DiaryRepository:
    def __init__(self, mongo_db):
        self.diaries_collection = mongo_db["diaries"]

    def find_open_diary(self, user_id):
        return self.diaries_collection.find_one({
            "user_id": ObjectId(user_id),
            "open": True
        })

    def create_diary(self, user_id):
        new_diary = {
            "user_id": ObjectId(user_id),
            "open": True,
            "creation_date": datetime.utcnow(),
            "duration_time": 0,
            "activities": []
        }
        result = self.diaries_collection.insert_one(new_diary)
        return result.inserted_id

    def get_diaries_by_user(self, user_id):
        return list(self.diaries_collection.find({"user_id": ObjectId(user_id)}))