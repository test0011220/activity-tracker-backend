
class CategoryRepository:
    def __init__(self, mongo_db):
        self.categories_collection = mongo_db["categories"]

    def get_category_map(self):
        categories = self.categories_collection.find()
        return {category["name"]: category["_id"] for category in categories}