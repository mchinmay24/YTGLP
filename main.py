import sys
import os
from PyQt5.QtWidgets import QApplication
from core.dependencies import missing_dependencies
from ui.dialogs.dependency_dialog import DependencyDialog
from ui.main_window import MainWindow
from core.settings import SettingsManager

def load_theme(app):
    qss_path = os.path.join("resources", "qss", "dark.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r") as f:
            app.setStyleSheet(f.read())

def main():
    app = QApplication(sys.argv)
    settings = SettingsManager()
    load_theme(app)
    missing = missing_dependencies()
    if missing:
        dlg = DependencyDialog(missing)
        dlg.exec_()
        sys.exit(0)

    window = MainWindow(settings=settings, app=app)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
