from bson.objectid import ObjectId

class QuestionnaireRepository:
    def __init__(self, mongo_db):
        self.questionnaires_collection = mongo_db["questionnaires"]
        self.questions_collection = mongo_db["questions"]
        self.questionnaire_responses_collection = mongo_db["questionnaire_responses"]

    def create_questionnaire(self, questionnaire):
        result = self.questionnaires_collection.insert_one(questionnaire)
        return result.inserted_id

    def update_questionnaire(self, questionnaire_id, updated_data):
        try:
            result = self.questionnaires_collection.update_one(
                {"_id": ObjectId(questionnaire_id)},
                {"$set": updated_data}
            )
            return result
        except Exception as e:
            print(f"DEBUG: Error updating questionnaire {questionnaire_id}: {str(e)}")
            return None

    def get_questionnaires(self, user_id=None, user_filieres=None, user_years=None, fetch_all=False):
        query = {}
        if not fetch_all and user_filieres and user_years:
            query.update({"is_active": True ,
                "$or": [
                    {"filieres": {"$in": user_filieres}},
                    {"years": {"$in": user_years}}
                ]
            })

        questionnaires = self.questionnaires_collection.find(query)

        answered_questionnaire_ids = []
        if user_id:
            try:
                answered_responses = self.questionnaire_responses_collection.find({"user_id": ObjectId(user_id)})
                answered_questionnaire_ids = [str(response["questionnaire_id"]) for response in answered_responses]
            except Exception as e:
                print(f"DEBUG: Error fetching answered questionnaires for user {user_id}: {str(e)}")

        return [
            {
                "_id": str(q["_id"]),
                "title": q["title"],
                "description": q["description"],
                "category": q["category"],
                "filieres": q["filieres"],
                "years": q["years"],
                "created_at": q["created_at"].isoformat(),
                "is_active": q["is_active"],
                "is_answered": str(q["_id"]) in answered_questionnaire_ids if user_id else False
            }
            for q in questionnaires
        ]

    def get_questionnaire_by_id(self, questionnaire_id):
        try:
            return self.questionnaires_collection.find_one({"_id": ObjectId(questionnaire_id)})
        except Exception as e:
            print(f"DEBUG: Error fetching questionnaire {questionnaire_id}: {str(e)}")
            return None

    def get_questionnaires_by_ids(self, questionnaire_ids):
        try:
            valid_ids = []
            for q_id in questionnaire_ids:
                try:
                    valid_ids.append(ObjectId(q_id))
                except Exception as e:
                    print(f"DEBUG: Invalid questionnaire_id {q_id}: {str(e)}")
                    continue

            if not valid_ids:
                return []

            questionnaires = self.questionnaires_collection.find({"_id": {"$in": valid_ids}})
            return [
                {
                    "_id": str(q["_id"]),
                    "title": q["title"],
                    "description": q["description"],
                    "category": q["category"],
                    "filieres": q["filieres"],
                    "years": q["years"],
                    "created_at": q["created_at"].isoformat(),
                    "is_active": q["is_active"]
                }
                for q in questionnaires
            ]
        except Exception as e:
            print(f"DEBUG: Error fetching questionnaires by IDs: {str(e)}")
            return []

    def submit_response(self, response_doc):
        self.questionnaire_responses_collection.insert_one(response_doc)

    def get_user_responses(self, user_id, questionnaire_id):
        try:
            response = self.questionnaire_responses_collection.find_one({
                "user_id": ObjectId(user_id),
                "questionnaire_id": ObjectId(questionnaire_id)
            })
            if not response:
                return None
            return {
                "_id": str(response["_id"]),
                "questionnaire_id": str(response["questionnaire_id"]),
                "user_id": str(response["user_id"]),
                "responses": [
                    {
                        "question_id": str(r["question_id"]),
                        "selected_proposition_id": r.get("selected_proposition_id"),
                        "answer_text": r.get("answer_text"),
                        "is_correct": r.get("is_correct")
                    }
                    for r in response["responses"]
                ],
                "duration_seconds": response["duration_seconds"],
                "feedback": response["feedback"],
                "completed_at": response["completed_at"].isoformat()
            }
        except Exception as e:
            print(f"DEBUG: Error fetching user responses for user {user_id}, questionnaire {questionnaire_id}: {str(e)}")
            return None

    def get_user_answered_questionnaires(self, user_id):
        try:
            responses = self.questionnaire_responses_collection.find({"user_id": ObjectId(user_id)})
            return [
                {
                    "questionnaire_id": str(response["questionnaire_id"]),
                    "completed_at": response["completed_at"].isoformat()
                }
                for response in responses
            ]
        except Exception as e:
            print(f"DEBUG: Error fetching answered questionnaires for user {user_id}: {str(e)}")
            return []

    def add_questionnaire(self, new_question):
        self.questionnaires_collection.insert_one(new_question)

    def delete_questionnaire(self, questionnaire_id):
        try:
            questionnaire_obj_id = ObjectId(questionnaire_id)
            questionnaire_result = self.questionnaires_collection.delete_one({"_id": questionnaire_obj_id})
            if questionnaire_result.deleted_count == 0:
                return False

            self.questions_collection.delete_many({"questionnaire_id": questionnaire_obj_id})
            self.questionnaire_responses_collection.delete_many({"questionnaire_id": questionnaire_obj_id})
            return True
        except Exception as e:
            print(f"DEBUG: Error deleting questionnaire {questionnaire_id}: {str(e)}")
            return False



    def delete_questions_by_questionnaire(self, questionnaire_id):
        try:
            self.questions_collection.delete_many({"questionnaire_id": ObjectId(questionnaire_id)})
        except Exception as e:
            print(f"DEBUG: Error deleting questions for questionnaire {questionnaire_id}: {str(e)}")

    def get_questionnaire_by_title(self, title):
        try:
            return self.questionnaires_collection.find_one({"title": title})
        except Exception as e:
            print(f"DEBUG: Error fetching questionnaire by title {title}: {str(e)}")
            return None