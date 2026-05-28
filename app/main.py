import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Red Dual ISP — RT-BE50")
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
    main()
