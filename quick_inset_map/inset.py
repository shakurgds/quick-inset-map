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

"""Core logic for Quick Inset Map: build an inset (locator) map and keep it in sync.

Nothing in this module touches the GUI, so it can be tested from the Python console.
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCsException,
    QgsFillSymbol,
    QgsLayoutItemMap,
    QgsLayoutMeasurement,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsProject,
    QgsRectangle,
)

# Custom properties stored on the inset item, so links survive save and reload.
PROP_MAIN = "quick_inset_map/main_uuid"
PROP_FACTOR = "quick_inset_map/factor"

CORNERS = ("top_right", "top_left", "bottom_right", "bottom_left")


class InsetOptions:
    """Settings for one inset map. Lengths are in layout units (millimetres by default)."""

    def __init__(self):
        self.corner = "top_right"
        self.size_percent = 25.0  # inset width as a share of the main map width
        self.square = False  # False: same shape as the main map
        self.margin = 3.0  # gap between the inset and the main map edge
        self.context_mode = "factor"  # "factor" or "layer"
        self.factor = 8.0  # inset shows this many times the main map's width
        self.context_layer = None  # layer whose extent the inset shows ("layer" mode)
        self.layers_mode = "main"  # "main", "theme" or "layer"
        self.theme = ""  # map theme name ("theme" mode)
        self.only_layer = None  # single layer to draw ("layer" mode)
        self.box_color = "#e31a1c"
        self.frame = True


def is_inset(item):
    return isinstance(item, QgsLayoutItemMap) and bool(item.customProperty(PROP_MAIN, ""))


def main_maps(layout):
    """Map items in a layout that are not insets themselves."""
    return [
        i for i in layout.items() if isinstance(i, QgsLayoutItemMap) and not is_inset(i)
    ]


def factor_extent(main, factor):
    """The main map's extent grown about its centre by `factor`."""
    ext = main.extent()
    c = ext.center()
    w = ext.width() * factor
    h = ext.height() * factor
    rect = QgsRectangle(c.x() - w / 2, c.y() - h / 2, c.x() + w / 2, c.y() + h / 2)
    world = _world_bounds(main.crs())
    if world is not None:
        clipped = rect.intersect(world)
        if not clipped.isEmpty():
            rect = clipped
    return rect


def _world_bounds(crs):
    """The whole-world rectangle for a global CRS, in that CRS; None for regional ones.

    Used to stop a zoomed-out inset from running past the edge of the world.
    Regional systems such as UTM zones are left alone: their official bounds are
    narrow, and clipping to them would cut off useful context.
    """
    if crs.isGeographic():
        return QgsRectangle(-180, -90, 180, 90)
    bounds = crs.bounds()
    if bounds.isEmpty() or bounds.width() < 359:
        return None
    try:
        transform = QgsCoordinateTransform(
            QgsCoordinateReferenceSystem("EPSG:4326"), crs, QgsProject.instance()
        )
        transform.setBallparkTransformsAreAppropriate(True)
        rect = transform.transformBoundingBox(bounds)
    except QgsCsException:
        return None
    if rect.isEmpty() or not rect.isFinite():
        return None
    return rect


def layer_extent(main, layer):
    """A layer's extent in the main map's CRS, grown to include the main map."""
    transform = QgsCoordinateTransform(layer.crs(), main.crs(), QgsProject.instance())
    transform.setBallparkTransformsAreAppropriate(True)
    rect = transform.transformBoundingBox(layer.extent())
    rect.combineExtentWith(main.extent())
    rect.scale(1.05)
    return rect


def update_inset(main, inset):
    """Re-centre a factor-based inset on its main map. No-op for layer-based insets."""
    try:
        factor = float(inset.customProperty(PROP_FACTOR, 0) or 0)
    except (TypeError, ValueError):
        factor = 0
    if factor > 0:
        inset.zoomToExtent(factor_extent(main, factor))


def _place(main, inset, opts):
    main_w = main.rect().width()
    main_h = main.rect().height()
    width = main_w * opts.size_percent / 100.0
    height = width if opts.square else width * main_h / main_w
    height = min(height, main_h - 2 * opts.margin)

    origin = main.scenePos()
    left = origin.x() + opts.margin
    right = origin.x() + main_w - width - opts.margin
    top = origin.y() + opts.margin
    bottom = origin.y() + main_h - height - opts.margin
    x = left if opts.corner.endswith("left") else right
    y = top if opts.corner.startswith("top") else bottom

    units = main.layout().units()
    inset.attemptResize(QgsLayoutSize(width, height, units))
    inset.attemptMove(QgsLayoutPoint(x, y, units))


def _set_layers(main, inset, opts):
    if opts.layers_mode == "theme" and opts.theme:
        inset.setFollowVisibilityPreset(True)
        inset.setFollowVisibilityPresetName(opts.theme)
    elif opts.layers_mode == "layer" and opts.only_layer is not None:
        inset.setLayers([opts.only_layer])
        inset.setKeepLayerSet(True)
    elif main.followVisibilityPreset():
        inset.setFollowVisibilityPreset(True)
        inset.setFollowVisibilityPresetName(main.followVisibilityPresetName())
    elif main.keepLayerSet():
        inset.setLayers(main.layers())
        inset.setKeepLayerSet(True)


def create_inset(main, opts):
    """Add an inset map for `main` to its layout and return the new item."""
    layout = main.layout()
    layout.undoStack().beginMacro("Add inset map")
    try:
        inset = QgsLayoutItemMap(layout)
        inset.setId("Inset map")
        inset.setCrs(main.crs())
        _place(main, inset, opts)
        _set_layers(main, inset, opts)

        if opts.context_mode == "layer" and opts.context_layer is not None:
            inset.zoomToExtent(layer_extent(main, opts.context_layer))
            factor = 0.0
        else:
            factor = max(float(opts.factor), 1.5)
            inset.zoomToExtent(factor_extent(main, factor))

        inset.setFrameEnabled(opts.frame)
        if opts.frame:
            inset.setFrameStrokeWidth(QgsLayoutMeasurement(0.3))

        overview = inset.overview()
        overview.setLinkedMap(main)
        overview.setFrameSymbol(
            QgsFillSymbol.createSimple(
                {
                    "style": "no",
                    "outline_color": opts.box_color,
                    "outline_width": "0.6",
                }
            )
        )
        overview.setEnabled(True)

        inset.setCustomProperty(PROP_MAIN, main.uuid())
        inset.setCustomProperty(PROP_FACTOR, factor)
        layout.addLayoutItem(inset)
    finally:
        layout.undoStack().endMacro()
    return inset


class InsetLinker:
    """Keeps factor-based insets centred on their main map when it is panned or zoomed."""

    def __init__(self):
        self._wired = {}

    def wire(self, main, inset):
        key = inset.uuid()
        if key in self._wired:
            return

        def handler():
            try:
                update_inset(main, inset)
            except RuntimeError:  # an item was deleted
                pass

        main.extentChanged.connect(handler)
        self._wired[key] = (main, handler)

    def wire_layout(self, layout):
        for item in layout.items():
            if not is_inset(item):
                continue
            main = layout.itemByUuid(item.customProperty(PROP_MAIN, ""))
            if isinstance(main, QgsLayoutItemMap):
                self.wire(main, item)

    def wire_project(self):
        for layout in QgsProject.instance().layoutManager().layouts():
            self.wire_layout(layout)

    def clear(self):
        for main, handler in self._wired.values():
            try:
                main.extentChanged.disconnect(handler)
            except (RuntimeError, TypeError):
                pass
        self._wired = {}
