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


# ============================================================
# CONFIG
# ============================================================

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


# ============================================================
# OLLAMA
# ============================================================

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

        except Exception:

            try:

                creation_flags = 0

                if os.name == "nt":
                    creation_flags = (
                        subprocess.CREATE_NO_WINDOW
                    )

                subprocess.Popen(
                    [
                        "ollama",
                        "serve"
                    ],
                    creationflags=creation_flags
                )

                for _ in range(20):

                    time.sleep(0.5)

                    try:

                        requests.get(
                            OLLAMA_TAGS,
                            timeout=2
                        )

                        return True

                    except Exception:
                        pass

            except Exception:
                pass

        return False

    def online(self):

        try:

            response = requests.get(
                OLLAMA_TAGS,
                timeout=2
            )

            return response.status_code == 200

        except Exception:

            return False

    def ask(self, prompt):

        if not self.online():

            self.start_server()

        try:

            response = requests.post(

                OLLAMA_URL,

                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False
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


# ============================================================
# DATABASE
# ============================================================

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

            self.db.execute(table)

        self.db.commit()

    # ========================================================
    # MEMORY
    # ========================================================

    def add_memory(
        self,
        text,
        category="general",
        importance=1
    ):

        text = str(text).strip()

        if not text:
            return False

        self.db.execute(
            """
            INSERT INTO memories
            (
                text,
                category,
                importance
            )
            VALUES(?,?,?)
            """,
            (
                text,
                category,
                importance
            )
        )

        self.db.commit()

        return True

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

    def get_memory_records(self):

        result = self.db.execute(
            """
            SELECT
                id,
                text,
                category,
                importance,
                created
            FROM memories
            ORDER BY id DESC
            """
        )

        return [
            {
                "id": row[0],
                "text": row[1],
                "category": row[2],
                "importance": row[3],
                "created": row[4]
            }
            for row in result.fetchall()
        ]

    def forget(self, text):

        text = str(text).strip()

        if not text:
            return False

        self.db.execute(
            """
            DELETE FROM memories
            WHERE text LIKE ?
            AND category != 'identity'
            """,
            (
                "%" + text + "%",
            )
        )

        self.db.commit()

        return True

    def forget_id(self, memory_id):

        self.db.execute(
            """
            DELETE FROM memories
            WHERE id=?
            AND category != 'identity'
            """,
            (
                int(memory_id),
            )
        )

        self.db.commit()

        return True

    def clear_memory(self):

        self.db.execute(
            """
            DELETE FROM memories
            WHERE category != 'identity'
            """
        )

        self.db.commit()

        return True

    def context(self):

        memories = self.get_memories()

        return "\n".join(
            memories[:20]
        )

    # ========================================================
    # USER IDENTITY
    # ========================================================

    def set_user_name(self, name):

        name = str(name).strip()

        if not name:
            return False

        # Remove previous identity record.
        self.db.execute(
            """
            DELETE FROM memories
            WHERE category='identity'
            AND text LIKE 'User real name:%'
            """
        )

        self.db.execute(
            """
            INSERT INTO memories
            (
                text,
                category,
                importance
            )
            VALUES(?,?,?)
            """,
            (
                "User real name: " + name,
                "identity",
                10
            )
        )

        self.db.commit()

        return True

    def get_user_name(self):

        result = self.db.execute(
            """
            SELECT text
            FROM memories
            WHERE category='identity'
            AND text LIKE 'User real name:%'
            ORDER BY id DESC
            LIMIT 1
            """
        )

        row = result.fetchone()

        if not row:
            return None

        prefix = "User real name:"

        if row[0].startswith(prefix):

            return row[0][len(prefix):].strip()

        return None

    # ========================================================
    # CHAT HISTORY
    # ========================================================

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
                int(chat_id),
            )
        )

        return result.fetchall()

    def delete_chat(
        self,
        chat_id
    ):

        chat_id = int(chat_id)

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

        return True


# ============================================================
# APP SCANNER
# ============================================================

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

            except Exception:
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

            try:

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

            except Exception:
                pass

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

        except Exception:
            pass

    def find(
        self,
        name
    ):

        name = str(name).lower().strip()

        for app, path in self.apps.items():

            if name in app:

                return path

        return None

    def open(
        self,
        name
    ):

        path = self.find(name)

        if path:

            try:

                subprocess.Popen(path)

                return True

            except Exception:
                pass

        return False


# ============================================================
# SYSTEM AGENT
# ============================================================

try:

    from system_agent import SystemAgent

except Exception:

    SystemAgent = None


