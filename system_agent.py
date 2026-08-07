import platform
import subprocess
import urllib.request
import psutil

import win32gui
import win32con
import win32api


class SystemAgent:

    def __init__(self):
        self.system = platform.system()


    # =========================
    # WINDOWS
    # =========================

    def get_window_list(self):

        windows = []

        def callback(hwnd, _):

            if win32gui.IsWindowVisible(hwnd):

                title = win32gui.GetWindowText(hwnd)

                if title.strip():

                    windows.append({
                        "hwnd": hwnd,
                        "title": title
                    })


        win32gui.EnumWindows(
            callback,
            None
        )

        return windows



    def window_summary(self):

        windows = self.get_window_list()

        if not windows:
            return "No windows found."

        return "\n".join(
            [
                "Open windows:",
                *[
                    "- " + w["title"]
                    for w in windows[:25]
                ]
            ]
        )



    def get_active_window(self):

        hwnd = win32gui.GetForegroundWindow()

        return win32gui.GetWindowText(hwnd)



    def minimize_all_except(self, keep):

        count = 0

        for window in self.get_window_list():

            if keep.lower() not in window["title"].lower():

                win32gui.ShowWindow(
                    window["hwnd"],
                    win32con.SW_MINIMIZE
                )

                count += 1


        return f"Minimized {count} windows."



    def arrange_windows(self):

        windows = self.get_window_list()

        if not windows:
            return "No windows found."


        width = win32api.GetSystemMetrics(0)
        height = win32api.GetSystemMetrics(1)


        positions = [

            (0, 0, width//2, height),
            (width//2, 0, width//2, height)

        ]


        moved = 0


        for i, window in enumerate(windows[:2]):

            x,y,w,h = positions[i]


            win32gui.ShowWindow(
                window["hwnd"],
                win32con.SW_RESTORE
            )


            win32gui.MoveWindow(
                window["hwnd"],
                x,
                y,
                w,
                h,
                True
            )


            moved += 1


        return f"Arranged {moved} windows."



    # =========================
    # APPLICATIONS
    # =========================

    def open_app(self, app):

        try:

            subprocess.Popen(
                app,
                shell=True
            )

            return f"Opening {app}"

        except Exception as e:

            return f"Could not open {app}: {e}"



    def close_window(self, name):

        closed = 0


        for window in self.get_window_list():

            if name.lower() in window["title"].lower():

                win32gui.PostMessage(
                    window["hwnd"],
                    win32con.WM_CLOSE,
                    0,
                    0
                )

                closed += 1


        return f"Closed {closed} windows."



    # =========================
    # INTERNET
    # =========================

    def internet_status(self):

        try:

            urllib.request.urlopen(
                "https://www.google.com",
                timeout=3
            )

            return {
                "online": True,
                "status": "Connected"
            }


        except:

            return {
                "online": False,
                "status": "Offline"
            }



    # =========================
    # SYSTEM
    # =========================

    def status(self):

        return {

            "cpu":
            psutil.cpu_percent(),

            "ram":
            psutil.virtual_memory().percent,

            "disk":
            psutil.disk_usage(
                "/"
            ).percent,

            "windows":
            len(
                self.get_window_list()
            ),

            "internet":
            self.internet_status()

        }