"""一条命令启动网页并自动打开浏览器：python start_web.py"""

from threading import Timer
from webbrowser import open as open_browser

from web_app import HOST, PORT, run


if __name__ == "__main__":
    Timer(1.0, lambda: open_browser(f"http://{HOST}:{PORT}")).start()
    run()
