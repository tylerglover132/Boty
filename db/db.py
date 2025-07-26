import sqlite3
from .User import User


class DB:

    def __init__(self) -> None:
        self.conn = sqlite3.connect("database.db")
        self.cursor = self.conn.cursor()
        self.init_table()

    def __del__(self) -> None:
        self.conn.close()


    def init_table(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                points INTEGER
            )
        ''')
        self.conn.commit()

    def add_user(self, new_user: User) -> bool:
        try:
            self.cursor.execute("INSERT INTO users (id, name, points) VALUES (?,?,?)", (new_user.dist_id, new_user.name,new_user.points))
            self.conn.commit()
            return True
        except Exception as e:
            print("Well shit... The db didn't work")
            return False

    def get_user(self, dist_id: int) -> User:
        try:
            self.cursor.execute("SELECT * FROM users WHERE id = ?", (dist_id,))
            result = self.cursor.fetchone()
            user = User(int(result[0]), str(result[1]), int(result[2]))
        except Exception as e:
            print("FUCK")
            return User(0, 'null', -1)
        return user

    def get_users(self) -> list:
        users = []
        try:
            self.cursor.execute("SELECT * FROM users ORDER BY points DESC")
            result = self.cursor.fetchall()
            for user in result:
                new_user = User(int(user[0]), str(user[1]), int(user[2]))
                users.append(new_user)
        except Exception as e:
            print("ASS")
            return users
        return users

    def update_user(self, user_info: User) -> bool:
        try:
            self.cursor.execute('''
            UPDATE users
            SET points = ?
            WHERE id = ?
            ''', (user_info.points, user_info.dist_id))
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Heck: {e}")
            return False

    def delete_user(self, dist_id: int) -> bool:
        try:
            self.cursor.execute("DELETE FROM users WHERE id = ?", (dist_id,))
            self.conn.commit()
            return True
        except Exception as e:
            print("#@$(&")
            return False

if __name__=='__main__':
    db = DB()
    users = db.get_users()
    for user in users:
        print(user.name)