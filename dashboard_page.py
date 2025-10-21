from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton, QWidget, QHBoxLayout, QMessageBox, QMainWindow, QGridLayout, QScrollArea, QSizePolicy
from PySide6.QtCore import Qt, Signal
import os
from PySide6.QtGui import QPixmap
from styled_widget import StyledWidget
from loading_widget import LoadingSpinner, LoadingOverlay
from app_config import list_all_apps, get_app_metadata
from launcher_for_all_files import launch_with_animation
from referral_details_window import ReferralDetailsWindow
from workers import ReferralSyncWorker
from utils import debug_log

class DashboardPage(StyledWidget):
    logout = Signal()

    def __init__(self):
        super().__init__()
        self.profile = {}
        self._id_token = None
        self._local_id = None
        self.loading_overlay = None
        # legacy workers removed
        self.referral_sync_worker = None
        self.init_ui()
        self.setup_loading_overlay()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        # Header
        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title = QLabel("Dashboard")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setMinimumHeight(40)
        logout_btn.clicked.connect(lambda: self.logout.emit())
        header_layout.addWidget(logout_btn)

        layout.addWidget(header)

        # User info container
        user_info_container = QWidget()
        user_info_container.setStyleSheet("""
            QWidget {
                background-color: #3E3E42;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        user_info_layout = QVBoxLayout(user_info_container)

        # User info labels
        self.email_label = QLabel("")
        self.email_label.setStyleSheet("font-size: 14px;")
        user_info_layout.addWidget(self.email_label)

        self.username_label = QLabel("")
        self.username_label.setStyleSheet("font-size: 14px;")
        user_info_layout.addWidget(self.username_label)

        self.membership_label = QLabel("")
        self.membership_label.setStyleSheet("font-size: 14px;")
        user_info_layout.addWidget(self.membership_label)

        # Membership time remaining label
        self.membership_time_label = QLabel("")
        self.membership_time_label.setStyleSheet("font-size: 14px; color: #FF9800;")
        user_info_layout.addWidget(self.membership_time_label)

        # Referral information display removed to avoid attribute errors

        # Referral details button
        self.referral_btn = QPushButton("View Referral Details")
        self.referral_btn.setMinimumHeight(35)
        self.referral_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                margin: 5px 0;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
        """)
        self.referral_btn.clicked.connect(self.open_referral_details)
        user_info_layout.addWidget(self.referral_btn)

        layout.addWidget(user_info_container)

        # Apps section title
        apps_title = QLabel("Available Applications")
        apps_title.setStyleSheet("font-size: 18px; font-weight: bold; margin-top: 10px; margin-bottom: 15px;")
        layout.addWidget(apps_title)

        # Create scrollable area for apps
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #2D2D30;
                width: 12px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #4E4E52;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #5E5E62;
            }
        """)

        # Create scrollable content widget
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 0, 0, 0)

        # Apps grid with horizontal layout
        grid = QVBoxLayout()
        grid.setSpacing(5)  # Minimal spacing between rows
        
        # Build app entries from central app_config
        try:
            apps_catalog = list_all_apps()
        except Exception:
            apps_catalog = {"local": {}, "github": {}}
        app_entries = []
        for _name, _path in (apps_catalog.get("local") or {}).items():
            app_entries.append((_name, _path, True))
        for _name, _url in (apps_catalog.get("github") or {}).items():
            app_entries.append((_name, _url, False))

        for name, url_or_path, is_local in app_entries:
            cell_widget = QWidget()
            cell_widget.setFixedHeight(100)  # Increased height to accommodate larger images
            cell_widget.setStyleSheet("""
                QWidget {
                    background-color: #3E3E42;
                    border-radius: 8px;
                    padding: 8px;
                    margin: 2px;
                }
                QWidget:hover {
                    background-color: #4E4E52;
                    border: 2px solid #2196F3;
                }
            """)
            
            # Horizontal layout for each app
            cell_layout = QHBoxLayout(cell_widget)
            cell_layout.setContentsMargins(10, 5, 10, 5)
            cell_layout.setSpacing(15)  # Minimal spacing between elements

            # App icon - Left side, larger
            img_label = QLabel()
            img_label.setFixedSize(130, 100)  # Increased from 60x60 to 80x80
            
            # Load icon if available from metadata
            def _get_app_icon_pixmap(app_name: str):
                try:
                    meta = get_app_metadata(app_name) or {}
                    icon_rel = meta.get("icon")
                    if icon_rel:
                        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        icon_path = os.path.join(base_dir, icon_rel)
                        if os.path.exists(icon_path):
                            return QPixmap(icon_path)
                except Exception:
                    pass
                return QPixmap()

            pix = _get_app_icon_pixmap(name)
            
            if not pix.isNull():
                img_label.setPixmap(pix.scaled(130, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                img_label.setText("[No Image]")
                img_label.setAlignment(Qt.AlignCenter)
                img_label.setStyleSheet("font-size: 14px; color: #CCCCCC;")
            cell_layout.addWidget(img_label)

            # App name - Center, takes remaining space
            name_label = QLabel(name)
            name_label.setAlignment(Qt.AlignCenter)
            name_label.setStyleSheet("font-weight: bold; font-size: 16px; color: white;")
            name_label.setWordWrap(True)
            name_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            cell_layout.addWidget(name_label)

            # Launch button - Right side, larger
            btn = QPushButton("Launch")
            btn.setFixedSize(120, 50)  # Fixed size for consistency
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """)
            btn.clicked.connect(lambda checked, n=name, u=url_or_path, l=is_local: self.on_app_clicked(n, u, l))
            cell_layout.addWidget(btn)

            grid.addWidget(cell_widget)

        scroll_layout.addLayout(grid)
        scroll_layout.addStretch()  # Add stretch to push content to top
        
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)
        layout.addStretch()
        self.setLayout(layout)

    def setup_loading_overlay(self):
        """Set up the loading overlay for this page"""
        self.loading_overlay = LoadingOverlay(self, "Processing...")
        
    def resizeEvent(self, event):
        """Handle resize events to properly position loading overlay"""
        super().resizeEvent(event)
        if self.loading_overlay:
            self.loading_overlay.resize(self.size())

    def on_app_clicked(self, name: str, url_or_path: str, is_local: bool):
        """Native app launch via universal launcher."""
        username = self.profile.get("username", "guest")
        
        # Disable main app UI during launch
        self.setEnabled(False)
        
        try:
            # Start loading overlay
            if self.loading_overlay:
                self.loading_overlay.show_loading(f"Launching {name}...")
            
            # Try universal launcher for local apps
            if url_or_path and is_local:
                # window title from metadata if present
                meta = get_app_metadata(name) or {}
                title = meta.get("window_title")
                launch_with_animation(name, url_or_path, window_title=title, parent=self, timeout_seconds=60)
            else:
                # GitHub apps: download then launch
                meta = get_app_metadata(name) or {}
                title = meta.get("window_title")
                from app_config import get_github_app_url
                url = get_github_app_url(name)
                if url:
                    from launcher_for_all_files import download_and_launch_with_animation
                    download_and_launch_with_animation(name, url, window_title=title, parent=self, timeout_seconds=60)
                else:
                    QMessageBox.information(self, "Launch Unavailable", f"'{name}' has no configured URL.")
            
            # Re-enable main app UI after successful launch
            self.setEnabled(True)
            
            # Hide loading overlay after successful launch
            if self.loading_overlay:
                self.loading_overlay.hide_loading()
                
        except Exception as e:
            # Re-enable main app UI on error
            self.setEnabled(True)
            # Hide loading overlay on error
            if self.loading_overlay:
                self.loading_overlay.hide_loading()
            QMessageBox.critical(self, "Launch Error", f"Failed to launch {name}: {e}")
    
    def on_launch_started(self, app_name: str):
        """Handle when app launch starts"""
        if self.loading_overlay:
            self.loading_overlay.show_loading(f"Launching {app_name}...")
    
    def on_download_progress(self, message: str):
        """Handle download progress updates"""
        if self.loading_overlay:
            self.loading_overlay.show_loading(message)
    
    def on_gui_detected(self):
        """Handle when the launched app's GUI window is detected"""
        # Re-enable main app UI when GUI is detected
        self.setEnabled(True)
        
        # Hide loading overlay
        if self.loading_overlay:
            self.loading_overlay.hide_loading()
    
    def on_launch_completed(self, success: bool, message: str):
        """Handle when app launch is completed"""
        # Re-enable main app UI
        self.setEnabled(True)
        
        if self.loading_overlay:
            self.loading_overlay.hide_loading()
        
        # Only show error messages, not success messages
        if not success:
            QMessageBox.critical(self, "Launch Failed", message)
        else:
            pass

    def cleanup_workers(self):
        """Clean up any running workers"""
        # legacy workers removed; nothing to cleanup here
        
        if self.referral_sync_worker:
            self.referral_sync_worker = None
    
    def closeEvent(self, event):
        """Handle close event to cleanup workers"""
        self.cleanup_workers()
        super().closeEvent(event)

    def set_profile(self, id_token: str, local_id: str, profile: dict):
        self._id_token = id_token
        self._local_id = local_id
        self.profile = profile or {}
        email = self.profile.get("email", "")
        username = self.profile.get("username", "")
        membership = self.profile.get("membership", False)
        membership_expires = self.profile.get("membership_expires", "")

        self.email_label.setText(f"Email: {email}")
        self.username_label.setText(f"Username: {username}")
        self.membership_label.setText(f"Membership: {'Active' if membership else 'Inactive'}")

        # Referral info removed from dashboard UI

        # Calculate and display membership time remaining
        if membership and membership_expires:
            try:
                from datetime import datetime
                expires_date = datetime.fromisoformat(membership_expires.replace('Z', '+00:00'))
                current_date = datetime.now(expires_date.tzinfo)
                time_remaining = expires_date - current_date

                if time_remaining.days > 0:
                    self.membership_time_label.setText(f"Membership expires in: {time_remaining.days} days")
                elif time_remaining.total_seconds() > 0:
                    hours = int(time_remaining.total_seconds() // 3600)
                    self.membership_time_label.setText(f"Membership expires in: {hours} hours")
                else:
                    self.membership_time_label.setText("Membership expired")
            except:
                self.membership_time_label.setText("Membership time: Unknown")
        else:
            self.membership_time_label.setText("No active membership")

    def open_referral_details(self):
        """Open the referral details window with referral sync and loading indicators."""
        try:
            if not self._id_token or not self._local_id:
                QMessageBox.warning(self, "Error", "User authentication required.")
                return
            
            # Show loading while syncing referral data
            if self.loading_overlay:
                self.loading_overlay.show_loading("Syncing referral data...")
            
            # Disable the referral button during loading
            self.referral_btn.setEnabled(False)
            
            debug_log(f"Starting referral sync for user: {self._local_id}, username: {self.profile.get('username', 'Unknown')}")
            
            # Start referral sync worker first
            self.referral_sync_worker = ReferralSyncWorker(self._id_token, self._local_id)
            self.referral_sync_worker.progress.connect(self.on_referral_sync_progress)
            self.referral_sync_worker.finished.connect(self.on_referral_sync_completed)
            self.referral_sync_worker.start()
            
        except Exception as e:
            # Hide loading and re-enable button on error
            if self.loading_overlay:
                self.loading_overlay.hide_loading()
            self.referral_btn.setEnabled(True)
            
            debug_log(f"Exception in open_referral_details: {e}")
            QMessageBox.critical(self, "Error", f"Failed to start referral sync: {e}")
    
    def on_referral_sync_progress(self, message: str):
        """Handle referral sync progress updates"""
        if self.loading_overlay:
            self.loading_overlay.show_loading(f"Syncing referral data... {message}")
    
    def on_referral_sync_completed(self, success: bool, result: dict):
        """Handle referral sync completion"""
        try:
            if not success:
                debug_log(f"Referral sync failed: {result}")
                # Still show referral details even if sync failed
            else:
                debug_log(f"Referral sync completed successfully: {result}")
                # Update current user data with sync results
                if hasattr(self, 'parent') and hasattr(self.parent(), 'current_user'):
                    main_window = self.parent()
                    while main_window and not hasattr(main_window, 'current_user'):
                        main_window = main_window.parent()
                    if main_window and hasattr(main_window, 'current_user'):
                        try:
                            if isinstance(result, dict) and result.get("results"):
                                main_window.current_user.update(result.get("results"))
                        except Exception as e:
                            debug_log(f"Failed to update current_user with sync results: {e}")
            
            # Now open the referral details window
            if self.loading_overlay:
                self.loading_overlay.show_loading("Loading referral details...")
            
            username = self.profile.get("username", "Unknown")
            referral_window = ReferralDetailsWindow(self._id_token, self._local_id, username, self)
            
            # Connect to window's finished signal to hide loading
            referral_window.finished.connect(self.on_referral_details_closed)
            
            referral_window.show()
            
        except Exception as e:
            # Hide loading and re-enable button on error
            if self.loading_overlay:
                self.loading_overlay.hide_loading()
            self.referral_btn.setEnabled(True)
            
            debug_log(f"Exception in on_referral_sync_completed: {e}")
            QMessageBox.critical(self, "Error", f"Failed to open referral details: {e}")
    
    def on_referral_details_closed(self):
        """Handle when referral details window is closed"""
        if self.loading_overlay:
            self.loading_overlay.hide_loading()
        self.referral_btn.setEnabled(True)