# ============================================================
# ACTION AGENT
# ============================================================

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

            self.current_chat = (
                self.db.create_chat(
                    "New Chat"
                )
            )

    # ========================================================
    # USER PROFILE
    # ========================================================

    def set_user_name(
        self,
        name
    ):

        return self.db.set_user_name(
            name
        )

    def get_user_name(self):

        return self.db.get_user_name()

    def get_profile(self):

        return {
            "name": self.get_user_name()
        }

    # ========================================================
    # AI CHAT
    # ========================================================

    def chat(
        self,
        message
    ):

        self.db.save_message(
            self.current_chat,
            "user",
            message
        )

        user_name = (
            self.get_user_name()
        )

        identity = ""

        if user_name:

            identity = f"""
User identity:
The user's real name is {user_name}.
This is their real name, not a username.
You may naturally address the user by this name.
Do not call their real name a username.
"""

        memory_context = (
            self.db.context()
        )

        prompt = f"""
You are PickleAI.

You are a local desktop AI assistant.

{identity}

Remember the following information when useful:

{memory_context}

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

    # ========================================================
    # COMMAND PROCESSOR
    # ========================================================

    def process(
        self,
        message
    ):

        if not message:

            return ""

        message = str(message).strip()

        if not message:

            return ""

        cmd = message.lower()

        # ====================================================
        # REMEMBER
        # ====================================================

        if cmd.startswith("remember "):

            memory = message[9:].strip()

            if not memory:

                return "Tell me what you want me to remember."

            self.db.add_memory(
                memory
            )

            return "Memory saved."

        # ====================================================
        # NAME
        # ====================================================

        if (
            cmd.startswith("my name is ")
            or
            cmd.startswith("call me ")
        ):

            if cmd.startswith("my name is "):

                name = message[11:].strip()

            else:

                name = message[8:].strip()

            if name:

                self.set_user_name(
                    name
                )

                return (
                    "Got it. I'll remember "
                    + name
                    + " as your name."
                )

        # ====================================================
        # DATE / TIME
        # ====================================================

        if (
            "date" in cmd
            or
            "today" in cmd
        ):

            return (
                "Today is "
                +
                datetime.datetime.now().strftime(
                    "%A, %B %d, %Y"
                )
            )

        if "time" in cmd:

            return (
                "The time is "
                +
                datetime.datetime.now().strftime(
                    "%I:%M %p"
                )
            )

        # ====================================================
        # INTERNET
        # ====================================================

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

            except Exception:

                return (
                    "No internet connection."
                )

        # ====================================================
        # GOOGLE SEARCH
        # ====================================================

        if (
            cmd.startswith("search ")
            or
            cmd.startswith("google ")
        ):

            query = (
                cmd
                .replace(
                    "search",
                    "",
                    1
                )
                .replace(
                    "google",
                    "",
                    1
                )
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

        # ====================================================
        # OPEN WEBSITE
        # ====================================================

        if cmd.startswith(
            "open website "
        ):

            url = message[13:].strip()

            if not url:

                return "Tell me which website to open."

            if not url.startswith(
                (
                    "http://",
                    "https://"
                )
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

        # ====================================================
        # WEATHER
        # ====================================================

        if cmd.startswith("weather"):

            city = (
                message[7:].strip()
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

        # ====================================================
        # OPEN APPS
        # ====================================================

        if cmd.startswith("open "):

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

        # ====================================================
        # SYSTEM COMMANDS
        # ====================================================

        if self.system:

            if "show windows" in cmd:

                return (
                    self.system.window_summary()
                )

            if "arrange windows" in cmd:

                return (
                    self.system.arrange_windows()
                )

            if "active window" in cmd:

                return (
                    self.system.get_active_window()
                )

            if cmd.startswith("close "):

                return (
                    self.system.close_window(
                        message[6:].strip()
                    )
                )

            if "system status" in cmd:

                return str(
                    self.system.status()
                )

        # ====================================================
        # FALLBACK AI
        # ====================================================

        return self.chat(
            message
        )

    # ========================================================
    # APP OPENING
    # ========================================================

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

        key = (
            str(name)
            .lower()
            .strip()
        )

        if key in shortcuts:

            try:

                subprocess.Popen(
                    shortcuts[key],
                    shell=True
                )

                return True

            except Exception:
                pass

        return self.apps.open(
            name
        )

    # ========================================================
    # MEMORY GUI
    # ========================================================

    def get_memory_menu(self):

        return {

            "memories":
            self.db.get_memories(),

            "memory_records":
            self.db.get_memory_records(),

            "chats":
            self.db.get_chats(),

            "profile":
            self.get_profile()

        }

    def add_memory(
        self,
        text
    ):

        if self.db.add_memory(
            text
        ):

            return "Memory saved."

        return "Memory could not be saved."

    def forget_memory(
        self,
        text
    ):

        self.db.forget(
            text
        )

        return "Memory removed."

    def forget_memory_id(
        self,
        memory_id
    ):

        self.db.forget_id(
            memory_id
        )

        return "Memory removed."

    def clear_memories(self):

        self.db.clear_memory()

        return "Memories cleared."

    # ========================================================
    # CHATS
    # ========================================================

    def get_saved_chats(self):

        return self.db.get_chats()

    def load_chat(
        self,
        chat_id
    ):

        return self.db.get_messages(
            int(chat_id)
        )

    def delete_chat(
        self,
        chat_id
    ):

        chat_id = int(chat_id)

        self.db.delete_chat(
            chat_id
        )

        # Make sure there is always
        # a valid current chat.

        chats = self.db.get_chats()

        if chats:

            self.current_chat = chats[0][0]

        else:

            self.current_chat = (
                self.db.create_chat(
                    "New Chat"
                )
            )

        return "Deleted"

    def new_chat(
        self,
        title="New Chat"
    ):

        self.current_chat = (
            self.db.create_chat(
                title
            )
        )

        return self.current_chat

    # ========================================================
    # SYSTEM STATUS
    # ========================================================

    def system_status(self):

        if self.system:

            try:

                return self.system.status()

            except Exception:
                pass

        try:

            disk_path = os.path.abspath(
                BASE_DIR
            )

            disk = psutil.disk_usage(
                disk_path
            ).percent

        except Exception:

            disk = 0

        return {

            "cpu":
            psutil.cpu_percent(),

            "ram":
            psutil.virtual_memory().percent,

            "disk":
            disk,

            "ollama":
            self.ai.online()

        }

    def internet_status(self):

        try:

            socket.create_connection(
                (
                    "google.com",
                    80
                ),
                timeout=3
            )

            return {
                "online": True,
                "status": "Online"
            }

        except Exception:

            return {
                "online": False,
                "status": "Offline"
            }

    # ========================================================
    # MINI AI PANEL
    # ========================================================

    def run_panel_action(
        self,
        action,
        value=""
    ):

        action = (
            str(action)
            .lower()
            .strip()
        )

        value = (
            str(value)
            .strip()
        )

        # ----------------------------------------------------
        # AI
        # ----------------------------------------------------

        if action == "chat":

            return self.process(
                value
            )

        # ----------------------------------------------------
        # MEMORY
        # ----------------------------------------------------

        if action == "memory":

            return self.get_memory_menu()

        if action == "remember":

            if not value:

                return (
                    "Nothing to remember."
                )

            return self.add_memory(
                value
            )

        # ----------------------------------------------------
        # PROFILE
        # ----------------------------------------------------

        if action == "profile":

            return self.get_profile()

        if action == "set_name":

            if not value:

                return (
                    "No name supplied."
                )

            self.set_user_name(
                value
            )

            return (
                "Name saved."
            )

        # ----------------------------------------------------
        # SYSTEM
        # ----------------------------------------------------

        if action == "system_status":

            return self.system_status()

        if action == "internet":

            return self.internet_status()

        # ----------------------------------------------------
        # APPS
        # ----------------------------------------------------

        if action == "open_app":

            if not value:

                return (
                    "No application supplied."
                )

            if self.open_app(value):

                return (
                    "Opening "
                    +
                    value
                )

            return (
                "Could not find "
                +
                value
            )

        # ----------------------------------------------------
        # SEARCH
        # ----------------------------------------------------

        if action == "search":

            if not value:

                return (
                    "No search query."
                )

            webbrowser.open(
                "https://www.google.com/search?q="
                +
                urllib.parse.quote(
                    value
                )
            )

            return (
                "Searching for "
                +
                value
            )

        # ----------------------------------------------------
        # NEW CHAT
        # ----------------------------------------------------

        if action == "new_chat":

            self.new_chat()

            return (
                "New chat created."
            )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        if action == "date":

            return (
                "Today is "
                +
                datetime.datetime.now().strftime(
                    "%A, %B %d, %Y"
                )
            )

        # ----------------------------------------------------
        # TIME
        # ----------------------------------------------------

        if action == "time":

            return (
                "The time is "
                +
                datetime.datetime.now().strftime(
                    "%I:%M %p"
                )
            )

        # ----------------------------------------------------
        # OPEN WEBSITE
        # ----------------------------------------------------

        if action == "website":

            if not value:

                return (
                    "No website supplied."
                )

            url = value

            if not url.startswith(
                (
                    "http://",
                    "https://"
                )
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

        return (
            "Unknown panel action: "
            +
            action
        )

    # ========================================================
    # MINI PANEL BUTTON DEFINITIONS
    # ========================================================

    def get_default_panel_buttons(self):

        return [

            {
                "id": "chat",
                "name": "Ask AI",
                "icon": "💬",
                "action": "chat"
            },

            {
                "id": "memory",
                "name": "Memory",
                "icon": "🧠",
                "action": "memory"
            },

            {
                "id": "remember",
                "name": "Add Memory",
                "icon": "➕",
                "action": "remember"
            },

            {
                "id": "system",
                "name": "System",
                "icon": "🖥️",
                "action": "system_status"
            },

            {
                "id": "internet",
                "name": "Internet",
                "icon": "🌐",
                "action": "internet"
            },

            {
                "id": "new_chat",
                "name": "New Chat",
                "icon": "✨",
                "action": "new_chat"
            },

            {
                "id": "time",
                "name": "Time",
                "icon": "🕒",
                "action": "time"
            },

            {
                "id": "date",
                "name": "Date",
                "icon": "📅",
                "action": "date"
            }

        ]