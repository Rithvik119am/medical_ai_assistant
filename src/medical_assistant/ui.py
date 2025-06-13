import os
from PySide6.QtWidgets import (
    QMainWindow, QVBoxLayout, QWidget, QListWidget,
    QLineEdit, QFormLayout, QSplitter, QPushButton, QLabel,
    QListWidgetItem, QHBoxLayout, QMessageBox, QFileDialog, QTextEdit,
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QTextOption

from langchain_core.messages import HumanMessage, AIMessage

from src.medical_assistant.workers import (
    ChromaDBIngestionWorker, MedicalAgentWorker, AgentInitializationWorker
)

class MedicalMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Medical AI Assistant")
        self.setGeometry(100, 100, 1200, 800)

        self.agent_executor = None
        self.vector_store = None
        self.chat_history = []

        self.main_layout = QVBoxLayout()

        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setSelectionMode(QListWidget.NoSelection)
        self.chat_list_widget.setStyleSheet("QListWidget { border: none; }")

        self.user_input_line = QLineEdit()
        self.user_input_line.setPlaceholderText("Initialize agent to begin...")
        self.user_input_line.returnPressed.connect(self.handle_user_input)
        self.user_input_line.setEnabled(False)

        self.main_layout.addWidget(self.chat_list_widget)
        self.main_layout.addWidget(self.user_input_line)

        sidebar_layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.google_apiKeyInput = QLineEdit()
        self.google_apiKeyInput.setEchoMode(QLineEdit.Password)
        if "GOOGLE_API_KEY" in os.environ:
            self.google_apiKeyInput.setText(os.environ["GOOGLE_API_KEY"])
        form_layout.addRow(QLabel("Google AI API Key:"), self.google_apiKeyInput)
        
        self.serper_apiKeyInput = QLineEdit()
        self.serper_apiKeyInput.setEchoMode(QLineEdit.Password)
        if "SERPER_API_KEY" in os.environ:
            self.serper_apiKeyInput.setText(os.environ["SERPER_API_KEY"])
        form_layout.addRow(QLabel("Serper API Key:"), self.serper_apiKeyInput)

        self.initAgentButton = QPushButton("Initialize Agent")
        self.initAgentButton.clicked.connect(self.initialize_agent)
        form_layout.addRow(self.initAgentButton)

        self.upload_button = QPushButton("Add Document to Knowledge Base")
        self.upload_button.setEnabled(False)
        self.upload_button.clicked.connect(self.open_file_dialog)
        form_layout.addRow(self.upload_button)

        self.statusLabel = QLabel("Status: Not Initialized")
        self.statusLabel.setWordWrap(True)
        form_layout.addRow(self.statusLabel)

        sidebar_layout.addLayout(form_layout)
        sidebar_layout.addStretch()

        self.clearChatButton = QPushButton("Clear Chat")
        self.clearChatButton.clicked.connect(self.clear_chat)
        sidebar_layout.addWidget(self.clearChatButton)

        sidebar_widget = QWidget()
        sidebar_widget.setLayout(sidebar_layout)
        sidebar_widget.setMaximumWidth(350)

        chat_widget = QWidget()
        chat_widget.setLayout(self.main_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(sidebar_widget)
        splitter.addWidget(chat_widget)
        splitter.setStretchFactor(1, 3)

        self.setCentralWidget(splitter)

    def initialize_agent(self):
        google_api_key = self.google_apiKeyInput.text()
        serper_api_key = self.serper_apiKeyInput.text()

        if not google_api_key or not serper_api_key:
            self.statusLabel.setText("Status: Both API Keys are required.")
            self.statusLabel.setStyleSheet("color: red;")
            return
        
        os.environ['GOOGLE_API_KEY'] = google_api_key
        os.environ['SERPER_API_KEY'] = serper_api_key

        self.statusLabel.setText("Status: Initializing agent... (This may take a moment)")
        self.statusLabel.setStyleSheet("color: orange;")
        self.initAgentButton.setEnabled(False)

        self.init_worker = AgentInitializationWorker(google_api_key)
        self.init_worker.agent_initialized.connect(self.on_agent_initialized)
        self.init_worker.start()

    def on_agent_initialized(self, success, agent_executor, vector_store):
        if success:
            self.agent_executor = agent_executor
            self.vector_store = vector_store
            self.statusLabel.setText("Status: Agent is ready.")
            self.statusLabel.setStyleSheet("color: green;")
            self.user_input_line.setEnabled(True)
            self.user_input_line.setPlaceholderText("Ask a medical question...")
            self.upload_button.setEnabled(True)
        else:
            self.statusLabel.setText("Status: Failed to initialize. Check console for errors.")
            self.statusLabel.setStyleSheet("color: red;")
            self.initAgentButton.setEnabled(True)

    def open_file_dialog(self):
        file_filters = "Documents (*.txt *.pdf *.docx *.md);;All Files (*)"
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Document", "", file_filters
        )
        if file_name:
            self.statusLabel.setText("Status: Ingesting document...")
            self.statusLabel.setStyleSheet("color: orange;")
            self.upload_button.setEnabled(False)

            self.ingestion_worker = ChromaDBIngestionWorker(file_name, self.vector_store)
            self.ingestion_worker.finished.connect(self.on_ingestion_finished)
            self.ingestion_worker.start()

    def on_ingestion_finished(self, success, message):
        self.statusLabel.setText(f"Status: {message}")
        self.statusLabel.setStyleSheet("color: green;" if success else "color: red;")
        self.upload_button.setEnabled(True)

    def handle_user_input(self):
        if not self.agent_executor:
            self.add_message("System", "Please initialize the agent first.")
            return

        user_text = self.user_input_line.text().strip()
        if not user_text:
            return

        self.add_message("You", user_text)
        self.user_input_line.clear()

        self.agent_worker = MedicalAgentWorker(
            agent_executor=self.agent_executor,
            vector_store=self.vector_store,
            serper_apiKeyInput=self.serper_apiKeyInput.text(),
            query=user_text,
            chat_history=self.chat_history
        )
        self.agent_worker.response_generated.connect(self.on_ai_response)
        self.agent_worker.start()

    def on_ai_response(self, text):
        self.add_message("Assistant", text, is_ai=True)
        self.chat_history.append(HumanMessage(content=self.user_input_line.placeholderText()))
        self.chat_history.append(AIMessage(content=text))

    def add_message(self, sender, text, is_ai=False):
        item = QListWidgetItem()
        message_widget = QWidget()
        layout = QHBoxLayout(message_widget)
        layout.setContentsMargins(5, 5, 5, 5)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setTextInteractionFlags(Qt.TextSelectableByMouse)
        text_edit.setWordWrapMode(QTextOption.WrapMode.WordWrap)
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        max_width = int(self.chat_list_widget.viewport().width() * 0.7)
        text_edit.setMaximumWidth(max_width)

        doc = text_edit.document()
        doc.setTextWidth(max_width)

        if is_ai:
            text_edit.setMarkdown(text)
            text_edit.setStyleSheet(
                "background-color: #2c3e50; color: #ecf0f1; border-radius: 10px; padding: 10px; border: none;"
            )
            layout.addWidget(text_edit)
            layout.addStretch()
        else:
            text_edit.setPlainText(text)
            bg_color = "#0078d4" if sender == "You" else "#6c757d"
            text_edit.setStyleSheet(
                f"background-color: {bg_color}; color: #ffffff; border-radius: 10px; padding: 10px; border: none;"
            )
            layout.addStretch()
            layout.addWidget(text_edit)

        doc.adjustSize()
        height = doc.size().height()
        text_edit.setFixedHeight(int(height) + 15)

        item.setSizeHint(QSize(self.chat_list_widget.width() - 5, text_edit.height() + 15))
        self.chat_list_widget.addItem(item)
        self.chat_list_widget.setItemWidget(item, message_widget)
        self.chat_list_widget.scrollToBottom()

    def clear_chat(self):
        reply = QMessageBox.question(self, 'Clear Chat',
                                     "Are you sure you want to clear the chat history?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.chat_list_widget.clear()
            self.chat_history.clear()