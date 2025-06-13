import sys
from PySide6.QtWidgets import QApplication
from qt_material import apply_stylesheet

from src.medical_assistant.ui import MedicalMainWindow
from dotenv import load_dotenv
load_dotenv()
def main():
    """Main function to launch the application."""
    app = QApplication(sys.argv)

    try:
        apply_stylesheet(app, theme='dark_yellow.xml')
    except Exception as e:
        print(f"Could not apply stylesheet: {e}. Using default style.")

    window = MedicalMainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()