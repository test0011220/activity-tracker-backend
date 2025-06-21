from datetime import datetime, timezone
import bcrypt
from firebase_admin import  firestore


class UserService:
    def __init__(self, user_repository, log_service):
        self.user_repository = user_repository
        self.log_service = log_service

    def login(self, username, password):
        user = self.user_repository.find_user_by_pseudonym(username)
        if not user:
            self.log_service.log_event("login_fail", "Utilisateur non trouvé", username)
            return None, {"message": "Utilisateur non trouvé"}, 404

        user_data = user.to_dict()
        stored_hash = user_data.get("password")
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        if not bcrypt.checkpw(password.encode('utf-8'), stored_hash):
            self.log_service.log_event("login_fail", "Mot de passe incorrect", username)
            return None, {"message": "Mot de passe incorrect"}, 401

        mongo_user_id = self.user_repository.sync_user_to_mongo(username)
        self.log_service.log_event("login_success", f"{username} s'est connecté avec succès", username)
        response_data = {
            "message": "Login successful",
            "role": user_data.get("role"),
            "pseudonym": user_data.get("pseudonym"),
            "email": user_data.get("email_address", ""),
            "created_at": user_data.get("created_at", "").isoformat() if user_data.get("created_at") else "",
            "mongo_user_id": str(mongo_user_id)
        }
        if user_data.get("role") == "student":
            response_data.update({
                "year": user_data.get("year", ""),
                "studies": user_data.get("studies", ""),
                "semester": user_data.get("semester", "")
            })
        return response_data, None, 200

    def google_login(self, email, uid, custom_token):
        user_doc = self.user_repository.users_collection.document(email).get()
        if not user_doc.exists:
            user_data = {
                "custom_token": custom_token,
                "pseudonym": "",
                "role": "student",
                "email_address": email,
                "google_uid": uid,
                "password": "",
                "year": "",
                "studies": "",
                "semester": "",
                "gender": "",
                "created_at": firestore.SERVER_TIMESTAMP
            }
            self.user_repository.users_collection.document(email).set(user_data)
        else:
            user_data = user_doc.to_dict()

        mongo_user_id = self.user_repository.sync_user_to_mongo(email)
        role = user_data.get("role", "student")
        needs_profile_completion = not all([
            user_data.get("password", ""),
            user_data.get("year", ""),
            user_data.get("studies", ""),
            user_data.get("semester", "")
        ])

        self.log_service.log_event("google_login", f"Google login successful for {email}", email)
        return {
            "message": "Login successful",
            "role": role,
            "needsProfileCompletion": needs_profile_completion,
            "mongo_user_id": str(mongo_user_id),
            "userInfo": {
                "email": user_data.get("email_address", ""),
                "role": role,
                "pseudonym": user_data.get("pseudonym", ""),
                "year": user_data.get("year", ""),
                "studies": user_data.get("studies", ""),
                "semester": user_data.get("semester", ""),
                "gender": user_data.get("gender", ""),
                "created_at": user_data.get("created_at", "").isoformat() if user_data.get("created_at") else ""
            }
        }, 200

    def update_user_info(self, email, data):
        if not email:
            self.log_service.log_event("update_user_info_fail", "Email requis")
            return {"message": "Email requis"}, 400

        user_doc = self.user_repository.users_collection.document(email).get()
        if not user_doc.exists:
            self.log_service.log_event("update_user_info_fail", "Utilisateur non trouvé", email)
            return {"message": "Utilisateur non trouvé"}, 404

        hashed_password = bcrypt.hashpw(data.get("password", "").encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        update_data = {
            "pseudonym": data.get("pseudonym", ""),
            "password": hashed_password,
            "year": data.get("year", ""),
            "studies": data.get("studies", ""),
            "semester": data.get("semester", ""),
            "gender": data.get("gender", "")
        }
        self.user_repository.update_user(email, update_data)
        self.user_repository.update_mongo_user_pseudonym(email, data.get("pseudonym", ""))
        self.log_service.log_event("update_user_info", f"Profil mis à jour pour {email}", email)
        return {"message": "Profil mis à jour"}, 200

    def change_password(self, username, current_password, new_password):
        if not all([username, current_password, new_password]):
            self.log_service.log_event("change_password_fail", "Champs manquants", username)
            return {"message": "Champs manquants"}, 400

        user = self.user_repository.find_user_by_pseudonym(username)
        if not user:
            self.log_service.log_event("change_password_fail", "Utilisateur non trouvé", username)
            return {"message": "Utilisateur non trouvé"}, 404

        user_data = user.to_dict()
        stored_hash = user_data.get("password")
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode('utf-8')

        if not bcrypt.checkpw(current_password.encode('utf-8'), stored_hash):
            self.log_service.log_event("change_password_fail", "Mot de passe actuel incorrect", username)
            return {"message": "Mot de passe actuel incorrect"}, 401

        hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        self.user_repository.users_collection.document(user.id).update({"password": hashed_new_password})
        self.log_service.log_event("change_password_success", f"Mot de passe modifié pour {username}", username)
        return {"message": "Mot de passe modifié avec succès"}, 200

    def forgot_password(self, username):
        if not username:
            self.log_service.log_event("forgot_password_fail", "Nom d'utilisateur manquant")
            return {"message": "Nom d'utilisateur requis"}, 400

        user = self.user_repository.find_user_by_pseudonym(username)
        if not user:
            self.log_service.log_event("forgot_password_fail", "Utilisateur non trouvé", username)
            return {"message": "Utilisateur non trouvé"}, 404

        self.log_service.log_event(
            "forgot_password_request",
            f"Demande de réinitialisation de mot de passe pour {username}",
            username
        )
        requests_collection = self.user_repository.mongo_users_collection.database["password_reset_requests"]
        requests_collection.insert_one({
            "username": username,
            "timestamp": datetime.now(timezone.utc),
            "status": "pending"
        })
        return {"message": "Demande de réinitialisation envoyée à l'administrateur"}, 200

    def add_user(self, transaction, data):
        pseudonym = data.get("username")
        password = data.get("password")
        role = data.get("role")
        email = data.get("email")
        gender = data.get("gender")

        hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user_data = {
            "pseudonym": pseudonym,
            "password": hashed_password,
            "role": role,
            "email_address": email,
            "gender": gender,
            "created_at": firestore.SERVER_TIMESTAMP
        }

        if role == "student":
            user_data.update({
                "age": data.get("age"),
                "studies": data.get("studies"),
                "year": data.get("year"),
                "semester": data.get("semester")
            })

        self.user_repository.add_user_to_firestore(transaction, pseudonym, user_data)
        mongo_user_id = self.user_repository.sync_user_to_mongo(pseudonym)
        self.log_service.log_event("add_user", f"Ajout utilisateur {pseudonym}", pseudonym)
        return {"message": "Utilisateur ajouté", "pseudonym": pseudonym}, 200

    def delete_user(self, username):
        if self.user_repository.delete_user(username):
            self.log_service.log_event("delete_user", f"Utilisateur supprimé : {username}", username)
            return {"message": "Utilisateur supprimé"}, 200
        else:
            self.log_service.log_event("delete_user_fail", f"Utilisateur non trouvé : {username}", username)
            return {"message": "Utilisateur non trouvé"}, 404

    def get_students_with_activities(self, activity_repository):
        users = self.user_repository.get_students()
        result = []

        for user in users:
            username = user.get("pseudonym")
            mongo_user = self.user_repository.find_mongo_user_by_pseudonym(username)
            if not mongo_user:
                continue
            mongo_user_id = mongo_user["_id"]

            all_activities = []

            activities = activity_repository.get_activities_by_user(mongo_user_id)
            all_activities.extend(activities)

            result.append({
                "pseudonym": username,
                "email": user.get("email_address"),
                "year": user.get("year"),
                "semester": user.get("semester"),
                "studies": user.get("studies"),
                "mongo_user_id": str(mongo_user_id),
                "activities": all_activities
            })

        return result, 200