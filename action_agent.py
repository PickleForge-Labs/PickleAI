import os
import json
import glob
import sqlite3
import subprocess
import requests
import psutil
import urllib.parse
import webbrowser
import time
import datetime
import socket


# =========================
# CONFIG
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

MEMORY_DB = os.path.join(
    BASE_DIR,
    "pickle_memory.db"
)

APP_CACHE = os.path.join(
    BASE_DIR,
    "apps.json"
)

OLLAMA_URL = (
    "http://127.0.0.1:11434/api/generate"
)

OLLAMA_TAGS = (
    "http://127.0.0.1:11434/api/tags"
)

OLLAMA_MODEL = (
    "qwen2.5:3b-instruct"
)



# =========================
# OLLAMA
# =========================

class Ollama:


    def __init__(self):

        self.start_server()



    def start_server(self):

        try:

            requests.get(
                OLLAMA_TAGS,
                timeout=2
            )

            return True


        except:

            try:

                subprocess.Popen(
                    [
                        "ollama",
                        "serve"
                    ],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )


                for _ in range(20):

                    time.sleep(0.5)

                    try:

                        requests.get(
                            OLLAMA_TAGS,
                            timeout=2
                        )

                        return True

                    except:

                        pass


            except:

                pass


        return False



    def online(self):

        try:

            r = requests.get(
                OLLAMA_TAGS,
                timeout=2
            )

            return r.status_code == 200


        except:

            return False



    def ask(
        self,
        prompt
    ):


        if not self.online():

            self.start_server()


        try:

            response = requests.post(

                OLLAMA_URL,

                json={

                    "model":
                    OLLAMA_MODEL,

                    "prompt":
                    prompt,

                    "stream":
                    False

                },

                timeout=180

            )


            response.raise_for_status()


            data = response.json()


            return data.get(
                "response",
                "No response."
            )


        except Exception as e:


            return (
                "Ollama error: "
                + str(e)
            )



# =========================
# DATABASE
# =========================

