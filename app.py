import json
from bson import ObjectId
from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import csv
from datetime import datetime, timezone

# Import repositories
from repositories.user_repository import UserRepository
from repositories.diary_repository import DiaryRepository
from repositories.activity_repository import ActivityRepository
from repositories.log_repository import LogRepository
from repositories.module_repository import ModuleRepository
from repositories.category_repository import CategoryRepository
from repositories.questionnaire_repository import QuestionnaireRepository
from repositories.question_repository import QuestionRepository

# Import services
from services.user_service import UserService
from services.auth_service import AuthService
from services.activity_service import ActivityService
from services.log_service import LogService
from services.module_service import ModuleService
from services.questionnaire_service import QuestionnaireService
from services.question_service import QuestionService

app = Flask(__name__)
CORS(app, origins=["https://yourusername.pythonanywhere.com", "http://localhost:*"])

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
if not mongo_uri:
    raise ValueError("MONGO_URI not set in environment variables")

# Firebase setup
firebase_cred_json = os.getenv("FIREBASE_CRED_JSON")
if not firebase_cred_json:
    raise ValueError("FIREBASE_CRED_JSON environment variable is not set")
try:
    firebase_cred_dict = json.loads(firebase_cred_json)
except json.JSONDecodeError as e:
    raise ValueError(f"Invalid FIREBASE_CRED_JSON format: {str(e)}")
cred = credentials.Certificate(firebase_cred_dict)
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# Initialize MongoDB
client = MongoClient(mongo_uri)
mongo_db = client["dev_mobile"]

# Initialize repositories
user_repository = UserRepository(mongo_db, firestore_db)
diary_repository = DiaryRepository(mongo_db)
activity_repository = ActivityRepository(mongo_db)
log_repository = LogRepository(mongo_db)
module_repository = ModuleRepository(mongo_db)
category_repository = CategoryRepository(mongo_db)
questionnaire_repository = QuestionnaireRepository(mongo_db)
question_repository = QuestionRepository(mongo_db)

# Initialize services
log_service = LogService(log_repository)
user_service = UserService(user_repository, log_service)
auth_service = AuthService()
activity_service = ActivityService(user_repository, diary_repository, activity_repository, category_repository, log_service)
module_service = ModuleService(module_repository)
questionnaire_service = QuestionnaireService(user_repository, questionnaire_repository, question_repository, log_service)
question_service = QuestionService(question_repository, log_service)

# 🔐 Route de connexion (manual login with Firestore)
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    response_data, error, status = user_service.login(username, password)
    if error:
        return jsonify(error), status
    return jsonify(response_data), status

# 🔐 Route de connexion Google
@app.route('/google-login', methods=['POST'])
def google_login():
    data = request.get_json()
    id_token = data.get("id_token")

    try:
        decoded_token = auth.verify_id_token(id_token)
        email = decoded_token['email']
        uid = decoded_token['uid']
        custom_token = auth.create_custom_token(uid)

        response_data, status = user_service.google_login(email, uid, custom_token)
        return jsonify(response_data), status
    except ValueError as e:
        log_service.log_event("google_login_fail", f"Invalid token: {str(e)}", email)
        return jsonify({"message": "Invalid token", "error": str(e)}), 401

@app.route('/update_user_info', methods=['POST'])
def update_user_info():
    data = request.get_json()
    email = data.get("email")
    response, status = user_service.update_user_info(email, data)
    return jsonify(response), status

@app.route('/change_password', methods=['POST'])
def change_password():
    data = request.get_json()
    username = data.get("username")
    current_password = data.get("current_password")
    new_password = data.get("new_password")

    is_valid, error = auth_service.validate_password(new_password)
    if not is_valid:
        log_service.log_event("change_password_fail", "Nouveau mot de passe trop faible", username)
        return jsonify(error), 400

    response, status = user_service.change_password(username, current_password, new_password)
    return jsonify(response), status

