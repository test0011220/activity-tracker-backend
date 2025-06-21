from datetime import datetime, timezone

class LogRepository:
    def __init__(self, mongo_db):
        self.logs_collection = mongo_db["logs"]

    def log_event(self, event_type, message, user=None):
        log = {
            "timestamp": datetime.now(timezone.utc),
            "event_type": event_type,
            "message": message,
            "user": user
        }
        self.logs_collection.insert_one(log)

    def get_logs(self):
        logs = list(self.logs_collection.find().sort("timestamp", -1))
        for log in logs:
            log["_id"] = str(log["_id"])
            log["timestamp"] = log["timestamp"].isoformat()
        return logs