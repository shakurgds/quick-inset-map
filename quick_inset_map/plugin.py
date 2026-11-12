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

"""QGIS plugin entry point for Quick Inset Map."""

import os

from qgis.core import (
    QgsLayoutItemMap,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsPrintLayout,
    QgsProject,
)
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox

from .dialog import InsetDialog
from .inset import InsetLinker, create_inset

MENU = "&Quick Inset Map"


class QuickInsetMapPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.linker = InsetLinker()
        self.icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.svg"))

    def initGui(self):
        self.action = QAction(self.icon, "Add inset map to layout…", self.iface.mainWindow())
        self.action.triggered.connect(lambda: self.run())
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(MENU, self.action)

        self.iface.layoutDesignerOpened.connect(self._designer_opened)
        QgsProject.instance().readProject.connect(self._rewire)
        QgsProject.instance().cleared.connect(self.linker.clear)
        self._rewire()

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginMenu(MENU, self.action)
        self.iface.layoutDesignerOpened.disconnect(self._designer_opened)
        QgsProject.instance().readProject.disconnect(self._rewire)
        QgsProject.instance().cleared.disconnect(self.linker.clear)
        self.linker.clear()

    def _rewire(self, *args):
        self.linker.clear()
        self.linker.wire_project()

    def _designer_opened(self, designer):
        self.linker.wire_layout(designer.layout())
        action = QAction(self.icon, "Add Inset Map…", designer.window())
        action.triggered.connect(lambda: self.run(designer.layout(), designer.window()))
        designer.itemsMenu().addAction(action)
        designer.actionsToolbar().addAction(action)

    def _new_layout_from_canvas(self):
        """Create a simple A4 landscape layout holding the current map view."""
        project = QgsProject.instance()
        manager = project.layoutManager()
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        layout.setName(manager.generateUniqueTitle())

        page = layout.pageCollection().page(0).rect()
        margin = 10.0
        item = QgsLayoutItemMap(layout)
        item.setId("Main map")
        item.attemptResize(
            QgsLayoutSize(page.width() - 2 * margin, page.height() - 2 * margin, layout.units())
        )
        item.attemptMove(QgsLayoutPoint(margin, margin, layout.units()))
        item.setCrs(project.crs())
        item.zoomToExtent(self.iface.mapCanvas().extent())
        item.setFrameEnabled(True)
        layout.addLayoutItem(item)
        manager.addLayout(layout)
        return layout

    def run(self, layout=None, parent=None):
        parent = parent or self.iface.mainWindow()
        opened_from_designer = layout is not None

        if not QgsProject.instance().layoutManager().printLayouts():
            answer = QMessageBox.question(
                parent,
                "Quick Inset Map",
                "This project has no print layout yet.\n"
                "Create one from the current map view?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            layout = self._new_layout_from_canvas()

        dialog = InsetDialog(parent, layout)
        if not dialog.exec():
            return
        main = dialog.selected_map()
        if main is None:
            return

        inset = create_inset(main, dialog.options())
        self.linker.wire(main, inset)
        if not opened_from_designer:
            self.iface.openLayoutDesigner(dialog.selected_layout())
