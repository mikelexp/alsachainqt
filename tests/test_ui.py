from alsachainqt.models import Profile, Stage
from alsachainqt.main import APP_ICON
from alsachainqt.ui import AboutDialog, DspDialog, MainWindow, ProfileDialog, StageConfigDialog, action_button
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QMenu, QPushButton, QScrollArea, QSlider, QTableWidget


class FakeService:
    def list_profiles(self):
        return [Profile("dac", "USB DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, True)]

    def state(self, profile):
        from alsachainqt.alsa import PlaybackState
        return PlaybackState()

    def diagnostics(self):
        from alsachainqt.deps import DependencyReport
        return DependencyReport([])

    def devices(self):
        from alsachainqt.alsa import Device
        return [Device("USB", 1, "USB DAC", 0, "USB audio", "plughw:CARD=USB,DEV=0")]


def test_application_icon_exists() -> None:
    assert APP_ICON.is_file()


def test_main_window_exposes_primary_actions_as_buttons(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)

    labels = {button.text() for button in window.findChildren(QPushButton)}
    assert {"New profile", "Refresh", "Diagnostics"}.issubset(labels)
    window.show()


def test_main_window_exposes_profiles_and_help_menus(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)

    menus = {menu.title(): [action.text() for action in menu.actions()] for menu in window.menuBar().findChildren(QMenu)}
    assert menus == {
        "Profiles": ["Add", "Remove selected"],
        "Help": ["Go to ALSAChainQT Website", "About"],
    }


def test_about_dialog_shows_application_details(qtbot) -> None:
    dialog = AboutDialog(QIcon(), None)
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "About ALSAChainQT"
    assert dialog.minimumWidth() >= 460
    assert "Version: TBD" in {label.text() for label in dialog.findChildren(QLabel)}
    assert "Close" in {button.text() for button in dialog.findChildren(QPushButton)}


def test_main_window_shows_scrollable_profile_cards_without_a_detail_panel(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)

    cards = [frame for frame in window.findChildren(QFrame) if frame.objectName() == "profileCard"]
    assert len(cards) == 1
    assert not window.findChildren(QTableWidget)
    assert window.profile_scroll.widgetResizable()
    assert window.profile_scroll.frameShape() == QFrame.Shape.NoFrame
    assert cards[0].layout().contentsMargins().left() == 16
    assert cards[0].layout().contentsMargins().top() == 14
    assert any("Public PCM: dac" in label.text() for label in cards[0].findChildren(QLabel))


def test_profile_card_explains_bitperfect_disables_configured_dsp(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)
    profile = Profile("dac", "USB DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, True, [Stage("gain", "gain", gain_db=0)])

    card = window.profile_card(profile)

    assert any("DSP: Disabled by bit-perfect mode (Gain configured)" in label.text() for label in card.findChildren(QLabel))


def test_selecting_a_profile_only_styles_its_outer_card(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)

    card = next(frame for frame in window.findChildren(QFrame) if frame.objectName() == "profileCard")
    assert "QFrame#profileCard" in card.styleSheet()


def test_double_clicking_a_profile_card_edits_its_profile(qtbot) -> None:
    window = MainWindow(FakeService())
    qtbot.addWidget(window)
    window.show()
    edited = []
    window.edit_profile = lambda profile: edited.append(profile.id)

    card = next(frame for frame in window.findChildren(QFrame) if frame.objectName() == "profileCard")
    qtbot.mouseDClick(card, Qt.MouseButton.LeftButton)

    assert edited == ["dac"]


def test_action_button_reserves_space_for_its_label(qtbot) -> None:
    button = action_button(None, "Use bit-perfect mode", QIcon(), "", lambda: None)
    qtbot.addWidget(button)

    assert button.minimumWidth() >= button.sizeHint().width()


def test_action_button_uses_a_semantic_role(qtbot) -> None:
    button = action_button(None, "Delete", QIcon(), "", lambda: None, danger=True)
    qtbot.addWidget(button)

    assert button.objectName() == "dangerButton"
    assert "#b42318" in button.styleSheet()


def test_profile_dialog_uses_expanding_text_inputs(qtbot) -> None:
    dialog = ProfileDialog(FakeService())
    qtbot.addWidget(dialog)

    assert isinstance(dialog.identifier, QLineEdit)
    assert isinstance(dialog.name, QLineEdit)
    assert dialog.identifier.sizePolicy().horizontalPolicy().name == "Expanding"


def test_dsp_dialog_groups_stage_add_actions_in_a_button_menu(qtbot) -> None:
    profile = FakeService().list_profiles()[0]
    dialog = DspDialog(FakeService(), profile)
    qtbot.addWidget(dialog)

    button = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Add DSP stage")
    assert [action.text() for action in button.menu().actions()] == ["Equalizer", "Crossfeed", "Gain"]
    assert "Close" not in {button.text() for button in dialog.findChildren(QPushButton)}


def test_dsp_dialog_keeps_a_stage_selected_across_refresh_and_removal(qtbot) -> None:
    class DspService:
        def __init__(self):
            self.profile = Profile("dac", "USB DAC", "dac", "plughw:CARD=USB,DEV=0", 2, True, False, [Stage("eq", "equalizer", "dac", "/tmp/dac.bin"), Stage("gain", "gain", gain_db=0)])

        def list_profiles(self):
            return [self.profile]

        def update_stages(self, profile, stages):
            profile.stages = stages

    service = DspService()
    dialog = DspDialog(service, service.profile)
    qtbot.addWidget(dialog)

    assert dialog.stages.currentRow() == 0
    dialog.stages.setCurrentRow(1)
    dialog.refresh()
    assert dialog.stages.currentRow() == 1

    dialog.remove()
    assert dialog.stages.currentRow() == 0
    assert dialog.stages.currentItem().data(Qt.ItemDataRole.UserRole) == "eq"


def test_dsp_dialog_opens_configuration_on_double_click(qtbot) -> None:
    profile = FakeService().list_profiles()[0]
    profile.stages = [Stage("gain", "gain", gain_db=0)]
    dialog = DspDialog(FakeService(), profile)
    qtbot.addWidget(dialog)
    opened = []
    dialog.configure = lambda: opened.append(dialog.stages.currentRow())

    dialog.stages.itemDoubleClicked.emit(dialog.stages.item(0))

    assert opened == [0]


def test_dsp_dialog_opens_configuration_for_a_new_stage(qtbot) -> None:
    profile = FakeService().list_profiles()[0]
    dialog = DspDialog(FakeService(), profile)
    qtbot.addWidget(dialog)
    configured = []
    def add(stage_type):
        dialog.profile.stages.append(Stage("gain", stage_type, gain_db=0))
        dialog.refresh()

    dialog.add = add
    dialog.configure = lambda: configured.append(dialog.stages.currentRow())

    dialog.add_and_configure("gain")

    qtbot.waitUntil(lambda: bool(configured))
    assert configured == [0]


def test_equalizer_configuration_uses_vertical_sliders_without_scrolling(qtbot) -> None:
    class EqualizerService:
        def equalizer_bands(self, profile):
            from alsachainqt.equalizer import EqualizerBand
            return [EqualizerBand(f"{index}Hz", f"{index} Hz", 0, 72, 49) for index in range(10)]

    profile = FakeService().list_profiles()[0]
    stage = Stage("eq", "equalizer", "dac")
    dialog = StageConfigDialog(EqualizerService(), profile, stage)
    qtbot.addWidget(dialog)

    sliders = dialog.findChildren(QSlider)
    assert len(sliders) == 10
    assert all(slider.orientation() == Qt.Orientation.Vertical for slider in sliders)
    assert all((slider.minimum(), slider.maximum(), slider.value()) == (-49, 49, 0) for slider in sliders)
    assert not dialog.findChildren(QScrollArea)
    assert dialog.minimumSize().height() >= 560


def test_stage_configuration_has_one_save_button(qtbot) -> None:
    class EqualizerService:
        def equalizer_bands(self, profile):
            from alsachainqt.equalizer import EqualizerBand
            return [EqualizerBand("63Hz", "63 Hz", 0, 72, 49)]

    profile = FakeService().list_profiles()[0]
    dialog = StageConfigDialog(EqualizerService(), profile, Stage("eq", "equalizer", "dac"))
    qtbot.addWidget(dialog)

    labels = [button.text() for button in dialog.findChildren(QPushButton)]
    save = next(button for button in dialog.findChildren(QPushButton) if button.text() == "Save")
    qtbot.mouseClick(save, Qt.MouseButton.LeftButton)

    assert dialog.result() == dialog.DialogCode.Accepted
    assert labels == ["Save"]


def test_gain_configuration_uses_a_half_db_slider_in_a_larger_dialog(qtbot) -> None:
    class GainService:
        def update_stages(self, profile, stages):
            pass

    profile = FakeService().list_profiles()[0]
    dialog = StageConfigDialog(GainService(), profile, Stage("gain", "gain", gain_db=-3.5))
    qtbot.addWidget(dialog)

    slider = dialog.findChild(QSlider)
    assert slider.orientation() == Qt.Orientation.Horizontal
    assert (slider.minimum(), slider.maximum(), slider.value()) == (-48, 24, -7)
    assert dialog.minimumSize().width() >= 500
    assert dialog.minimumSize().height() == 0


def test_crossfeed_configuration_uses_the_valid_range_without_a_forced_height(qtbot) -> None:
    profile = FakeService().list_profiles()[0]
    dialog = StageConfigDialog(FakeService(), profile, Stage("crossfeed", "crossfeed", settings="normal"))
    qtbot.addWidget(dialog)

    sliders = dialog.findChildren(QSlider)
    assert {(slider.minimum(), slider.maximum(), slider.value()) for slider in sliders} == {(300, 2000, 700), (10, 150, 60)}
    assert dialog.minimumSize().width() >= 500
    assert dialog.minimumSize().height() == 0
    labels = {label.text() for label in dialog.findChildren(QLabel)}
    assert "Cutoff frequency: 700 Hz" in labels
    assert "Crossfeed level: 6 dB" in labels
