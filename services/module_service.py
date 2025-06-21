class ModuleService:
    def __init__(self, module_repository):
        self.module_repository = module_repository

    def get_modules(self, data):
        year = data.get("year")
        studies = data.get("studies")
        semester = data.get("semester")

        if not all([year, studies, semester]):
            return {"message": "Missing data"}, 400

        modules = self.module_repository.get_modules(year, studies, semester)
        return modules, 200