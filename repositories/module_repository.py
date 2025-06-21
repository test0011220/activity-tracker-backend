
class ModuleRepository:
    def __init__(self, mongo_db):
        self.modules_collection = mongo_db["modules"]

    def get_modules(self, year, studies, semester):
        return list(self.modules_collection.find(
            {"year": year, "studies": studies, "semester": semester},
            {"_id": 0, "name": 1}
        ))