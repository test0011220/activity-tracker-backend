from datetime import datetime
from bson.objectid import ObjectId

class QuestionService:
    def __init__(self, question_repository, log_service):
        self.question_repository = question_repository
        self.log_service = log_service

    def add_question(self, data):
        questionnaire_id = data.get("questionnaire_id")
        text = data.get("text")
        type = data.get("type", "multiple_choice")
        propositions = data.get("propositions", [])
        order = data.get("order", 1)

        if not questionnaire_id or not text:
            self.log_service.log_event("add_question_fail", "Champs requis manquants")
            return {"message": "Champs requis manquants"}, 400

        question = {
            "questionnaire_id": ObjectId(questionnaire_id),
            "text": text,
            "type": type,
            "propositions": propositions,
            "order": order,
            "created_at": datetime.utcnow()
        }

        question_id = self.question_repository.add_question(question)
        self.log_service.log_event("add_question", f"Question ajoutée au questionnaire {questionnaire_id}")
        return {"message": "Question ajoutée", "question_id": str(question_id)}, 200