@app.route('/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get("username")
    response, status = user_service.forgot_password(username)
    return jsonify(response), status

# ➕ Ajouter un utilisateur
@app.route('/add_user', methods=['POST'])
def add_user():
    data = request.get_json()
    print(data)
    pseudonym = data.get("username")
    password = data.get("password")
    role = data.get("role")
    email = data.get("email")
    gender = data.get("gender")

    if not all([pseudonym, password, role, email, gender]):
        log_service.log_event("add_user_fail", "Champs manquants lors de l'ajout")
        return jsonify({"message": "Champs manquants"}), 400

    is_valid, error = auth_service.validate_email(email)
    if not is_valid:
        log_service.log_event("add_user_fail", "Email invalide", pseudonym)
        return jsonify(error), 400

    is_valid, error = auth_service.validate_password(password)
    if not is_valid:
        log_service.log_event("add_user_fail", "Mot de passe trop faible", pseudonym)
        return jsonify(error), 400

    if role == "student":
        age = data.get("age")
        studies = data.get("studies")
        year = data.get("year")
        semester = data.get("semester")

        if not all([age, year, semester]):
            log_service.log_event("add_user_fail", "Champs étudiants manquants", pseudonym)
            return jsonify({"message": "Champs étudiants manquants"}), 400

        data.update({
            "age": age,
            "studies": studies,
            "year": year,
            "semester": semester
        })

    try:
        @firestore.transactional
        def add_user_transaction(transaction):
            return user_service.add_user(transaction, data)

        response = add_user_transaction(firestore_db.transaction())
        return jsonify(response[0]), response[1]
    except ValueError as e:
        log_service.log_event("add_user_fail", str(e), pseudonym)
        return jsonify({"message": str(e)}), 409
    except Exception as e:
        log_service.log_event("add_user_fail", f"Erreur serveur: {str(e)}", pseudonym)
        return jsonify({"message": "Erreur serveur", "error": str(e)}), 500

# 🗑️ Supprimer un utilisateur
@app.route('/delete_user/<username>', methods=['DELETE'])
def delete_user(username):
    response, status = user_service.delete_user(username)
    return jsonify(response), status

# 🕒 Enregistrement d'une activité
@app.route('/log_activity', methods=['POST'])
def log_activity():
    data = request.get_json()
    response, status = activity_service.log_activity(data)
    return jsonify(response), status

# 📚 Récupérer les modules
@app.route('/modules', methods=['POST'])
def get_modules():
    data = request.get_json()
    response, status = module_service.get_modules(data)
    return jsonify(response), status

# 👥 Voir tous les utilisateurs (Firestore)
@app.route('/users', methods=['GET'])
def get_users():
    try:
        users = user_repository.get_all_users()
        return jsonify(users), 200
    except Exception as e:
        log_service.log_event("error", f"Erreur serveur /users: {e}")
        return jsonify({"message": "Erreur serveur", "details": str(e)}), 500

# 📊 Admin : voir les étudiants et leurs activités
@app.route('/admin/etudiants_activites', methods=['GET'])
def get_students_with_activities():
    response, status = user_service.get_students_with_activities(activity_repository)
    return jsonify(response), status

# 🧾 Voir toutes les entrées du journal
@app.route('/logs', methods=['GET'])
def get_logs():
    response, status = log_service.get_logs()
    return jsonify(response), status

@app.route('/create_questionnaire', methods=['POST'])
def create_questionnaire():
    data = request.get_json()
    response, status = questionnaire_service.create_questionnaire(data)
    return jsonify(response), status

@app.route('/update_questionnaire/<questionnaire_id>', methods=['PUT'])
def update_questionnaire(questionnaire_id):
    data = request.get_json()
    response, status = questionnaire_service.update_questionnaire(questionnaire_id, data)
    return jsonify(response), status

@app.route('/toggle_questionnaire_status/<questionnaire_id>', methods=['PUT'])
def toggle_questionnaire_status(questionnaire_id):
    data = request.get_json()
    is_active = data.get("is_active", True)
    print("the status of activate is : ", is_active)
    response, status = questionnaire_service.toggle_questionnaire_status(questionnaire_id, is_active)
    return jsonify(response), status

@app.route('/duplicate_questionnaire/<questionnaire_id>', methods=['POST'])
def duplicate_questionnaire(questionnaire_id):
    data = request.get_json()
    response, status = questionnaire_service.duplicate_questionnaire(questionnaire_id, data)
    return jsonify(response), status

@app.route('/add_question', methods=['POST'])
def add_question():
    data = request.get_json()
    response, status = question_service.add_question(data)
    return jsonify(response), status

@app.route('/questionnaires', methods=['POST'])
def get_questionnaires():
    data = request.get_json()
    response, status = questionnaire_service.get_questionnaires(data)
    return jsonify(response), status

@app.route('/answered_questionnaires', methods=['POST'])
def get_answered_questionnaires():
    data = request.get_json()
    user_id = data.get("mongo_user_id")

    if not user_id:
        return jsonify({"message": "mongo_user_id manquant"}), 400

    try:
        response, status = questionnaire_service.get_user_answered_questionnaires(user_id)
        return jsonify(response), status
    except Exception as e:
        print(f"ERROR: Exception in get_answered_questionnaires: {str(e)}")
        return jsonify({"message": "Erreur serveur", "error": str(e)}), 500

@app.route('/questionnaire/<questionnaire_id>', methods=['GET'])
def get_questionnaire(questionnaire_id):
    response, status = questionnaire_service.get_questionnaire(questionnaire_id)
    return jsonify(response), status

@app.route('/submit_questionnaire_response', methods=['POST'])
def submit_questionnaire_response():
    data = request.get_json()
    response, status = questionnaire_service.submit_questionnaire_response(data)
    return jsonify(response), status

@app.route('/user_responses/<user_id>/<questionnaire_id>', methods=['GET'])
def get_user_responses(user_id, questionnaire_id):
    response, status = questionnaire_service.get_user_responses(user_id, questionnaire_id)
    return jsonify(response), status

# 🗑️ Supprimer un questionnaire et ses données associées
@app.route('/delete_questionnaire/<questionnaire_id>', methods=['DELETE'])
def delete_questionnaire(questionnaire_id):
    try:
        if questionnaire_repository.delete_questionnaire(questionnaire_id):
            log_service.log_event("delete_questionnaire", f"Questionnaire supprimé: {questionnaire_id}")
            return jsonify({"message": "Questionnaire supprimé avec succès"}), 200
        else:
            log_service.log_event("delete_questionnaire_fail", f"Questionnaire non trouvé: {questionnaire_id}")
            return jsonify({"message": "Questionnaire non trouvé"}), 404
    except Exception as e:
        log_service.log_event("delete_questionnaire_error", f"Erreur lors de la suppression du questionnaire {questionnaire_id}: {str(e)}")
        return jsonify({"message": "Erreur lors de la suppression du questionnaire", "error": str(e)}), 500

# 📥 Route d'importation CSV
@app.route('/upload_csv', methods=['POST'])
def upload_csv():
    if 'file' not in request.files:
        return jsonify({"message": "Fichier manquant"}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)

    if not filename.endswith('.csv'):
        return jsonify({"message": "Le fichier doit être un CSV"}), 400

    try:
        decoded_file = file.read().decode('utf-8').splitlines()
        reader = csv.DictReader(decoded_file)
        inserted_questionnaires = 0
        inserted_questions = 0

        questionnaires = {}
        for row_idx, row in enumerate(reader, start=1):
            title = row.get("questionnaire_title")
            if not title:
                log_service.log_event("upload_csv_warning", f"Row {row_idx}: Missing questionnaire_title, skipping")
                continue

            if title not in questionnaires:
                filieres = [f.strip() for f in row.get("filieres", "").split(',') if f.strip()]
                years = [y.strip() for y in row.get("years", "").split(',') if y.strip()]
                activity_id = row.get("activity_id", None)

                if activity_id:
                    try:
                        ObjectId(activity_id)
                    except Exception as e:
                        log_service.log_event("upload_csv_error", f"Row {row_idx}: Invalid activity_id '{activity_id}': {str(e)}")
                        continue

                questionnaires[title] = {
                    "title": title,
                    "description": row.get("description", ""),
                    "category": row.get("category", "Autre"),
                    "filieres": filieres,
                    "years": years,
                    "activity_id": activity_id,
                    "questions": []
                }

            propositions = []
            if row.get("question_type") != "open_ended" and row.get("propositions"):
                try:
                    raw_props = row["propositions"].strip()
                    log_service.log_event("upload_csv_debug", f"Row {row_idx}: Raw propositions: {raw_props}")

                    props_str = raw_props.replace("'", '"').replace('\"', '"')
                    props = json.loads(props_str)
                    log_service.log_event("upload_csv_debug", f"Row {row_idx}: Parsed propositions: {props}")

                    propositions = [
                        {"id": p["id"], "text": p["text"], "is_correct": p["is_correct"]}
                        for p in props
                    ]
                except json.JSONDecodeError as e:
                    log_service.log_event(
                        "upload_csv_error",
                        f"Row {row_idx}: Invalid propositions format for question '{row.get('question_text')}': {str(e)}"
                    )
                    continue

            try:
                question_order = int(row.get("question_order", len(questionnaires[title]["questions"]) + 1))
            except (ValueError, TypeError) as e:
                log_service.log_event("upload_csv_error", f"Row {row_idx}: Invalid question_order '{row.get('question_order')}': {str(e)}")
                continue

            questionnaires[title]["questions"].append({
                "text": row.get("question_text", ""),
                "type": row.get("question_type", "open_ended"),
                "propositions": propositions,
                "order": question_order
            })

        for title, q_data in questionnaires.items():
            if not q_data["filieres"] or not q_data["years"] or not q_data["questions"]:
                log_service.log_event("upload_csv_error", f"Invalid questionnaire data for title: {title}")
                continue

            questionnaire_doc = {
                "title": q_data["title"],
                "description": q_data["description"],
                "category": q_data["category"],
                "filieres": q_data["filieres"],
                "years": q_data["years"],
                "activity_id": ObjectId(q_data["activity_id"]) if q_data["activity_id"] else None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc)
            }
            result = questionnaire_repository.create_questionnaire(questionnaire_doc)
            inserted_questionnaires += 1

            for question in q_data["questions"]:
                question_doc = {
                    "questionnaire_id": result,
                    "text": question["text"],
                    "type": question["type"],
                    "propositions": question["propositions"],
                    "order": question["order"],
                    "created_at": datetime.now(timezone.utc)
                }
                question_repository.add_question(question_doc)
                inserted_questions += 1

        log_service.log_event("upload_csv", f"{inserted_questionnaires} questionnaires et {inserted_questions} questions ajoutés depuis CSV")
        return jsonify({
            "message": f"{inserted_questionnaires} questionnaires et {inserted_questions} questions ajoutés depuis le fichier CSV."
        }), 200

    except Exception as e:
        log_service.log_event("upload_csv_error", f"Erreur lors de l'importation CSV: {str(e)}")
        return jsonify({"message": "Erreur lors du traitement du fichier.", "error": str(e)}), 500

# 🚀 Lancer l'app
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
