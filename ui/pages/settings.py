"""Settings page – general + integrations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

if TYPE_CHECKING:
    from core.application import DevDeskApplication


class SettingsPage(QWidget):
    def __init__(self, app: "DevDeskApplication", parent=None) -> None:
        super().__init__(parent)
        self._app = app
        self._build()
        self._load()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        layout.addWidget(title)

        tabs = QTabWidget()
        tabs.addTab(self._build_general(), "General")
        tabs.addTab(self._build_jira(), "Jira")
        tabs.addTab(self._build_github(), "GitHub")
        tabs.addTab(self._build_bitbucket(), "Bitbucket")
        tabs.addTab(self._build_working_time(), "Working Time")
        layout.addWidget(tabs, stretch=1)

        row = QHBoxLayout()
        self.btn_save = QPushButton("Save All")
        self.btn_save.clicked.connect(self._save)
        row.addWidget(self.btn_save)
        row.addStretch()
        layout.addLayout(row)

    def _build_general(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_start_minimized = QCheckBox("Start minimized to tray")
        form.addRow(self.chk_start_minimized)
        self.chk_minimize_on_close = QCheckBox("Minimize to tray on close")
        form.addRow(self.chk_minimize_on_close)
        self.cmb_theme = QComboBox()
        self.cmb_theme.addItems(["System", "Light", "Dark"])
        form.addRow("Theme", self.cmb_theme)
        self.chk_notifications = QCheckBox("Enable notifications")
        form.addRow(self.chk_notifications)
        return w

    def _build_jira(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_jira = QCheckBox("Enable Jira integration")
        form.addRow(self.chk_jira)
        self.jira_url = QLineEdit()
        self.jira_url.setPlaceholderText("https://your-domain.atlassian.net")
        form.addRow("Base URL", self.jira_url)
        self.jira_email = QLineEdit()
        form.addRow("Email", self.jira_email)
        self.jira_token = QLineEdit()
        self.jira_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.jira_token.setPlaceholderText("API token (stored in keyring)")
        form.addRow("API Token", self.jira_token)
        self.jira_jql = QTextEdit()
        self.jira_jql.setMaximumHeight(70)
        self.jira_jql.setPlaceholderText("assignee = currentUser() AND resolution = Unresolved …")
        form.addRow("JQL", self.jira_jql)
        self.jira_interval = QSpinBox()
        self.jira_interval.setRange(1, 60)
        self.jira_interval.setSuffix(" min")
        form.addRow("Sync interval", self.jira_interval)
        btn = QPushButton("Test Connection")
        btn.setObjectName("secondary")
        btn.clicked.connect(self._test_jira)
        form.addRow(btn)
        return w

    def _build_github(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_github = QCheckBox("Enable GitHub integration")
        form.addRow(self.chk_github)
        self.gh_token = QLineEdit()
        self.gh_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.gh_token.setPlaceholderText("Personal Access Token (keyring)")
        form.addRow("PAT", self.gh_token)
        self.gh_interval = QSpinBox()
        self.gh_interval.setRange(1, 60)
        self.gh_interval.setSuffix(" min")
        form.addRow("Sync interval", self.gh_interval)
        btn = QPushButton("Test Connection")
        btn.setObjectName("secondary")
        btn.clicked.connect(self._test_github)
        form.addRow(btn)
        return w

    def _build_bitbucket(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.chk_bitbucket = QCheckBox("Enable Bitbucket integration")
        form.addRow(self.chk_bitbucket)
        self.bb_user = QLineEdit()
        form.addRow("Username", self.bb_user)
        self.bb_token = QLineEdit()
        self.bb_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.bb_token.setPlaceholderText("App password (keyring)")
        form.addRow("App Password", self.bb_token)
        self.bb_workspaces = QLineEdit()
        self.bb_workspaces.setPlaceholderText("workspace1, workspace2")
        form.addRow("Workspaces", self.bb_workspaces)
        self.bb_interval = QSpinBox()
        self.bb_interval.setRange(1, 60)
        self.bb_interval.setSuffix(" min")
        form.addRow("Sync interval", self.bb_interval)
        btn = QPushButton("Test Connection")
        btn.setObjectName("secondary")
        btn.clicked.connect(self._test_bitbucket)
        form.addRow(btn)
        return w

    def _build_working_time(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.wt_target = QSpinBox()
        self.wt_target.setRange(1, 16)
        self.wt_target.setSuffix(" hours")
        form.addRow("Daily target", self.wt_target)
        return w

    def _load(self) -> None:
        cfg = self._app.config
        self.chk_start_minimized.setChecked(cfg.start_minimized)
        self.chk_minimize_on_close.setChecked(cfg.minimize_on_close)
        theme_map = {"system": 0, "light": 1, "dark": 2}
        self.cmb_theme.setCurrentIndex(theme_map.get(cfg.theme, 0))
        self.chk_notifications.setChecked(bool(cfg.get("notifications.enabled", True)))

        self.chk_jira.setChecked(bool(cfg.get("jira.enabled", False)))
        self.jira_url.setText(str(cfg.get("jira.base_url", "")))
        self.jira_email.setText(str(cfg.get("jira.email", "")))
        self.jira_jql.setPlainText(str(cfg.get("jira.jql", "")))
        self.jira_interval.setValue(int(cfg.get("jira.sync_interval_minutes", 5)))
        # Do not load token into UI for security – show placeholder if exists
        if self._app.credentials.get_jira_token():
            self.jira_token.setPlaceholderText("•••••••• (saved in keyring)")

        self.chk_github.setChecked(bool(cfg.get("github.enabled", False)))
        self.gh_interval.setValue(int(cfg.get("github.sync_interval_minutes", 3)))
        if self._app.credentials.get_github_token("default"):
            self.gh_token.setPlaceholderText("•••••••• (saved in keyring)")

        self.chk_bitbucket.setChecked(bool(cfg.get("bitbucket.enabled", False)))
        self.bb_user.setText(str(cfg.get("bitbucket.username", "")))
        workspaces = cfg.get("bitbucket.workspaces", []) or []
        self.bb_workspaces.setText(", ".join(workspaces) if isinstance(workspaces, list) else str(workspaces))
        self.bb_interval.setValue(int(cfg.get("bitbucket.sync_interval_minutes", 3)))
        if self._app.credentials.get_bitbucket_token():
            self.bb_token.setPlaceholderText("•••••••• (saved in keyring)")

        self.wt_target.setValue(int(cfg.get("working_time.daily_target_hours", 8)))

    def _save(self) -> None:
        cfg = self._app.config
        cfg.start_minimized = self.chk_start_minimized.isChecked()
        cfg.minimize_on_close = self.chk_minimize_on_close.isChecked()
        themes = ["system", "light", "dark"]
        cfg.theme = themes[self.cmb_theme.currentIndex()]
        cfg.set("notifications.enabled", self.chk_notifications.isChecked())

        cfg.set("jira.enabled", self.chk_jira.isChecked())
        cfg.set("jira.base_url", self.jira_url.text().strip())
        cfg.set("jira.email", self.jira_email.text().strip())
        jql = self.jira_jql.toPlainText().strip()
        if jql:
            cfg.set("jira.jql", jql)
        cfg.set("jira.sync_interval_minutes", self.jira_interval.value())
        token = self.jira_token.text().strip()
        if token:
            self._app.credentials.set_jira_token(token)
            self.jira_token.clear()
            self.jira_token.setPlaceholderText("•••••••• (saved in keyring)")

        cfg.set("github.enabled", self.chk_github.isChecked())
        cfg.set("github.sync_interval_minutes", self.gh_interval.value())
        gh_token = self.gh_token.text().strip()
        if gh_token:
            self._app.credentials.set_github_token("default", gh_token)
            # Also store account list for sync
            cfg.set("github.accounts", [{"name": "default"}])
            self.gh_token.clear()
            self.gh_token.setPlaceholderText("•••••••• (saved in keyring)")

        cfg.set("bitbucket.enabled", self.chk_bitbucket.isChecked())
        cfg.set("bitbucket.username", self.bb_user.text().strip())
        ws = [w.strip() for w in self.bb_workspaces.text().split(",") if w.strip()]
        cfg.set("bitbucket.workspaces", ws)
        cfg.set("bitbucket.sync_interval_minutes", self.bb_interval.value())
        bb_token = self.bb_token.text().strip()
        if bb_token:
            self._app.credentials.set_bitbucket_token(bb_token)
            self.bb_token.clear()
            self.bb_token.setPlaceholderText("•••••••• (saved in keyring)")

        cfg.set("working_time.daily_target_hours", float(self.wt_target.value()))
        cfg.save()

        from ui.styles import get_stylesheet
        if self._app.main_window:
            self._app.main_window.setStyleSheet(get_stylesheet(cfg.theme))

        if hasattr(self._app, "sync_service") and self._app.sync_service:
            self._app.sync_service.refresh_intervals()

        QMessageBox.information(self, "Settings", "Settings saved.")

    def _test_jira(self) -> None:
        from integrations.jira import JiraClient
        from integrations.base import IntegrationError

        url = self.jira_url.text().strip() or self._app.config.get("jira.base_url", "")
        email = self.jira_email.text().strip() or self._app.config.get("jira.email", "")
        token = self.jira_token.text().strip() or self._app.credentials.get_jira_token()
        if not all([url, email, token]):
            QMessageBox.warning(self, "Jira", "URL, email and token are required.")
            return
        try:
            client = JiraClient(url, email, token)
            info = client.test_connection()
            client.close()
            QMessageBox.information(
                self, "Jira", f"Connected as {info.get('display_name')} ({info.get('email')})"
            )
        except IntegrationError as exc:
            QMessageBox.critical(self, "Jira", f"Connection failed:\n{exc}")

    def _test_github(self) -> None:
        from integrations.github import GitHubClient
        from integrations.base import IntegrationError

        token = self.gh_token.text().strip() or self._app.credentials.get_github_token("default")
        if not token:
            QMessageBox.warning(self, "GitHub", "Token is required.")
            return
        try:
            client = GitHubClient(token)
            info = client.test_connection()
            client.close()
            QMessageBox.information(self, "GitHub", f"Connected as {info.get('login')}")
        except IntegrationError as exc:
            QMessageBox.critical(self, "GitHub", f"Connection failed:\n{exc}")

    def _test_bitbucket(self) -> None:
        from integrations.bitbucket import BitbucketClient
        from integrations.base import IntegrationError

        user = self.bb_user.text().strip() or self._app.config.get("bitbucket.username", "")
        token = self.bb_token.text().strip() or self._app.credentials.get_bitbucket_token()
        if not user or not token:
            QMessageBox.warning(self, "Bitbucket", "Username and app password are required.")
            return
        try:
            client = BitbucketClient(user, token)
            info = client.test_connection()
            client.close()
            QMessageBox.information(
                self, "Bitbucket", f"Connected as {info.get('display_name') or info.get('username')}"
            )
        except IntegrationError as exc:
            QMessageBox.critical(self, "Bitbucket", f"Connection failed:\n{exc}")
