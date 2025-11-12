"""Codexa Desktop GUI application."""

import sys
import os
from typing import Optional, List
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QComboBox,
    QCheckBox,
    QStackedWidget,
    QTabWidget,
    QProgressBar,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor
import httpx


class SearchWorker(QThread):
    """Worker thread for performing searches."""

    search_completed = Signal(dict)
    search_failed = Signal(str)

    def __init__(
        self,
        query: str,
        top_k: int = 10,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        project: Optional[str] = None,
        generate_answer: bool = True,
    ) -> None:
        """Initialize search worker."""
        super().__init__()
        self.query = query
        self.top_k = top_k
        self.api_url = api_url
        self.api_key = api_key or os.getenv("CODEXA_API_KEY")
        self.project = project
        self.generate_answer = generate_answer

    def run(self) -> None:
        """Execute search in background thread."""
        try:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            with httpx.Client(timeout=60.0, headers=headers) as client:
                payload = {
                    "query": self.query,
                    "top_k": self.top_k,
                    "generate_answer": self.generate_answer,
                }
                if self.project is not None:
                    payload["project"] = self.project
                response = client.post(f"{self.api_url}/search", json=payload)
                response.raise_for_status()
                self.search_completed.emit(response.json())
        except Exception as e:
            self.search_failed.emit(str(e))


class IndexWorker(QThread):
    """Worker thread for indexing files."""

    index_completed = Signal(dict)
    index_failed = Signal(str)

    def __init__(
        self,
        file_paths: List[str],
        encrypt: bool = False,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        project: Optional[str] = None,
    ) -> None:
        """Initialize index worker."""
        super().__init__()
        self.file_paths = file_paths
        self.encrypt = encrypt
        self.api_url = api_url
        self.api_key = api_key or os.getenv("CODEXA_API_KEY")
        self.project = project

    def run(self) -> None:
        """Execute indexing in background thread."""
        try:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            with httpx.Client(timeout=60.0, headers=headers) as client:
                payload = {
                    "file_paths": self.file_paths,
                    "encrypt": self.encrypt,
                }
                if self.project is not None:
                    payload["project"] = self.project
                response = client.post(f"{self.api_url}/index", json=payload)
                response.raise_for_status()
                self.index_completed.emit(response.json())
        except Exception as e:
            self.index_failed.emit(str(e))


class IndexDirectoryWorker(QThread):
    """Worker thread for indexing a directory."""

    index_completed = Signal(dict)
    index_failed = Signal(str)

    def __init__(
        self,
        directory_path: str,
        extensions: List[str],
        recursive: bool = True,
        encrypt: bool = False,
        api_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        project: Optional[str] = None,
    ) -> None:
        """Initialize directory index worker."""
        super().__init__()
        self.directory_path = directory_path
        self.extensions = extensions
        self.recursive = recursive
        self.encrypt = encrypt
        self.api_url = api_url
        self.api_key = api_key or os.getenv("CODEXA_API_KEY")
        self.project = project

    def run(self) -> None:
        """Execute directory indexing in background thread."""
        try:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            with httpx.Client(timeout=300.0, headers=headers) as client:
                payload = {
                    "directory_path": self.directory_path,
                    "extensions": self.extensions,
                    "recursive": self.recursive,
                    "encrypt": self.encrypt,
                }
                if self.project is not None:
                    payload["project"] = self.project
                response = client.post(f"{self.api_url}/index/directory", json=payload)
                response.raise_for_status()
                self.index_completed.emit(response.json())
        except Exception as e:
            self.index_failed.emit(str(e))


