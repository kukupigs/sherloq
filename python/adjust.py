import cv2 as cv
import numpy as np
from PySide2.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QGridLayout,
    QCheckBox,
    QPushButton,
    QComboBox)

from tools import ToolWidget, ParamSlider
from utility import create_lut, signed_value, modify_font
from viewer import ImageViewer


class AdjustWidget(ToolWidget):
    def __init__(self, image, parent=None):
        super(AdjustWidget, self).__init__(parent)

        self.bright_slider = ParamSlider([-255, +255], 8, 16, 0)
        self.sat_slider = ParamSlider([-255, +255], 8, 16, 0)
        self.hue_slider = ParamSlider([0, 180], 5, 10, 0, '°')
        self.gamma_slider = ParamSlider([1, 50], 1, 10, 10)
        self.shadow_slider = ParamSlider([-100, +100], 2, 10, 0, '%')
        self.high_slider = ParamSlider([-100, +100], 2, 10, 0, '%')
        self.sweep_slider = ParamSlider([0, 255], 2, 8, 127)
        self.width_slider = ParamSlider([0, 255], 2, 8, 255)
        self.thr_slider = ParamSlider([0, 255], 1, 16, 255)
        self.equalize_combo = QComboBox()
        self.equalize_combo.addItems(
            [self.tr('No equalization'), self.tr('Histogram EQ'), self.tr('Weak CLAHE'),
             self.tr('Medium CLAHE'), self.tr('Strong CLAHE'), self.tr('Extreme CLAHE')])
        self.invert_check = QCheckBox(self.tr('Invert'))
        self.reset_button = QPushButton(self.tr('Reset'))

        self.image = image
        self.viewer = ImageViewer(self.image, self.image)
        self.process()

        self.bright_slider.value_changed.connect(self.process)
        self.sat_slider.value_changed.connect(self.process)
        self.hue_slider.value_changed.connect(self.process)
        self.gamma_slider.value_changed.connect(self.process)
        self.shadow_slider.value_changed.connect(self.process)
        self.high_slider.value_changed.connect(self.process)
        self.sweep_slider.value_changed.connect(self.process)
        self.width_slider.value_changed.connect(self.process)
        self.thr_slider.value_changed.connect(self.process)
        self.equalize_combo.currentIndexChanged.connect(self.process)
        self.invert_check.stateChanged.connect(self.process)
        self.reset_button.clicked.connect(self.reset)

        params_layout = QGridLayout()
        params_layout.addWidget(QLabel(self.tr('Brightness')), 0, 0)
        params_layout.addWidget(QLabel(self.tr('Saturation')), 1, 0)
        params_layout.addWidget(QLabel(self.tr('Hue')), 2, 0)
        params_layout.addWidget(self.bright_slider, 0, 1)
        params_layout.addWidget(self.sat_slider, 1, 1)
        params_layout.addWidget(self.hue_slider, 2, 1)
        params_layout.addWidget(QLabel(self.tr('Gamma')), 0, 2)
        params_layout.addWidget(QLabel(self.tr('Shadows')), 1, 2)
        params_layout.addWidget(QLabel(self.tr('Highlights')), 2, 2)
        params_layout.addWidget(self.gamma_slider, 0, 3)
        params_layout.addWidget(self.shadow_slider, 1, 3)
        params_layout.addWidget(self.high_slider, 2, 3)
        params_layout.addWidget(QLabel(self.tr('Sweep')), 0, 4)
        params_layout.addWidget(QLabel(self.tr('Width')), 1, 4)
        params_layout.addWidget(QLabel(self.tr('Threshold')), 2, 4)
        params_layout.addWidget(self.sweep_slider, 0, 5)
        params_layout.addWidget(self.width_slider, 1, 5)
        params_layout.addWidget(self.thr_slider, 2, 5)
        params_layout.addWidget(self.equalize_combo, 0, 6)
        params_layout.addWidget(self.invert_check, 1, 6)
        params_layout.addWidget(self.reset_button, 2, 6)
        top_layout = QHBoxLayout()
        top_layout.addLayout(params_layout)
        top_layout.addStretch()

        main_layout = QVBoxLayout()
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.viewer)
        self.setLayout(main_layout)

    def process(self):
        brightness = self.bright_slider.value()
        saturation = self.sat_slider.value()
        hue = self.hue_slider.value()
        gamma = self.gamma_slider.value() / 10
        shadows = self.shadow_slider.value()
        highlights = self.high_slider.value()
        equalize = self.equalize_combo.currentIndex()
        invert = self.invert_check.isChecked()
        sweep = self.sweep_slider.value()
        width = self.width_slider.value()
        threshold = self.thr_slider.value()

        result = np.copy(self.image)
        if brightness != 0 or saturation != 0 or hue != 0:
            h, s, v = cv.split(cv.cvtColor(result, cv.COLOR_BGR2HSV))
            if hue != 0:
                h = h.astype(np.float64) + hue
                h[h < 0] += 180
                h[h > 180] -= 180
                h = h.astype(np.uint8)
            if saturation != 0:
                s = cv.add(s, saturation)
            if brightness != 0:
                v = cv.add(v, brightness)
            result = cv.cvtColor(cv.merge((h, s, v)), cv.COLOR_HSV2BGR)
        if gamma != 0:
            inverse = 1 / gamma
            lut = np.array([((i / 255) ** inverse) * 255 for i in np.arange(0, 256)]).astype(np.uint8)
            result = cv.LUT(result, lut)
        if shadows != 0:
            result = cv.LUT(result, create_lut(int(shadows / 100 * 255), 0))
        if highlights != 0:
            result = cv.LUT(result, create_lut(0, int(highlights / 100 * 255)))
        if width < 255:
            radius = width // 2
            low = max(sweep - radius, 0)
            high = 255 - min(sweep + radius, 255)
            result = cv.LUT(result, create_lut(low, high))
        if equalize > 0:
            h, s, v = cv.split(cv.cvtColor(result, cv.COLOR_BGR2HSV))
            if equalize == 1:
                v = cv.equalizeHist(v)
            elif equalize > 1:
                clip = 0
                if equalize == 2:
                    clip = 2
                elif equalize == 3:
                    clip = 10
                elif equalize == 4:
                    clip = 20
                elif equalize == 5:
                    clip = 40
                v = cv.createCLAHE(clip).apply(v)
            result = cv.cvtColor(cv.merge((h, s, v)), cv.COLOR_HSV2BGR)
        if threshold < 255:
            if threshold == 0:
                gray = cv.cvtColor(result, cv.COLOR_BGR2GRAY)
                threshold, result = cv.threshold(gray, 0, 255, cv.THRESH_OTSU)
                result = cv.cvtColor(result, cv.COLOR_GRAY2BGR)
            else:
                _, result = cv.threshold(result, threshold, 255, cv.THRESH_BINARY)
        if invert:
            result = cv.bitwise_not(result)
        self.viewer.update_processed(result)

    def reset(self):
        self.bright_slider.setValue(0)
        self.sat_slider.setValue(0)
        self.hue_slider.setValue(0)
        self.gamma_slider.setValue(10)
        self.shadow_slider.setValue(0)
        self.high_slider.setValue(0)
        self.equalize_combo.setCurrentIndex(0)
        self.invert_check.setChecked(False)
