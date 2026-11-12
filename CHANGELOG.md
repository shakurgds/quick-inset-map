# Changelog

## 0.1.0 - 2026-11-12

First release (marked experimental).

- Add an inset (locator) map to a print layout from the main QGIS toolbar,
  the Plugins menu, or the layout designer's Add Item menu and toolbar.
- Options: layout and main map, corner, size, square shape, context extent
  (zoom-out factor or the extent of a layer), layers (same as the main map,
  a map theme, or one layer), extent box colour, frame.
- The inset draws the main map's extent as a box and, in zoom-out mode,
  re-centres itself when the main map is panned or zoomed. The link is stored
  in the project and restored when it is reopened.
- Offers to create an A4 landscape layout from the current map view when the
  project has no print layout.
- Supports QGIS 3.28 to 4.x (Qt5 and Qt6).