class CodexaDesktop(QMainWindow):
    """Main desktop application window."""

    def __init__(self) -> None:
        """Initialize the desktop application."""
        super().__init__()
        # Support CODEXA_API_URL environment variable for remote access
        self.api_url = os.getenv("CODEXA_API_URL", "http://localhost:8000")
        self.current_worker: Optional[QThread] = None
        self.current_project: Optional[str] = None
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Codexa - AI Dev Knowledge Vault")
        self.setMinimumSize(1200, 800)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("🤖 Codexa - AI Knowledge Vault")
        title_font = QFont()
        title_font.setPointSize(22)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        # Project selector (mandatory, selection only)
        toolbar_layout.addWidget(QLabel("Project:"))
        self.project_combo = QComboBox()
        self.project_combo.setEditable(False)  # Selection only, no creating new projects here
        self.project_combo.setMinimumWidth(150)
        self.project_combo.currentTextChanged.connect(self.on_project_changed)
        toolbar_layout.addWidget(self.project_combo)
        
        # Add project button
        add_project_btn = QPushButton("➕ Add Project")
        add_project_btn.clicked.connect(self.add_project)
        add_project_btn.setMaximumWidth(120)
        toolbar_layout.addWidget(add_project_btn)
        
        toolbar_layout.addStretch()
        
        # Action buttons
        index_files_btn = QPushButton("📁 Index Files")
        index_files_btn.clicked.connect(self.index_files)
        index_dir_btn = QPushButton("📂 Index Directory")
        index_dir_btn.clicked.connect(self.index_directory)
        
        # Delete buttons
        delete_files_btn = QPushButton("🗑️ Delete Files")
        delete_files_btn.clicked.connect(self.delete_indexed_files)
        delete_dir_btn = QPushButton("🗑️ Delete Directory")
        delete_dir_btn.clicked.connect(self.delete_indexed_directory)
        
        settings_btn = QPushButton("⚙️ Settings")
        settings_btn.clicked.connect(self.show_settings)
        toolbar_layout.addWidget(index_files_btn)
        toolbar_layout.addWidget(index_dir_btn)
        toolbar_layout.addWidget(delete_files_btn)
        toolbar_layout.addWidget(delete_dir_btn)
        toolbar_layout.addWidget(settings_btn)
        layout.addLayout(toolbar_layout)

        # Search input section
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Ask anything about your codebase...")
        self.search_input.returnPressed.connect(self.perform_search)
        self.search_input.setMinimumHeight(35)
        
        search_font = QFont()
        search_font.setPointSize(11)
        self.search_input.setFont(search_font)

        self.search_button = QPushButton("🔍 Ask")
        self.search_button.clicked.connect(self.perform_search)
        self.search_button.setMinimumWidth(100)
        self.search_button.setMinimumHeight(35)

        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Main content area - Stacked widget for AI Answer vs Raw Results
        self.content_stack = QStackedWidget()
        
        # Page 1: AI Answer (Primary View)
        ai_page = QWidget()
        ai_layout = QVBoxLayout(ai_page)
        ai_layout.setContentsMargins(0, 0, 0, 0)
        
        # AI Answer header
        ai_header = QHBoxLayout()
        ai_title = QLabel("🤖 AI Answer")
        ai_title_font = QFont()
        ai_title_font.setPointSize(14)
        ai_title_font.setBold(True)
        ai_title.setFont(ai_title_font)
        ai_header.addWidget(ai_title)
        ai_header.addStretch()
        
        # Toggle buttons
        self.show_raw_btn = QPushButton("📋 View Raw Results")
        self.show_raw_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        self.show_docs_btn = QPushButton("📚 Indexed Documents")
        self.show_docs_btn.clicked.connect(self.show_indexed_documents)
        ai_header.addWidget(self.show_raw_btn)
        ai_header.addWidget(self.show_docs_btn)
        ai_layout.addLayout(ai_header)
        
        # Context window usage visualization
        self.context_usage_layout = QHBoxLayout()
        self.context_usage_label = QLabel("Context Usage:")
        self.context_usage_label.setMinimumWidth(100)
        self.context_usage_bar = QProgressBar()
        self.context_usage_bar.setMinimum(0)
        self.context_usage_bar.setMaximum(100)
        self.context_usage_bar.setFormat("%p%")
        self.context_usage_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        self.context_usage_text = QLabel("")
        self.context_usage_text.setMinimumWidth(200)
        self.context_usage_layout.addWidget(self.context_usage_label)
        self.context_usage_layout.addWidget(self.context_usage_bar, stretch=1)
        self.context_usage_layout.addWidget(self.context_usage_text)
        self.context_usage_widget = QWidget()
        self.context_usage_widget.setLayout(self.context_usage_layout)
        self.context_usage_widget.setVisible(False)  # Hide until we have stats
        ai_layout.addWidget(self.context_usage_widget)
        
        # AI Answer display
        self.ai_answer = QTextEdit()
        self.ai_answer.setReadOnly(True)
        self.ai_answer.setPlaceholderText("Ask a question to get an AI-powered answer based on your indexed knowledge...")
        answer_font = QFont()
        answer_font.setPointSize(11)
        self.ai_answer.setFont(answer_font)
        ai_layout.addWidget(self.ai_answer, stretch=1)
        
        # Source documents preview (collapsible)
        sources_label = QLabel("📚 Source Documents")
        sources_font = QFont()
        sources_font.setBold(True)
        sources_label.setFont(sources_font)
        ai_layout.addWidget(sources_label)
        
        self.sources_list = QListWidget()
        self.sources_list.setMaximumHeight(150)
        self.sources_list.itemClicked.connect(self.show_source_detail)
        ai_layout.addWidget(self.sources_list)
        
        self.content_stack.addWidget(ai_page)
        
        # Page 2: Raw Search Results (Secondary View)
        raw_page = QWidget()
        raw_layout = QVBoxLayout(raw_page)
        raw_layout.setContentsMargins(0, 0, 0, 0)
        
        # Raw results header
        raw_header = QHBoxLayout()
        raw_title = QLabel("🔍 Semantic Search Results")
        raw_title_font = QFont()
        raw_title_font.setPointSize(14)
        raw_title_font.setBold(True)
        raw_title.setFont(raw_title_font)
        raw_header.addWidget(raw_title)
        raw_header.addStretch()
        
        # Toggle buttons
        self.show_ai_btn = QPushButton("🤖 Back to AI Answer")
        self.show_ai_btn.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.show_docs_btn2 = QPushButton("📚 Indexed Documents")
        self.show_docs_btn2.clicked.connect(self.show_indexed_documents)
        raw_header.addWidget(self.show_ai_btn)
        raw_header.addWidget(self.show_docs_btn2)
        raw_layout.addLayout(raw_header)
        
        # Splitter for raw results
        raw_splitter = QSplitter(Qt.Horizontal)
        
        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_result_detail)
        raw_splitter.addWidget(self.results_list)
        
        # Result detail view
        self.result_detail = QTextEdit()
        self.result_detail.setReadOnly(True)
        raw_splitter.addWidget(self.result_detail)
        
        raw_splitter.setStretchFactor(0, 1)
        raw_splitter.setStretchFactor(1, 2)
        raw_layout.addWidget(raw_splitter, stretch=1)
        
        self.content_stack.addWidget(raw_page)
        
        # Page 3: Indexed Documents
        docs_page = QWidget()
        docs_layout = QVBoxLayout(docs_page)
        docs_layout.setContentsMargins(0, 0, 0, 0)
        
        # Documents header
        docs_header = QHBoxLayout()
        docs_title = QLabel("📚 Indexed Documents")
        docs_title_font = QFont()
        docs_title_font.setPointSize(14)
        docs_title_font.setBold(True)
        docs_title.setFont(docs_title_font)
        docs_header.addWidget(docs_title)
        docs_header.addStretch()
        
        # Refresh button
        refresh_docs_btn = QPushButton("🔄 Refresh")
        refresh_docs_btn.clicked.connect(self.load_indexed_documents)
        docs_header.addWidget(refresh_docs_btn)
        
        # Delete button
        delete_doc_btn = QPushButton("🗑️ Delete Selected")
        delete_doc_btn.clicked.connect(self.delete_selected_document)
        docs_header.addWidget(delete_doc_btn)
        
        # Toggle buttons
        self.show_ai_btn3 = QPushButton("🤖 AI Answer")
        self.show_ai_btn3.clicked.connect(lambda: self.content_stack.setCurrentIndex(0))
        self.show_raw_btn3 = QPushButton("📋 Raw Results")
        self.show_raw_btn3.clicked.connect(lambda: self.content_stack.setCurrentIndex(1))
        
        # Auto-load documents when switching to this view
        self.content_stack.currentChanged.connect(self.on_content_stack_changed)
        docs_header.addWidget(self.show_ai_btn3)
        docs_header.addWidget(self.show_raw_btn3)
        docs_layout.addLayout(docs_header)
        
        # Documents list
        self.documents_list = QListWidget()
        self.documents_list.itemClicked.connect(self.show_document_detail)
        docs_layout.addWidget(self.documents_list, stretch=1)
        
        # Document detail view
        self.document_detail = QTextEdit()
        self.document_detail.setReadOnly(True)
        self.document_detail.setMaximumHeight(200)
        docs_layout.addWidget(self.document_detail)
        
        self.content_stack.addWidget(docs_page)
        
        # Start with AI answer view
        self.content_stack.setCurrentIndex(0)
        
        layout.addWidget(self.content_stack, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready - Ask a question to get started")

        # Store results data
        self.results_data: List[dict] = []
        
        # Load project list
        self.load_projects()
        
        # Store documents data
        self.documents_data: List[dict] = []

    def load_projects(self) -> None:
        """Load available projects from API and config."""
        projects = set()
        
        # First, get current project from config (even if not indexed yet)
        try:
            from core.config import get_current_project
            current_project = get_current_project()
            if current_project:
                projects.add(current_project)
        except ImportError:
            pass
        
        # Then, get projects from indexed documents
        try:
            headers = {}
            api_key = os.getenv("CODEXA_API_KEY")
            if api_key:
                headers["X-API-Key"] = api_key
            with httpx.Client(base_url=self.api_url, headers=headers, timeout=5.0) as client:
                # Try to get projects by searching (limited)
                resp = client.post("/search", json={"query": "", "top_k": 100, "generate_answer": False})
                if resp.status_code == 200:
                    data = resp.json()
                    results = data.get("results", [])
                    for result in results:
                        project = result.get("metadata", {}).get("project")
                        if project:
                            projects.add(project)
        except Exception:
            pass  # Silently fail - will use projects from config
        
        # Update combo box (projects only, no global option)
        # Block signals to avoid triggering on_project_changed during update
        self.project_combo.blockSignals(True)
        current_text = self.project_combo.currentText()
        self.project_combo.clear()
        for proj in sorted(projects):
            self.project_combo.addItem(proj)
        
        # Restore selection or use current project from config
        index = self.project_combo.findText(current_text)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
        elif self.project_combo.count() > 0:
            # Try to use current project from config
            try:
                from core.config import get_current_project
                config_project = get_current_project()
                config_index = self.project_combo.findText(config_project)
                if config_index >= 0:
                    self.project_combo.setCurrentIndex(config_index)
                    current_text = config_project
                else:
                    self.project_combo.setCurrentIndex(0)
                    current_text = self.project_combo.currentText()
            except ImportError:
                self.project_combo.setCurrentIndex(0)
                current_text = self.project_combo.currentText()
        
        self.project_combo.blockSignals(False)
        
        # Update current project if selection changed
        if current_text and current_text != self.current_project:
            self.on_project_changed(current_text)

    def on_project_changed(self, text: str) -> None:
        """Handle project selection change."""
        # Projects are mandatory - always set the selected project
        self.current_project = text

    def add_project(self) -> None:
        """Show dialog to create a new project."""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QPushButton as QBtn, QLabel, QLineEdit
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Create New Project")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # Instructions
        info_label = QLabel(
            "Create a new project to organize your indexed documents.\n\n"
            "Projects help isolate knowledge by workspace or context.\n\n"
            "Note: Use the dropdown in the toolbar to select existing projects."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Project name input
        name_label = QLabel("Project Name:")
        layout.addWidget(name_label)
        
        name_input = QLineEdit()
        name_input.setPlaceholderText("e.g., my-project, frontend, backend")
        name_input.setMinimumHeight(30)
        layout.addWidget(name_input)
        
        # Show existing projects for reference
        if self.project_combo.count() > 0:
            existing_label = QLabel("Existing projects:")
            existing_label.setStyleSheet("color: gray; font-size: 10pt;")
            layout.addWidget(existing_label)
            existing_list = QLabel(", ".join([self.project_combo.itemText(i) for i in range(self.project_combo.count())]))
            existing_list.setStyleSheet("color: gray; font-size: 9pt;")
            existing_list.setWordWrap(True)
            layout.addWidget(existing_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        create_btn = QBtn("Create Project")
        create_btn.setDefault(True)
        cancel_btn = QBtn("Cancel")
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        create_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        
        # Focus on input
        name_input.setFocus()
        
        if dialog.exec():
            project_name = name_input.text().strip()
            
            if not project_name:
                QMessageBox.warning(self, "Empty Name", "Please enter a project name.")
                return
            
            # Check if project already exists
            existing_index = self.project_combo.findText(project_name)
            if existing_index >= 0:
                QMessageBox.warning(
                    self,
                    "Project Exists",
                    f"Project '{project_name}' already exists.\n\n"
                    f"Please use the dropdown in the toolbar to select it."
                )
                return
            
            # Set as current project in config
            try:
                from core.config import set_current_project
                set_current_project(project_name)
                
                # Add to combo box (insert in sorted position)
                # Find insertion point
                insert_index = 0
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemText(i) > project_name:
                        insert_index = i
                        break
                    insert_index = i + 1
                
                self.project_combo.insertItem(insert_index, project_name)
                self.project_combo.setCurrentText(project_name)
                self.on_project_changed(project_name)
                
                # Don't reload projects here - it would clear the newly created project
                # if no documents are indexed yet. The project is already added above.
                # It will be included in future load_projects() calls via config.
                
                QMessageBox.information(
                    self,
                    "Project Created",
                    f"✅ Project '{project_name}' created and set as current.\n\n"
                    f"Documents indexed without specifying a project will use this project."
                )
            except ImportError:
                # Fallback: just add to combo box
                insert_index = 0
                for i in range(self.project_combo.count()):
                    if self.project_combo.itemText(i) > project_name:
                        insert_index = i
                        break
                    insert_index = i + 1
                self.project_combo.insertItem(insert_index, project_name)
                self.project_combo.setCurrentText(project_name)
                self.on_project_changed(project_name)
                QMessageBox.information(
                    self,
                    "Project Added",
                    f"✅ Project '{project_name}' added to list.\n\n"
                    f"Note: Config module not available, project not saved to config file."
                )

    def index_files(self) -> None:
        """Open file dialog and index selected files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Index",
            "",
            "Python and Markdown Files (*.py *.md);;All Files (*)",
        )

        if not file_paths:
            return

        # Ask about encryption
        encrypt = False
        if len(file_paths) > 0:
            reply = QMessageBox.question(
                self,
                "Encrypt Files?",
                "Do you want to encrypt the content of these files?\n\n"
                "Encrypted files are secure but cannot be searched as efficiently.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            encrypt = reply == QMessageBox.Yes

        self.statusBar().showMessage(f"Indexing {len(file_paths)} files...")
        self.search_button.setEnabled(False)

        # Start indexing in background thread
        self.current_worker = IndexWorker(
            file_paths,
            encrypt=encrypt,
            api_url=self.api_url,
            project=self.current_project,
        )
        self.current_worker.index_completed.connect(self.on_index_completed)
        self.current_worker.index_failed.connect(self.on_index_failed)
        self.current_worker.start()

    def delete_indexed_files(self) -> None:
        """Open file dialog to delete indexed files."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Files to Delete from Index",
            "",
            "All Files (*.*);;Markdown (*.md);;Python (*.py);;Text (*.txt)",
        )
        if not file_paths:
            return
        
        for file_path in file_paths:
            self.delete_file_from_index(file_path)
        
        # Reload documents after deletion
        self.load_indexed_documents()
    
    def delete_indexed_directory(self) -> None:
        """Open directory dialog to delete indexed directory."""
        directory_path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory to Delete from Index",
            "",
        )
        if not directory_path:
            return
        
        # Ask about recursive deletion
        recursive = (
            QMessageBox.question(
                self,
                "Recursive Deletion?",
                "Delete files in subdirectories too?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            == QMessageBox.Yes
        )
        
        self.delete_directory_from_index(directory_path, recursive=recursive)
    
    def index_directory(self) -> None:
        """Open directory dialog and index all files in directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory to Index", "", QFileDialog.ShowDirsOnly
        )

        if not directory:
            return

        # Ask about encryption
        reply = QMessageBox.question(
            self,
            "Encrypt Files?",
            "Do you want to encrypt the content of files in this directory?\n\n"
            "Encrypted files are secure but cannot be searched as efficiently.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        encrypt = reply == QMessageBox.Yes

        # Default extensions
        extensions = [".py", ".md"]

        self.statusBar().showMessage(f"Indexing directory: {directory}...")
        self.search_button.setEnabled(False)

        # Start directory indexing in background thread
        self.current_worker = IndexDirectoryWorker(
            directory_path=directory,
            extensions=extensions,
            recursive=True,
            encrypt=encrypt,
            api_url=self.api_url,
            project=self.current_project,
        )
        self.current_worker.index_completed.connect(self.on_index_completed)
        self.current_worker.index_failed.connect(self.on_index_failed)
        self.current_worker.start()

    def on_index_completed(self, result: dict) -> None:
        """Handle index completion."""
        self.search_button.setEnabled(True)
        indexed = result.get("indexed_count", 0)
        failed = result.get("failed_count", 0)
        errors = result.get("errors", [])

        message = f"Indexed {indexed} files"
        if failed > 0:
            message += f", {failed} failed"
            if errors:
                error_details = "\n".join(
                    [
                        f"  • {e.get('file_path', 'Unknown')}: {e.get('error', 'Unknown error')}"
                        for e in errors[:5]
                    ]
                )
                if len(errors) > 5:
                    error_details += f"\n  ... and {len(errors) - 5} more errors"
                message += f"\n\nErrors:\n{error_details}"

        self.statusBar().showMessage(message.split("\n")[0])
        QMessageBox.information(self, "Indexing Complete", message)
        
        # Reload projects
        self.load_projects()

    def on_index_failed(self, error: str) -> None:
        """Handle index failure."""
        self.search_button.setEnabled(True)
        self.statusBar().showMessage("Indexing failed")
        QMessageBox.critical(self, "Indexing Error", f"Failed to index files:\n{error}")

    def perform_search(self) -> None:
        """Perform semantic search with AI answer."""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a search query.")
            return

        self.statusBar().showMessage(f"Searching: {query}...")
        self.search_button.setEnabled(False)
        self.ai_answer.clear()
        self.sources_list.clear()
        self.results_list.clear()
        self.result_detail.clear()

        # Start search in background thread
        self.current_worker = SearchWorker(
            query,
            top_k=10,
            api_url=self.api_url,
            project=self.current_project,
            generate_answer=True,
        )
        self.current_worker.search_completed.connect(self.on_search_completed)
        self.current_worker.search_failed.connect(self.on_search_failed)
        self.current_worker.start()

    def on_search_completed(self, result: dict) -> None:
        """Handle search completion."""
        self.search_button.setEnabled(True)
        results = result.get("results", [])
        answer = result.get("answer")
        answer_stats = result.get("answer_stats", {})
        self.results_data = results

        # Show AI answer prominently
        if answer:
            self.ai_answer.setPlainText(answer)
            self.statusBar().showMessage("✅ Answer generated")
        else:
            self.ai_answer.setPlainText(
                "No AI answer available. Make sure Ollama is running and configured."
            )
            self.statusBar().showMessage("⚠️ No AI answer (check LLM settings)")
        
        # Update context window usage visualization
        if answer_stats:
            usage_pct = answer_stats.get("context_usage_percent", 0)
            context_window = answer_stats.get("context_window", 0)
            total_tokens = answer_stats.get("total_tokens", 0)
            truncated = answer_stats.get("context_truncated", False)
            docs_used = answer_stats.get("context_documents_used", 0)
            docs_available = answer_stats.get("context_documents_available", 0)
            
            # Update progress bar
            self.context_usage_bar.setValue(int(usage_pct))
            
            # Color code based on usage
            if usage_pct > 90:
                self.context_usage_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #f44336;
                    }
                """)
            elif usage_pct > 75:
                self.context_usage_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #ff9800;
                    }
                """)
            else:
                self.context_usage_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid #ccc;
                        border-radius: 3px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #4CAF50;
                    }
                """)
            
            # Update text
            text_parts = []
            if context_window:
                text_parts.append(f"{context_window//1024}k tokens")
            if total_tokens:
                text_parts.append(f"{total_tokens:,} used")
            if truncated:
                text_parts.append("⚠️ Truncated")
            if docs_used and docs_available:
                text_parts.append(f"{docs_used}/{docs_available} docs")
            
            self.context_usage_text.setText(" | ".join(text_parts))
            self.context_usage_widget.setVisible(True)
            
            # Show warning in status bar if high usage
            if usage_pct > 90:
                self.statusBar().showMessage(
                    f"⚠️ High context usage ({usage_pct:.1f}%) - consider increasing context window",
                    5000
                )
            elif usage_pct > 75:
                self.statusBar().showMessage(
                    f"Context usage: {usage_pct:.1f}%",
                    3000
                )
        else:
            self.context_usage_widget.setVisible(False)

        # Populate source documents
        self.sources_list.clear()
        for idx, res in enumerate(results[:5], 1):  # Show top 5 sources
            file_path = res.get("file_path", "Unknown")
            score = res.get("score", 0.0)
            file_type = res.get("file_type", "")
            score_pct = f"{score * 100:.0f}%"
            display_path = file_path.split("/")[-1] if "/" in file_path else file_path
            item_text = f"[{idx}] {display_path} ({file_type}) - {score_pct}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, idx - 1)
            self.sources_list.addItem(item)

        # Also populate raw results list for secondary view
        self.results_list.clear()
        for idx, res in enumerate(results, 1):
            file_path = res.get("file_path", "Unknown")
            score = res.get("score", 0.0)
            file_type = res.get("file_type", "")
            score_pct = f"{score * 100:.1f}%"
            display_path = file_path.split("/")[-1] if "/" in file_path else file_path
            item_text = f"[{idx}] {display_path} | {file_type} | {score_pct}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, idx - 1)
            self.results_list.addItem(item)

        # Auto-select first result in raw view
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
            self.show_result_detail(self.results_list.item(0))

    def on_search_failed(self, error: str) -> None:
        """Handle search failure."""
        self.search_button.setEnabled(True)
        self.statusBar().showMessage("Search failed")
        self.ai_answer.setPlainText(f"Error: {error}")
        QMessageBox.critical(self, "Search Error", f"Failed to perform search:\n{error}")

    def show_source_detail(self, item: QListWidgetItem) -> None:
        """Show details of selected source document."""
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self.results_data):
            return

        result = self.results_data[idx]
        file_path = result.get("file_path", "Unknown")
        file_type = result.get("file_type", "Unknown")
        score = result.get("score", 0.0)
        score_pct = f"{score * 100:.1f}%"
        content = result.get("content", "No content available")
        doc_id = result.get("document_id", "N/A")

        detail_text = f"📄 File: {file_path}\n"
        detail_text += f"📋 Type: {file_type} | 🎯 Relevance: {score_pct} | 🆔 ID: {doc_id[:8]}...\n"
        detail_text += f"\n{'=' * 80}\n\n"
        detail_text += content

        # Show in a popup or switch to raw view
        self.content_stack.setCurrentIndex(1)
        self.result_detail.setPlainText(detail_text)
        self.results_list.setCurrentRow(idx)

    def show_result_detail(self, item: QListWidgetItem) -> None:
        """Display details of selected result."""
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self.results_data):
            return

        result = self.results_data[idx]
        file_path = result.get("file_path", "Unknown")
        file_type = result.get("file_type", "Unknown")
        score = result.get("score", 0.0)
        score_pct = f"{score * 100:.1f}%"
        content = result.get("content", "No content available")
        doc_id = result.get("document_id", "N/A")

        detail_text = f"📄 File: {file_path}\n"
        detail_text += f"📋 Type: {file_type} | 🎯 Relevance: {score_pct} | 🆔 ID: {doc_id[:8]}...\n"
        detail_text += f"\n{'=' * 80}\n\n"
        detail_text += content

        self.result_detail.setPlainText(detail_text)

    def show_settings(self) -> None:
        """Show settings dialog."""
        from PySide6.QtWidgets import QDialog, QFormLayout, QLineEdit, QPushButton as QBtn, QTabWidget, QCheckBox, QLabel

        dialog = QDialog(self)
        dialog.setWindowTitle("Codexa Settings")
        dialog.setMinimumWidth(500)
        dialog.setMinimumHeight(400)

        tabs = QTabWidget()
        dialog_layout = QVBoxLayout(dialog)
        dialog_layout.addWidget(tabs)

        # LLM Settings Tab
        llm_tab = QWidget()
        llm_layout = QFormLayout(llm_tab)

        # Model dropdown
        model_combo = QComboBox()
        model_combo.setEditable(True)  # Allow manual entry if needed
        model_combo.setMinimumWidth(250)
        
        current_model = "llama3.2"
        current_url = "http://localhost:11434"
        available_models = []
        
        try:
            headers = {}
            api_key = os.getenv("CODEXA_API_KEY")
            if api_key:
                headers["X-API-Key"] = api_key
            with httpx.Client(base_url=self.api_url, headers=headers, timeout=5.0) as client:
                # Get current config
                resp = client.get("/config/llm")
                if resp.status_code == 200:
                    data = resp.json()
                    current_model = data.get("model", "llama3.2")
                    current_url = data.get("base_url", "http://localhost:11434")
                    current_context_window = data.get("context_window", 4096)
                
                # Get available models
                models_resp = client.get("/config/llm/models")
                if models_resp.status_code == 200:
                    models_data = models_resp.json()
                    available_models = models_data.get("models", [])
        except Exception:
            pass

        # Populate dropdown with available models
        if available_models:
            for model_info in available_models:
                name = model_info.get("name", "")
                size_gb = model_info.get("size_gb", 0)
                display_text = f"{name} ({size_gb} GB)" if size_gb > 0 else name
                model_combo.addItem(display_text, name)
        else:
            # Fallback: add common models
            model_combo.addItem("llama3.2:latest", "llama3.2:latest")
            model_combo.addItem("llama3.2", "llama3.2")
            model_combo.addItem("mistral:latest", "mistral:latest")
            model_combo.addItem("codellama:latest", "codellama:latest")
        
        # Set current model
        current_index = model_combo.findData(current_model)
        if current_index >= 0:
            model_combo.setCurrentIndex(current_index)
        else:
            # If not in list, set as current text
            model_combo.setCurrentText(current_model)
        
        llm_layout.addRow("Ollama Model:", model_combo)
        
        # Context window dropdown
        context_combo = QComboBox()
        context_combo.setEditable(False)
        context_combo.setMinimumWidth(200)
        context_options = [
            (4096, "4k (Default)"),
            (8192, "8k"),
            (16384, "16k"),
            (32768, "32k"),
            (65536, "64k"),
            (131072, "128k"),
            (262144, "256k (Maximum)"),
        ]
        for value, label in context_options:
            context_combo.addItem(label, value)
        
        # Set current context window
        current_context_window = current_context_window if 'current_context_window' in locals() else 4096
        context_index = context_combo.findData(current_context_window)
        if context_index >= 0:
            context_combo.setCurrentIndex(context_index)
        else:
            # Find closest
            closest = min(context_options, key=lambda x: abs(x[0] - current_context_window))
            context_combo.setCurrentIndex(context_options.index(closest))
        
        llm_layout.addRow("Context Window:", context_combo)
        
        # Info label about Ollama configuration
        context_info = QLabel(
            f"⚠️ Important: Set Ollama's num_ctx to match this value.\n"
            f"Configure via: OLLAMA_NUM_CTX={context_combo.currentData()} or in Ollama settings."
        )
        context_info.setWordWrap(True)
        context_info.setStyleSheet("color: orange; font-size: 9pt;")
        llm_layout.addRow("", context_info)
        
        # Refresh button to reload models
        refresh_btn = QBtn("🔄 Refresh Models")
        refresh_btn.setMaximumWidth(150)
        def refresh_models():
            try:
                headers = {}
                api_key = os.getenv("CODEXA_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                with httpx.Client(base_url=self.api_url, headers=headers, timeout=5.0) as client:
                    models_resp = client.get("/config/llm/models")
                    if models_resp.status_code == 200:
                        models_data = models_resp.json()
                        new_models = models_data.get("models", [])
                        model_combo.clear()
                        if new_models:
                            for model_info in new_models:
                                name = model_info.get("name", "")
                                size_gb = model_info.get("size_gb", 0)
                                display_text = f"{name} ({size_gb} GB)" if size_gb > 0 else name
                                model_combo.addItem(display_text, name)
                            QMessageBox.information(self, "Models Refreshed", f"✅ Loaded {len(new_models)} model(s)")
                        else:
                            QMessageBox.warning(self, "No Models", "No models found. Make sure Ollama is running.")
            except Exception as e:
                QMessageBox.warning(self, "Refresh Failed", f"Failed to refresh models: {str(e)}")
        refresh_btn.clicked.connect(refresh_models)
        llm_layout.addRow("", refresh_btn)

        url_input = QLineEdit()
        url_input.setText(current_url)
        llm_layout.addRow("Ollama URL:", url_input)

        test_btn = QBtn("Test Connection")
        test_btn.clicked.connect(
            lambda: self.test_ollama_connection(url_input.text(), model_combo.currentData() or model_combo.currentText())
        )
        llm_layout.addRow("", test_btn)
        
        # Test Context Window button
        test_ctx_btn = QBtn("🧪 Test Context Window")
        test_ctx_btn.clicked.connect(
            lambda: self.test_context_window(
                model_combo.currentData() or model_combo.currentText(),
                url_input.text(),
                context_combo.currentData()
            )
        )
        llm_layout.addRow("", test_ctx_btn)

        tabs.addTab(llm_tab, "🤖 LLM Settings")

        # Buttons
        btn_layout = QHBoxLayout()
        ok_btn = QBtn("OK")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn = QBtn("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        dialog_layout.addLayout(btn_layout)

        if dialog.exec():
            # Get model name from dropdown (data if available, else text)
            model = model_combo.currentData()
            if not model:
                model = model_combo.currentText().strip()
            url = url_input.text().strip()
            context_window = context_combo.currentData()
            if model:
                try:
                    headers = {}
                    api_key = os.getenv("CODEXA_API_KEY")
                    if api_key:
                        headers["X-API-Key"] = api_key
                    with httpx.Client(base_url=self.api_url, headers=headers, timeout=10.0) as client:
                        payload = {"model": model}
                        if url:
                            payload["base_url"] = url
                        if context_window:
                            payload["context_window"] = context_window
                        resp = client.post("/config/llm", json=payload)
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("available"):
                                context_info = ""
                                if "context_window" in data:
                                    context_info = f"\n\nContext Window: {data['context_window']} tokens"
                                    if "detected_context_window" in data and data["detected_context_window"]:
                                        if data["detected_context_window"] != data["context_window"]:
                                            context_info += f"\n⚠️ Detected Ollama: {data['detected_context_window']} (mismatch!)"
                                        else:
                                            context_info += f"\n✅ Detected Ollama: {data['detected_context_window']} (matches)"
                                    if "memory_estimate_gb" in data:
                                        context_info += f"\n💾 Estimated RAM: ~{data['memory_estimate_gb']} GB"
                                    if "warning" in data:
                                        context_info += f"\n\n⚠️ {data['warning']}"
                                    if "note" in data:
                                        context_info += f"\n\n{data['note']}"
                                    if "smart_recommendation" in data:
                                        rec = data["smart_recommendation"]
                                        context_info += f"\n\n💡 Smart Recommendation: {rec.get('reason', '')}"
                                QMessageBox.information(
                                    self, "Settings Updated",
                                    f"✅ LLM configuration updated successfully!{context_info}"
                                )
                            else:
                                QMessageBox.warning(
                                    self,
                                    "Settings Updated",
                                    "⚠️ Configuration saved, but LLM is not available.\n\n"
                                    f"Make sure Ollama is running: ollama serve\n"
                                    f"Install model: ollama pull {model}",
                                )
                except httpx.ConnectError:
                    QMessageBox.warning(
                        self, "API Not Available", "⚠️ API server is not running."
                    )
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to update settings:\n{str(e)}")

    def test_context_window(self, model: str, url: str, context_window: int) -> None:
        """Test context window configuration."""
        try:
            headers = {}
            api_key = os.getenv("CODEXA_API_KEY")
            if api_key:
                headers["X-API-Key"] = api_key
            
            with httpx.Client(base_url=self.api_url, headers=headers, timeout=30.0) as client:
                payload = {
                    "model": model,
                    "base_url": url or None,
                    "context_window": context_window,
                }
                resp = client.post("/config/llm/test", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("validated"):
                        msg = f"✅ Context window test passed!\n\n"
                        msg += f"Model: {data.get('model')}\n"
                        msg += f"Context Window: {data.get('context_window')} tokens\n"
                        if data.get("detected_context_window"):
                            if data["detected_context_window"] == data["context_window"]:
                                msg += f"✅ Detected Ollama: {data['detected_context_window']} (matches)\n"
                            else:
                                msg += f"⚠️ Detected Ollama: {data['detected_context_window']} (mismatch!)\n"
                        if "test_stats" in data:
                            stats = data["test_stats"]
                            msg += f"\nTest Results:\n"
                            msg += f"  Usage: {stats.get('context_usage_percent', 0):.1f}%\n"
                            msg += f"  Tokens: {stats.get('total_tokens', 0):,}\n"
                        QMessageBox.information(self, "Context Window Test", msg)
                    else:
                        QMessageBox.warning(
                            self, "Context Window Test Failed",
                            f"❌ Test failed: {data.get('message', 'Unknown error')}"
                        )
                else:
                    QMessageBox.warning(
                        self, "Test Failed",
                        f"API error: {resp.status_code}\n{resp.text[:200]}"
                    )
        except Exception as e:
            QMessageBox.critical(self, "Test Error", f"Failed to test context window:\n{str(e)}")
    
    def test_ollama_connection(self, base_url: str, model: str) -> None:
        """Test Ollama connection."""
        try:
            import httpx
            with httpx.Client(base_url=base_url.rstrip("/"), timeout=5.0) as client:
                resp = client.get("/api/tags")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
                    model_names = [m.get("name", "") for m in models]
                    
                    # Check for exact match or with :latest
                    found = False
                    resolved_model = model
                    if model in model_names:
                        found = True
                    elif f"{model}:latest" in model_names:
                        found = True
                        resolved_model = f"{model}:latest"
                    else:
                        # Check if base name matches
                        base_name = model.split(":")[0]
                        for name in model_names:
                            if name.startswith(f"{base_name}:"):
                                found = True
                                resolved_model = name
                                break
                    
                    if found:
                        if resolved_model != model:
                            QMessageBox.information(
                                self,
                                "Connection Test",
                                f"✅ Connected!\n\n"
                                f"Model '{model}' resolved to '{resolved_model}'.\n"
                                f"This model is available and will be used."
                            )
                        else:
                            QMessageBox.information(
                                self, "Connection Test", f"✅ Connected!\nModel '{model}' is available."
                            )
                    else:
                        QMessageBox.warning(
                            self,
                            "Connection Test",
                            f"⚠️ Connected, but model '{model}' not found.\n\n"
                            f"Available models: {', '.join(model_names[:5])}\n\n"
                            f"Install with: ollama pull {model}\n\n"
                            f"Note: Ollama stores models with tags (e.g., llama3.2:latest). "
                            f"Codexa will automatically resolve this."
                        )
                else:
                    QMessageBox.warning(self, "Connection Test", f"❌ Error: {resp.status_code}")
        except Exception as e:
            QMessageBox.critical(
                self,
                "Connection Test",
                f"❌ Failed to connect:\n{str(e)}\n\nMake sure Ollama is running: ollama serve",
            )
    
    def show_indexed_documents(self) -> None:
        """Switch to indexed documents view and load documents."""
        self.content_stack.setCurrentIndex(2)
        self.load_indexed_documents()
    
    def on_content_stack_changed(self, index: int) -> None:
        """Handle content stack page change."""
        if index == 2:  # Indexed documents page
            self.load_indexed_documents()
    
    def load_indexed_documents(self) -> None:
        """Load and display indexed documents."""
        self.statusBar().showMessage("Loading indexed documents...")
        self.documents_list.clear()
        self.document_detail.clear()
        self.documents_data = []
        
        try:
            headers = {}
            api_key = os.getenv("CODEXA_API_KEY")
            if api_key:
                headers["X-API-Key"] = api_key
            
            # Use current project
            project = self.current_project if self.current_project else None
            
            with httpx.Client(base_url=self.api_url, headers=headers, timeout=10.0) as client:
                params = {}
                if project:
                    params["project"] = project
                resp = client.get("/documents", params=params)
                
                if resp.status_code == 200:
                    data = resp.json()
                    documents = data.get("documents", [])
                    self.documents_data = documents
                    
                    # Display documents in list
                    for doc in documents:
                        file_path = doc.get("file_path", "")
                        file_name = doc.get("file_name", os.path.basename(file_path) if file_path else "Unknown")
                        file_type = doc.get("file_type", "")
                        indexed_at = doc.get("indexed_at", "")
                        has_changed = doc.get("has_changed", False)
                        file_exists = doc.get("file_exists", True)
                        
                        # Format date
                        date_str = "Unknown"
                        if indexed_at:
                            try:
                                from datetime import datetime
                                dt = datetime.fromisoformat(indexed_at)
                                date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                            except (ValueError, TypeError):
                                date_str = indexed_at
                        
                        # Create display text
                        status_icon = "⚠️" if has_changed else "✅" if file_exists else "❌"
                        status_text = " (Changed)" if has_changed else "" if file_exists else " (Missing)"
                        
                        display_text = f"{status_icon} {file_name} [{file_type}] - Indexed: {date_str}{status_text}"
                        
                        item = QListWidgetItem(display_text)
                        item.setData(Qt.UserRole, doc)
                        self.documents_list.addItem(item)
                    
                    total = data.get("total", len(documents))
                    self.statusBar().showMessage(f"Loaded {total} indexed document(s)")
                else:
                    self.statusBar().showMessage(f"Failed to load documents: {resp.status_code}")
                    QMessageBox.warning(
                        self,
                        "Error",
                        f"Failed to load indexed documents:\n{resp.text}"
                    )
        except Exception as e:
            self.statusBar().showMessage(f"Error loading documents: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to load indexed documents:\n{str(e)}"
            )
    
    def show_document_detail(self, item: QListWidgetItem) -> None:
        """Show details for selected document."""
        doc = item.data(Qt.UserRole)
        if not doc:
            return
        
        file_path = doc.get("file_path", "")
        file_name = doc.get("file_name", "")
        file_type = doc.get("file_type", "")
        project = doc.get("project", "")
        indexed_at = doc.get("indexed_at", "")
        file_modified = doc.get("file_modified", "")
        has_changed = doc.get("has_changed", False)
        file_exists = doc.get("file_exists", True)
        doc_id = doc.get("id", "")
        
        # Format dates
        indexed_date_str = "Unknown"
        if indexed_at:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(indexed_at)
                indexed_date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                indexed_date_str = indexed_at
        
        modified_date_str = "N/A"
        if file_modified:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(file_modified)
                modified_date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                modified_date_str = file_modified
        
        # Build detail text
        detail_text = f"📄 File: {file_name}\n"
        detail_text += f"📍 Path: {file_path}\n"
        detail_text += f"📦 Project: {project}\n"
        detail_text += f"🏷️  Type: {file_type}\n"
        detail_text += f"🆔 ID: {doc_id[:36]}...\n\n"
        detail_text += f"📅 Indexed: {indexed_date_str}\n"
        detail_text += f"📝 Modified: {modified_date_str}\n"
        detail_text += f"📊 Status: "
        
        if has_changed:
            detail_text += "⚠️ File has changed since indexing (needs reindex)\n"
        elif file_exists:
            detail_text += "✅ File is up to date\n"
        else:
            detail_text += "❌ File not found\n"
        
        self.document_detail.setPlainText(detail_text)
    
    def delete_selected_document(self) -> None:
        """Delete the currently selected document."""
        current_item = self.documents_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Selection", "Please select a document to delete.")
            return
        
        doc = current_item.data(Qt.UserRole)
        if not doc:
            return
        
        file_path = doc.get("file_path", "")
        file_name = doc.get("file_name", "")
        doc_id = doc.get("id", "")
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete indexed document?\n\nFile: {file_name}\nPath: {file_path}\n\nThis will remove the document from the knowledge vault.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                headers = {}
                api_key = os.getenv("CODEXA_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                
                with httpx.Client(base_url=self.api_url, headers=headers, timeout=10.0) as client:
                    resp = client.delete(f"/documents/{doc_id}")
                    
                    if resp.status_code == 204:
                        QMessageBox.information(self, "Deleted", f"✅ Document deleted successfully.")
                        # Reload documents list
                        self.load_indexed_documents()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to delete document: {resp.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete document:\n{str(e)}")
    
    def delete_file_from_index(self, file_path: str) -> None:
        """Delete all documents for a specific file path."""
        abs_file_path = os.path.abspath(file_path)
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete all indexed documents for this file?\n\n{abs_file_path}\n\nThis will remove all documents for this file from the knowledge vault.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                headers = {}
                api_key = os.getenv("CODEXA_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                
                with httpx.Client(base_url=self.api_url, headers=headers, timeout=10.0) as client:
                    resp = client.delete("/documents/file", json={"file_path": abs_file_path})
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        QMessageBox.information(self, "Deleted", f"✅ {data.get('message', 'Deleted')}")
                        # Reload documents list
                        self.load_indexed_documents()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to delete: {resp.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete file:\n{str(e)}")
    
    def delete_directory_from_index(self, directory_path: str, recursive: bool = True) -> None:
        """Delete all documents in a directory."""
        abs_dir_path = os.path.abspath(directory_path)
        recursive_text = "recursively" if recursive else "non-recursively"
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Delete all indexed documents in this directory {recursive_text}?\n\n{abs_dir_path}\n\nThis will remove all documents in this directory from the knowledge vault.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                headers = {}
                api_key = os.getenv("CODEXA_API_KEY")
                if api_key:
                    headers["X-API-Key"] = api_key
                
                with httpx.Client(base_url=self.api_url, headers=headers, timeout=30.0) as client:
                    resp = client.delete(
                        "/documents/directory",
                        json={"directory_path": abs_dir_path, "recursive": recursive}
                    )
                    
                    if resp.status_code == 200:
                        data = resp.json()
                        QMessageBox.information(self, "Deleted", f"✅ {data.get('message', 'Deleted')}")
                        # Reload documents list
                        self.load_indexed_documents()
                    else:
                        QMessageBox.warning(self, "Error", f"Failed to delete: {resp.status_code}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete directory:\n{str(e)}")


def main() -> None:
    """Run the desktop application."""
    app = QApplication(sys.argv)
    window = CodexaDesktop()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
