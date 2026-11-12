# Quick Inset Map - a QGIS plugin that adds an inset (locator) map to a print layout.
# Copyright (C) 2026 Abdishakur
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Options dialog for Quick Inset Map."""

from qgis.core import QgsProject
from qgis.gui import QgsColorButton, QgsMapLayerComboBox
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .inset import InsetOptions, main_maps


class InsetDialog(QDialog):
    def __init__(self, parent=None, layout=None):
        super().__init__(parent)
        self.setWindowTitle("Add inset map")
        self._maps = []

        self.layout_combo = QComboBox()
        for print_layout in QgsProject.instance().layoutManager().printLayouts():
            self.layout_combo.addItem(print_layout.name(), print_layout)
        if layout is not None:
            index = self.layout_combo.findText(layout.name())
            if index >= 0:
                self.layout_combo.setCurrentIndex(index)
        self.layout_combo.currentIndexChanged.connect(self._fill_maps)

        self.map_combo = QComboBox()

        self.corner_combo = QComboBox()
        self.corner_combo.addItem("Top right", "top_right")
        self.corner_combo.addItem("Top left", "top_left")
        self.corner_combo.addItem("Bottom right", "bottom_right")
        self.corner_combo.addItem("Bottom left", "bottom_left")

        self.size_spin = QSpinBox()
        self.size_spin.setRange(10, 50)
        self.size_spin.setValue(25)
        self.size_spin.setSuffix(" % of main map width")

        self.square_check = QCheckBox("Square inset")

        self.context_combo = QComboBox()
        self.context_combo.addItem("Zoomed out from the main map", "factor")
        self.context_combo.addItem("Whole extent of a layer", "layer")
        self.context_combo.currentIndexChanged.connect(self._sync_enabled)

        self.factor_spin = QDoubleSpinBox()
        self.factor_spin.setRange(1.5, 500.0)
        self.factor_spin.setDecimals(1)
        self.factor_spin.setValue(8.0)
        self.factor_spin.setSuffix(" x wider than the main map")

        self.context_layer_combo = QgsMapLayerComboBox()

        self.layers_combo = QComboBox()
        self.layers_combo.addItem("Same layers as the main map", "main")
        self.layers_combo.addItem("A map theme", "theme")
        self.layers_combo.addItem("One layer only", "layer")
        self.layers_combo.currentIndexChanged.connect(self._sync_enabled)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(QgsProject.instance().mapThemeCollection().mapThemes())

        self.only_layer_combo = QgsMapLayerComboBox()

        self.color_button = QgsColorButton()
        self.color_button.setColor(QColor("#e31a1c"))

        self.frame_check = QCheckBox("Draw a frame around the inset")
        self.frame_check.setChecked(True)

        form = QFormLayout()
        form.addRow("Layout", self.layout_combo)
        form.addRow("Main map", self.map_combo)
        form.addRow("Corner", self.corner_combo)
        form.addRow("Size", self.size_spin)
        form.addRow("", self.square_check)
        form.addRow("Inset shows", self.context_combo)
        form.addRow("Zoom out", self.factor_spin)
        form.addRow("Extent layer", self.context_layer_combo)
        form.addRow("Inset layers", self.layers_combo)
        form.addRow("Map theme", self.theme_combo)
        form.addRow("Layer", self.only_layer_combo)
        form.addRow("Extent box colour", self.color_button)
        form.addRow("", self.frame_check)

        self.hint = QLabel()
        self.hint.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.ok_button = buttons.button(QDialogButtonBox.StandardButton.Ok)

        box = QVBoxLayout(self)
        box.addLayout(form)
        box.addWidget(self.hint)
        box.addWidget(buttons)

        self._fill_maps()
        self._sync_enabled()

    def _fill_maps(self):
        self.map_combo.clear()
        layout = self.layout_combo.currentData()
        self._maps = main_maps(layout) if layout is not None else []
        reference = layout.referenceMap() if layout is not None else None
        for number, item in enumerate(self._maps, start=1):
            self.map_combo.addItem(item.id() or item.displayName() or "Map %d" % number)
            if item is reference:
                self.map_combo.setCurrentIndex(number - 1)
        self.ok_button.setEnabled(bool(self._maps))
        self.hint.setText("" if self._maps else "This layout has no map item yet.")

    def _sync_enabled(self):
        by_layer = self.context_combo.currentData() == "layer"
        self.factor_spin.setEnabled(not by_layer)
        self.context_layer_combo.setEnabled(by_layer)
        layers_mode = self.layers_combo.currentData()
        self.theme_combo.setEnabled(layers_mode == "theme")
        self.only_layer_combo.setEnabled(layers_mode == "layer")

    def selected_layout(self):
        return self.layout_combo.currentData()

    def selected_map(self):
        index = self.map_combo.currentIndex()
        return self._maps[index] if 0 <= index < len(self._maps) else None

    def options(self):
        opts = InsetOptions()
        opts.corner = self.corner_combo.currentData()
        opts.size_percent = float(self.size_spin.value())
        opts.square = self.square_check.isChecked()
        opts.context_mode = self.context_combo.currentData()
        opts.factor = self.factor_spin.value()
        opts.context_layer = self.context_layer_combo.currentLayer()
        opts.layers_mode = self.layers_combo.currentData()
        opts.theme = self.theme_combo.currentText()
        opts.only_layer = self.only_layer_combo.currentLayer()
        opts.box_color = self.color_button.color().name()
        opts.frame = self.frame_check.isChecked()
        return opts
