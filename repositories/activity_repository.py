
class ActivityRepository:
    def __init__(self, mongo_db):
        self.activities_collection = mongo_db["activities"]

    def log_activity(self, activity_doc):
        self.activities_collection.insert_one(activity_doc)

    def get_activities_by_user(self, user_id):
        activities = list(self.activities_collection.find({"user_id": user_id}))
        print(activities)
        print(("-----------------------------------"))
        return [
            {
                "activity": act.get("activity"),
                "start_time": act.get("start_time").isoformat(),
                "end_time": act.get("end_time").isoformat(),
                "duration": act.get("duration_seconds")
            }
            for act in activities
        ]