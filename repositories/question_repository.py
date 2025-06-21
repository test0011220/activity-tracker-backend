from bson.objectid import ObjectId

class QuestionRepository:
    def __init__(self, mongo_db):
        self.questions_collection = mongo_db["questions"]

    def add_question(self, question):
        result = self.questions_collection.insert_one(question)
        return result.inserted_id

    def get_questions_by_questionnaire(self, questionnaire_id):
        questions = self.questions_collection.find({"questionnaire_id": ObjectId(questionnaire_id)}).sort("order", 1)
        return [
            {
                "_id": str(q["_id"]),
                "text": q["text"],
                "type": q["type"],
                "propositions": q["propositions"],
                "points":q.get("points", 0),
                "order": q["order"]
            }
            for q in questions
        ]

    def get_question_by_id(self, question_id):
        return self.questions_collection.find_one({"_id": ObjectId(question_id)})