import pickle, os
from typing import Dict, List

"""
This verision of Nick management does not manage nicknames however it exists as a login to the perm system
"""

class Register:
    def __init__(self):
        self.db: List[Dict[str, str]]= []
        self.db_location= "nirc.db"
        self.load_db()
        self.save_db()

    def load_db(self):
        if os.path.exists(self.db_location):
            with open(self.db_location, "rb") as file:
                self.db= pickle.load(file)

    def save_db(self):
        with open(self.db_location, "wb") as file:
            pickle.dump(self.db, file)

    def get_db(self):
        return self.db

    def login(self, username: str, password: str):
        logged_in= False
        for entry in self.db:
            if username in entry and entry[username]== password:
                logged_in= True
        return logged_in

    def register(self, username: str, password: str):
        for entry in self.db:
            if username in entry:
                return
        self.db.append({username: password})
        self.save_db()

    def delete_acc(self, username: str):
        old_db= self.db.copy()
        self.db.clear()
        for entry in old_db:
            if not username in entry:
                self.db.append(entry)
        self.save_db()
