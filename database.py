import sqlite3
import json
import uuid
import os

class ProductsDatabase(sqlite3.Connection):
    def __init__(self):
        super().__init__("products.db")

        if not os.path.exists("photos"):
            os.mkdir("photos")

        self.execute("CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, desc TEXT, subproducts TEXT, photo TEXT, loaded_into_bot INTEGER)")
        self.commit()

    def __json_subproducts(self, labels: list, prices: list) -> str:
        # labels and prices arrays must be equal
        saving_dict = []
        for i in range(len(labels)):
            if labels[i] == "" or prices[i] == "": continue
            saving_dict.append( {"label": labels[i], "price": prices[i]} )
        return json.dumps(saving_dict)
    def __get_product_by_id(self, _id) -> tuple:
        return self.execute("SELECT * FROM products WHERE id=?", (_id, )).fetchone()
    
    def get_all_products(self) -> list:
        return self.execute("SELECT * FROM products").fetchall()
    def get_all_unloaded(self) -> list:
        return self.execute("SELECT * FROM products WHERE loaded_into_bot=0").fetchall()
    def upload_photo_to_bot(self, _id: int, photo: str) -> None:
        self.execute("UPDATE products SET photo=?, loaded_into_bot=1 WHERE id=?", (photo, _id) )
        self.commit()
    def delete_product(self, _id: int) -> None:
        origin = self.__get_product_by_id(_id)

        if origin[5] == 0 and origin[4] != "":
            os.remove(origin[4])

        self.execute("DELETE FROM products WHERE id=?", (_id, ))
        self.commit()
    def add_product(self, title: str, desc: str, labels: list, prices: list, photo: str):
        subproducts = self.__json_subproducts(labels, prices)

        self.execute("INSERT INTO products(title, desc, subproducts, photo, loaded_into_bot) VALUES(?,?,?,?,0)", (title, desc, subproducts, photo))
        self.commit()
    def edit_product(self, _id: int, title: str, desc: str, labels: list, prices: list, photo: str):
        # firstly we need to check, what have been changed
        origin_values = self.__get_product_by_id(_id)
        set_commands = []   # gonna contain the str's of sql command
        set_args = []   # will be casted to tuple in order to pass as args

        subproducts = self.__json_subproducts(labels, prices)

        set_commands.append("loaded_into_bot=0")
        if title != "" and title != origin_values[1]:
            set_commands.append("title=?")
            set_args.append(title)
        if desc != "" and desc != origin_values[2]:
            set_commands.append("desc=?")
            set_args.append(desc)
        if subproducts != "" and subproducts != origin_values[3]:
            set_commands.append("subproducts=?")
            set_args.append(subproducts)
        if  photo != "" and photo != origin_values[4]:
            set_commands.append("photo=?")
            set_args.append(photo)
        # If nothing changed
        if len(set_commands) == 0: return
        set_args.append(_id) # adding the id last because id is the last parameter

        formed_set_commands = ",".join(set_commands)
        full_sql_command = f"UPDATE products SET {formed_set_commands} WHERE id=?"

        self.execute(full_sql_command, tuple(set_args))
        self.commit()

class AdminsDatabase(sqlite3.Connection):
    def __init__(self):
        super().__init__("admins.db")

        self.execute("CREATE TABLE IF NOT EXISTS admins(id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT UNIQUE)")
        self.commit()

    def check_user(self, ip: str) -> bool:
        return self.execute("SELECT id FROM admins WHERE ip=?", (ip,)).fetchone() != None
    def delete_user(self, ip: str):
        try:
            self.execute("DELETE FROM admins WHERE ip=?", (ip, ))
            self.commit()
        except Exception as e:
            print(f"Non critical error in delete_user: {e}")
    def add_user(self, ip: str):
        try:
            self.execute("INSERT INTO admins(ip) VALUES(?)", (ip,) )
            self.commit()
        except Exception as e:
            print(f"Non critical error in add_user: {e}")