class PickleDatabase:


    def __init__(self):

        self.db = sqlite3.connect(
            MEMORY_DB,
            check_same_thread=False
        )

        self.setup()



    def setup(self):

        tables = [

            """
            CREATE TABLE IF NOT EXISTS memories(
                id INTEGER PRIMARY KEY,
                text TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance INTEGER DEFAULT 1,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,


            """
            CREATE TABLE IF NOT EXISTS chats(
                id INTEGER PRIMARY KEY,
                title TEXT DEFAULT 'New Chat',
                updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,


            """
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                role TEXT,
                content TEXT,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """

        ]


        for table in tables:

            self.db.execute(
                table
            )


        self.db.commit()





    # =====================
    # MEMORY
    # =====================

    def add_memory(
        self,
        text
    ):

        self.db.execute(
            """
            INSERT INTO memories(text)
            VALUES(?)
            """,
            (
                text,
            )
        )

        self.db.commit()



    def get_memories(self):

        result = self.db.execute(
            """
            SELECT text
            FROM memories
            ORDER BY id DESC
            """
        )


        return [
            row[0]
            for row in result.fetchall()
        ]



    def forget(
        self,
        text
    ):

        self.db.execute(
            """
            DELETE FROM memories
            WHERE text LIKE ?
            """,
            (
                "%" + text + "%",
            )
        )

        self.db.commit()



    def clear_memory(self):

        self.db.execute(
            """
            DELETE FROM memories
            """
        )

        self.db.commit()



    def context(self):

        memories = self.get_memories()


        return "\n".join(
            memories[:20]
        )





    # =====================
    # CHAT HISTORY
    # =====================

    def create_chat(
        self,
        title="New Chat"
    ):

        cur = self.db.execute(
            """
            INSERT INTO chats(title)
            VALUES(?)
            """,
            (
                title,
            )
        )

        self.db.commit()


        return cur.lastrowid





    def save_message(
        self,
        chat_id,
        role,
        content
    ):

        self.db.execute(
            """
            INSERT INTO messages
            (
                chat_id,
                role,
                content
            )
            VALUES(?,?,?)
            """,
            (
                chat_id,
                role,
                content
            )
        )


        self.db.execute(
            """
            UPDATE chats
            SET updated=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                chat_id,
            )
        )


        self.db.commit()





    def get_chats(self):

        result = self.db.execute(
            """
            SELECT id,title,updated
            FROM chats
            ORDER BY updated DESC
            """
        )


        return result.fetchall()





    def get_messages(
        self,
        chat_id
    ):

        result = self.db.execute(
            """
            SELECT role,content
            FROM messages
            WHERE chat_id=?
            ORDER BY id
            """,
            (
                chat_id,
            )
        )


        return result.fetchall()





    def delete_chat(
        self,
        chat_id
    ):

        self.db.execute(
            """
            DELETE FROM messages
            WHERE chat_id=?
            """,
            (
                chat_id,
            )
        )


        self.db.execute(
            """
            DELETE FROM chats
            WHERE id=?
            """,
            (
                chat_id,
            )
        )


        self.db.commit()



# =========================
# APP SCANNER
# =========================

class AppScanner:


    def __init__(self):

        self.apps = {}

        self.load()



    def load(self):

        if os.path.exists(APP_CACHE):

            try:

                with open(
                    APP_CACHE,
                    "r",
                    encoding="utf8"
                ) as f:

                    self.apps = json.load(f)

                return


            except:

                pass


        self.scan()



    def scan(self):

        folders = [

            os.environ.get(
                "PROGRAMFILES",
                ""
            ),

            os.environ.get(
                "PROGRAMFILES(X86)",
                ""
            ),

            os.environ.get(
                "LOCALAPPDATA",
                ""
            )

        ]


        for folder in folders:

            if not folder:
                continue


            for exe in glob.glob(
                folder + "\\**\\*.exe",
                recursive=True
            ):

                name = os.path.basename(
                    exe
                ).lower()


                self.apps[
                    name.replace(
                        ".exe",
                        ""
                    )
                ] = exe



        try:

            with open(
                APP_CACHE,
                "w",
                encoding="utf8"
            ) as f:

                json.dump(
                    self.apps,
                    f,
                    indent=2
                )

        except:

            pass



    def find(
        self,
        name
    ):

        name = name.lower()


        for app,path in self.apps.items():

            if name in app:

                return path


        return None



    def open(
        self,
        name
    ):

        path = self.find(name)


        if path:

            subprocess.Popen(path)

            return True


        return False

# =========================
# SYSTEM AGENT
# =========================

try:

    from system_agent import SystemAgent

except:

    SystemAgent = None



# =========================
# ACTION AGENT
# =========================

class ActionAgent:


    def __init__(self):

        self.db = PickleDatabase()

        self.apps = AppScanner()

        self.ai = Ollama()


        self.system = (
            SystemAgent()
            if SystemAgent
            else None
        )


        chats = self.db.get_chats()


        if chats:

            self.current_chat = chats[0][0]

        else:

            self.current_chat = self.db.create_chat(
                "New Chat"
            )





    # =====================
    # AI CHAT
    # =====================

    def chat(
        self,
        message
    ):


        self.db.save_message(
            self.current_chat,
            "user",
            message
        )


        prompt = f"""
You are PickleAI.

You are a local desktop AI assistant.

Memory:
{self.db.context()}


User:
{message}


Assistant:
"""


        reply = self.ai.ask(
            prompt
        )


        self.db.save_message(
            self.current_chat,
            "assistant",
            reply
        )


        return reply





    # =====================
    # COMMAND PROCESSOR
    # =====================

    def process(
        self,
        message
    ):


        if not message:

            return ""



        cmd = message.lower().strip()



        # =================
        # MEMORY
        # =================

        if cmd.startswith("remember "):

            self.db.add_memory(
                message[9:]
            )

            return "Memory saved."





        # =================
        # DATE / TIME
        # =================

        if "date" in cmd or "today" in cmd:

            return (
                "Today is "
                +
                datetime.datetime.now()
                .strftime("%A, %B %d, %Y")
            )



        if "time" in cmd:

            return (
                "The time is "
                +
                datetime.datetime.now()
                .strftime("%I:%M %p")
            )





        # =================
        # INTERNET STATUS
        # =================

        if (
            "internet" in cmd
            or
            "online" in cmd
        ):


            try:

                socket.create_connection(
                    (
                        "google.com",
                        80
                    ),
                    timeout=3
                )


                return (
                    "Internet connection is working."
                )


            except:

                return (
                    "No internet connection."
                )





        # =================
        # GOOGLE SEARCH
        # =================

        if (
            cmd.startswith("search ")
            or
            cmd.startswith("google ")
        ):


            query = (
                cmd
                .replace("search","")
                .replace("google","")
                .strip()
            )


            if query:


                webbrowser.open(
                    "https://www.google.com/search?q="
                    +
                    urllib.parse.quote(query)
                )


                return (
                    "Searching for "
                    +
                    query
                )





        # =================
        # OPEN WEBSITE
        # =================

        if cmd.startswith(
            "open website "
        ):


            url = message[13:].strip()


            if not url.startswith(
                "http"
            ):

                url = (
                    "https://"
                    +
                    url
                )


            webbrowser.open(url)


            return (
                "Opening "
                +
                url
            )





        # =================
        # WEATHER
        # =================

        if cmd.startswith(
            "weather"
        ):


            city = (
                message
                .replace(
                    "weather",
                    ""
                )
                .strip()
            )


            if not city:

                return (
                    "Tell me a city."
                )


            webbrowser.open(
                "https://www.google.com/search?q=weather+"
                +
                urllib.parse.quote(city)
            )


            return (
                "Checking weather for "
                +
                city
            )





        # =================
        # OPEN APPS
        # =================

        if cmd.startswith(
            "open "
        ):


            app = message[5:].strip()


            if self.open_app(app):

                return (
                    "Opening "
                    +
                    app
                )


            return (
                "Could not find "
                +
                app
            )

# =================
        # SYSTEM COMMANDS
        # =================

        if self.system:


            if "show windows" in cmd:

                return self.system.window_summary()



            if "arrange windows" in cmd:

                return self.system.arrange_windows()



            if "active window" in cmd:

                return self.system.get_active_window()



            if cmd.startswith(
                "close "
            ):

                return self.system.close_window(
                    message[6:]
                )



            if "system status" in cmd:

                return str(
                    self.system.status()
                )





        # =================
        # FALLBACK AI
        # =================

        return self.chat(
            message
        )





    # =====================
    # APP OPENING
    # =====================

    def open_app(
        self,
        name
    ):


        shortcuts = {

            "edge":
            "msedge",

            "microsoft edge":
            "msedge",

            "calculator":
            "calc",

            "notepad":
            "notepad"

        }


        key = name.lower()



        if key in shortcuts:


            try:

                subprocess.Popen(
                    shortcuts[key],
                    shell=True
                )

                return True


            except:

                pass



        return self.apps.open(
            name
        )





    # =====================
    # GUI FUNCTIONS
    # =====================

    def get_memory_menu(self):

        return {

            "memories":
            self.db.get_memories(),

            "chats":
            self.db.get_chats()

        }





    def get_saved_chats(self):

        return self.db.get_chats()





    def load_chat(
        self,
        chat_id
    ):

        return self.db.get_messages(
            chat_id
        )





    def delete_chat(
        self,
        chat_id
    ):

        self.db.delete_chat(
            chat_id
        )

        return "Deleted"





    def new_chat(
        self,
        title="New Chat"
    ):


        self.current_chat = (
            self.db.create_chat(title)
        )


        return self.current_chat





    def system_status(self):


        if self.system:

            return self.system.status()



        return {

            "cpu":
            psutil.cpu_percent(),

            "ram":
            psutil.virtual_memory().percent,

            "disk":
            psutil.disk_usage("/").percent

        }