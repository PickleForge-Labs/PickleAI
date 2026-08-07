import os
import sys
import webview


# =========================
# HIDE CONSOLE
# =========================

if sys.platform == "win32":

    import ctypes

    hwnd = ctypes.windll.kernel32.GetConsoleWindow()

    if hwnd:

        ctypes.windll.user32.ShowWindow(
            hwnd,
            0
        )


# =========================
# IMPORT AGENT
# =========================

from action_agent import ActionAgent



# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)


HTML_FILE = os.path.join(
    BASE_DIR,
    "gui",
    "index.html"
)



# =========================
# GUI API
# =========================

class PickleAPI:


    def __init__(self):

        self.agent = ActionAgent()



    # CHAT

    def send_message(
        self,
        text
    ):

        return self.agent.process(
            text
        )



    # MEMORY

    def get_memory(self):

        return self.agent.get_memory_menu()



    def forget_memory(
        self,
        text
    ):

        self.agent.db.forget(
            text
        )

        return "Removed"



    # CHATS

    def get_saved_chats(self):

        return self.agent.get_saved_chats()



    def load_chat(
        self,
        chat_id
    ):

        return self.agent.load_chat(
            int(chat_id)
        )



    def delete_chat(
        self,
        chat_id
    ):

        return self.agent.delete_chat(
            int(chat_id)
        )



    def new_chat(
        self,
        title="New Chat"
    ):

        return self.agent.new_chat(
            title
        )



    # SYSTEM

    def get_system_status(self):

        return self.agent.system_status()



    # APPS

    def open_app(
        self,
        name
    ):

        return self.agent.open_app(
            name
        )



    # INTERNET

    def internet_status(self):

        if self.agent.system:

            return (
                self.agent.system.internet_status()
            )

        return {
            "online": False,
            "status": "Unavailable"
        }



# =========================
# START
# =========================

def start():


    api = PickleAPI()


    window = webview.create_window(

        "PickleAI",

        HTML_FILE,

        js_api=api,

        width=1200,

        height=800,

        min_size=(
            900,
            600
        )

    )


    webview.start()



if __name__ == "__main__":

    start()