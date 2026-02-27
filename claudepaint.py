#!/usr/bin/env python3
"""Claude Paint — MS Paint clone built with Python + PyQt5."""

import math
import os
import sys
from collections import deque
from enum import Enum, auto

from PyQt5.QtCore import (
    QPoint, QPointF, QRect, QRectF, QSettings, QSize, QTimer, Qt, pyqtSignal,
)
from PyQt5.QtGui import (
    QBrush, QColor, QCursor, QFont, QFontMetricsF, QIcon, QImage,
    QKeySequence, QPainter, QPainterPath, QPen, QPixmap, QTransform,
)
from PyQt5.QtWidgets import (
    QAction, QApplication, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QFileDialog, QFontDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton,
    QSizePolicy, QSlider, QSpinBox, QStatusBar, QToolBar, QToolButton,
    QVBoxLayout, QWidget,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
APP_NAME = "Claude Paint"
DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
DEFAULT_DIR = os.path.expanduser("~/Pictures")
MAX_UNDO = 50
ZOOM_MIN = 0.25
ZOOM_MAX = 64.0
ZOOM_STEP = 0.25

PALETTE_COLORS = [
    "#000000", "#808080", "#800000", "#808000",
    "#008000", "#008080", "#000080", "#800080",
    "#808040", "#004040", "#0080FF", "#004080",
    "#4000FF", "#804000",
    "#FFFFFF", "#C0C0C0", "#FF0000", "#FFFF00",
    "#00FF00", "#00FFFF", "#0000FF", "#FF00FF",
    "#FFFF80", "#00FF80", "#80FFFF", "#0080FF",
    "#FF0080", "#FF8040",
]


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------
class ToolType(Enum):
    PENCIL = auto()
    BRUSH = auto()
    ERASER = auto()
    ALPHA_BRUSH = auto()
    LINE = auto()
    RECTANGLE = auto()
    ELLIPSE = auto()
    TEXT = auto()
    FILL = auto()
    PICKER = auto()
    SELECTION = auto()


class ShapeFillMode(Enum):
    OUTLINE = auto()
    FILLED = auto()
    BOTH = auto()


TOOL_SHORTCUTS = {
    Qt.Key_S: ToolType.SELECTION,
    Qt.Key_P: ToolType.PENCIL,
    Qt.Key_B: ToolType.BRUSH,
    Qt.Key_E: ToolType.ERASER,
    Qt.Key_A: ToolType.ALPHA_BRUSH,
    Qt.Key_L: ToolType.LINE,
    Qt.Key_R: ToolType.RECTANGLE,
    Qt.Key_O: ToolType.ELLIPSE,
    Qt.Key_T: ToolType.TEXT,
    Qt.Key_F: ToolType.FILL,
    Qt.Key_I: ToolType.PICKER,
}

TOOL_SHORTCUT_LABELS = {v: chr(k) for k, v in TOOL_SHORTCUTS.items()}

TOOL_GROUPS = [
    ("Selection", [ToolType.SELECTION]),
    ("Drawing", [ToolType.PENCIL, ToolType.BRUSH, ToolType.ERASER, ToolType.ALPHA_BRUSH]),
    ("Shapes", [ToolType.LINE, ToolType.RECTANGLE, ToolType.ELLIPSE]),
    ("Tools", [ToolType.TEXT, ToolType.FILL, ToolType.PICKER]),
]


# ---------------------------------------------------------------------------
# Tool classes (Strategy pattern)
# ---------------------------------------------------------------------------
class BaseTool:
    """Base interface for all drawing tools."""

    name = "Base"

    def __init__(self, canvas):
        self.canvas = canvas

    def mouse_press(self, event):
        pass

    def mouse_move(self, event):
        pass

    def mouse_release(self, event):
        pass

    def paint_overlay(self, painter):
        pass

    def get_cursor(self):
        return Qt.CrossCursor

    def activate(self):
        pass

    def deactivate(self):
        pass


class PencilTool(BaseTool):
    name = "Pencil"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._last = None

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._last = event.pos()
        p = self.canvas.make_painter()
        color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color
        size = self.canvas.brush_size
        p.setPen(QPen(color, size, Qt.SolidLine, Qt.RoundCap))
        p.drawPoint(self._last)
        p.end()
        self.canvas.update()

    def mouse_move(self, event):
        if self._last is None:
            return
        p = self.canvas.make_painter()
        color = self.canvas.fg_color if event.buttons() & Qt.LeftButton else self.canvas.bg_color
        size = self.canvas.brush_size
        p.setPen(QPen(color, size, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(self._last, event.pos())
        p.end()
        self._last = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        self._last = None
        self.canvas.set_modified()


class BrushTool(BaseTool):
    name = "Brush"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._last = None

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._last = event.pos()
        p = self.canvas.make_painter()
        color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color
        size = self.canvas.brush_size
        p.setPen(QPen(color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPoint(self._last)
        p.end()
        self.canvas.update()

    def mouse_move(self, event):
        if self._last is None:
            return
        p = self.canvas.make_painter()
        color = self.canvas.fg_color if event.buttons() & Qt.LeftButton else self.canvas.bg_color
        size = self.canvas.brush_size
        p.setPen(QPen(color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(self._last, event.pos())
        p.end()
        self._last = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        self._last = None
        self.canvas.set_modified()


class EraserTool(BaseTool):
    name = "Eraser"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._last = None

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._last = event.pos()
        p = self.canvas.make_painter()
        size = self.canvas.brush_size
        p.setPen(QPen(self.canvas.bg_color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPoint(self._last)
        p.end()
        self.canvas.update()

    def mouse_move(self, event):
        if self._last is None:
            return
        p = self.canvas.make_painter()
        size = self.canvas.brush_size
        p.setPen(QPen(self.canvas.bg_color, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawLine(self._last, event.pos())
        p.end()
        self._last = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        self._last = None
        self.canvas.set_modified()

    def get_cursor(self):
        return Qt.CrossCursor


class AlphaBrushTool(BaseTool):
    """Brush that erases pixels to transparent."""
    name = "Alpha"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._last = None

    def _make_painter(self):
        p = QPainter(self.canvas.pixmap)
        p.setCompositionMode(QPainter.CompositionMode_Clear)
        size = self.canvas.brush_size
        p.setPen(QPen(Qt.transparent, size, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        return p

    def mouse_press(self, event):
        self.canvas.save_undo()
        pos = event.pos()
        if event.modifiers() & Qt.ShiftModifier:
            self._alpha_flood_fill(pos)
            return
        self._last = pos
        p = self._make_painter()
        p.drawPoint(self._last)
        p.end()
        self.canvas.update()

    def _alpha_flood_fill(self, pos):
        img = self.canvas.pixmap.toImage()
        w, h = img.width(), img.height()
        if pos.x() < 0 or pos.x() >= w or pos.y() < 0 or pos.y() >= h:
            return
        target = img.pixelColor(pos)
        if target.alpha() == 0:
            return
        target_rgb = target.rgba()
        fill = QColor(0, 0, 0, 0)
        queue = deque()
        queue.append((pos.x(), pos.y()))
        visited = set()
        visited.add((pos.x(), pos.y()))
        while queue:
            cx, cy = queue.popleft()
            if img.pixelColor(cx, cy).rgba() != target_rgb:
                continue
            img.setPixelColor(cx, cy, fill)
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))
        self.canvas.pixmap = QPixmap.fromImage(img)
        self.canvas.update()
        self.canvas.set_modified()

    def mouse_move(self, event):
        if self._last is None:
            return
        p = self._make_painter()
        p.drawLine(self._last, event.pos())
        p.end()
        self._last = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        self._last = None
        self.canvas.set_modified()


class LineTool(BaseTool):
    name = "Line"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start = None
        self._end = None
        self._color = None

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._start = event.pos()
        self._end = event.pos()
        self._color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color

    def mouse_move(self, event):
        if self._start is None:
            return
        self._end = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        if self._start is None:
            return
        p = self.canvas.make_painter()
        p.setPen(QPen(self._color, self.canvas.brush_size, Qt.SolidLine, Qt.RoundCap))
        p.drawLine(self._start, self._end)
        p.end()
        self._start = None
        self._end = None
        self.canvas.update()
        self.canvas.set_modified()

    def paint_overlay(self, painter):
        if self._start is not None and self._end is not None:
            painter.setPen(QPen(self._color, self.canvas.brush_size, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(self._start, self._end)


class RectangleTool(BaseTool):
    name = "Rectangle"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start = None
        self._end = None
        self._color = None

    def _rect(self):
        return QRect(self._start, self._end).normalized()

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._start = event.pos()
        self._end = event.pos()
        self._color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color

    def mouse_move(self, event):
        if self._start is None:
            return
        self._end = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        if self._start is None:
            return
        p = self.canvas.make_painter()
        self._draw_shape(p)
        p.end()
        self._start = None
        self._end = None
        self.canvas.update()
        self.canvas.set_modified()

    def _draw_shape(self, painter):
        mode = self.canvas.shape_fill_mode
        pen = QPen(self._color, self.canvas.brush_size)
        if mode == ShapeFillMode.OUTLINE:
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
        elif mode == ShapeFillMode.FILLED:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._color))
        else:  # BOTH
            painter.setPen(pen)
            painter.setBrush(QBrush(self.canvas.bg_color))
        painter.drawRect(self._rect())

    def paint_overlay(self, painter):
        if self._start is not None and self._end is not None:
            self._draw_shape(painter)


class EllipseTool(BaseTool):
    name = "Ellipse"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._start = None
        self._end = None
        self._color = None

    def _rect(self):
        return QRect(self._start, self._end).normalized()

    def mouse_press(self, event):
        self.canvas.save_undo()
        self._start = event.pos()
        self._end = event.pos()
        self._color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color

    def mouse_move(self, event):
        if self._start is None:
            return
        self._end = event.pos()
        self.canvas.update()

    def mouse_release(self, event):
        if self._start is None:
            return
        p = self.canvas.make_painter()
        self._draw_shape(p)
        p.end()
        self._start = None
        self._end = None
        self.canvas.update()
        self.canvas.set_modified()

    def _draw_shape(self, painter):
        mode = self.canvas.shape_fill_mode
        pen = QPen(self._color, self.canvas.brush_size)
        if mode == ShapeFillMode.OUTLINE:
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
        elif mode == ShapeFillMode.FILLED:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._color))
        else:
            painter.setPen(pen)
            painter.setBrush(QBrush(self.canvas.bg_color))
        painter.drawEllipse(self._rect())

    def paint_overlay(self, painter):
        if self._start is not None and self._end is not None:
            self._draw_shape(painter)


class _DraggableFontBar(QWidget):
    """A small bar showing the font name.  Drag to move, click to change font.

    Emits *drag_delta* with raw widget-pixel QPoint deltas each mouse move.
    A click (press + release without significant movement) emits *choose_font*.
    """
    drag_delta = pyqtSignal(QPoint)
    drag_finished = pyqtSignal()
    choose_font = pyqtSignal()

    _DRAG_THRESHOLD = 4  # pixels before press becomes a drag

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._label = label
        self._dragging = False
        self._press_gpos = QPoint()
        self._last_gpos = QPoint()
        self._was_drag = False
        self.setFixedHeight(22)
        self.setCursor(Qt.SizeAllCursor)

    def set_label(self, text):
        self._label = text
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(224, 224, 224))
        p.setPen(QColor(100, 100, 100))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.setPen(QColor(40, 40, 40))
        p.setFont(QFont(p.font().family(), 8))
        p.drawText(self.rect().adjusted(4, 0, -4, 0), Qt.AlignVCenter, self._label)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.parent().mousePressEvent(event)
            return
        if event.button() == Qt.LeftButton:
            self._press_gpos = event.globalPos()
            self._last_gpos = event.globalPos()
            self._dragging = True
            self._was_drag = False
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MiddleButton:
            self.parent().mouseMoveEvent(event)
            return
        if self._dragging:
            gpos = event.globalPos()
            delta = gpos - self._last_gpos
            total = gpos - self._press_gpos
            if not self._was_drag:
                if abs(total.x()) + abs(total.y()) >= self._DRAG_THRESHOLD:
                    self._was_drag = True
            if self._was_drag:
                self.drag_delta.emit(delta)
            self._last_gpos = gpos
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.parent().mouseReleaseEvent(event)
            return
        if self._dragging:
            was_drag = self._was_drag
            self._dragging = False
            if was_drag:
                self.drag_finished.emit()
            else:
                self.choose_font.emit()
            event.accept()


class TextTool(BaseTool):
    """Text tool – WYSIWYG text on the canvas.

    A transparent QPlainTextEdit is positioned over the text area.  Its text
    colour is invisible; the actual rendering is done in paint_overlay via
    QPainter so it's pixel-identical to the final commit.  The editor still
    provides click-to-position-cursor, text selection highlights, and a
    manually-drawn blinking caret.

    The font bar above the text can be dragged to move the text block, or
    clicked to open the font dialog.  Escape or clicking outside commits.
    """
    name = "Text"

    def __init__(self, canvas):
        super().__init__(canvas)
        self._font = QFont("Sans Serif", 16)
        self._pos = QPointF(0, 0)      # canvas-space top-left (float)
        self._text = ""
        self._active = False
        self._editor = None            # _InlineTextEditor
        self._font_bar = None          # _DraggableFontBar
        self._cached_pm = None         # cached rendered pixmap
        self._cache_key = None         # (text, font_key, fg_rgba)

    # --- Rendering helper ---

    def _render_text_pixmap(self):
        """Render current text to a transparent QPixmap at canvas resolution.

        Uses fontMetrics().height() as line step to match QPlainTextEdit's
        block height, so the overlay aligns with the editor for selection.
        Cached — only re-rendered when text, font, or color changes.
        """
        if not self._text:
            self._cached_pm = None
            self._cache_key = None
            return None
        fg = self.canvas.fg_color
        key = (self._text, self._font.key(), fg.rgba())
        if self._cache_key == key and self._cached_pm is not None:
            return self._cached_pm
        dummy = QPixmap(1, 1)
        p_tmp = QPainter(dummy)
        p_tmp.setFont(self._font)
        metrics = p_tmp.fontMetrics()
        lines = self._text.split('\n')
        max_w = max(metrics.horizontalAdvance(ln) for ln in lines) if lines else 1
        line_h = metrics.height()
        total_h = line_h * len(lines)
        p_tmp.end()
        if max_w < 1 or total_h < 1:
            self._cached_pm = None
            self._cache_key = None
            return None
        pm = QPixmap(max_w + 1, total_h + 1)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.TextAntialiasing)
        p.setFont(self._font)
        p.setPen(fg)
        y = metrics.ascent()
        for line in lines:
            p.drawText(QPointF(0, y), line)
            y += line_h
        p.end()
        self._cached_pm = pm
        self._cache_key = key
        return pm

    def _text_rect(self):
        """Return the canvas-space QRectF occupied by the current text."""
        pm = self._render_text_pixmap()
        if pm is None:
            h = self._font.pointSizeF() * 1.5 + 4
            return QRectF(self._pos.x(), self._pos.y(), 100.0, h)
        return QRectF(self._pos.x(), self._pos.y(), pm.width(), pm.height())

    # --- Widget management ---

    def _show_editor(self):
        """Create the transparent editor overlay + draggable font bar."""
        if self._editor is not None:
            self._sync_widgets()
            self._editor.setFocus()
            return

        # Editor – transparent text, positioned over canvas text area
        self._editor = _InlineTextEditor(self.canvas)
        self._editor.textChanged.connect(self._on_text_changed)
        self._editor.commit_requested.connect(self._commit)
        self._editor.document().setDocumentMargin(0)
        self._sync_editor_style()
        self._sync_widgets()
        self._editor.show()
        self._editor.setFocus()

        # Font bar
        self._font_bar = _DraggableFontBar(
            f"{self._font.family()}, {self._font.pointSize()}pt",
            self.canvas)
        self._font_bar.drag_delta.connect(self._on_bar_drag)
        self._font_bar.drag_finished.connect(self._on_bar_drag_done)
        self._font_bar.choose_font.connect(self._choose_font)
        self._sync_widgets()
        self._font_bar.show()

    def _sync_editor_style(self):
        """Update the editor font and stylesheet."""
        if self._editor is None:
            return
        display_font = QFont(self._font)
        display_font.setPointSizeF(self._font.pointSizeF() * self.canvas.zoom)
        self._editor.setFont(display_font)
        self._editor.setStyleSheet(
            "QPlainTextEdit { background: transparent; border: none;"
            " color: transparent;"
            " selection-background-color: rgba(0,120,215,80);"
            " selection-color: transparent; }")

    def _sync_widgets(self):
        """Position editor + font bar in widget coords over the text area."""
        z = self.canvas.zoom
        ox, oy = self.canvas._pan_offset.x(), self.canvas._pan_offset.y()
        wx = int(self._pos.x() * z + ox)
        wy = int(self._pos.y() * z + oy)
        tr = self._text_rect()
        bar_w = max(160, int(tr.width() * z))
        if self._editor is not None:
            fm = self._editor.fontMetrics()
            n = max(1, self._text.count('\n') + 1) if self._text else 1
            lines = self._text.split('\n') if self._text else ['']
            max_w = max(fm.horizontalAdvance(ln) for ln in lines)
            ew = max(bar_w, max_w + 16)
            eh = n * fm.height() + fm.height()
            self._editor.setGeometry(wx, wy, ew, eh)
        if self._font_bar is not None:
            self._font_bar.setGeometry(wx, wy - 22, bar_w, 22)

    def _destroy_editor(self):
        if self._editor is not None:
            self._editor.deleteLater()
            self._editor = None
        if self._font_bar is not None:
            self._font_bar.deleteLater()
            self._font_bar = None

    # --- Events ---

    _in_text_change = False

    def _on_text_changed(self):
        if self._editor is None or self._in_text_change:
            return
        self._in_text_change = True
        try:
            self._text = self._editor.toPlainText()
            self._sync_widgets()
            self.canvas.update()
        finally:
            self._in_text_change = False

    def _on_bar_drag(self, widget_delta):
        """Font bar dragged – move text in canvas space."""
        z = self.canvas.zoom if self.canvas.zoom > 0 else 1.0
        self._pos = QPointF(self._pos.x() + widget_delta.x() / z,
                            self._pos.y() + widget_delta.y() / z)
        self._sync_widgets()
        self.canvas.update()

    def _on_bar_drag_done(self):
        """Refocus editor after drag so cursor position is preserved."""
        if self._editor:
            self._editor.setFocus()

    def _choose_font(self):
        font, ok = QFontDialog.getFont(self._font, self.canvas)
        if ok:
            self._font = font
            if self._font_bar:
                self._font_bar.set_label(f"{font.family()}, {font.pointSize()}pt")
            self._sync_editor_style()
            self._sync_widgets()
            self.canvas.update()
        if self._editor:
            self._editor.setFocus()

    def mouse_press(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.pos()  # canvas coords (QPoint)
        if self._active:
            tr = self._text_rect()
            if tr.contains(QPointF(pos)):
                if self._editor:
                    self._editor.setFocus()
                return
            self._commit()
            return
        self._pos = QPointF(pos)
        self._text = ""
        self._active = True
        self._show_editor()
        self.canvas.update()

    def mouse_move(self, event):
        pass

    def mouse_release(self, event):
        pass

    def _commit(self):
        if not self._active:
            return
        if self._text:
            self.canvas.save_undo()
            pm = self._render_text_pixmap()
            if pm:
                p = QPainter(self.canvas.pixmap)
                p.drawPixmap(QPointF(self._pos.x(), self._pos.y()), pm)
                p.end()
                self.canvas.set_modified()
        self._destroy_editor()
        self._active = False
        self._text = ""
        self.canvas.update()

    def on_zoom_changed(self):
        """Called when canvas zoom or pan changes – reposition widgets."""
        if self._active:
            self._sync_editor_style()
            self._sync_widgets()

    def paint_overlay(self, painter):
        if not self._active:
            return
        # WYSIWYG text – identical to final commit
        pm = self._render_text_pixmap()
        if pm:
            painter.drawPixmap(QPointF(self._pos.x(), self._pos.y()), pm)
        # Dashed border
        tr = self._text_rect()
        inv_z = 1.0 / self.canvas.zoom if self.canvas.zoom > 0 else 1.0
        painter.setPen(QPen(QColor(0, 120, 215), inv_z, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(tr)

    def deactivate(self):
        self._commit()

    def get_cursor(self):
        return Qt.IBeamCursor


class FillTool(BaseTool):
    name = "Fill"

    def mouse_press(self, event):
        pos = event.pos()
        img = self.canvas.pixmap.toImage()
        w, h = img.width(), img.height()
        if pos.x() < 0 or pos.x() >= w or pos.y() < 0 or pos.y() >= h:
            return
        target = img.pixelColor(pos)
        fill_color = self.canvas.fg_color if event.button() == Qt.LeftButton else self.canvas.bg_color
        if target == fill_color:
            return
        self.canvas.save_undo()
        self._flood_fill(img, pos.x(), pos.y(), target, fill_color, w, h)
        self.canvas.pixmap = QPixmap.fromImage(img)
        self.canvas.update()
        self.canvas.set_modified()

    @staticmethod
    def _flood_fill(img, x, y, target, fill, w, h):
        target_rgb = target.rgba()
        queue = deque()
        queue.append((x, y))
        visited = set()
        visited.add((x, y))
        while queue:
            cx, cy = queue.popleft()
            if img.pixelColor(cx, cy).rgba() != target_rgb:
                continue
            img.setPixelColor(cx, cy, fill)
            for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in visited:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

    def get_cursor(self):
        return Qt.CrossCursor


class PickerTool(BaseTool):
    name = "Eyedropper"

    def mouse_press(self, event):
        pos = event.pos()
        img = self.canvas.pixmap.toImage()
        if 0 <= pos.x() < img.width() and 0 <= pos.y() < img.height():
            color = QColor(img.pixelColor(pos))
            if event.button() == Qt.LeftButton:
                self.canvas.fg_color = color
            else:
                self.canvas.bg_color = color
            self.canvas.color_changed.emit()

    def get_cursor(self):
        return Qt.CrossCursor


class SelectionTool(BaseTool):
    """Rectangular selection with resize handles and rotation."""

    name = "Selection"

    _HANDLE_NAMES = ("nw", "n", "ne", "e", "se", "s", "sw", "w")
    _OPPOSITE = {
        "nw": "se", "n": "s", "ne": "sw", "e": "w",
        "se": "nw", "s": "n", "sw": "ne", "w": "e",
    }
    _CHANGES_X = {"nw", "ne", "sw", "se", "e", "w"}
    _CHANGES_Y = {"nw", "ne", "sw", "se", "n", "s"}

    def __init__(self, canvas):
        super().__init__(canvas)
        self._state = "idle"  # idle, selecting, selected, moving, resizing, rotating
        self._start = None
        self._rect = QRect()
        self._snippet = None       # QPixmap of selected area
        self._snippet_display = None  # snippet composited over checkerboard
        self._angle = 0.0          # rotation in degrees
        self._move_offset = None
        self._active_handle = None
        self._resize_anchor = None  # QPointF, fixed point during resize
        self._drag_start_rect = None
        self._drag_start_angle = None
        self._drag_start_sel_angle = None

    def activate(self):
        self._reset()

    def deactivate(self):
        self._commit()
        self._reset()

    def _reset(self):
        self._state = "idle"
        self._start = None
        self._rect = QRect()
        self._snippet = None
        self._snippet_display = None
        self._angle = 0.0
        self._move_offset = None
        self._active_handle = None
        self._resize_anchor = None
        self._drag_start_rect = None
        self._drag_start_angle = None
        self._drag_start_sel_angle = None
        self.canvas.update()

    def _make_snippet_display(self):
        """Create snippet composited over checkerboard for overlay display."""
        if self._snippet and not self._snippet.isNull():
            sw, sh = self._snippet.width(), self._snippet.height()
            self._snippet_display = QPixmap(sw, sh)
            tp = QPainter(self._snippet_display)
            tp.drawTiledPixmap(0, 0, sw, sh, self.canvas._checker_tile)
            tp.drawPixmap(0, 0, self._snippet)
            tp.end()
        else:
            self._snippet_display = None

    # --- Geometry helpers ---

    @staticmethod
    def _rotate_point(point, center, angle_deg):
        """Rotate a QPointF around center by angle_deg degrees."""
        rad = math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        dx = point.x() - center.x()
        dy = point.y() - center.y()
        return QPointF(center.x() + dx * cos_a - dy * sin_a,
                       center.y() + dx * sin_a + dy * cos_a)

    def _get_handle_positions(self):
        """Return dict of handle_name -> QPointF in canvas coords."""
        if self._rect.width() < 2 or self._rect.height() < 2:
            return {}
        r = QRectF(self._rect)
        center = r.center()
        hw, hh = r.width() / 2, r.height() / 2
        local = {
            "nw": QPointF(-hw, -hh), "n": QPointF(0, -hh), "ne": QPointF(hw, -hh),
            "e": QPointF(hw, 0),
            "se": QPointF(hw, hh), "s": QPointF(0, hh), "sw": QPointF(-hw, hh),
            "w": QPointF(-hw, 0),
        }
        rot_off = 20 / self.canvas.zoom if self.canvas.zoom > 0 else 20
        local["rotate"] = QPointF(0, -hh - rot_off)
        positions = {}
        for name, lp in local.items():
            positions[name] = self._rotate_point(
                QPointF(center.x() + lp.x(), center.y() + lp.y()),
                center, self._angle)
        return positions

    def _hit_handle(self, pos):
        """Return handle name if pos is near a handle, else None."""
        if self._state not in ("selected", "moving"):
            return None
        positions = self._get_handle_positions()
        thr = max(6, 8 / self.canvas.zoom)
        thr_sq = thr * thr
        pf = QPointF(pos.x(), pos.y())
        for name, hp in positions.items():
            dx, dy = pf.x() - hp.x(), pf.y() - hp.y()
            if dx * dx + dy * dy < thr_sq:
                return name
        return None

    def _point_in_selection(self, pos):
        """Check if canvas pos is inside the (possibly rotated) selection."""
        if self._rect.width() < 2 or self._rect.height() < 2:
            return False
        center = QPointF(self._rect.center())
        local = self._rotate_point(QPointF(pos.x(), pos.y()), center, -self._angle)
        return QRectF(self._rect).contains(local)

    def _cursor_for_handle(self, handle):
        """Return appropriate resize/rotate cursor for a handle."""
        if handle == "rotate":
            return Qt.PointingHandCursor
        base = {"n": 0, "ne": 45, "e": 90, "se": 135,
                "s": 180, "sw": 225, "w": 270, "nw": 315}
        total = (base[handle] + self._angle) % 360
        if total < 0:
            total += 360
        cursors = [Qt.SizeVerCursor, Qt.SizeBDiagCursor,
                   Qt.SizeHorCursor, Qt.SizeFDiagCursor,
                   Qt.SizeVerCursor, Qt.SizeBDiagCursor,
                   Qt.SizeHorCursor, Qt.SizeFDiagCursor]
        return cursors[int((total + 22.5) / 45) % 8]

    def cursor_at(self, pos):
        """Return the cursor for the given canvas-space position."""
        if self._state in ("selected", "moving"):
            handle = self._hit_handle(pos)
            if handle:
                return self._cursor_for_handle(handle)
            if self._point_in_selection(pos):
                return Qt.SizeAllCursor
        elif self._state == "resizing":
            return self._cursor_for_handle(self._active_handle)
        elif self._state == "rotating":
            return Qt.PointingHandCursor
        return Qt.CrossCursor

    # --- Commit ---

    @staticmethod
    def _snap_alpha(pixmap):
        """Snap every pixel's alpha to 0 (was 0) or 255 (was >0)."""
        img = pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = img.bits()
        ptr.setsize(img.height() * img.bytesPerLine())
        data = bytearray(ptr)
        bpl = img.bytesPerLine()
        w_bytes = img.width() * 4
        for y in range(img.height()):
            base = y * bpl
            for x in range(3, w_bytes, 4):
                i = base + x
                if data[i] == 0:
                    data[i-3] = data[i-2] = data[i-1] = 0
                else:
                    data[i] = 255
        return QPixmap.fromImage(
            QImage(bytes(data), img.width(), img.height(),
                   bpl, QImage.Format_ARGB32))

    def _render_rotated(self, w, h, source=None):
        """Render snippet scaled to w*h and rotated, with 2x supersampling.

        Returns a QPixmap containing the rotated result (bounding-box sized,
        transparent corners).  Centre of the returned pixmap corresponds to
        the centre of the target rectangle.
        If *source* is given it is drawn instead of self._snippet.
        """
        src = source if source is not None else self._snippet
        sw, sh = src.width(), src.height()
        SS = 2  # supersample factor
        t_rot = QTransform().rotate(self._angle)
        rotated_bbox = t_rot.mapRect(QRectF(-w / 2.0, -h / 2.0, w, h))
        buf_w = int(math.ceil(abs(rotated_bbox.width()) * SS)) + 4
        buf_h = int(math.ceil(abs(rotated_bbox.height()) * SS)) + 4
        tmp = QPixmap(buf_w, buf_h)
        tmp.fill(Qt.transparent)
        tp = QPainter(tmp)
        tp.setRenderHint(QPainter.SmoothPixmapTransform)
        tp.setRenderHint(QPainter.Antialiasing)
        tp.translate(buf_w / 2.0, buf_h / 2.0)
        tp.rotate(self._angle)
        tp.scale(w * SS / float(sw), h * SS / float(sh))
        tp.translate(-sw / 2.0, -sh / 2.0)
        tp.drawPixmap(0, 0, src)
        tp.end()
        out_w = int(math.ceil(abs(rotated_bbox.width()))) + 2
        out_h = int(math.ceil(abs(rotated_bbox.height()))) + 2
        return tmp.scaled(out_w, out_h, Qt.IgnoreAspectRatio,
                          Qt.SmoothTransformation)

    def _commit(self):
        """Stamp the (possibly transformed) snippet back onto the pixmap."""
        if not (self._snippet and not self._snippet.isNull()
                and self._state in ("selected", "moving", "resizing", "rotating")):
            return
        r = QRectF(self._rect)
        w, h = max(int(r.width()), 1), max(int(r.height()), 1)
        if abs(self._angle) < 0.01:
            # No rotation — single resample at most
            if w == self._snippet.width() and h == self._snippet.height():
                scaled = self._snippet
            else:
                scaled = self._snap_alpha(
                    self._snippet.scaled(w, h, Qt.IgnoreAspectRatio,
                                         Qt.SmoothTransformation))
            needed_w = self._rect.x() + w
            needed_h = self._rect.y() + h
            cur_w, cur_h = self.canvas.pixmap.width(), self.canvas.pixmap.height()
            if needed_w > cur_w or needed_h > cur_h:
                new_pm = QPixmap(max(cur_w, needed_w), max(cur_h, needed_h))
                new_pm.fill(self.canvas.bg_color)
                p = QPainter(new_pm)
                p.setCompositionMode(QPainter.CompositionMode_Source)
                p.drawPixmap(0, 0, self.canvas.pixmap)
                p.drawPixmap(self._rect.topLeft(), scaled)
                p.end()
                self.canvas.pixmap = new_pm
                w_ = self.canvas.window()
                if hasattr(w_, '_update_size_label'):
                    w_._update_size_label()
            else:
                p = QPainter(self.canvas.pixmap)
                p.setCompositionMode(QPainter.CompositionMode_Source)
                p.drawPixmap(self._rect.topLeft(), scaled)
                p.end()
        else:
            # With rotation — 2x supersample for high-quality interpolation
            result = self._snap_alpha(self._render_rotated(w, h))
            dest_x = r.center().x() - result.width() / 2.0
            dest_y = r.center().y() - result.height() / 2.0
            dest_pt = QPointF(dest_x, dest_y)
            # Clip path: rotated rectangle in canvas coordinates
            cx, cy = r.center().x(), r.center().y()
            rad = math.radians(self._angle)
            cos_a, sin_a = math.cos(rad), math.sin(rad)
            clip = QPainterPath()
            corners = [(-w / 2.0, -h / 2.0), (w / 2.0, -h / 2.0),
                       (w / 2.0, h / 2.0), (-w / 2.0, h / 2.0)]
            first = True
            for dx, dy in corners:
                pt = QPointF(dx * cos_a - dy * sin_a + cx,
                             dx * sin_a + dy * cos_a + cy)
                if first:
                    clip.moveTo(pt)
                    first = False
                else:
                    clip.lineTo(pt)
            clip.closeSubpath()
            needed_w = int(math.ceil(dest_x + result.width()))
            needed_h = int(math.ceil(dest_y + result.height()))
            cur_w, cur_h = self.canvas.pixmap.width(), self.canvas.pixmap.height()
            if needed_w > cur_w or needed_h > cur_h:
                new_pm = QPixmap(max(cur_w, needed_w), max(cur_h, needed_h))
                new_pm.fill(self.canvas.bg_color)
                p = QPainter(new_pm)
                p.setCompositionMode(QPainter.CompositionMode_Source)
                p.drawPixmap(0, 0, self.canvas.pixmap)
                p.end()
                self.canvas.pixmap = new_pm
                w_ = self.canvas.window()
                if hasattr(w_, '_update_size_label'):
                    w_._update_size_label()
            p = QPainter(self.canvas.pixmap)
            p.setRenderHint(QPainter.Antialiasing, False)
            p.setClipPath(clip)
            p.setCompositionMode(QPainter.CompositionMode_Source)
            p.drawPixmap(dest_pt, result)
            p.end()
        self.canvas.update()

    # --- Mouse events ---

    def mouse_press(self, event):
        if event.button() != Qt.LeftButton:
            return
        pos = event.pos()
        if self._state in ("selected", "moving"):
            handle = self._hit_handle(pos)
            if handle == "rotate":
                center = QPointF(self._rect.center())
                self._drag_start_angle = math.degrees(
                    math.atan2(pos.y() - center.y(), pos.x() - center.x()))
                self._drag_start_sel_angle = self._angle
                self._state = "rotating"
                return
            elif handle:
                self._active_handle = handle
                opp = self._OPPOSITE[handle]
                self._resize_anchor = self._get_handle_positions()[opp]
                self._drag_start_rect = QRectF(self._rect)
                self._state = "resizing"
                return
            elif self._point_in_selection(pos):
                self._state = "moving"
                self._move_offset = QPointF(pos.x() - self._rect.center().x(),
                                            pos.y() - self._rect.center().y())
                return
        # Click outside or no selection — commit and start new
        if self._state in ("selected", "moving", "resizing", "rotating"):
            self._commit()
        self.canvas.save_undo()
        self._state = "selecting"
        self._start = pos
        self._rect = QRect(pos, pos)
        self._snippet = None
        self._angle = 0.0

    def mouse_move(self, event):
        pos = event.pos()
        if self._state == "selecting":
            self._rect = QRect(self._start, pos).normalized()
            self.canvas.update()
        elif self._state == "moving" and self._move_offset is not None:
            nc = QPointF(pos.x(), pos.y()) - self._move_offset
            self._rect.moveCenter(QPoint(int(nc.x()), int(nc.y())))
            self.canvas.update()
        elif self._state == "resizing":
            self._do_resize(pos)
            self.canvas.update()
        elif self._state == "rotating":
            self._do_rotate(pos)
            self.canvas.update()

    def _do_resize(self, pos):
        anchor = self._resize_anchor
        mouse = QPointF(pos.x(), pos.y())
        rad = math.radians(self._angle)
        cos_a, sin_a = math.cos(rad), math.sin(rad)
        vx, vy = mouse.x() - anchor.x(), mouse.y() - anchor.y()
        proj_x = vx * cos_a + vy * sin_a
        proj_y = -vx * sin_a + vy * cos_a
        handle = self._active_handle
        orig_w = self._drag_start_rect.width()
        orig_h = self._drag_start_rect.height()
        new_w = max(abs(proj_x), 4) if handle in self._CHANGES_X else orig_w
        new_h = max(abs(proj_y), 4) if handle in self._CHANGES_Y else orig_h
        sx = (proj_x / 2) if handle in self._CHANGES_X else 0
        sy = (proj_y / 2) if handle in self._CHANGES_Y else 0
        cx = anchor.x() + sx * cos_a - sy * sin_a
        cy = anchor.y() + sx * sin_a + sy * cos_a
        self._rect = QRect(int(cx - new_w / 2), int(cy - new_h / 2),
                           int(new_w), int(new_h))

    def _do_rotate(self, pos):
        center = QPointF(self._rect.center())
        cur = math.degrees(math.atan2(pos.y() - center.y(),
                                      pos.x() - center.x()))
        self._angle = self._drag_start_sel_angle + (cur - self._drag_start_angle)

    def mouse_release(self, event):
        if self._state == "selecting":
            self._rect = QRect(self._start, event.pos()).normalized()
            if self._rect.width() > 1 and self._rect.height() > 1:
                self._snippet = self.canvas.pixmap.copy(self._rect)
                p = QPainter(self.canvas.pixmap)
                p.fillRect(self._rect, self.canvas.bg_color)
                p.end()
                self._make_snippet_display()
                self._state = "selected"
            else:
                self._reset()
            self.canvas.update()
        elif self._state == "moving":
            self._state = "selected"
            self.canvas.set_modified()
        elif self._state == "resizing":
            self._state = "selected"
            self._active_handle = None
            self.canvas.set_modified()
        elif self._state == "rotating":
            self._state = "selected"
            self.canvas.set_modified()

    # --- Overlay rendering ---

    def paint_overlay(self, painter):
        if self._state == "selecting":
            pen_b = QPen(QColor(0, 0, 0, 180), 0)
            pen_b.setCosmetic(True)
            pen_w = QPen(QColor(255, 255, 255, 180), 0, Qt.DashLine)
            pen_w.setCosmetic(True)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(pen_b)
            painter.drawRect(self._rect)
            painter.setPen(pen_w)
            painter.drawRect(self._rect)
        elif self._state in ("selected", "moving", "resizing", "rotating"):
            r = QRectF(self._rect)
            hw, hh = r.width() / 2, r.height() / 2
            center = r.center()
            inv_z = 1.0 / self.canvas.zoom if self.canvas.zoom > 0 else 1.0
            # Draw snippet (rotated + scaled) with checkerboard behind transparency
            display = self._snippet_display if self._snippet_display else self._snippet
            if display and not display.isNull():
                painter.save()
                painter.translate(center)
                painter.rotate(self._angle)
                painter.drawPixmap(QRectF(-hw, -hh, r.width(), r.height()),
                                   display, QRectF(display.rect()))
                painter.restore()
            # Border and handles (in rotated space)
            painter.save()
            painter.translate(center)
            painter.rotate(self._angle)
            rect_f = QRectF(-hw, -hh, r.width(), r.height())
            pen_b = QPen(QColor(0, 0, 0, 180), 0)
            pen_b.setCosmetic(True)
            pen_w = QPen(QColor(255, 255, 255, 180), 0, Qt.DashLine)
            pen_w.setCosmetic(True)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(pen_b)
            painter.drawRect(rect_f)
            painter.setPen(pen_w)
            painter.drawRect(rect_f)
            # Rotation handle: line + circle above top-center
            pw = inv_z
            rot_off = 20 * inv_z
            painter.setPen(QPen(QColor(0, 120, 215), pw))
            painter.drawLine(QPointF(0, -hh), QPointF(0, -hh - rot_off))
            painter.setBrush(QColor(0, 120, 215))
            rr = 4 * inv_z
            painter.drawEllipse(QPointF(0, -hh - rot_off), rr, rr)
            # Resize handles (white squares with black border)
            hs = 4 * inv_z
            painter.setPen(QPen(QColor(0, 0, 0), pw))
            painter.setBrush(QColor(255, 255, 255))
            for hx, hy in [(-hw, -hh), (0, -hh), (hw, -hh), (hw, 0),
                           (hw, hh), (0, hh), (-hw, hh), (-hw, 0)]:
                painter.drawRect(QRectF(hx - hs, hy - hs, hs * 2, hs * 2))
            painter.restore()

    def get_cursor(self):
        return Qt.CrossCursor

    # --- Clipboard operations ---

    def _get_transformed_snippet(self):
        """Return snippet with current scale and rotation applied."""
        r = QRectF(self._rect)
        w, h = max(int(r.width()), 1), max(int(r.height()), 1)
        sw, sh = self._snippet.width(), self._snippet.height()
        if abs(self._angle) < 0.01:
            if w == sw and h == sh:
                return self._snippet.copy()
            return self._snippet.scaled(w, h, Qt.IgnoreAspectRatio,
                                        Qt.SmoothTransformation)
        return self._render_rotated(w, h)

    def copy_selection(self):
        if self._snippet and not self._snippet.isNull():
            QApplication.clipboard().setPixmap(self._get_transformed_snippet())

    def cut_selection(self):
        self.copy_selection()
        self._snippet = None
        self._reset()
        self.canvas.update()
        self.canvas.set_modified()

    def delete_selection(self):
        self._snippet = None
        self._reset()
        self.canvas.update()
        self.canvas.set_modified()

    def paste(self, pixmap, center=None):
        """Paste a pixmap as a new floating selection.

        *center* is an optional canvas-coordinate QPoint; the pasted image
        is centred there.  When the pasted image is larger than the canvas
        the canvas is expanded and the image placed at (0, 0).
        """
        self._commit()
        self.canvas.save_undo()
        pw, ph = pixmap.width(), pixmap.height()
        cw, ch = self.canvas.pixmap.width(), self.canvas.pixmap.height()
        if pw > cw or ph > ch:
            # Expand canvas to fit – place image at origin
            new_pm = QPixmap(max(cw, pw), max(ch, ph))
            new_pm.fill(self.canvas.bg_color)
            p = QPainter(new_pm)
            p.setCompositionMode(QPainter.CompositionMode_Source)
            p.drawPixmap(0, 0, self.canvas.pixmap)
            p.end()
            self.canvas.pixmap = new_pm
            self.canvas.update()
            w = self.canvas.window()
            if hasattr(w, '_update_size_label'):
                w._update_size_label()
            # Large paste always starts at origin so nothing is clipped
            x, y = 0, 0
        elif center is not None:
            x = center.x() - pw // 2
            y = center.y() - ph // 2
        else:
            x, y = 0, 0
        self._snippet = pixmap
        self._make_snippet_display()
        self._rect = QRect(QPoint(x, y), pixmap.size())
        self._angle = 0.0
        self._state = "selected"
        self.canvas.update()

    def select_all(self):
        self._commit()
        self.canvas.save_undo()
        r = self.canvas.pixmap.rect()
        self._snippet = self.canvas.pixmap.copy(r)
        p = QPainter(self.canvas.pixmap)
        p.fillRect(r, self.canvas.bg_color)
        p.end()
        self._make_snippet_display()
        self._rect = r
        self._angle = 0.0
        self._state = "selected"
        self.canvas.update()

    def has_selection(self):
        return (self._state in ("selected", "moving", "resizing", "rotating")
                and self._snippet is not None)


# ---------------------------------------------------------------------------
# Canvas widget
# ---------------------------------------------------------------------------
class Canvas(QWidget):
    color_changed = pyqtSignal()
    modified_changed = pyqtSignal()
    zoom_changed = pyqtSignal(float)
    cursor_moved = pyqtSignal(int, int)

    @property
    def pixmap(self):
        return self._pixmap

    @pixmap.setter
    def pixmap(self, pm):
        """Ensure the canvas pixmap always has an alpha channel."""
        if isinstance(pm, QPixmap) and not pm.hasAlphaChannel():
            alpha_pm = QPixmap(pm.size())
            alpha_pm.fill(Qt.transparent)
            p = QPainter(alpha_pm)
            p.drawPixmap(0, 0, pm)
            p.end()
            self._pixmap = alpha_pm
        else:
            self._pixmap = pm

    def __init__(self, width=DEFAULT_WIDTH, height=DEFAULT_HEIGHT, parent=None):
        super().__init__(parent)
        self._pixmap = QPixmap(width, height)
        self._pixmap.fill(Qt.transparent)
        p = QPainter(self._pixmap)
        p.fillRect(0, 0, width, height, Qt.white)
        p.end()

        self.fg_color = QColor(Qt.black)
        self.bg_color = QColor(Qt.white)
        self.brush_size = 3
        self.shape_fill_mode = ShapeFillMode.OUTLINE
        self.antialiasing = True
        self.zoom = 1.0
        self._modified = False

        # Pan offset: where pixmap origin sits in widget coords (before zoom)
        self._pan_offset = QPoint(40, 40)
        self._pending_center = True  # center on first real resize

        # Undo / redo stacks
        self._undo_stack = []
        self._redo_stack = []

        # Tools
        self._tools = {
            ToolType.PENCIL: PencilTool(self),
            ToolType.BRUSH: BrushTool(self),
            ToolType.ERASER: EraserTool(self),
            ToolType.ALPHA_BRUSH: AlphaBrushTool(self),
            ToolType.LINE: LineTool(self),
            ToolType.RECTANGLE: RectangleTool(self),
            ToolType.ELLIPSE: EllipseTool(self),
            ToolType.TEXT: TextTool(self),
            ToolType.FILL: FillTool(self),
            ToolType.PICKER: PickerTool(self),
            ToolType.SELECTION: SelectionTool(self),
        }
        self._current_tool_type = ToolType.PENCIL
        self._current_tool = self._tools[ToolType.PENCIL]

        self._mouse_pos = QPoint(-1, -1)  # widget-space mouse position
        # Pre-built checker tile for transparency display
        cs = 8
        self._checker_tile = QPixmap(cs * 2, cs * 2)
        cp = QPainter(self._checker_tile)
        cp.fillRect(0, 0, cs, cs, QColor(220, 180, 220))
        cp.fillRect(cs, 0, cs, cs, QColor(180, 140, 180))
        cp.fillRect(0, cs, cs, cs, QColor(180, 140, 180))
        cp.fillRect(cs, cs, cs, cs, QColor(220, 180, 220))
        cp.end()

        self._init_wheel_timer()

        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setAcceptDrops(True)

    # --- Tool switching ---
    def set_tool(self, tool_type):
        if self._current_tool_type == tool_type:
            return
        self._current_tool.deactivate()
        self._current_tool_type = tool_type
        self._current_tool = self._tools[tool_type]
        self._current_tool.activate()
        if tool_type in self._SIZE_CURSOR_TOOLS:
            self.setCursor(Qt.BlankCursor)
        else:
            self.setCursor(self._current_tool.get_cursor())
        self.update()

    def current_tool_type(self):
        return self._current_tool_type

    def current_tool(self):
        return self._current_tool

    def make_painter(self):
        """Create a QPainter on the pixmap with current AA setting."""
        p = QPainter(self.pixmap)
        if self.antialiasing:
            p.setRenderHint(QPainter.Antialiasing)
        return p

    # --- Modified state ---
    @property
    def modified(self):
        return self._modified

    def set_modified(self, val=True):
        if self._modified != val:
            self._modified = val
            self.modified_changed.emit()

    # --- Undo / Redo ---
    def save_undo(self):
        self._undo_stack.append(self.pixmap.copy())
        if len(self._undo_stack) > MAX_UNDO:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        if not self._undo_stack:
            return
        self._redo_stack.append(self.pixmap.copy())
        self.pixmap = self._undo_stack.pop()
        self.update()
        self.set_modified()
        w = self.window()
        if hasattr(w, '_update_size_label'):
            w._update_size_label()

    def redo(self):
        if not self._redo_stack:
            return
        self._undo_stack.append(self.pixmap.copy())
        self.pixmap = self._redo_stack.pop()
        self.update()
        self.set_modified()
        w = self.window()
        if hasattr(w, '_update_size_label'):
            w._update_size_label()

    # --- Zoom ---
    def set_zoom(self, z, anchor=None):
        """Set zoom level. anchor is a widget-space point to zoom toward."""
        z = max(ZOOM_MIN, min(ZOOM_MAX, z))
        if abs(z - self.zoom) < 1e-9:
            return
        if anchor is None:
            anchor = QPoint(self.width() // 2, self.height() // 2)
        # Adjust offset so the point under anchor stays fixed
        old_z = self.zoom
        self._pan_offset = anchor - ((anchor - self._pan_offset) * z / old_z)
        self.zoom = z
        # Notify current tool so it can reposition overlay widgets
        if hasattr(self._current_tool, 'on_zoom_changed'):
            self._current_tool.on_zoom_changed()
        self.update()
        self.zoom_changed.emit(z)

    def zoom_in(self):
        self.set_zoom(self.zoom + ZOOM_STEP)

    def zoom_out(self):
        self.set_zoom(self.zoom - ZOOM_STEP)

    def zoom_reset(self):
        self.set_zoom(1.0)

    def center_canvas(self):
        """Center the pixmap in the widget."""
        pw = int(self.pixmap.width() * self.zoom)
        ph = int(self.pixmap.height() * self.zoom)
        self._pan_offset = QPoint((self.width() - pw) // 2,
                                  (self.height() - ph) // 2)
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pending_center:
            self.center_canvas()

    # --- Wheel zoom / brush size ---
    _brush_wheel_accum = 0
    _zoom_wheel_notches = 0.0
    _zoom_anchor = None
    brush_size_changed = pyqtSignal(int)

    _ZOOM_NOTCH_FACTOR = 1.15

    def _init_wheel_timer(self):
        """Set up a single-shot 0ms timer that fires once the event queue is
        drained.  All wheel deltas accumulated while the queue was busy are
        applied in one batch, followed by exactly one
        ``update()``/paint cycle."""
        self._wheel_timer = QTimer(self)
        self._wheel_timer.setSingleShot(True)
        self._wheel_timer.setInterval(0)
        self._wheel_timer.timeout.connect(self._flush_wheel)

    def wheelEvent(self, event):
        raw_y = event.angleDelta().y()
        if event.modifiers() & Qt.ShiftModifier:
            self._brush_wheel_accum += raw_y
        elif raw_y != 0:
            self._zoom_wheel_notches += raw_y / 120.0
            self._zoom_anchor = event.pos()
        if not self._wheel_timer.isActive():
            self._wheel_timer.start()
        event.accept()

    def _flush_wheel(self):
        """Apply accumulated zoom and brush-size changes, then repaint once."""
        if self._zoom_wheel_notches != 0:
            factor = self._ZOOM_NOTCH_FACTOR ** self._zoom_wheel_notches
            new_z = max(ZOOM_MIN, min(ZOOM_MAX, self.zoom * factor))
            self._zoom_wheel_notches = 0.0
            self.set_zoom(new_z, self._zoom_anchor)
        if self._brush_wheel_accum >= 120 or self._brush_wheel_accum <= -120:
            while self._brush_wheel_accum >= 120:
                self._brush_wheel_accum -= 120
                self.brush_size = min(100, self.brush_size + 1)
            while self._brush_wheel_accum <= -120:
                self._brush_wheel_accum += 120
                self.brush_size = max(1, self.brush_size - 1)
            self.brush_size_changed.emit(self.brush_size)
            self.update()

    # --- Coordinate helpers ---
    def _canvas_pos(self, event):
        """Map widget position to pixmap coordinates."""
        wp = event.pos()
        return QPoint(int((wp.x() - self._pan_offset.x()) / self.zoom),
                      int((wp.y() - self._pan_offset.y()) / self.zoom))

    def _is_over_canvas(self, widget_pos):
        """Check if a widget-space position is over the pixmap area."""
        cx = (widget_pos.x() - self._pan_offset.x()) / self.zoom
        cy = (widget_pos.y() - self._pan_offset.y()) / self.zoom
        return 0 <= cx < self.pixmap.width() and 0 <= cy < self.pixmap.height()

    def _near_canvas_corner(self, widget_pos, margin=8):
        """Check if widget_pos is near the bottom-right corner of the canvas."""
        br_x = self._pan_offset.x() + self.pixmap.width() * self.zoom
        br_y = self._pan_offset.y() + self.pixmap.height() * self.zoom
        dx = abs(widget_pos.x() - br_x)
        dy = abs(widget_pos.y() - br_y)
        return dx < margin and dy < margin

    # --- Middle-mouse pan state ---
    _pan_active = False
    _pan_start = QPoint()

    # --- Corner-drag resize state ---
    _resize_active = False
    _resize_preview_size = None  # QSize during drag

    # --- Mouse events ---
    def mousePressEvent(self, event):
        self._pending_center = False
        self.setFocus()
        if event.button() == Qt.MiddleButton:
            self._pan_active = True
            self._pan_start = event.globalPos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._near_canvas_corner(event.pos()):
            self._resize_active = True
            self._resize_preview_size = self.pixmap.size()
            self.setCursor(Qt.SizeFDiagCursor)
            event.accept()
            return
        e = self._make_canvas_event(event)
        self._current_tool.mouse_press(e)

    def mouseMoveEvent(self, event):
        self._mouse_pos = event.pos()
        if self._pan_active:
            delta = event.globalPos() - self._pan_start
            self._pan_start = event.globalPos()
            self._pan_offset += delta
            if hasattr(self._current_tool, 'on_zoom_changed'):
                self._current_tool.on_zoom_changed()
            self.update()
            event.accept()
            return
        if self._resize_active:
            new_w = max(1, int((event.pos().x() - self._pan_offset.x()) / self.zoom))
            new_h = max(1, int((event.pos().y() - self._pan_offset.y()) / self.zoom))
            self._resize_preview_size = QSize(new_w, new_h)
            w = self.window()
            if hasattr(w, '_size_label'):
                w._size_label.setText(f"{new_w} x {new_h} px")
            self.update()
            event.accept()
            return
        # Show resize cursor when near corner (before tool cursor logic)
        if self._near_canvas_corner(event.pos()):
            if self.cursor().shape() != Qt.SizeFDiagCursor:
                self.setCursor(Qt.SizeFDiagCursor)
        # Toggle cursor: blank over canvas for size-cursor tools, normal otherwise
        elif self._current_tool_type in self._SIZE_CURSOR_TOOLS:
            if self._is_over_canvas(event.pos()):
                if self.cursor().shape() != Qt.BlankCursor:
                    self.setCursor(Qt.BlankCursor)
            else:
                if self.cursor().shape() == Qt.BlankCursor:
                    self.setCursor(Qt.ArrowCursor)
        elif self._current_tool_type == ToolType.SELECTION:
            cp = self._canvas_pos(event)
            cur = self._current_tool.cursor_at(cp)
            if self.cursor().shape() != cur:
                self.setCursor(cur)
        elif self.cursor().shape() == Qt.SizeFDiagCursor:
            self.setCursor(self._current_tool.get_cursor())
        cp = self._canvas_pos(event)
        self.cursor_moved.emit(cp.x(), cp.y())
        e = self._make_canvas_event(event)
        self._current_tool.mouse_move(e)
        self.update()  # repaint for cursor circle

    def leaveEvent(self, event):
        self._mouse_pos = QPoint(-1, -1)
        if self.cursor().shape() == Qt.BlankCursor:
            self.setCursor(Qt.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton and self._pan_active:
            self._pan_active = False
            if self._current_tool_type in self._SIZE_CURSOR_TOOLS:
                self.setCursor(Qt.BlankCursor)
            else:
                self.setCursor(self._current_tool.get_cursor())
            event.accept()
            return
        if event.button() == Qt.LeftButton and self._resize_active:
            self._resize_active = False
            sz = self._resize_preview_size
            self._resize_preview_size = None
            if sz and (sz.width() != self.pixmap.width()
                       or sz.height() != self.pixmap.height()):
                self.resize_canvas(sz.width(), sz.height())
            w = self.window()
            if hasattr(w, '_update_size_label'):
                w._update_size_label()
            self.setCursor(self._current_tool.get_cursor())
            event.accept()
            return
        e = self._make_canvas_event(event)
        self._current_tool.mouse_release(e)

    def _make_canvas_event(self, event):
        """Create a lightweight wrapper with canvas-space pos()."""
        class _E:
            pass
        e = _E()
        e.pos = lambda: self._canvas_pos(event)
        e.button = event.button
        e.buttons = event.buttons
        e.modifiers = event.modifiers
        return e

    # --- Drag and drop ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls():
            for url in mime.urls():
                path = url.toLocalFile()
                if path:
                    self.window().open_file(path)
                    return
        if mime.hasImage():
            img = mime.imageData()
            if isinstance(img, QImage) and not img.isNull():
                self.pixmap = QPixmap.fromImage(img)
            elif isinstance(img, QPixmap) and not img.isNull():
                self.pixmap = img
            self.center_canvas()
            w = self.window()
            if hasattr(w, '_update_size_label'):
                w._update_size_label()
            self.set_modified()

    # --- Keyboard fallback (in case QAction shortcuts don't fire) ---
    def keyPressEvent(self, event):
        log.info(f"[key] {event.key()} mods={int(event.modifiers())}")
        mods = event.modifiers()
        key = event.key()
        ctrl = mods & Qt.ControlModifier
        shift = mods & Qt.ShiftModifier
        if ctrl and key == Qt.Key_V:
            self.window()._edit_paste()
        elif ctrl and key == Qt.Key_C:
            self.window()._edit_copy()
        elif ctrl and key == Qt.Key_X:
            self.window()._edit_cut()
        elif ctrl and key == Qt.Key_A:
            self.window()._edit_select_all()
        elif ctrl and key == Qt.Key_Z:
            self.undo()
        elif ctrl and key == Qt.Key_Y:
            self.redo()
        elif ctrl and key == Qt.Key_N:
            self.window()._file_new()
        elif ctrl and key == Qt.Key_O:
            self.window()._file_open()
        elif ctrl and shift and key == Qt.Key_S:
            self.window()._file_save_as()
        elif ctrl and key == Qt.Key_S:
            self.window()._file_save()
        elif ctrl and key == Qt.Key_Equal:
            self.zoom_in()
        elif ctrl and key == Qt.Key_Minus:
            self.zoom_out()
        elif ctrl and key == Qt.Key_0:
            self.zoom_reset()
        elif key == Qt.Key_Delete:
            self.window()._edit_delete()
        elif not ctrl and not shift and key in TOOL_SHORTCUTS:
            self.window()._on_tool_selected(TOOL_SHORTCUTS[key])
        else:
            super().keyPressEvent(event)

    _SIZE_CURSOR_TOOLS = {ToolType.BRUSH, ToolType.ERASER, ToolType.ALPHA_BRUSH,
                          ToolType.LINE, ToolType.RECTANGLE, ToolType.ELLIPSE}

    # --- Pixel-snapped brush outline cache ---
    _brush_outline_cache = (-1, None)  # (brush_size, QPainterPath)

    def _get_brush_outline(self, brush_size):
        """Return a QPainterPath tracing the pixel outline of a round brush,
        centered at origin in canvas pixel coordinates.  Cached per size."""
        if self._brush_outline_cache[0] == brush_size:
            return self._brush_outline_cache[1]

        # Rasterize one dot at canvas resolution (no AA, matches brush drawing)
        pad = 2
        s = brush_size + pad * 2
        center = s // 2
        img = QImage(s, s, QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.Antialiasing, False)
        p.setPen(QPen(Qt.white, brush_size, Qt.SolidLine, Qt.RoundCap))
        p.drawPoint(center, center)
        p.end()

        # Fast alpha access via raw bytes
        stride = img.bytesPerLine()
        ptr = img.constBits()
        ptr.setsize(s * stride)
        buf = bytes(ptr)

        def alpha(x, y):
            if 0 <= x < s and 0 <= y < s:
                return buf[y * stride + x * 4 + 3]
            return 0

        ox, oy = center, center
        path = QPainterPath()

        # Horizontal edges (top / bottom), merged per row
        for y in range(s):
            x = 0
            while x < s:
                if alpha(x, y) and not alpha(x, y - 1):
                    xs = x
                    while x < s and alpha(x, y) and not alpha(x, y - 1):
                        x += 1
                    path.moveTo(xs - ox, y - oy)
                    path.lineTo(x - ox, y - oy)
                else:
                    x += 1
            x = 0
            while x < s:
                if alpha(x, y) and not alpha(x, y + 1):
                    xs = x
                    while x < s and alpha(x, y) and not alpha(x, y + 1):
                        x += 1
                    path.moveTo(xs - ox, (y + 1) - oy)
                    path.lineTo(x - ox, (y + 1) - oy)
                else:
                    x += 1

        # Vertical edges (left / right), merged per column
        for x in range(s):
            y = 0
            while y < s:
                if alpha(x, y) and not alpha(x - 1, y):
                    ys = y
                    while y < s and alpha(x, y) and not alpha(x - 1, y):
                        y += 1
                    path.moveTo(x - ox, ys - oy)
                    path.lineTo(x - ox, y - oy)
                else:
                    y += 1
            y = 0
            while y < s:
                if alpha(x, y) and not alpha(x + 1, y):
                    ys = y
                    while y < s and alpha(x, y) and not alpha(x + 1, y):
                        y += 1
                    path.moveTo((x + 1) - ox, ys - oy)
                    path.lineTo((x + 1) - ox, y - oy)
                else:
                    y += 1

        self._brush_outline_cache = (brush_size, path)
        return path

    # --- Paint ---
    _paint_count = 0
    _last_paint_time = 0.0

    def paintEvent(self, event):
        import time
        t0 = time.perf_counter()
        self._paint_count += 1
        dt = (t0 - self._last_paint_time) * 1000
        self._last_paint_time = t0

        painter = QPainter(self)
        # Gray workspace background
        painter.fillRect(self.rect(), QColor(128, 128, 128))
        # Draw pixmap and tool overlay in canvas coordinate space
        painter.translate(self._pan_offset)
        painter.scale(self.zoom, self.zoom)
        # Checkerboard behind canvas to show transparency (with parallax)
        # Offset the tiling origin so the checkerboard scrolls at half the
        # canvas rate, creating a subtle depth/parallax effect.
        tile_w = self._checker_tile.width()
        tile_h = self._checker_tile.height()
        parallax = 0.5  # 0 = locked to canvas, 1 = locked to screen
        px_off = int(self._pan_offset.x() * parallax / self.zoom) % tile_w
        py_off = int(self._pan_offset.y() * parallax / self.zoom) % tile_h
        painter.drawTiledPixmap(0, 0, self.pixmap.width(), self.pixmap.height(),
                                self._checker_tile,
                                px_off, py_off)
        painter.drawPixmap(0, 0, self.pixmap)
        if self.antialiasing:
            painter.setRenderHint(QPainter.Antialiasing)
        self._current_tool.paint_overlay(painter)
        # Pixel-snapped brush outline (drawn in canvas coords so it aligns
        # with the pixel grid when zoomed in)
        _draw_cursor = (self._mouse_pos.x() >= 0
                        and self._current_tool_type in self._SIZE_CURSOR_TOOLS
                        and self._is_over_canvas(self._mouse_pos))
        if _draw_cursor:
            mx, my = self._mouse_pos.x(), self._mouse_pos.y()
            cx = int((mx - self._pan_offset.x()) / self.zoom)
            cy = int((my - self._pan_offset.y()) / self.zoom)
            outline = self._get_brush_outline(self.brush_size)
            painter.save()
            painter.translate(cx, cy)
            painter.setRenderHint(QPainter.Antialiasing, False)
            pen_b = QPen(QColor(0, 0, 0, 180), 0)
            pen_b.setCosmetic(True)
            painter.setPen(pen_b)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(outline)
            pen_w = QPen(QColor(255, 255, 255, 180), 0, Qt.DashLine)
            pen_w.setCosmetic(True)
            painter.setPen(pen_w)
            painter.drawPath(outline)
            painter.restore()
        painter.resetTransform()
        # Resize drag preview (dashed outline in widget coords)
        if self._resize_active and self._resize_preview_size:
            sz = self._resize_preview_size
            rx = self._pan_offset.x()
            ry = self._pan_offset.y()
            rw = sz.width() * self.zoom
            rh = sz.height() * self.zoom
            pen_k = QPen(QColor(0, 0, 0), 1, Qt.DashLine)
            pen_k.setCosmetic(True)
            painter.setPen(pen_k)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(QRectF(rx, ry, rw, rh))
            pen_wh = QPen(QColor(255, 255, 255), 1, Qt.DashLine)
            pen_wh.setCosmetic(True)
            pen_wh.setDashOffset(4)
            painter.setPen(pen_wh)
            painter.drawRect(QRectF(rx, ry, rw, rh))
            # Dimensions label near corner
            painter.setPen(QPen(QColor(0, 0, 0)))
            painter.drawText(int(rx + rw + 4), int(ry + rh + 14),
                             f"{sz.width()} x {sz.height()}")
        # Grip square at bottom-right corner (visual affordance)
        if not self._resize_active:
            br_x = self._pan_offset.x() + self.pixmap.width() * self.zoom
            br_y = self._pan_offset.y() + self.pixmap.height() * self.zoom
            s = 6
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QColor(255, 255, 255))
            painter.drawRect(QRectF(br_x - s / 2, br_y - s / 2, s, s))
        # Crosshair at exact mouse position (widget coords, XOR for visibility)
        if _draw_cursor:
            painter.setRenderHint(QPainter.Antialiasing, False)
            painter.setCompositionMode(QPainter.RasterOp_SourceXorDestination)
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            c = 4
            painter.drawLine(mx - c, my, mx + c, my)
            painter.drawLine(mx, my - c, mx, my + c)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        painter.end()
        import time
        elapsed = (time.perf_counter() - t0) * 1000
        if elapsed > 5 or self._paint_count % 50 == 0:
            log.debug(
                f"[paint #{self._paint_count}] dt_since_last={dt:.1f}ms "
                f"paint_ms={elapsed:.1f} zoom={self.zoom:.4f} "
                f"canvas={self.pixmap.width()}x{self.pixmap.height()}"
            )

    # --- Canvas operations ---
    def commit_selection(self):
        """Commit any floating selection back to the pixmap."""
        tool = self._tools.get(ToolType.SELECTION)
        if tool and tool.has_selection():
            tool._commit()
            tool._reset()

    def clear_canvas(self):
        log.info("[clear_canvas] called")
        self.commit_selection()
        self.save_undo()
        self.pixmap.fill(self.bg_color)
        self.update()
        self.set_modified()

    def resize_canvas(self, new_w, new_h):
        self.commit_selection()
        self.save_undo()
        new_pm = QPixmap(new_w, new_h)
        new_pm.fill(self.bg_color)
        p = QPainter(new_pm)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.drawPixmap(0, 0, self.pixmap)
        p.end()
        self.pixmap = new_pm
        self.update()
        self.set_modified()

    def rotate(self, degrees):
        log.info(f"[rotate] {degrees}")
        self.commit_selection()
        self.save_undo()
        transform = QTransform().rotate(degrees)
        img = self.pixmap.toImage()
        img = img.transformed(transform)
        self.pixmap = QPixmap.fromImage(img)
        w = self.window()
        if hasattr(w, '_update_size_label'):
            w._update_size_label()
        self.update()
        self.set_modified()

    def flip_horizontal(self):
        log.info("[flip_h] called")
        self.commit_selection()
        self.save_undo()
        img = self.pixmap.toImage().mirrored(True, False)
        self.pixmap = QPixmap.fromImage(img)
        self.update()
        self.set_modified()

    def flip_vertical(self):
        self.commit_selection()
        self.save_undo()
        img = self.pixmap.toImage().mirrored(False, True)
        self.pixmap = QPixmap.fromImage(img)
        self.update()
        self.set_modified()

    def load_image(self, path):
        img = QImage(path)
        if img.isNull():
            return False
        self.pixmap = QPixmap.fromImage(img)
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.center_canvas()
        w = self.window()
        if hasattr(w, '_update_size_label'):
            w._update_size_label()
        self.set_modified(False)
        return True

    def new_canvas(self, w=DEFAULT_WIDTH, h=DEFAULT_HEIGHT):
        self.pixmap = QPixmap(w, h)
        self.pixmap.fill(Qt.transparent)
        p = QPainter(self.pixmap)
        p.fillRect(0, 0, w, h, Qt.white)
        p.end()
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.center_canvas()
        self.set_modified(False)


# ---------------------------------------------------------------------------
# Dialogs
# ---------------------------------------------------------------------------
class ResizeDialog(QDialog):
    PRESETS = [
        ("640 x 480", 640, 480),
        ("800 x 600", 800, 600),
        ("1024 x 768", 1024, 768),
        ("1280 x 720 (HD)", 1280, 720),
        ("1920 x 1080 (Full HD)", 1920, 1080),
        ("2560 x 1440 (QHD)", 2560, 1440),
        ("3840 x 2160 (4K)", 3840, 2160),
        ("256 x 256", 256, 256),
        ("512 x 512", 512, 512),
        ("1024 x 1024", 1024, 1024),
    ]

    def __init__(self, current_w, current_h, parent=None, pixmap=None):
        super().__init__(parent)
        self.setWindowTitle("Resize Canvas")
        self._pixmap = pixmap
        layout = QVBoxLayout(self)

        form = QGridLayout()
        form.addWidget(QLabel("Width:"), 0, 0)
        self.w_spin = QSpinBox()
        self.w_spin.setRange(1, 10000)
        self.w_spin.setValue(current_w)
        form.addWidget(self.w_spin, 0, 1)

        form.addWidget(QLabel("Height:"), 1, 0)
        self.h_spin = QSpinBox()
        self.h_spin.setRange(1, 10000)
        self.h_spin.setValue(current_h)
        form.addWidget(self.h_spin, 1, 1)
        layout.addLayout(form)

        # --- Presets ---
        preset_label = QLabel("Presets:")
        layout.addWidget(preset_label)
        self._preset_combo = QComboBox()
        self._preset_combo.addItem("— Select preset —")
        for name, w, h in self.PRESETS:
            self._preset_combo.addItem(name)
        self._preset_combo.currentIndexChanged.connect(self._on_preset)
        layout.addWidget(self._preset_combo)

        # --- Trim to content ---
        trim_btn = QPushButton("Trim to Content")
        trim_btn.setToolTip("Resize to the bounding box of non-white / non-transparent pixels")
        trim_btn.clicked.connect(self._on_trim)
        layout.addWidget(trim_btn)

        btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    def _on_preset(self, index):
        if index <= 0:
            return
        _, w, h = self.PRESETS[index - 1]
        self.w_spin.setValue(w)
        self.h_spin.setValue(h)

    def _on_trim(self):
        if self._pixmap is None:
            return
        img = self._pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        w, h = img.width(), img.height()
        # Use raw pixel data for speed (ARGB32: 4 bytes per pixel)
        ptr = img.constBits()
        ptr.setsize(h * img.bytesPerLine())
        data = bytes(ptr)
        bpl = img.bytesPerLine()
        min_x, min_y, max_x, max_y = w, h, -1, -1
        for y in range(h):
            row_off = y * bpl
            for x in range(w):
                off = row_off + x * 4
                b, g, r, a = data[off], data[off+1], data[off+2], data[off+3]
                # Skip fully transparent or fully white pixels
                if a == 0:
                    continue
                if r == 255 and g == 255 and b == 255:
                    continue
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y
        if max_x < 0:
            return
        self._trim_offset = (min_x, min_y)
        self.w_spin.setValue(max_x - min_x + 1)
        self.h_spin.setValue(max_y - min_y + 1)

    def get_size(self):
        return self.w_spin.value(), self.h_spin.value()

    def get_trim_offset(self):
        """Return (x, y) offset from trim, or None if not trimmed."""
        return getattr(self, '_trim_offset', None)


class _InlineTextEditor(QPlainTextEdit):
    """Transparent text editor overlay.

    Text is invisible (rendered by paint_overlay for WYSIWYG).  The editor
    provides cursor positioning, text selection highlights, and a blinking
    caret drawn manually.
    """
    commit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._cursor_on = True
        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(530)
        self.setCursorWidth(0)  # hide built-in cursor; we draw our own

    def _blink(self):
        self._cursor_on = not self._cursor_on
        self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        # Draw blinking caret using cursorRect for position (so it stays
        # consistent with QPlainTextEdit's selection/click handling) but
        # clamp height to font ascent+descent.
        if self._cursor_on and self.hasFocus():
            cr = self.cursorRect(self.textCursor())
            fm = self.fontMetrics()
            x = cr.left()
            top = cr.top()
            bot = top + fm.ascent() + fm.descent()
            p = QPainter(self.viewport())
            p.setPen(QPen(QColor(0, 0, 0), 1))
            p.drawLine(x, top, x, bot)
            p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.parent().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MiddleButton:
            self.parent().mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.parent().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.commit_requested.emit()
        else:
            super().keyPressEvent(event)
            self.ensureCursorVisible()
            # Reset blink so cursor is visible right after typing
            self._cursor_on = True
            self.viewport().update()


# ---------------------------------------------------------------------------
# UI widgets
# ---------------------------------------------------------------------------
def _make_tool_icon(tool_type, size=24):
    """Draw a simple icon for each tool programmatically."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(40, 40, 40), 1.5)
    p.setPen(pen)
    m = 3  # margin

    if tool_type == ToolType.PENCIL:
        p.drawLine(m, size - m, size - m, m)
        p.drawLine(size - m, m, size - m - 3, m + 1)

    elif tool_type == ToolType.BRUSH:
        path = QPainterPath()
        path.moveTo(m, size - m)
        path.cubicTo(size * 0.3, size * 0.3, size * 0.6, size * 0.5, size - m, m)
        p.setPen(QPen(QColor(40, 40, 40), 3, Qt.SolidLine, Qt.RoundCap))
        p.drawPath(path)

    elif tool_type == ToolType.ERASER:
        p.setBrush(QBrush(QColor(255, 200, 200)))
        p.drawRect(m, m + 4, size - 2 * m, size - 2 * m - 4)

    elif tool_type == ToolType.ALPHA_BRUSH:
        # Checkerboard square to indicate transparency
        sq = (size - 2 * m) // 2
        for row in range(2):
            for col in range(2):
                c = QColor(200, 200, 200) if (row + col) % 2 == 0 else QColor(255, 255, 255)
                p.fillRect(m + col * sq, m + 2 + row * sq, sq, sq, c)
        p.setPen(QPen(QColor(40, 40, 40), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawRect(m, m + 2, sq * 2, sq * 2)
        # Diagonal stroke through it
        p.setPen(QPen(QColor(200, 60, 60), 2))
        p.drawLine(m + 2, size - m - 2, size - m - 2, m + 4)

    elif tool_type == ToolType.LINE:
        p.setPen(QPen(QColor(40, 40, 40), 2))
        p.drawLine(m, size - m, size - m, m)

    elif tool_type == ToolType.RECTANGLE:
        p.setBrush(Qt.NoBrush)
        p.drawRect(m, m + 2, size - 2 * m, size - 2 * m - 2)

    elif tool_type == ToolType.ELLIPSE:
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(m, m + 2, size - 2 * m, size - 2 * m - 4)

    elif tool_type == ToolType.TEXT:
        p.setFont(QFont("Sans Serif", 14, QFont.Bold))
        p.drawText(pm.rect(), Qt.AlignCenter, "A")

    elif tool_type == ToolType.FILL:
        # Paint bucket icon
        s = size
        # Bucket body (tilted trapezoid)
        body = QPainterPath()
        body.moveTo(s * 0.20, s * 0.30)
        body.lineTo(s * 0.15, s * 0.85)
        body.lineTo(s * 0.65, s * 0.90)
        body.lineTo(s * 0.60, s * 0.35)
        body.closeSubpath()
        p.setPen(QPen(QColor(40, 40, 40), 1.2))
        p.setBrush(QBrush(QColor(180, 180, 180)))
        p.drawPath(body)
        # Paint fill inside bucket
        fill = QPainterPath()
        fill.moveTo(s * 0.22, s * 0.45)
        fill.lineTo(s * 0.17, s * 0.83)
        fill.lineTo(s * 0.63, s * 0.88)
        fill.lineTo(s * 0.58, s * 0.50)
        fill.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(80, 150, 255)))
        p.drawPath(fill)
        # Handle arc
        p.setPen(QPen(QColor(40, 40, 40), 1.5))
        p.setBrush(Qt.NoBrush)
        p.drawArc(QRectF(s * 0.25, s * 0.12, s * 0.30, s * 0.28), 30 * 16, 150 * 16)
        # Paint pouring from bucket rim
        pour = QPainterPath()
        pour.moveTo(s * 0.62, s * 0.38)
        pour.cubicTo(s * 0.75, s * 0.35, s * 0.85, s * 0.50, s * 0.78, s * 0.70)
        pour.cubicTo(s * 0.72, s * 0.80, s * 0.68, s * 0.82, s * 0.70, s * 0.88)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(80, 150, 255)))
        p.drawPath(pour)

    elif tool_type == ToolType.PICKER:
        # Eyedropper icon (diagonal pipette)
        s = size
        p.setPen(QPen(QColor(40, 40, 40), 1.2))
        # Tip (pointed triangle at bottom-left)
        tip = QPainterPath()
        tip.moveTo(s * 0.10, s * 0.90)
        tip.lineTo(s * 0.22, s * 0.70)
        tip.lineTo(s * 0.30, s * 0.78)
        tip.closeSubpath()
        p.setBrush(QBrush(QColor(60, 60, 60)))
        p.drawPath(tip)
        # Shaft (diagonal rectangle)
        shaft = QPainterPath()
        shaft.moveTo(s * 0.22, s * 0.70)
        shaft.lineTo(s * 0.55, s * 0.37)
        shaft.lineTo(s * 0.63, s * 0.45)
        shaft.lineTo(s * 0.30, s * 0.78)
        shaft.closeSubpath()
        p.setBrush(QBrush(QColor(200, 200, 200)))
        p.drawPath(shaft)
        # Bulb (wider section at top-right)
        bulb = QPainterPath()
        bulb.moveTo(s * 0.55, s * 0.37)
        bulb.lineTo(s * 0.65, s * 0.20)
        bulb.lineTo(s * 0.80, s * 0.35)
        bulb.lineTo(s * 0.63, s * 0.45)
        bulb.closeSubpath()
        p.setBrush(QBrush(QColor(120, 120, 120)))
        p.drawPath(bulb)
        # Rubber squeeze top
        p.setBrush(QBrush(QColor(180, 80, 80)))
        p.drawEllipse(QPointF(s * 0.76, s * 0.22), s * 0.10, s * 0.08)

    elif tool_type == ToolType.SELECTION:
        p.setPen(QPen(QColor(40, 40, 40), 1, Qt.DashLine))
        p.setBrush(Qt.NoBrush)
        p.drawRect(m, m + 2, size - 2 * m, size - 2 * m - 2)

    p.end()
    return QIcon(pm)


def _make_fill_mode_icon(mode, size=24):
    """Draw an icon for shape fill mode."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    m = 4
    r = QRect(m, m, size - 2 * m, size - 2 * m)
    if mode == ShapeFillMode.OUTLINE:
        p.setPen(QPen(QColor(40, 40, 40), 2))
        p.setBrush(Qt.NoBrush)
        p.drawRect(r)
    elif mode == ShapeFillMode.FILLED:
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(100, 100, 100)))
        p.drawRect(r)
    else:  # BOTH
        p.setPen(QPen(QColor(40, 40, 40), 2))
        p.setBrush(QBrush(QColor(180, 180, 180)))
        p.drawRect(r)
    p.end()
    return QIcon(pm)


def _make_undo_icon(size=24):
    """Draw a curved undo arrow."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(40, 40, 40), 2))
    path = QPainterPath()
    path.moveTo(6, 12)
    path.arcTo(QRectF(6, 6, 14, 12), 180, -180)
    p.drawPath(path)
    # arrowhead
    p.drawLine(6, 12, 10, 9)
    p.drawLine(6, 12, 10, 15)
    p.end()
    return QIcon(pm)


def _make_redo_icon(size=24):
    """Draw a curved redo arrow."""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(QPen(QColor(40, 40, 40), 2))
    path = QPainterPath()
    path.moveTo(18, 12)
    path.arcTo(QRectF(4, 6, 14, 12), 0, 180)
    p.drawPath(path)
    # arrowhead
    p.drawLine(18, 12, 14, 9)
    p.drawLine(18, 12, 14, 15)
    p.end()
    return QIcon(pm)


class ColorSwatch(QWidget):
    """Small clickable color swatch."""
    clicked = pyqtSignal(QColor, int)  # color, button (1=left, 2=right)

    def __init__(self, color, parent=None, size=22):
        super().__init__(parent)
        self.color = QColor(color)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setPen(QPen(QColor(128, 128, 128), 1))
        p.setBrush(QBrush(self.color))
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)
        p.end()

    def mousePressEvent(self, event):
        btn = 1 if event.button() == Qt.LeftButton else 2
        self.clicked.emit(self.color, btn)


class ColorSelector(QWidget):
    """Shows FG/BG color with click-to-change and swap button."""
    color_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fg_color = QColor(Qt.black)
        self.bg_color = QColor(Qt.white)
        self.setFixedSize(48, 48)
        self.setToolTip("Left-click: foreground  Right-click: background")

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        # BG (bottom-right)
        p.setPen(QPen(QColor(100, 100, 100), 1))
        p.setBrush(QBrush(self.bg_color))
        p.drawRect(16, 20, 28, 22)
        # FG (top-left, overlapping)
        p.setBrush(QBrush(self.fg_color))
        p.drawRect(2, 2, 28, 22)
        # Swap icon (top-right corner)
        p.setPen(QPen(QColor(80, 80, 80), 1.5))
        p.setBrush(Qt.NoBrush)
        # small double-arrow swap icon
        p.drawLine(34, 6, 44, 6)
        p.drawLine(44, 6, 41, 3)
        p.drawLine(44, 6, 41, 9)
        p.drawLine(44, 14, 34, 14)
        p.drawLine(34, 14, 37, 11)
        p.drawLine(34, 14, 37, 17)
        p.end()

    def mousePressEvent(self, event):
        # Check if click is in the swap area (top-right)
        if event.x() >= 30 and event.y() <= 20:
            self.fg_color, self.bg_color = QColor(self.bg_color), QColor(self.fg_color)
            self.color_changed.emit()
            self.update()
            return
        if event.button() == Qt.LeftButton:
            c = QColorDialog.getColor(self.fg_color, self, "Foreground Color")
            if c.isValid():
                self.fg_color = c
                self.color_changed.emit()
                self.update()
        elif event.button() == Qt.RightButton:
            c = QColorDialog.getColor(self.bg_color, self, "Background Color")
            if c.isValid():
                self.bg_color = c
                self.color_changed.emit()
                self.update()


class ColorPalette(QWidget):
    """28-color palette in 2 rows of 14, plus a 3rd row for recent colours."""
    color_picked = pyqtSignal(QColor, int)

    MAX_RECENT = 14

    def __init__(self, parent=None, swatch_size=22):
        super().__init__(parent)
        self._recent_colors = []
        self._recent_swatches = []
        self._grid = QGridLayout(self)
        self._grid.setSpacing(1)
        self._grid.setContentsMargins(0, 0, 0, 0)
        # Rows 0-1: static palette
        for i, hex_color in enumerate(PALETTE_COLORS):
            row = i // 14
            col = i % 14
            swatch = ColorSwatch(hex_color, size=swatch_size)
            swatch.clicked.connect(self._on_swatch)
            self._grid.addWidget(swatch, row, col)
        # Row 2: recent colour slots (initially empty/dim)
        for col in range(self.MAX_RECENT):
            sw = ColorSwatch("#FFFFFF", size=swatch_size)
            sw.setEnabled(False)
            sw.setStyleSheet("QWidget:disabled { opacity: 0.3; }")
            sw.clicked.connect(self._on_swatch)
            self._grid.addWidget(sw, 2, col)
            self._recent_swatches.append(sw)

    def add_color(self, color):
        """Add a colour to the recent row (no duplicates, most recent first)."""
        c = QColor(color)
        hex_val = c.name()
        self._recent_colors = [x for x in self._recent_colors if x != hex_val]
        self._recent_colors.insert(0, hex_val)
        self._recent_colors = self._recent_colors[:self.MAX_RECENT]
        for i, sw in enumerate(self._recent_swatches):
            if i < len(self._recent_colors):
                sw.color = QColor(self._recent_colors[i])
                sw.setEnabled(True)
                sw.setStyleSheet("")
                sw.update()
            else:
                sw.color = QColor("#FFFFFF")
                sw.setEnabled(False)
                sw.setStyleSheet("QWidget:disabled { opacity: 0.3; }")
                sw.update()

    def _on_swatch(self, color, button):
        self.color_picked.emit(color, button)


class BrushSizeSelector(QWidget):
    """Compact brush size: preview + spinbox stacked vertically."""
    size_changed = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)

        self._preview = QWidget()
        self._preview.setFixedSize(34, 34)
        self._preview.paintEvent = self._paint_preview
        layout.addWidget(self._preview, alignment=Qt.AlignHCenter)

        self.spin = QSpinBox()
        self.spin.setRange(1, 100)
        self.spin.setValue(3)
        self.spin.setFixedWidth(52)
        self.spin.valueChanged.connect(self._on_value)
        layout.addWidget(self.spin, alignment=Qt.AlignHCenter)

    def _paint_preview(self, event):
        p = QPainter(self._preview)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self._preview.rect(), QColor(255, 255, 255))
        p.setPen(QPen(QColor(200, 200, 200), 1))
        p.drawRect(0, 0, 33, 33)
        size = self.spin.value()
        r = min(size, 30) / 2.0
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(QColor(0, 0, 0)))
        p.drawEllipse(QPointF(17, 17), r, r)
        p.end()

    def _on_value(self, v):
        self._preview.update()
        self.size_changed.emit(v)


class ShapeFillSelector(QWidget):
    """Horizontal icon buttons for shape fill mode."""
    mode_changed = pyqtSignal(ShapeFillMode)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        self._buttons = {}
        for mode, tip in [
            (ShapeFillMode.OUTLINE, "Outline only"),
            (ShapeFillMode.FILLED, "Filled only"),
            (ShapeFillMode.BOTH, "Outline + Fill"),
        ]:
            btn = QToolButton()
            btn.setIcon(_make_fill_mode_icon(mode))
            btn.setIconSize(QSize(24, 24))
            btn.setToolTip(tip)
            btn.setCheckable(True)
            btn.setFixedSize(32, 32)
            btn.clicked.connect(lambda checked, m=mode: self._select(m))
            layout.addWidget(btn)
            self._buttons[mode] = btn
        self._buttons[ShapeFillMode.OUTLINE].setChecked(True)

    def _select(self, mode):
        for m, btn in self._buttons.items():
            btn.setChecked(m == mode)
        self.mode_changed.emit(mode)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class PaintApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 750)

        self._file_path = None

        # Canvas as central widget (offset-based pan, no scroll area)
        self.canvas = Canvas()
        self.setCentralWidget(self.canvas)

        # Connect canvas signals
        self.canvas.color_changed.connect(self._sync_colors_from_canvas)
        self.canvas.modified_changed.connect(self._update_title)
        self.canvas.zoom_changed.connect(self._on_zoom_changed)
        self.canvas.cursor_moved.connect(self._on_cursor_moved)

        self._build_top_toolbar()
        self._build_menus()
        self._build_status_bar()

        self.canvas.brush_size_changed.connect(self._on_brush_size_from_canvas)
        self._sync_colors_to_canvas()
        self._update_title()
        self._restore_geometry()

    # ---- Top ribbon toolbar ----
    def _build_top_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(Qt.TopToolBarArea, tb)

        ribbon = QWidget()
        ribbon_layout = QHBoxLayout(ribbon)
        ribbon_layout.setContentsMargins(4, 2, 4, 2)
        ribbon_layout.setSpacing(0)

        def _vsep():
            s = QFrame()
            s.setFrameShape(QFrame.VLine)
            s.setFrameShadow(QFrame.Sunken)
            return s

        def _ribbon_group(content, label_text):
            """Wrap content widget with a bottom label, like MS Paint ribbon."""
            group = QWidget()
            vbox = QVBoxLayout(group)
            vbox.setContentsMargins(6, 2, 6, 0)
            vbox.setSpacing(1)
            vbox.addWidget(content)
            lbl = QLabel(label_text)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: gray; font-size: 9px;")
            vbox.addWidget(lbl)
            return group

        # --- Undo/Redo group ---
        undo_redo = QWidget()
        ur_layout = QVBoxLayout(undo_redo)
        ur_layout.setContentsMargins(0, 0, 0, 0)
        ur_layout.setSpacing(2)
        ur_row = QHBoxLayout()
        ur_row.setSpacing(2)

        undo_btn = QToolButton()
        undo_btn.setIcon(_make_undo_icon())
        undo_btn.setToolTip("Undo (Ctrl+Z)")
        undo_btn.setFixedSize(32, 32)
        undo_btn.clicked.connect(self.canvas.undo)
        ur_row.addWidget(undo_btn)

        redo_btn = QToolButton()
        redo_btn.setIcon(_make_redo_icon())
        redo_btn.setToolTip("Redo (Ctrl+Y)")
        redo_btn.setFixedSize(32, 32)
        redo_btn.clicked.connect(self.canvas.redo)
        ur_row.addWidget(redo_btn)
        ur_layout.addLayout(ur_row)

        ribbon_layout.addWidget(_ribbon_group(undo_redo, "History"))
        ribbon_layout.addWidget(_vsep())

        # --- Tools group (2-row grid) ---
        self._tool_buttons = {}
        self._tool_actions = {}

        tools_widget = QWidget()
        tools_grid = QGridLayout(tools_widget)
        tools_grid.setSpacing(1)
        tools_grid.setContentsMargins(0, 0, 0, 0)

        all_tools = []
        for _, tools in TOOL_GROUPS:
            all_tools.extend(tools)

        for i, tt in enumerate(all_tools):
            shortcut_key = TOOL_SHORTCUT_LABELS.get(tt, "")
            tool_name = self.canvas._tools[tt].name
            tip = f"{tool_name} ({shortcut_key})" if shortcut_key else tool_name

            btn = QToolButton()
            btn.setIcon(_make_tool_icon(tt, size=28))
            btn.setIconSize(QSize(28, 28))
            btn.setFixedSize(34, 34)
            btn.setCheckable(True)
            btn.setToolTip(tip)
            btn.clicked.connect(lambda checked, t=tt: self._on_tool_selected(t))
            tools_grid.addWidget(btn, i % 2, i // 2)  # 2 rows
            self._tool_buttons[tt] = btn

            act = QAction(self)
            act.setCheckable(True)
            self._tool_actions[tt] = act

        self._tool_buttons[ToolType.PENCIL].setChecked(True)
        self._tool_actions[ToolType.PENCIL].setChecked(True)

        ribbon_layout.addWidget(_ribbon_group(tools_widget, "Tools"))
        ribbon_layout.addWidget(_vsep())

        # --- Brush Size group ---
        self._brush_size_sel = BrushSizeSelector()
        self._brush_size_sel.size_changed.connect(self._on_brush_size)
        ribbon_layout.addWidget(_ribbon_group(self._brush_size_sel, "Size"))
        ribbon_layout.addWidget(_vsep())

        # --- Shape Fill group ---
        self._shape_fill_sel = ShapeFillSelector()
        self._shape_fill_sel.mode_changed.connect(self._on_shape_fill_mode)
        ribbon_layout.addWidget(_ribbon_group(self._shape_fill_sel, "Shapes"))
        ribbon_layout.addWidget(_vsep())

        # --- Antialiasing toggle ---
        self._aa_btn = QToolButton()
        self._aa_btn.setText("AA")
        self._aa_btn.setToolTip("Toggle antialiasing")
        self._aa_btn.setCheckable(True)
        self._aa_btn.setChecked(True)
        self._aa_btn.setFixedSize(34, 34)
        self._aa_btn.setStyleSheet(
            "QToolButton { font-weight: bold; font-size: 11px; }"
            "QToolButton:checked { background: #cde; border: 1px solid #89a; }")
        self._aa_btn.toggled.connect(self._on_aa_toggled)
        ribbon_layout.addWidget(_ribbon_group(self._aa_btn, "Smooth"))
        ribbon_layout.addWidget(_vsep())

        # --- Colors group ---
        colors_widget = QWidget()
        colors_layout = QHBoxLayout(colors_widget)
        colors_layout.setContentsMargins(0, 0, 0, 0)
        colors_layout.setSpacing(4)

        self._color_sel = ColorSelector()
        self._color_sel.color_changed.connect(self._sync_colors_to_canvas)
        colors_layout.addWidget(self._color_sel, 0, Qt.AlignVCenter)

        self._palette = ColorPalette(swatch_size=16)
        self._palette.color_picked.connect(self._on_palette_pick)
        colors_layout.addWidget(self._palette)

        edit_btn = QPushButton("Edit\nColors")
        edit_btn.setFixedHeight(48)
        edit_btn.setStyleSheet("font-size: 9px;")
        edit_btn.clicked.connect(self._edit_colors)
        colors_layout.addWidget(edit_btn, 0, Qt.AlignVCenter)

        ribbon_layout.addWidget(_ribbon_group(colors_widget, "Colors"))

        ribbon_layout.addStretch()
        tb.addWidget(ribbon)

    def _on_tool_selected(self, tool_type):
        for tt, act in self._tool_actions.items():
            act.setChecked(tt == tool_type)
        for tt, btn in self._tool_buttons.items():
            btn.setChecked(tt == tool_type)
        self.canvas.set_tool(tool_type)
        if hasattr(self, '_tool_label'):
            self._tool_label.setText(self.canvas._tools[tool_type].name)

    def _on_brush_size(self, size):
        self.canvas.brush_size = size
        if hasattr(self, '_brush_label'):
            self._brush_label.setText(f"Size: {size}")

    def _on_brush_size_from_canvas(self, size):
        self._brush_size_sel.spin.blockSignals(True)
        self._brush_size_sel.spin.setValue(size)
        self._brush_size_sel.spin.blockSignals(False)
        self._brush_size_sel._preview.update()
        if hasattr(self, '_brush_label'):
            self._brush_label.setText(f"Size: {size}")

    def _on_shape_fill_mode(self, mode):
        self.canvas.shape_fill_mode = mode

    def _on_aa_toggled(self, checked):
        self.canvas.antialiasing = checked

    def _on_palette_pick(self, color, button):
        if button == 1:
            self._color_sel.fg_color = QColor(color)
        else:
            self._color_sel.bg_color = QColor(color)
        self._color_sel.update()
        self._sync_colors_to_canvas()

    def _sync_colors_to_canvas(self):
        self.canvas.fg_color = QColor(self._color_sel.fg_color)
        self.canvas.bg_color = QColor(self._color_sel.bg_color)
        self._palette.add_color(self._color_sel.fg_color)

    def _sync_colors_from_canvas(self):
        self._color_sel.fg_color = QColor(self.canvas.fg_color)
        self._color_sel.bg_color = QColor(self.canvas.bg_color)
        self._color_sel.update()
        self._palette.add_color(self.canvas.fg_color)

    def _edit_colors(self):
        c = QColorDialog.getColor(self._color_sel.fg_color, self, "Edit Colors")
        if c.isValid():
            self._color_sel.fg_color = c
            self._color_sel.update()
            self._sync_colors_to_canvas()

    # ---- Menus ----
    def _build_menus(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("&File")
        self._add_action(file_menu, "&New", self._file_new, QKeySequence("Ctrl+N"))
        self._add_action(file_menu, "&Open...", self._file_open, QKeySequence("Ctrl+O"))
        file_menu.addSeparator()
        self._add_action(file_menu, "&Save", self._file_save, QKeySequence("Ctrl+S"))
        self._add_action(file_menu, "Save &As...", self._file_save_as, QKeySequence("Ctrl+Shift+S"))
        file_menu.addSeparator()
        self._add_action(file_menu, "E&xit", self.close, QKeySequence("Alt+F4"))

        # Edit
        edit_menu = mb.addMenu("&Edit")
        self._add_action(edit_menu, "&Undo", self.canvas.undo, QKeySequence("Ctrl+Z"))
        self._add_action(edit_menu, "&Redo", self.canvas.redo, QKeySequence("Ctrl+Y"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "Cu&t", self._edit_cut, QKeySequence("Ctrl+X"))
        self._add_action(edit_menu, "&Copy", self._edit_copy, QKeySequence("Ctrl+C"))
        self._add_action(edit_menu, "&Paste", self._edit_paste, QKeySequence("Ctrl+V"))
        self._add_action(edit_menu, "Select &All", self._edit_select_all, QKeySequence("Ctrl+A"))
        self._add_action(edit_menu, "&Delete", self._edit_delete, QKeySequence("Delete"))
        edit_menu.addSeparator()
        self._add_action(edit_menu, "C&lear Canvas", self.canvas.clear_canvas)

        # View
        view_menu = mb.addMenu("&View")
        self._add_action(view_menu, "Zoom &In", self.canvas.zoom_in, QKeySequence("Ctrl++"))
        self._add_action(view_menu, "Zoom &Out", self.canvas.zoom_out, QKeySequence("Ctrl+-"))
        self._add_action(view_menu, "&Reset Zoom", self.canvas.zoom_reset, QKeySequence("Ctrl+0"))

        # Image
        img_menu = mb.addMenu("&Image")
        self._add_action(img_menu, "&Resize Canvas...", self._image_resize)
        img_menu.addSeparator()
        self._add_action(img_menu, "Rotate 90° CW", lambda: self.canvas.rotate(90))
        self._add_action(img_menu, "Rotate 90° CCW", lambda: self.canvas.rotate(-90))
        self._add_action(img_menu, "Rotate 180°", lambda: self.canvas.rotate(180))
        img_menu.addSeparator()
        self._add_action(img_menu, "Flip &Horizontal", self.canvas.flip_horizontal)
        self._add_action(img_menu, "Flip &Vertical", self.canvas.flip_vertical)

        # Help
        help_menu = mb.addMenu("&Help")
        self._add_action(help_menu, "&Keyboard Shortcuts", self._show_shortcuts)
        help_menu.addSeparator()
        self._add_action(help_menu, "&About", self._show_about)

    def _add_action(self, menu, text, slot, shortcut=None):
        action = menu.addAction(text)
        def _handler(checked=False, _s=slot, _t=text):
            log.info(f"[action] {_t}")
            try:
                _s()
            except Exception as e:
                log.error(f"[action ERROR] {_t}: {e}", exc_info=True)
        action.triggered.connect(_handler)
        if shortcut:
            action.setShortcut(shortcut)
            action.setShortcutContext(Qt.ApplicationShortcut)
            self.addAction(action)
        return action

    # ---- File actions ----
    def _check_save(self):
        """Returns True if OK to proceed (user saved or discarded)."""
        if not self.canvas.modified:
            return True
        ret = QMessageBox.question(
            self, APP_NAME,
            "The image has been modified. Save changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
        )
        if ret == QMessageBox.Save:
            return self._file_save()
        return ret == QMessageBox.Discard

    def _file_new(self):
        if not self._check_save():
            return
        self._file_path = None
        self.canvas.new_canvas()
        self._update_title()

    def _file_open(self):
        log.info("[open] File > Open triggered")
        if not self._check_save():
            return
        start_dir = self._file_path or DEFAULT_DIR
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Image", start_dir,
            "Images (*.png *.jpg *.jpeg *.bmp *.gif *.webp);;All Files (*)")
        log.info(f"[open] Dialog returned: {path!r}")
        if path:
            self.open_file(path)

    def open_file(self, path):
        """Load an image file into the canvas."""
        log.info(f"[open] Loading: {path}")
        if self.canvas.load_image(path):
            self._file_path = path
            self._update_title()
            log.info(f"[open] OK: {self.canvas.pixmap.width()}x{self.canvas.pixmap.height()}")
        else:
            log.error(f"[open] Failed to load: {path}")
            QMessageBox.warning(self, APP_NAME, f"Could not open {path}")

    def _file_save(self):
        if self._file_path:
            return self._save_to(self._file_path)
        return self._file_save_as()

    def _file_save_as(self):
        start_dir = self._file_path or DEFAULT_DIR
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Image", start_dir,
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;All Files (*)")
        if path:
            if self._save_to(path):
                self._file_path = path
                self._update_title()
                return True
        return False

    def _save_to(self, path):
        import os
        # Default to .png if no recognized extension
        _, ext = os.path.splitext(path)
        if ext.lower() not in ('.png', '.jpg', '.jpeg', '.bmp'):
            path += '.png'
        log.info(f"[save] Saving to {path}")
        self.canvas.commit_selection()
        if self.canvas.pixmap.save(path):
            log.info("[save] OK")
            self.canvas.set_modified(False)
            self._update_title()
            return True
        log.error(f"[save] FAILED: {path}")
        QMessageBox.warning(self, APP_NAME, f"Could not save to {path}")
        return False

    # ---- Edit actions ----
    def _edit_cut(self):
        tool = self.canvas.current_tool()
        if isinstance(tool, SelectionTool) and tool.has_selection():
            tool.cut_selection()

    def _edit_copy(self):
        tool = self.canvas.current_tool()
        if isinstance(tool, SelectionTool) and tool.has_selection():
            tool.copy_selection()

    def _edit_paste(self):
        pm = self._pixmap_from_clipboard()
        if pm and not pm.isNull():
            log.info(f"[paste] Got image: {pm.width()}x{pm.height()}")
            # Switch to selection tool and paste as floating selection
            self._on_tool_selected(ToolType.SELECTION)
            sel_tool = self.canvas._tools[ToolType.SELECTION]
            # Paste at cursor position if cursor is over the canvas
            mp = self.canvas._mouse_pos
            if mp.x() >= 0 and self.canvas._is_over_canvas(mp):
                cx = int((mp.x() - self.canvas._pan_offset.x()) / self.canvas.zoom)
                cy = int((mp.y() - self.canvas._pan_offset.y()) / self.canvas.zoom)
                sel_tool.paste(pm, QPoint(cx, cy))
            else:
                # Paste centred on visible canvas area
                vw = self.canvas.width()
                vh = self.canvas.height()
                cx = int((vw / 2 - self.canvas._pan_offset.x()) / self.canvas.zoom)
                cy = int((vh / 2 - self.canvas._pan_offset.y()) / self.canvas.zoom)
                sel_tool.paste(pm, QPoint(cx, cy))
        else:
            fmts = []
            mime = QApplication.clipboard().mimeData()
            if mime:
                fmts = list(mime.formats())
            log.info(f"[paste] No image found. Formats: {fmts}")

    @staticmethod
    def _pixmap_from_clipboard():
        """Try multiple methods to get an image from the system clipboard."""
        clipboard = QApplication.clipboard()
        # Method 1: clipboard.image() — most reliable on Linux
        img = clipboard.image()
        if img and not img.isNull():
            return QPixmap.fromImage(img)
        # Method 2: clipboard.pixmap()
        pm = clipboard.pixmap()
        if pm and not pm.isNull():
            return pm
        # Method 3: read raw bytes from mime data (browser copies, etc.)
        mime = clipboard.mimeData()
        if mime:
            for fmt in ('image/png', 'image/jpeg', 'image/bmp'):
                if mime.hasFormat(fmt):
                    data = mime.data(fmt)
                    if data and not data.isEmpty():
                        img = QImage()
                        if img.loadFromData(data):
                            return QPixmap.fromImage(img)
            # Method 4: imageData() QVariant conversion
            if mime.hasImage():
                data = mime.imageData()
                if isinstance(data, QImage) and not data.isNull():
                    return QPixmap.fromImage(data)
                if isinstance(data, QPixmap) and not data.isNull():
                    return data
        return None

    def _edit_select_all(self):
        self._on_tool_selected(ToolType.SELECTION)
        sel_tool = self.canvas._tools[ToolType.SELECTION]
        sel_tool.select_all()

    def _edit_delete(self):
        tool = self.canvas.current_tool()
        if isinstance(tool, SelectionTool) and tool.has_selection():
            tool.delete_selection()

    # ---- Image actions ----
    def _image_resize(self):
        dlg = ResizeDialog(self.canvas.pixmap.width(),
                           self.canvas.pixmap.height(), self,
                           pixmap=self.canvas.pixmap)
        if dlg.exec_() == QDialog.Accepted:
            w, h = dlg.get_size()
            trim = dlg.get_trim_offset()
            if trim is not None:
                # Trim: crop to content bounding box
                self.canvas.commit_selection()
                self.canvas.save_undo()
                new_pm = QPixmap(w, h)
                new_pm.fill(Qt.transparent)
                p = QPainter(new_pm)
                p.drawPixmap(-trim[0], -trim[1], self.canvas.pixmap)
                p.end()
                self.canvas.pixmap = new_pm
                self.canvas.update()
                self.canvas.set_modified()
            else:
                self.canvas.resize_canvas(w, h)
            self._update_size_label()

    # ---- Status bar ----
    def _build_status_bar(self):
        sb = self.statusBar()
        self._pos_label = QLabel("0, 0 px")
        self._tool_label = QLabel("Pencil")
        self._brush_label = QLabel(f"Size: {self.canvas.brush_size}")
        self._size_label = QPushButton(
            f"{self.canvas.pixmap.width()} x {self.canvas.pixmap.height()} px")
        self._size_label.setFlat(True)
        self._size_label.setCursor(Qt.PointingHandCursor)
        self._size_label.setStyleSheet(
            "QPushButton { text-decoration: underline; }"
            "QPushButton:hover { color: #0066cc; }")
        self._size_label.clicked.connect(self._image_resize)

        # Zoom controls widget
        zoom_widget = QWidget()
        zoom_layout = QHBoxLayout(zoom_widget)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(2)

        zoom_out_btn = QPushButton("-")
        zoom_out_btn.setFixedSize(22, 22)
        zoom_out_btn.clicked.connect(self.canvas.zoom_out)
        zoom_layout.addWidget(zoom_out_btn)

        self._zoom_label = QLabel("100%")
        self._zoom_label.setMinimumWidth(40)
        self._zoom_label.setAlignment(Qt.AlignCenter)
        zoom_layout.addWidget(self._zoom_label)

        zoom_in_btn = QPushButton("+")
        zoom_in_btn.setFixedSize(22, 22)
        zoom_in_btn.clicked.connect(self.canvas.zoom_in)
        zoom_layout.addWidget(zoom_in_btn)

        sb.addWidget(self._pos_label)
        sb.addWidget(self._tool_label)
        sb.addWidget(self._brush_label)
        sb.addPermanentWidget(self._size_label)
        sb.addPermanentWidget(zoom_widget)

    def _on_cursor_moved(self, x, y):
        self._pos_label.setText(f"{x}, {y} px")

    def _on_zoom_changed(self, z):
        self._zoom_label.setText(f"{int(z * 100)}%")

    def _update_size_label(self):
        self._size_label.setText(
            f"{self.canvas.pixmap.width()} x {self.canvas.pixmap.height()} px")

    # ---- Title ----
    def _update_title(self):
        name = self._file_path if self._file_path else "Untitled"
        mod = "*" if self.canvas.modified else ""
        self.setWindowTitle(f"{name}{mod} - {APP_NAME}")
        self._update_size_label()

    # ---- About ----
    def _show_shortcuts(self):
        QMessageBox.information(
            self, "Keyboard Shortcuts",
            "<h3>Tools</h3>"
            "<table cellpadding='2'>"
            "<tr><td><b>P</b></td><td>Pencil (1px)</td></tr>"
            "<tr><td><b>B</b></td><td>Brush</td></tr>"
            "<tr><td><b>E</b></td><td>Eraser</td></tr>"
            "<tr><td><b>A</b></td><td>Alpha brush (erase to transparent)</td></tr>"
            "<tr><td><b>L</b></td><td>Line</td></tr>"
            "<tr><td><b>R</b></td><td>Rectangle</td></tr>"
            "<tr><td><b>O</b></td><td>Ellipse</td></tr>"
            "<tr><td><b>T</b></td><td>Text</td></tr>"
            "<tr><td><b>F</b></td><td>Flood fill</td></tr>"
            "<tr><td><b>I</b></td><td>Eyedropper</td></tr>"
            "<tr><td><b>S</b></td><td>Selection</td></tr>"
            "</table>"
            "<h3>File</h3>"
            "<table cellpadding='2'>"
            "<tr><td><b>Ctrl+N</b></td><td>New canvas</td></tr>"
            "<tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>"
            "<tr><td><b>Ctrl+S</b></td><td>Save</td></tr>"
            "<tr><td><b>Ctrl+Shift+S</b></td><td>Save as</td></tr>"
            "</table>"
            "<h3>Edit</h3>"
            "<table cellpadding='2'>"
            "<tr><td><b>Ctrl+Z</b></td><td>Undo</td></tr>"
            "<tr><td><b>Ctrl+Y</b></td><td>Redo</td></tr>"
            "<tr><td><b>Ctrl+C</b></td><td>Copy</td></tr>"
            "<tr><td><b>Ctrl+X</b></td><td>Cut</td></tr>"
            "<tr><td><b>Ctrl+V</b></td><td>Paste</td></tr>"
            "<tr><td><b>Ctrl+A</b></td><td>Select all</td></tr>"
            "<tr><td><b>Delete</b></td><td>Delete selection</td></tr>"
            "</table>"
            "<h3>View</h3>"
            "<table cellpadding='2'>"
            "<tr><td><b>Scroll wheel</b></td><td>Zoom in/out</td></tr>"
            "<tr><td><b>Shift+scroll</b></td><td>Change brush size</td></tr>"
            "<tr><td><b>Ctrl+=</b></td><td>Zoom in</td></tr>"
            "<tr><td><b>Ctrl+-</b></td><td>Zoom out</td></tr>"
            "<tr><td><b>Ctrl+0</b></td><td>Reset zoom</td></tr>"
            "<tr><td><b>Middle-click drag</b></td><td>Pan canvas</td></tr>"
            "</table>"
            "<h3>Alpha Brush</h3>"
            "<table cellpadding='2'>"
            "<tr><td><b>Shift+click</b></td><td>Flood fill to transparent</td></tr>"
            "</table>"
        )

    def _show_about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            "<p>A paint program built with Python and PyQt5.</p>"
            "<p>Features include drawing tools (pencil, brush, eraser, "
            "alpha brush), shapes (line, rectangle, ellipse), text, "
            "flood fill, eyedropper, selection with copy/paste, "
            "undo/redo, zoom, antialiasing toggle, and transparency "
            "support.</p>",
        )

    # ---- Window geometry persistence ----
    def _save_geometry(self):
        settings = QSettings("ClaudePaint", "Claude Paint")
        settings.setValue("geometry", self.saveGeometry())

    def _restore_geometry(self):
        settings = QSettings("ClaudePaint", "Claude Paint")
        geom = settings.value("geometry")
        if geom:
            self.restoreGeometry(geom)

    # ---- Close event ----
    def closeEvent(self, event):
        if self._check_save():
            self._save_geometry()
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
import logging, os
_log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug.log")
logging.basicConfig(filename=_log_path, level=logging.DEBUG,
                    format="%(asctime)s %(message)s", force=True)
log = logging.getLogger("paint")


def main():
    import traceback
    def _excepthook(t, v, tb):
        log.error("".join(traceback.format_exception(t, v, tb)))
        sys.__excepthook__(t, v, tb)
    sys.excepthook = _excepthook
    log.info("Starting (v4)")
    print("[Claude Paint] Starting (v4)...", flush=True)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = PaintApp()
    window.show()
    # Load file from command line: ./claude-paint image.png
    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
