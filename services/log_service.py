class LogService:
    def __init__(self, log_repository):
        self.log_repository = log_repository

    def log_event(self, event_type, message, user=None):
        self.log_repository.log_event(event_type, message, user)

    def get_logs(self):
        return self.log_repository.get_logs(), 200