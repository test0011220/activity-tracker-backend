import re

class AuthService:
    @staticmethod
    def validate_password(new_password):
        if len(new_password) < 8 or not re.search(r"[A-Z]", new_password) or not re.search(r"[a-z]", new_password) or not re.search(r"\d", new_password) or not re.search(r"[^\w\d\s]", new_password):
            return False, {
                "message": "Le nouveau mot de passe doit contenir au moins 8 caractères, une majuscule, une minuscule, un chiffre et un caractère spécial."
            }
        return True, None

    @staticmethod
    def validate_email(email):
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, email):
            return False, {"message": "Email invalide"}
        return True, None