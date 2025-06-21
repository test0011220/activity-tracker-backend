from datetime import datetime
from bson.objectid import ObjectId

class ActivityService:
    def __init__(self, user_repository, diary_repository, activity_repository, category_repository, log_service):
        self.user_repository = user_repository
        self.diary_repository = diary_repository
        self.activity_repository = activity_repository
        self.category_repository = category_repository
        self.log_service = log_service

    def log_activity(self, data):
        username = data.get("username")
        activity_name = data.get("activity")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        duration = data.get("duration_seconds")
        category_name = data.get("category")

        if not all([username, activity_name, start_time, end_time]) or duration is None:
            self.log_service.log_event("log_activity_fail", "Missing data", username)
            return {"message": "Missing data"}, 400

        user = self.user_repository.find_user_by_pseudonym(username)
        if not user:
            self.log_service.log_event("log_activity_fail", "Utilisateur non trouvé", username)
            return {"message": "Utilisateur non trouvé"}, 404

        mongo_user = self.user_repository.find_mongo_user_by_pseudonym(username)
        if not mongo_user:
            mongo_user_id = self.user_repository.sync_user_to_mongo(username)
        else:
            mongo_user_id = mongo_user["_id"]

        category_map = self.category_repository.get_category_map()
        category_id = None
        if category_name and category_name in category_map:
            category_id = category_map[category_name]
        elif category_name:
            self.log_service.log_event("log_activity_fail", f"Catégorie '{category_name}' non trouvée", username)
            return {"message": f"Catégorie '{category_name}' non trouvée"}, 404

        diary_id = self.diary_repository.find_open_diary(mongo_user_id)
        if not diary_id:
            diary_id = self.diary_repository.create_diary(mongo_user_id)

        activity_doc = {
            "user_id": ObjectId(mongo_user_id),
            "diary_id": diary_id,
            "activity": activity_name,
            "start_time": datetime.fromisoformat(start_time),
            "end_time": datetime.fromisoformat(end_time),
            "duration_seconds": duration,
            "category_id": ObjectId(category_id) if category_id else None,
        }

        self.activity_repository.log_activity(activity_doc)
        self.log_service.log_event("activity_log", f"Activité '{activity_name}' enregistrée avec catégorie '{category_name}'", username)
        return {"message": "Activity logged successfully"}, 200