import os
import sys
import ctypes
import ctypes.wintypes
import threading

# ============================================================
# WINDOWS SETTINGS
# ============================================================

if sys.platform == "win32":

    # Reduce the chance of WebView2 GPU rendering problems.
    # This must be set BEFORE importing/starting pywebview.
    os.environ.setdefault(
        "WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS",
        "--disable-gpu"
    )

    # Keep WebView2 data somewhere writable.
    # This avoids some permission/profile problems.
    BASE_FOR_ENV = os.path.dirname(
        os.path.abspath(__file__)
    )

    WEBVIEW_DATA = os.path.join(
        BASE_FOR_ENV,
        "webview_data"
    )

    try:
        os.makedirs(
            WEBVIEW_DATA,
            exist_ok=True
        )

        os.environ.setdefault(
            "WEBVIEW2_USER_DATA_FOLDER",
            WEBVIEW_DATA
        )

    except Exception:
        pass


import webview


# ============================================================
# WINDOWS CONSOLE HIDE
# ============================================================

if sys.platform == "win32":

    try:

        hwnd = ctypes.windll.kernel32.GetConsoleWindow()

        if hwnd:

            ctypes.windll.user32.ShowWindow(
                hwnd,
                0
            )

    except Exception:
        pass


# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

HTML_FILE = os.path.join(
    BASE_DIR,
    "gui",
    "index.html"
)


# ============================================================
# LAZY AGENT LOADER
#
# IMPORTANT:
# Do NOT construct ActionAgent while the GUI is starting.
# If ActionAgent takes time to initialize, Windows can think
# the GUI has frozen.
# ============================================================

class PickleAPI:

    def __init__(self):

        self.agent = None
        self.window = None

        self._agent_lock = threading.Lock()


    def _get_agent(self):

        if self.agent is not None:
            return self.agent

        with self._agent_lock:

            if self.agent is None:

                from action_agent import ActionAgent

                self.agent = ActionAgent()

        return self.agent


    # ========================================================
    # WINDOW
    # ========================================================

    def set_window(
        self,
        window
    ):

        self.window = window


    def show_window(self):

        if not self.window:
            return False

        try:

            self.window.show()

            try:
                self.window.restore()
            except Exception:
                pass

            try:
                self.window.bring_to_front()
            except Exception:
                pass

            return True

        except Exception:

            return False


    def hide_window(self):

        if not self.window:
            return False

        try:

            self.window.hide()

            return True

        except Exception:

            return False


    def toggle_window(self):

        if not self.window:
            return False

        try:

            self.window.restore()
            self.window.bring_to_front()

            return True

        except Exception:

            return False


    # ========================================================
    # CHAT
    # ========================================================

    def send_message(
        self,
        text
    ):

        try:

            agent = self._get_agent()

            return agent.process(
                text
            )

        except Exception as error:

            return (
                "PickleAI error: "
                + str(error)
            )


    def new_chat(
        self,
        title="New Chat"
    ):

        return self._get_agent().new_chat(
            title
        )


    # ========================================================
    # PROFILE
    # ========================================================

    def get_profile(self):

        return self._get_agent().get_profile()


    def get_user_name(self):

        return self._get_agent().get_user_name()


    def set_user_name(
        self,
        name
    ):

        return self._get_agent().set_user_name(
            name
        )


    # ========================================================
    # MEMORY
    # ========================================================

    def get_memory(self):

        return self._get_agent().get_memory_menu()


    def add_memory(
        self,
        text
    ):

        return self._get_agent().add_memory(
            text
        )


    def forget_memory(
        self,
        text
    ):

        return self._get_agent().forget_memory(
            text
        )


    def forget_memory_id(
        self,
        memory_id
    ):

        return self._get_agent().forget_memory_id(
            memory_id
        )


    def clear_memories(self):

        return self._get_agent().clear_memories()


    # ========================================================
    # CHATS
    # ========================================================

    def get_saved_chats(self):

        return self._get_agent().get_saved_chats()


    def load_chat(
        self,
        chat_id
    ):

        return self._get_agent().load_chat(
            int(chat_id)
        )


    def delete_chat(
        self,
        chat_id
    ):

        return self._get_agent().delete_chat(
            int(chat_id)
        )


    # ========================================================
    # SYSTEM
    # ========================================================

    def get_system_status(self):

        return self._get_agent().system_status()


    def internet_status(self):

        return self._get_agent().internet_status()


    # ========================================================
    # APPS
    # ========================================================

    def open_app(
        self,
        name
    ):

        return self._get_agent().open_app(
            name
        )


    # ========================================================
    # MINI PANEL
    # ========================================================

    def run_panel_action(
        self,
        action,
        value=""
    ):

        return self._get_agent().run_panel_action(
            action,
            value
        )


    def get_panel_buttons(self):

        return self._get_agent().get_default_panel_buttons()


    # ========================================================
    # AI STATUS
    # ========================================================

    def ollama_online(self):

        try:

            return self._get_agent().ai.online()

        except Exception:

            return False


