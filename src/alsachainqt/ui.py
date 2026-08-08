"""Button-first desktop UI. No keyboard shortcuts perform application actions."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QScrollArea, QSlider, QSpinBox, QMenu, QVBoxLayout, QWidget, QStyle,
)

from .asound import CROSSFEED
from .models import Profile, Stage
from .service import ALSAChainService
from .equalizer import slider_limit, slider_to_value, value_to_db, value_to_slider

BUTTON_ROLE_STYLES = {
    "primary": "QPushButton { color: white; background: #2563eb; border-color: #1d4ed8; } QPushButton:hover { background: #1d4ed8; border-color: #1e40af; }",
    "info": "QPushButton { color: white; background: #0f766e; border-color: #115e59; } QPushButton:hover { background: #115e59; border-color: #134e4a; }",
    "dsp": "QPushButton { color: white; background: #7c3aed; border-color: #6d28d9; } QPushButton:hover { background: #6d28d9; border-color: #5b21b6; }",
    "mode": "QPushButton { color: white; background: #b45309; border-color: #92400e; } QPushButton:hover { background: #92400e; border-color: #78350f; }",
    "danger": "QPushButton { color: white; background: #b42318; border-color: #8f1d14; } QPushButton:hover { background: #8f1d14; border-color: #751a12; }",
}


class ProfileCard(QFrame):
    clicked = Signal()
    double_clicked = Signal()

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class AboutDialog(QDialog):
    def __init__(self, icon: QIcon, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("About ALSAChainQT")
        self.setMinimumWidth(460)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(16)
        header = QHBoxLayout()
        header.setSpacing(16)
        icon_label = QLabel(self)
        icon_label.setPixmap(icon.pixmap(64, 64))
        header.addWidget(icon_label)
        details = QVBoxLayout()
        details.setSpacing(4)
        name = QLabel("ALSAChainQT", self)
        name.setObjectName("aboutName")
        details.addWidget(name)
        details.addWidget(QLabel("Version: TBD", self))
        header.addLayout(details)
        header.addStretch()
        layout.addLayout(header)
        description = QLabel("Manage ALSA virtual PCM profiles and DSP chains from a native Qt desktop application.", self)
        description.setWordWrap(True)
        layout.addWidget(description)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


def action_button(parent: QWidget, text: str, icon: QIcon, tooltip: str, callback: object, *, danger: bool = False, role: str = "secondary") -> QPushButton:
    if danger:
        role = "danger"
    button = QPushButton(icon, text, parent)
    # Keep the icon and complete label visible when a horizontal layout is tight.
    button.setMinimumWidth(button.sizeHint().width())
    button.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
    button.setToolTip(tooltip)
    button.setAccessibleName(text)
    button.clicked.connect(callback)
    button.setObjectName(f"{role}Button")
    button.setStyleSheet(BUTTON_ROLE_STYLES.get(role, ""))
    return button


class ProfileDialog(QDialog):
    def __init__(self, service: ALSAChainService, profile: Profile | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.service, self.profile = service, profile
        self.setWindowTitle("Edit output profile" if profile else "New output profile")
        self.setMinimumWidth(520)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.identifier = QLineEdit(profile.id if profile else "", self)
        self.name = QLineEdit(profile.display_name if profile else "", self)
        self.target = QComboBox(self)
        for device in service.devices():
            self.target.addItem(f"{device.card_name} - {device.description}", device.target)
        if profile:
            index = self.target.findData(profile.target)
            self.target.setCurrentIndex(index)
        form.addRow("Identifier", self.identifier)
        form.addRow("Visible name", self.name)
        form.addRow("Playback device", self.target)
        layout.addLayout(form)
        hint = QLabel("Changes apply to new ALSA connections. Restart playback after saving.", self)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save, self)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def save(self) -> None:
        if self.target.currentIndex() < 0:
            QMessageBox.warning(self, "Playback device required", "Select a detected ALSA playback device.")
            return
        try:
            updated = self.service.create_profile(self.identifier.text(), self.name.text(), str(self.target.currentData()))
            if self.profile:
                updated.created_at = self.profile.created_at
                updated.enabled = self.profile.enabled
                updated.bitperfect = self.profile.bitperfect
                updated.stages = self.profile.stages
            self.service.save_profile(updated, self.profile.id if self.profile else None)
        except ValueError as error:
            QMessageBox.critical(self, "Unable to save profile", str(error))
            return
        self.accept()


class DspDialog(QDialog):
    def __init__(self, service: ALSAChainService, profile: Profile, parent: QWidget | None = None):
        super().__init__(parent)
        self.service, self.profile = service, profile
        self.setWindowTitle(f"DSP chain: {profile.display_name}")
        self.setMinimumSize(580, 360)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Hardware -> DSP stages -> Public PCM", self))
        self.stages = QListWidget(self)
        self.stages.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.stages.itemDoubleClicked.connect(self.configure_item)
        layout.addWidget(self.stages)
        actions = QHBoxLayout()
        style = self.style()
        self.add_stage = action_button(self, "Add DSP stage", style.standardIcon(QStyle.StandardPixmap.SP_MediaVolume), "Add a DSP stage", lambda: None, role="dsp")
        menu = QMenu(self.add_stage)
        for label, stage_type in (("Equalizer", "equalizer"), ("Crossfeed", "crossfeed"), ("Gain", "gain")):
            action = QAction(label, menu)
            action.triggered.connect(lambda checked=False, value=stage_type: self.add_and_configure(value))
            menu.addAction(action)
        self.add_stage.setMenu(menu)
        actions.addWidget(self.add_stage)
        actions.addWidget(action_button(self, "Configure", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView), "Configure selected DSP stage", self.configure))
        actions.addWidget(action_button(self, "Move up", style.standardIcon(QStyle.StandardPixmap.SP_ArrowUp), "Move selected stage earlier in the signal chain", lambda: self.move(-1)))
        actions.addWidget(action_button(self, "Move down", style.standardIcon(QStyle.StandardPixmap.SP_ArrowDown), "Move selected stage later in the signal chain", lambda: self.move(1)))
        actions.addStretch()
        actions.addWidget(action_button(self, "Remove", style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Remove selected DSP stage", self.remove, danger=True))
        layout.addLayout(actions)
        self.refresh()

    def refresh(self, selected_stage_id: str | None = None, fallback_row: int = 0) -> None:
        if selected_stage_id is None and (current := self.stages.currentItem()):
            selected_stage_id = str(current.data(Qt.ItemDataRole.UserRole))
        self.stages.clear()
        for index, stage in enumerate(self.profile.stages, 1):
            item = QListWidgetItem(f"{index:02d}  {stage.type.title()}")
            item.setData(Qt.ItemDataRole.UserRole, stage.id)
            self.stages.addItem(item)
        if self.stages.count():
            row = next((index for index in range(self.stages.count()) if self.stages.item(index).data(Qt.ItemDataRole.UserRole) == selected_stage_id), fallback_row)
            self.stages.setCurrentRow(max(0, min(row, self.stages.count() - 1)))

    def add(self, stage_type: str) -> None:
        try:
            self.service.add_stage(self.profile, stage_type)
            self.profile = next(item for item in self.service.list_profiles() if item.id == self.profile.id)
            self.refresh()
        except ValueError as error:
            QMessageBox.warning(self, "Cannot add DSP stage", str(error))

    def add_and_configure(self, stage_type: str) -> None:
        previous_count = len(self.profile.stages)
        self.add(stage_type)
        if len(self.profile.stages) > previous_count:
            self.stages.setCurrentRow(previous_count)
            QTimer.singleShot(0, self, self.configure)

    def move(self, direction: int) -> None:
        row = self.stages.currentRow()
        if row < 0:
            return
        self.service.move_stage(self.profile, row, direction)
        self.profile = next(item for item in self.service.list_profiles() if item.id == self.profile.id)
        self.refresh()
        self.stages.setCurrentRow(max(0, min(row + direction, self.stages.count() - 1)))

    def remove(self) -> None:
        row = self.stages.currentRow()
        if row < 0:
            return
        stages = [stage for index, stage in enumerate(self.profile.stages) if index != row]
        self.service.update_stages(self.profile, stages)
        self.profile = next(item for item in self.service.list_profiles() if item.id == self.profile.id)
        self.refresh(fallback_row=max(0, row - 1))

    def configure(self) -> None:
        row = self.stages.currentRow()
        if row < 0:
            return
        stage = self.profile.stages[row]
        dialog = StageConfigDialog(self.service, self.profile, stage, self)
        dialog.exec()
        self.profile = next(item for item in self.service.list_profiles() if item.id == self.profile.id)
        self.refresh(stage.id)

    def configure_item(self, item: QListWidgetItem) -> None:
        self.stages.setCurrentRow(self.stages.row(item))
        self.configure()


class StageConfigDialog(QDialog):
    def __init__(self, service: ALSAChainService, profile: Profile, stage: Stage, parent: QWidget | None = None):
        super().__init__(parent)
        self.service, self.profile, self.stage = service, profile, stage
        self.setWindowTitle(f"Configure {stage.type.title()}")
        layout = QVBoxLayout(self)
        if stage.type == "equalizer":
            self.build_equalizer(layout)
        elif stage.type == "crossfeed":
            self.build_crossfeed(layout)
        else:
            self.build_gain(layout)

    def buttons(self, layout: QVBoxLayout, save: object) -> None:
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save, self)
        buttons.accepted.connect(save)
        layout.addWidget(buttons)

    def build_equalizer(self, layout: QVBoxLayout) -> None:
        self.setMinimumSize(900, 560)
        layout.addWidget(QLabel("Bands are read from the ALSA CTL. Changes are written immediately.", self))
        bands_layout = QHBoxLayout()
        try:
            bands = self.service.equalizer_bands(self.profile)
        except ValueError as error:
            bands_layout.addWidget(QLabel(str(error), self))
        else:
            for band in bands:
                column = QVBoxLayout()
                label = QLabel(f"{band.label}\n{self.format_db(value_to_db(band, band.value))}", self)
                label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
                slider = QSlider(Qt.Orientation.Vertical, self)
                limit = slider_limit(band)
                slider.setRange(-limit, limit)
                slider.setValue(value_to_slider(band, band.value))
                slider.setMinimumHeight(360)
                slider.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
                slider.setToolTip(f"Adjust {band.label}")
                slider.valueChanged.connect(lambda value, item=band, output=label: self.set_band(item, value, output))
                column.addWidget(label)
                column.addWidget(slider, 1, Qt.AlignmentFlag.AlignHCenter)
                bands_layout.addLayout(column, 1)
        layout.addLayout(bands_layout, 1)
        self.buttons(layout, self.accept)

    @staticmethod
    def format_db(value: int) -> str:
        return "0 dB" if value == 0 else f"{value:+d} dB"

    def set_band(self, band, slider_value: int, label: QLabel) -> None:
        value = slider_to_value(band, slider_value)
        try:
            self.service.set_equalizer_band(self.profile, band, value)
        except ValueError as error:
            QMessageBox.warning(self, "Unable to update equalizer", str(error))
            return
        label.setText(f"{band.label}\n{self.format_db(value_to_db(band, value))}")

    def build_crossfeed(self, layout: QVBoxLayout) -> None:
        self.setMinimumWidth(500)
        settings = self.stage.settings
        if isinstance(settings, str):
            self.cutoff, feed = CROSSFEED[settings]
        else:
            values = settings or {}
            self.cutoff, feed = values.get("cutoff", 700), values.get("feed", 6)
        self.cutoff_label = QLabel(self)
        self.cutoff_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.cutoff_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.cutoff_slider.setRange(300, 2000)
        self.cutoff_slider.setSingleStep(10)
        self.cutoff_slider.setTickInterval(100)
        self.cutoff_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.cutoff_slider.setToolTip("Adjust crossfeed cutoff frequency")
        self.cutoff_slider.setAccessibleName("Crossfeed cutoff frequency")
        self.cutoff_slider.setValue(int(self.cutoff))
        self.cutoff_slider.valueChanged.connect(self.update_cutoff_label)
        self.update_cutoff_label(self.cutoff_slider.value())
        layout.addWidget(self.cutoff_label)
        layout.addWidget(self.cutoff_slider)
        self.feed_label = QLabel(self)
        self.feed_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.feed = QSlider(Qt.Orientation.Horizontal, self)
        self.feed.setRange(10, 150)
        self.feed.setSingleStep(1)
        self.feed.setTickInterval(10)
        self.feed.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.feed.setValue(round(float(feed) * 10))
        self.feed.valueChanged.connect(self.update_feed_label)
        self.update_feed_label(self.feed.value())
        layout.addWidget(self.feed_label)
        layout.addWidget(self.feed)
        self.buttons(layout, self.save_crossfeed)

    def update_cutoff_label(self, value: int) -> None:
        self.cutoff_label.setText(f"Cutoff frequency: {value} Hz")

    def update_feed_label(self, value: int) -> None:
        self.feed_label.setText(f"Crossfeed level: {value / 10:g} dB")

    def save_crossfeed(self) -> None:
        self.stage.settings = {"cutoff": self.cutoff_slider.value(), "feed": self.feed.value() / 10}
        self.service.update_stages(self.profile, self.profile.stages)
        self.accept()

    def build_gain(self, layout: QVBoxLayout) -> None:
        self.setMinimumWidth(500)
        self.gain_value = QLabel(self)
        self.gain_value.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.gain_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.gain_slider.setRange(-48, 24)
        self.gain_slider.setSingleStep(1)
        self.gain_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.gain_slider.setTickInterval(6)
        self.gain_slider.setValue(round(float(self.stage.gain_db or 0) * 2))
        self.gain_slider.valueChanged.connect(self.update_gain_label)
        self.update_gain_label(self.gain_slider.value())
        layout.addWidget(self.gain_value)
        layout.addWidget(self.gain_slider)
        self.buttons(layout, self.save_gain)

    def update_gain_label(self, value: int) -> None:
        gain = value / 2
        self.gain_value.setText(f"{gain:+g} dB")

    def save_gain(self) -> None:
        self.stage.gain_db = self.gain_slider.value() / 2
        self.service.update_stages(self.profile, self.profile.stages)
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, service: ALSAChainService):
        super().__init__()
        self.service, self.profiles, self.playback_labels = service, [], []
        self.profile_cards: dict[str, ProfileCard] = {}
        self.selected_profile_id = ""
        self.setWindowTitle("ALSAChainQT")
        self.resize(1120, 720)
        self.build_ui()
        self.refresh()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_states)
        self.timer.start(1000)

    def build_ui(self) -> None:
        profiles_menu = self.menuBar().addMenu("Profiles")
        add_profile = QAction("Add", profiles_menu)
        add_profile.triggered.connect(self.new_profile)
        profiles_menu.addAction(add_profile)
        self.remove_selected_action = QAction("Remove selected", profiles_menu)
        self.remove_selected_action.triggered.connect(self.remove_selected_profile)
        self.remove_selected_action.setEnabled(False)
        profiles_menu.addAction(self.remove_selected_action)
        help_menu = self.menuBar().addMenu("Help")
        website = QAction("Go to ALSAChainQT Website", help_menu)
        website.triggered.connect(lambda: QDesktopServices.openUrl(QUrl("https://github.com/mikelexp/alsachainqt")))
        help_menu.addAction(website)
        about = QAction("About", help_menu)
        about.triggered.connect(self.show_about)
        help_menu.addAction(about)
        root = QWidget(self)
        layout = QVBoxLayout(root)
        style = self.style()
        self.profile_scroll = QScrollArea(root)
        self.profile_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.profile_scroll.setWidgetResizable(True)
        self.profile_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.profile_container = QWidget(self.profile_scroll)
        self.profile_layout = QVBoxLayout(self.profile_container)
        self.profile_layout.setContentsMargins(0, 0, 0, 0)
        self.profile_layout.setSpacing(10)
        self.profile_scroll.setWidget(self.profile_container)
        layout.addWidget(self.profile_scroll, 1)
        actions = QHBoxLayout()
        actions.addWidget(action_button(root, "New profile", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder), "Create an ALSAChain virtual PCM profile", self.new_profile, role="primary"))
        actions.addWidget(action_button(root, "Refresh", style.standardIcon(QStyle.StandardPixmap.SP_BrowserReload), "Rediscover devices and refresh playback state", self.refresh))
        actions.addWidget(action_button(root, "Diagnostics", style.standardIcon(QStyle.StandardPixmap.SP_MessageBoxInformation), "Show ALSA dependency diagnostics", self.show_diagnostics, role="info"))
        actions.addStretch()
        layout.addLayout(actions)
        self.setCentralWidget(root)

    def refresh(self) -> None:
        previous_selection = self.selected_profile_id
        self.profiles = self.service.list_profiles()
        self.clear_profiles()
        if not self.profiles:
            self.select_profile("")
            self.profile_layout.addWidget(QLabel("Create a profile to expose a managed ALSA output.", self.profile_container))
            self.profile_layout.addStretch()
            return
        for profile in self.profiles:
            self.profile_layout.addWidget(self.profile_card(profile))
        self.profile_layout.addStretch()
        self.select_profile(next((profile.id for profile in self.profiles if profile.id == previous_selection), self.profiles[0].id))

    def refresh_states(self) -> None:
        for profile, label in self.playback_labels:
            state = self.service.state(profile)
            label.setText(f"Playback: {state.state} {state.rate} {state.format}")

    def clear_profiles(self) -> None:
        self.playback_labels.clear()
        self.profile_cards.clear()
        while self.profile_layout.count():
            item = self.profile_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def selected_profile(self) -> Profile | None:
        return next((profile for profile in self.profiles if profile.id == self.selected_profile_id), None)

    def select_profile(self, identifier: str) -> None:
        self.selected_profile_id = identifier
        self.remove_selected_action.setEnabled(self.selected_profile() is not None)
        for profile_id, card in self.profile_cards.items():
            card.setStyleSheet("QFrame#profileCard { border: 2px solid palette(highlight); border-radius: 4px; }" if profile_id == identifier else "")

    def profile_card(self, profile: Profile) -> ProfileCard:
        card = ProfileCard(self.profile_container)
        card.setObjectName("profileCard")
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.clicked.connect(lambda: self.select_profile(profile.id))
        card.double_clicked.connect(lambda: self.edit_profile(profile))
        self.profile_cards[profile.id] = card
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 14, 16, 14)
        state = self.service.state(profile)
        heading = QLabel(profile.display_name, card)
        heading.setObjectName("profileTitle")
        layout.addWidget(heading)
        playback = QLabel(f"Playback: {state.state} {state.rate} {state.format}", card)
        self.playback_labels.append((profile, playback))
        stages = " -> ".join(stage.type.title() for stage in profile.stages)
        dsp = f"Disabled by bit-perfect mode ({stages} configured)" if profile.bitperfect and stages else stages or "No stages"
        info = QLabel(f"Public PCM: {profile.pcm_name}\nTarget: {profile.target}\nMode: {'Bit-perfect' if profile.bitperfect else 'Processed'}\nDSP: {dsp}", card)
        info.setWordWrap(True)
        layout.addWidget(playback)
        layout.addWidget(info)
        actions = QHBoxLayout()
        style = self.style()
        actions.addWidget(action_button(card, "Edit", style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView), "Edit profile name and playback device", lambda: self.edit_profile(profile)))
        mode = "Use processed mode" if profile.bitperfect else "Use bit-perfect mode"
        actions.addWidget(action_button(card, mode, style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), "Toggle DSP processing for new ALSA connections", lambda: self.toggle_mode(profile), role="mode"))
        actions.addWidget(action_button(card, "Manage DSP", style.standardIcon(QStyle.StandardPixmap.SP_MediaVolume), "Add, remove, and reorder DSP stages", lambda: self.manage_dsp(profile), role="dsp"))
        actions.addStretch()
        actions.addWidget(action_button(card, "Delete", style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon), "Delete this profile", lambda: self.delete_profile(profile), danger=True))
        layout.addLayout(actions)
        return card

    def new_profile(self) -> None:
        if ProfileDialog(self.service, parent=self).exec():
            self.refresh()

    def edit_profile(self, profile: Profile) -> None:
        if ProfileDialog(self.service, profile, self).exec():
            self.refresh()

    def toggle_mode(self, profile: Profile) -> None:
        try:
            self.service.set_bitperfect(profile, not profile.bitperfect)
        except ValueError as error:
            QMessageBox.critical(self, "Unable to change playback mode", str(error))
        self.refresh()

    def manage_dsp(self, profile: Profile) -> None:
        DspDialog(self.service, profile, self).exec()
        self.refresh()

    def delete_profile(self, profile: Profile) -> None:
        answer = QMessageBox.question(self, "Delete profile", f"Remove {profile.display_name}? Its ALSA definition will be removed.", QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.Cancel)
        if answer == QMessageBox.StandardButton.Yes:
            try:
                self.service.delete_profile(profile, True)
            except ValueError as error:
                QMessageBox.critical(self, "Unable to delete profile", str(error))
            self.refresh()

    def remove_selected_profile(self) -> None:
        profile = self.selected_profile()
        if profile:
            self.delete_profile(profile)

    def show_about(self) -> None:
        AboutDialog(self.windowIcon(), self).exec()

    def show_diagnostics(self) -> None:
        report = self.service.diagnostics()
        content = "\n".join(f"{'OK' if dependency.ok else 'Missing'}: {dependency.name} - {dependency.detail or dependency.purpose}" for dependency in report.dependencies)
        QMessageBox.information(self, "System diagnostics", content)
