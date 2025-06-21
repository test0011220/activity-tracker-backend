from pymongo import MongoClient
from firebase_admin import firestore
from bson.objectid import ObjectId

class UserRepository:
    def __init__(self, mongo_db, firestore_db):
        self.mongo_users_collection = mongo_db["users_objects"]
        self.users_collection = firestore_db.collection("users_test")

    def find_user_by_pseudonym(self, pseudonym):
        user_query = self.users_collection.where("pseudonym", "==", pseudonym).limit(1).get()
        return next(iter(user_query), None)

    def find_mongo_user_by_pseudonym(self, pseudonym):
        return self.mongo_users_collection.find_one({"pseudonym": pseudonym})

    def find_mongo_user_by_id(self, user_id):
        return self.mongo_users_collection.find_one({"_id": ObjectId(user_id)})

    def sync_user_to_mongo(self, pseudonym):
        existing_user = self.find_mongo_user_by_pseudonym(pseudonym)
        if not existing_user:
            result = self.mongo_users_collection.insert_one({"pseudonym": pseudonym})
            return result.inserted_id
        return existing_user["_id"]

    def add_user_to_firestore(self, transaction, pseudonym, user_data):
        doc_ref = self.users_collection.document(pseudonym)
        snapshot = doc_ref.get(transaction=transaction)
        if snapshot.exists:
            raise ValueError("Utilisateur existe déjà ")
        transaction.set(doc_ref, user_data)
        return True

    def update_user(self, email, update_data):
        user_ref = self.users_collection.document(email)
        user_ref.update(update_data)

    def update_mongo_user_pseudonym(self, old_pseudonym, new_pseudonym):
        self.mongo_users_collection.update_one(
            {"pseudonym": old_pseudonym},
            {"$set": {"pseudonym": new_pseudonym}}
        )

    def delete_user(self, username):
        doc_ref = self.users_collection.document(username)
        doc = doc_ref.get()
        if doc.exists:
            doc_ref.delete()
            self.mongo_users_collection.delete_one({"pseudonym": username})
            return True
        return False

    def get_all_users(self):
        users = []
        for u in self.users_collection.get():
            u_dict = u.to_dict()
            mongo_user = self.mongo_users_collection.find_one({"pseudonym": u_dict.get("pseudonym")})
            user = {
                "pseudonym": u_dict.get("pseudonym", ""),
                "role": u_dict.get("role", ""),
                "email_address": u_dict.get("email_address", ""),
                "gender": u_dict.get("gender", ""),
                "mongo_user_id": str(mongo_user["_id"]) if mongo_user else None
            }
            if u_dict.get("role") == "student":
                user.update({
                    "year": u_dict.get("year", ""),
                    "studies": u_dict.get("studies", ""),
                    "semester": u_dict.get("semester", ""),
                    "age": u_dict.get("age", "")
                })
            users.append(user)
        return users

    def get_students(self):
        return [u.to_dict() for u in self.users_collection.where("role", "==", "student").get()]