# ============================================================
# WINDOWS GLOBAL HOTKEY
#
# Ctrl + Shift + P
# ============================================================

def start_hotkey_listener(
    api
):

    if sys.platform != "win32":
        return

    user32 = None
    HOTKEY_ID = 9001

    try:

        user32 = ctypes.windll.user32

        MOD_CONTROL = 0x0002
        MOD_SHIFT = 0x0004
        VK_P = 0x50

        registered = user32.RegisterHotKey(
            None,
            HOTKEY_ID,
            MOD_CONTROL | MOD_SHIFT,
            VK_P
        )

        if not registered:
            return

        msg = ctypes.wintypes.MSG()

        while True:

            result = user32.GetMessageW(
                ctypes.byref(msg),
                None,
                0,
                0
            )

            if result <= 0:
                break

            if msg.message == 0x0312:

                try:

                    api.show_window()

                    if api.window:

                        api.window.evaluate_js(
                            """
                            if (window.toggleMiniPanel) {
                                window.toggleMiniPanel();
                            }
                            """
                        )

                except Exception:
                    pass

    except Exception:

        pass

    finally:

        try:

            if user32:

                user32.UnregisterHotKey(
                    None,
                    HOTKEY_ID
                )

        except Exception:
            pass


# ============================================================
# START
# ============================================================

def start():

    # --------------------------------------------------------
    # Verify HTML
    # --------------------------------------------------------

    if not os.path.isfile(
        HTML_FILE
    ):

        raise FileNotFoundError(
            "PickleAI GUI not found:\n"
            + HTML_FILE
        )


    # --------------------------------------------------------
    # Create API
    #
    # ActionAgent is intentionally NOT created here.
    # --------------------------------------------------------

    api = PickleAPI()


    # --------------------------------------------------------
    # Create WebView
    # --------------------------------------------------------

    window = webview.create_window(

        "PickleAI",

        HTML_FILE,

        js_api=api,

        width=1400,

        height=900,

        min_size=(
            1000,
            650
        ),

        resizable=True,

        background_color="#08090b"

    )


    api.set_window(
        window
    )


    # --------------------------------------------------------
    # Global hotkey
    # --------------------------------------------------------

    hotkey_thread = threading.Thread(

        target=start_hotkey_listener,

        args=(api,),

        daemon=True

    )

    hotkey_thread.start()


    # --------------------------------------------------------
    # START WEBVIEW
    #
    # Explicitly use EdgeChromium on Windows.
    # pywebview uses WebView2 for this renderer.
    # --------------------------------------------------------

    if sys.platform == "win32":

        webview.start(
            gui="edgechromium",
            debug=False
        )

    else:

        webview.start(
            debug=False
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    try:

        start()

    except Exception as error:

        # Since the console is hidden, make startup failures
        # visible instead of silently disappearing.

        if sys.platform == "win32":

            try:

                ctypes.windll.user32.MessageBoxW(
                    None,
                    (
                        "PickleAI could not start.\n\n"
                        + str(error)
                    ),
                    "PickleAI Startup Error",
                    0x10
                )

            except Exception:
                pass

        else:

            print(
                "PickleAI startup error:",
                error
            )