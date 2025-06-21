from datetime import datetime
from bson.objectid import ObjectId


class QuestionnaireService:
    def __init__(self, user_repository, questionnaire_repository, question_repository, log_service):
        self.user_repository = user_repository
        self.questionnaire_repository = questionnaire_repository
        self.question_repository = question_repository
        self.log_service = log_service

    def create_questionnaire(self, data):
        title = data.get("title")
        description = data.get("description", "")
        category = data.get("category", "Autre")
        activity_id = data.get("activity_id")
        filieres = data.get("filieres", [])
        years = data.get("years", [])
        questions = data.get("questions", [])

        if not title or not filieres or not years:
            self.log_service.log_event("create_questionnaire_fail", "Champs requis manquants")
            return {"message": "Champs requis manquants"}, 400

        questionnaire = {
            "title": title,
            "description": description,
            "category": category,
            "activity_id": ObjectId(activity_id) if activity_id else None,
            "filieres": filieres,
            "years": years,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        questionnaire_id = self.questionnaire_repository.create_questionnaire(questionnaire)

        # Process and save questions
        for question in questions:
            question_doc = {
                "questionnaire_id": ObjectId(questionnaire_id),
                "text": question["text"],
                "type": question["type"],
                "propositions": question.get("propositions", []),
                "order": question.get("order", 1),
                "points": question.get("points", 1),  # Include points if provided
                "created_at": datetime.utcnow()
            }
            self.question_repository.add_question(question_doc)

        self.log_service.log_event("create_questionnaire", f"Questionnaire créé: {title}")
        return {"message": "Questionnaire créé", "questionnaire_id": str(questionnaire_id)}, 200

    def update_questionnaire(self, questionnaire_id, data):
        title = data.get("title")
        description = data.get("description", "")
        category = data.get("category", "Autre")
        activity_id = data.get("activity_id")
        filieres = data.get("filieres", [])
        years = data.get("years", [])
        questions = data.get("questions", [])

        if not title or not filieres or not years:
            self.log_service.log_event("update_questionnaire_fail", "Champs requis manquants")
            return {"message": "Champs requis manquants"}, 400

        updated_data = {
            "title": title,
            "description": description,
            "category": category,
            "activity_id": ObjectId(activity_id) if activity_id else None,
            "filieres": filieres,
            "years": years,
            "updated_at": datetime.utcnow()
        }

        result = self.questionnaire_repository.update_questionnaire(questionnaire_id, updated_data)
        if result.modified_count > 0:
            # Update or add questions
            self.questionnaire_repository.delete_questions_by_questionnaire(questionnaire_id)
            for question in questions:
                question_doc = {
                    "questionnaire_id": ObjectId(questionnaire_id),
                    "text": question["text"],
                    "type": question["type"],
                    "propositions": question.get("propositions", []),
                    "order": question.get("order", 1),
                    "points": question.get("points", 1),  # Include points if provided
                    "created_at": datetime.utcnow()
                }
                self.question_repository.add_question(question_doc)
            self.log_service.log_event("update_questionnaire", f"Questionnaire mis à jour: {title}")
            return {"message": "Questionnaire mis à jour"}, 200
        return {"message": "Questionnaire non trouvé"}, 404

    def toggle_questionnaire_status(self, questionnaire_id, is_active):
        questionnaire = self.questionnaire_repository.get_questionnaire_by_id(questionnaire_id)
        if not questionnaire:
            self.log_service.log_event("toggle_status_fail", "Questionnaire non trouvé")
            return {"message": "Questionnaire non trouvé"}, 404


        updated_data = {
            "is_active": is_active,
            "updated_at": datetime.utcnow()
        }
        result = self.questionnaire_repository.update_questionnaire(questionnaire_id, updated_data)
        if result.modified_count > 0:
            self.log_service.log_event("toggle_status",
                                       f"Statut du questionnaire {questionnaire_id} changé à {not is_active}")
            return {"message": "Statut mis à jour"}, 200
        return {"message": "Erreur lors de la mise à jour du statut"}, 500
    def duplicate_questionnaire(self, questionnaire_id,data):
        try:
            new_title = data.get("title")

            # Fetch the original questionnaire
            original_questionnaire = self.questionnaire_repository.get_questionnaire_by_id(questionnaire_id)
            if not original_questionnaire:
                self.log_service.log_event("duplicate_questionnaire_fail", f"Questionnaire not found: {questionnaire_id}")
                return {"message": "Questionnaire non trouvé"} , 404

            # Increment the title if it already exists (simplified logic)
            base_title = original_questionnaire["title"]
            if new_title:
                base_title = new_title.rsplit('(', 1)[0].strip()
            count = 1
            while self.questionnaire_repository.get_questionnaire_by_title(f"{base_title}({count})"):
                count += 1
            final_title = f"{base_title}({count})"

            # Create new questionnaire
            new_questionnaire = {
                "title": final_title,
                "description": original_questionnaire["description"],
                "category": original_questionnaire["category"],
                "activity_id": original_questionnaire.get("activity_id"),
                "filieres": original_questionnaire["filieres"],
                "years": original_questionnaire["years"],
                "is_active": original_questionnaire["is_active"],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            new_questionnaire_id = self.questionnaire_repository.create_questionnaire(new_questionnaire)

            # Duplicate questions
            questions = self.question_repository.get_questions_by_questionnaire(questionnaire_id)
            for question in questions:
                new_question = {
                    "questionnaire_id": new_questionnaire_id,
                    "text": question["text"],
                    "type": question["type"],
                    "propositions": question["propositions"],
                    "order": question["order"],
                    "points": question.get("points", 1),
                    "created_at": datetime.utcnow()
                }
                self.question_repository.add_question(new_question)

            self.log_service.log_event("duplicate_questionnaire",
                                  f"Questionnaire duplicated: {questionnaire_id} -> {new_questionnaire_id}")
            return {"message": "Questionnaire dupliqué avec succès",
                            "new_questionnaire_id": str(new_questionnaire_id)}, 200
        except Exception as e:
            self.log_service.log_event("duplicate_questionnaire_error",
                                  f"Error duplicating questionnaire {questionnaire_id}: {str(e)}")
            return {"message": "Erreur lors de la duplication du questionnaire", "error": str(e)}, 500

    def get_questionnaires(self, data):
        user_id = data.get("mongo_user_id")
        if not user_id:
            self.log_service.log_event("get_questionnaires_fail", "mongo_user_id manquant")
            return {"message": "mongo_user_id requis"}, 400

        user = self.user_repository.find_mongo_user_by_id(user_id)
        if not user:
            self.log_service.log_event("get_questionnaires_fail",
                                       f"Utilisateur non trouvé pour mongo_user_id: {user_id}")
            return {"message": "Utilisateur non trouvé"}, 404

        user_query = self.user_repository.find_user_by_pseudonym(user["pseudonym"])
        if not user_query:
            self.log_service.log_event("get_questionnaires_fail",
                                       f"Utilisateur Firestore non trouvé pour pseudonym: {user['pseudonym']}")
            return {"message": "Utilisateur Firestore non trouvé"}, 404

        user_data = user_query.to_dict()
        role = user_data.get("role", "student")

        if role == "super_admin":
            questionnaires = self.questionnaire_repository.get_questionnaires(fetch_all=True)
            return questionnaires, 200

        studies = user_data.get("studies", "")
        user_filieres = [f.strip() for f in studies.split(",") if f.strip()] if isinstance(studies, str) else []

        user_year = user_data.get("year", "")
        user_years = [str(user_year)] if user_year else []
        if not user_years:
            self.log_service.log_event("get_questionnaires_fail", "Aucune année trouvée pour l'utilisateur",
                                       user["pseudonym"])
            return {"message": "Aucune année trouvée pour l'utilisateur"}, 400

        try:
            questionnaires = self.questionnaire_repository.get_questionnaires(
                user_id=user_id,
                user_filieres=user_filieres,
                user_years=user_years
            )
            unanswered_questionnaires = [q for q in questionnaires if not q["is_answered"]]
            return unanswered_questionnaires, 200
        except Exception as e:
            self.log_service.log_event("get_questionnaires_error",
                                       f"Erreur lors de la récupération des questionnaires: {str(e)}",
                                       user["pseudonym"])
            return {"message": "Erreur lors de la récupération des questionnaires", "error": str(e)}, 500

    def get_questionnaire(self, questionnaire_id):
        questionnaire = self.questionnaire_repository.get_questionnaire_by_id(questionnaire_id)
        if not questionnaire:
            return {"message": "Questionnaire non trouvé"}, 404

        questions = self.question_repository.get_questions_by_questionnaire(questionnaire_id)
        result = {
            "_id": str(questionnaire["_id"]),
            "title": questionnaire["title"],
            "description": questionnaire["description"],
            "category": questionnaire["category"],
            "filieres": questionnaire["filieres"],
            "years": questionnaire["years"],
            "questions": questions,
            "is_active": questionnaire["is_active"]
        }
        return result, 200

    def submit_questionnaire_response(self, data):
        questionnaire_id = data.get("questionnaire_id")
        user_id = data.get("mongo_user_id")
        responses = data.get("responses")
        duration_seconds = data.get("duration_seconds")
        feedback = data.get("feedback", "")

        if not questionnaire_id or not user_id or not responses:
            self.log_service.log_event("submit_response_fail", "Champs requis manquants")
            return {"message": "Champs requis manquants"}, 400

        questionnaire = self.questionnaire_repository.get_questionnaire_by_id(questionnaire_id)
        if not questionnaire or not questionnaire.get("is_active"):
            return {"message": "Questionnaire non trouvé ou désactivé"}, 404

        processed_responses = []
        for response in responses:
            question = self.question_repository.get_question_by_id(response["question_id"])
            if not question:
                continue
            is_correct = False
            if question["type"] == "multiple_choice" and response.get("selected_proposition_id"):
                selected = next((p for p in question["propositions"] if p["id"] == response["selected_proposition_id"]),
                                None)
                is_correct = selected["is_correct"] if selected else False
            processed_responses.append({
                "question_id": ObjectId(response["question_id"]),
                "selected_proposition_id": response.get("selected_proposition_id"),
                "answer_text": response.get("answer_text"),
                "is_correct": is_correct
            })

        response_doc = {
            "questionnaire_id": ObjectId(questionnaire_id),
            "user_id": ObjectId(user_id),
            "responses": processed_responses,
            "duration_seconds": duration_seconds,
            "feedback": feedback,
            "completed_at": datetime.utcnow()
        }

        self.questionnaire_repository.submit_response(response_doc)
        self.log_service.log_event("submit_response", f"Réponses soumises pour le questionnaire {questionnaire_id}",
                                   user_id)
        return {"message": "Réponses enregistrées avec succès"}, 200

    def get_user_responses(self, user_id, questionnaire_id):
        response = self.questionnaire_repository.get_user_responses(user_id, questionnaire_id)
        if not response:
            return {"message": "Aucune réponse trouvée"}, 404
        return response, 200

    def get_user_answered_questionnaires(self, user_id):
        try:
            try:
                user_id_obj = ObjectId(user_id)
            except Exception as e:
                self.log_service.log_event("get_answered_questionnaires_error", f"Invalid user_id {user_id}: {str(e)}")
                return {"message": "Invalid user_id"}, 400

            responses = self.questionnaire_repository.get_user_answered_questionnaires(user_id)
            if not responses:
                return [], 200

            questionnaire_ids = [response["questionnaire_id"] for response in responses]
            questionnaires = self.questionnaire_repository.get_questionnaires_by_ids(questionnaire_ids)

            questionnaire_map = {q["_id"]: q for q in questionnaires}

            result = []
            for response in responses:
                q_id = response["questionnaire_id"]
                if q_id in questionnaire_map:
                    q = questionnaire_map[q_id]
                    result.append({
                        "_id": q["_id"],
                        "title": q["title"],
                        "description": q["description"],
                        "category": q["category"],
                        "filieres": q["filieres"],
                        "years": q["years"],
                        "created_at": q["created_at"],
                        "completed_at": response["completed_at"]
                    })
                else:
                    self.log_service.log_event("get_answered_questionnaires_warning",
                                               f"Questionnaire {q_id} not found for user {user_id}")

            return result, 200
        except Exception as e:
            self.log_service.log_event("get_answered_questionnaires_error",
                                       f"Erreur lors de la récupération des questionnaires répondus: {str(e)}", user_id)
            return {"message": "Erreur lors de la récupération des questionnaires répondus", "error": str(e)}, 500