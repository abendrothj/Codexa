"""Codexa Desktop GUI application."""

import sys
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
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import httpx


class SearchWorker(QThread):
    """Worker thread for performing searches."""

    search_completed = Signal(dict)
    search_failed = Signal(str)

    def __init__(self, query: str, top_k: int = 10, api_url: str = "http://localhost:8000") -> None:
        """Initialize search worker."""
        super().__init__()
        self.query = query
        self.top_k = top_k
        self.api_url = api_url

    def run(self) -> None:
        """Execute search in background thread."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.api_url}/search",
                    json={"query": self.query, "top_k": self.top_k},
                )
                response.raise_for_status()
                self.search_completed.emit(response.json())
        except Exception as e:
            self.search_failed.emit(str(e))


class IndexWorker(QThread):
    """Worker thread for indexing files."""

    index_completed = Signal(dict)
    index_failed = Signal(str)

    def __init__(
        self, file_paths: List[str], encrypt: bool = False, api_url: str = "http://localhost:8000"
    ) -> None:
        """Initialize index worker."""
        super().__init__()
        self.file_paths = file_paths
        self.encrypt = encrypt
        self.api_url = api_url

    def run(self) -> None:
        """Execute indexing in background thread."""
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.post(
                    f"{self.api_url}/index",
                    json={"file_paths": self.file_paths, "encrypt": self.encrypt},
                )
                response.raise_for_status()
                self.index_completed.emit(response.json())
        except Exception as e:
            self.index_failed.emit(str(e))


class CodexaDesktop(QMainWindow):
    """Main desktop application window."""

    def __init__(self) -> None:
        """Initialize the desktop application."""
        super().__init__()
        self.api_url = "http://localhost:8000"
        self.current_worker: Optional[QThread] = None
        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle("Codexa - AI Dev Knowledge Vault")
        self.setMinimumSize(1000, 700)

        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Codexa Knowledge Vault")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Index section
        index_layout = QHBoxLayout()
        index_btn = QPushButton("Index Files")
        index_btn.clicked.connect(self.index_files)
        index_layout.addWidget(QLabel("Actions:"))
        index_layout.addWidget(index_btn)
        index_layout.addStretch()
        layout.addLayout(index_layout)

        # Search input section
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter your search query...")
        self.search_input.returnPressed.connect(self.perform_search)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.perform_search)
        self.search_button.setMinimumWidth(100)

        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input, stretch=1)
        search_layout.addWidget(self.search_button)
        layout.addLayout(search_layout)

        # Results section
        results_label = QLabel("Search Results:")
        results_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(results_label)

        # Splitter for results list and detail view
        splitter = QSplitter(Qt.Horizontal)

        # Results list
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_result_detail)
        splitter.addWidget(self.results_list)

        # Result detail view
        self.result_detail = QTextEdit()
        self.result_detail.setReadOnly(True)
        splitter.addWidget(self.result_detail)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        layout.addWidget(splitter, stretch=1)

        # Status bar
        self.statusBar().showMessage("Ready")

        # Store results data
        self.results_data: List[dict] = []

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

        self.statusBar().showMessage(f"Indexing {len(file_paths)} files...")
        self.search_button.setEnabled(False)

        # Start indexing in background thread
        self.current_worker = IndexWorker(file_paths, encrypt=False, api_url=self.api_url)
        self.current_worker.index_completed.connect(self.on_index_completed)
        self.current_worker.index_failed.connect(self.on_index_failed)
        self.current_worker.start()

    def on_index_completed(self, result: dict) -> None:
        """Handle index completion."""
        self.search_button.setEnabled(True)
        indexed = result.get("indexed_count", 0)
        failed = result.get("failed_count", 0)
        message = f"Indexed {indexed} files"
        if failed > 0:
            message += f", {failed} failed"
        self.statusBar().showMessage(message)
        QMessageBox.information(self, "Indexing Complete", message)

    def on_index_failed(self, error: str) -> None:
        """Handle index failure."""
        self.search_button.setEnabled(True)
        self.statusBar().showMessage("Indexing failed")
        QMessageBox.critical(self, "Indexing Error", f"Failed to index files:\n{error}")

    def perform_search(self) -> None:
        """Perform semantic search."""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Empty Query", "Please enter a search query.")
            return

        self.statusBar().showMessage(f"Searching for: {query}")
        self.search_button.setEnabled(False)
        self.results_list.clear()
        self.result_detail.clear()

        # Start search in background thread
        self.current_worker = SearchWorker(query, top_k=20, api_url=self.api_url)
        self.current_worker.search_completed.connect(self.on_search_completed)
        self.current_worker.search_failed.connect(self.on_search_failed)
        self.current_worker.start()

    def on_search_completed(self, result: dict) -> None:
        """Handle search completion."""
        self.search_button.setEnabled(True)
        results = result.get("results", [])
        self.results_data = results

        if not results:
            self.statusBar().showMessage("No results found")
            self.result_detail.setPlainText("No results found for your query.")
            return

        # Populate results list
        for idx, res in enumerate(results):
            file_path = res.get("file_path", "Unknown")
            score = res.get("score", 0.0)
            item_text = f"{idx + 1}. {file_path} (Score: {score:.3f})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, idx)
            self.results_list.addItem(item)

        self.statusBar().showMessage(f"Found {len(results)} results")

        # Auto-select first result
        if self.results_list.count() > 0:
            self.results_list.setCurrentRow(0)
            self.show_result_detail(self.results_list.item(0))

    def on_search_failed(self, error: str) -> None:
        """Handle search failure."""
        self.search_button.setEnabled(True)
        self.statusBar().showMessage("Search failed")
        QMessageBox.critical(self, "Search Error", f"Failed to perform search:\n{error}")

    def show_result_detail(self, item: QListWidgetItem) -> None:
        """Display details of selected result."""
        idx = item.data(Qt.UserRole)
        if idx is None or idx >= len(self.results_data):
            return

        result = self.results_data[idx]
        detail_text = f"File: {result.get('file_path', 'Unknown')}\n"
        detail_text += f"Type: {result.get('file_type', 'Unknown')}\n"
        detail_text += f"Score: {result.get('score', 0.0):.4f}\n"
        detail_text += f"\n{'=' * 60}\n\n"
        detail_text += result.get("content", "No content available")

        self.result_detail.setPlainText(detail_text)


def main() -> None:
    """Run the desktop application."""
    app = QApplication(sys.argv)
    window = CodexaDesktop()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
