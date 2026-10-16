"""Look and feel: colors, type, stylesheet and icons."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QIconEngine, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from bodega.core.looks import FONT
from bodega.ui.style import tokens
from bodega.ui.style.tokens import (
    BAR_CTRL_H,
    BAR_H,
    CONTROL_H,
    HANDLE,
    ICON,
    ICON_STROKE,
    INDICATOR,
    RADIUS,
    RADIUS_LG,
    RADIUS_SM,
    RADIUS_XS,
    SCROLL_INSET,
    SCROLL_MIN,
    SCROLL_W,
    SEG_INSET,
    SMALL_H,
    SORT_ARROW,
    SPACE_1,
    SPACE_1_5,
    SPACE_2,
    SPACE_2_5,
    SPACE_3,
    SPACE_4,
    SPACE_5,
    TABLE_ROW_H,
    TEXT_BRAND,
    TEXT_LG,
    TEXT_MD,
    TEXT_RECORD,
    TEXT_SM,
    TEXT_TITLE,
    TEXT_TITLEBAR,
    TEXT_XL,
    TEXT_XS,
    TRACK_BRAND,
    TRACK_H,
    TRACK_TITLE,
    TRACK_TITLEBAR,
    WEIGHT_BOLD,
    WEIGHT_MEDIUM,
    WEIGHT_REGULAR,
    WEIGHT_SEMIBOLD,
)

FONT_FAMILY = FONT  # the same Inter as the paper (core/looks.py): one font for the whole app

# A control's box = border (1px top + bottom) + content. Padding is horizontal only, so every
# button, dropdown and text field comes out exactly CONTROL_H tall.
_INNER = CONTROL_H - 2
_SMALL_INNER = SMALL_H - 2
_SEG_INNER = CONTROL_H - 2 - 2 * SEG_INSET  # segmented control: 1px border + inset
_BAR_INNER = BAR_CTRL_H - 2  # the bar's circles and search field


def _load_colors() -> None:
    """Copy the current color tokens here (theme.MUTED etc.), for the stylesheet and icons."""
    globals().update({k: getattr(tokens, k) for k in tokens.DARK})


_load_colors()


def load_fonts() -> str:
    """Register the bundled fonts (Inter for the app and the paper, IBM Plex Mono for serials)."""
    from bodega.doc.fonts import load_bundled

    return FONT_FAMILY if FONT_FAMILY in load_bundled() else ""


def _sheet() -> str:
    """The app stylesheet in the current colors."""
    return f"""
* {{ outline: none; }}  /* Qt's dotted focus box: every control draws its own focus ring below */
QWidget {{ color: {tokens.TEXT}; font-size: {TEXT_MD}px; }}
QMainWindow {{ background: {tokens.BG}; }}
*[glass="true"] {{ background: transparent; border: none; }}
QDialog {{ background: {tokens.PANEL}; }}
QDialog#Embedded {{ background: transparent; }}
QToolTip {{ background: {tokens.RAISED}; color: {tokens.TEXT}; border: 1px solid {tokens.BORDER_STRONG};
    padding: {SPACE_1}px {SPACE_2}px; border-radius: {RADIUS_SM}px; font-size: {TEXT_SM}px; }}

/* ---------- text styles */
#Wordmark {{ font-size: {TEXT_BRAND}px; font-weight: {WEIGHT_BOLD}; letter-spacing: {TRACK_BRAND}px; }}
#TitleBar {{ background: transparent; border: none; }}
#TitleWordmark {{ font-size: {TEXT_TITLEBAR}px; font-weight: {WEIGHT_BOLD}; letter-spacing: {TRACK_TITLEBAR}px; }}
#DialogTitle {{ font-size: {TEXT_XL}px; font-weight: {WEIGHT_BOLD}; }}
#SectionLabel {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_MEDIUM}; }}
#Hint {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; }}
#Muted {{ color: {tokens.MUTED}; }}
#Meta {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; }}

/* ---------- areas */
#PanelHeader {{ border: none; }}
#PanelTitle {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}

/* ---------- buttons: all CONTROL_H tall */
QPushButton {{  /* a word capsule (G.2): fill, text; hover fill-3 */
    background: {tokens.FILL}; border: {tokens.FOCUS_RING}px solid transparent; border-radius: {_INNER // 2}px;
    padding: 0 {SPACE_4 - 1}px; min-height: {_INNER}px; max-height: {_INNER}px; font-weight: {WEIGHT_MEDIUM};
}}
QPushButton:hover {{ background: {tokens.FILL_3}; }}
QPushButton:pressed {{ background: {tokens.FILL_3}; }}
QPushButton:disabled {{ color: {tokens.TEXT_OFF}; background: {tokens.FILL_OFF}; }}
QPushButton#Raised {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; }}  /* a record's next step */
QPushButton#Raised:hover, QPushButton#Raised:pressed {{ background: {tokens.RAISED_HOVER}; }}
QPushButton#Primary {{ background: {tokens.ACCENT_FILL}; color: {tokens.ON_ACCENT}; border-color: {tokens.ACCENT_FILL};
    font-weight: {WEIGHT_SEMIBOLD}; padding: 0 {SPACE_4}px; }}
QPushButton#Primary:hover {{ background: {tokens.ACCENT_FILL_HOVER}; border-color: {tokens.ACCENT_FILL_HOVER}; }}
QPushButton#Primary:pressed {{ background: {tokens.ACCENT_PRESS}; border-color: {tokens.ACCENT_PRESS}; }}
QPushButton#Primary:disabled {{ background: {tokens.ACCENT_OFF}; border-color: {tokens.ACCENT_OFF}; color: {tokens.ACCENT_OFF_TEXT}; }}
QPushButton#Ghost {{ background: transparent; border-color: transparent; color: {tokens.ACCENT_TEXT}; }}  /* quiet */
QPushButton#Ghost:hover {{ background: {tokens.ACCENT_TINT}; }}
QPushButton#AddChip {{ background: {tokens.CHIP}; border: 1px solid transparent; color: {tokens.ACCENT_TEXT}; padding: 0 {SPACE_3}px 0 {SPACE_2}px; font-weight: {WEIGHT_SEMIBOLD}; }}
QPushButton#FilterChip {{ background: {tokens.ACCENT_TINT}; border: 1px solid {tokens.ACCENT_EDGE}; color: {tokens.ACCENT_TEXT}; padding: 0 {SPACE_2}px 0 {SPACE_3}px; min-height: {tokens.CHIP_H}px; max-height: {tokens.CHIP_H}px; }}
QPushButton#FilterChip:hover {{ background: {tokens.CHIP_HOVER}; }}
QPushButton#AddChip:hover {{ background: {tokens.CHIP_HOVER}; }}
QPushButton#AddChip:pressed {{ background: {tokens.ACCENT_TINT}; }}
QToolButton#SectionAdd {{ background: transparent; border: none; border-radius: {tokens.SECTION_ADD // 2}px;
    min-width: {tokens.SECTION_ADD}px; max-width: {tokens.SECTION_ADD}px;
    min-height: {tokens.SECTION_ADD}px; max-height: {tokens.SECTION_ADD}px; }}
QToolButton#SectionAdd:hover {{ background: {tokens.CARD_HOVER}; }}
*[capsule="true"] {{ border-radius: {_INNER // 2}px; padding-left: {SPACE_4}px; }}
QPushButton#LinkBtn {{ background: transparent; border: none; padding: 0; color: {tokens.ACCENT_TEXT}; text-align: left; }}
QPushButton#LinkBtn:hover {{ color: {tokens.TEXT}; }}
QPushButton#LinkBtn:disabled {{ color: {tokens.TEXT_OFF}; background: transparent; }}
QPushButton#Disclosure {{ background: transparent; border: none; border-radius: 0; padding: 0; text-align: left;
    color: {tokens.MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; min-height: {SMALL_H}px; max-height: {SMALL_H}px; }}
QPushButton#Disclosure:hover {{ color: {tokens.TEXT}; background: transparent; }}
QPushButton#Danger {{ color: {tokens.BAD}; background: {tokens.BAD_TINT}; }}
QPushButton#Danger:hover {{ background: {tokens.BAD_HOVER}; }}
QPushButton::menu-indicator, QToolButton::menu-indicator {{ image: none; width: 0; }}

/* ---------- small controls: all SMALL_H tall */
QToolButton#IconBtn {{ background: transparent; border: none; border-radius: {SMALL_H // 2}px;
    min-width: {SMALL_H}px; max-width: {SMALL_H}px; min-height: {SMALL_H}px; max-height: {SMALL_H}px; }}
QToolButton#IconBtn:hover {{ background: {tokens.FILL}; }}
QToolButton#Circle, QToolButton#CirclePrimary {{ border-radius: {_INNER // 2}px; min-width: {_INNER}px; max-width: {_INNER}px;
    min-height: {_INNER}px; max-height: {_INNER}px; }}
QToolButton#Circle {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; }}
QToolButton#Circle:hover {{ background: {tokens.RAISED_HOVER}; }}
QToolButton#Circle:checked {{ background: {tokens.ACCENT_TINT}; border-color: {tokens.ACCENT_EDGE}; }}  /* on (the assistant) */
QToolButton#CirclePrimary {{ background: {tokens.ACCENT_FILL}; border: 1px solid {tokens.ACCENT_FILL}; }}
QToolButton#CirclePrimary:hover {{ background: {tokens.ACCENT_FILL_HOVER}; border-color: {tokens.ACCENT_FILL_HOVER}; }}
QToolButton#CirclePrimary:pressed {{ background: {tokens.ACCENT_PRESS}; }}
QToolButton#Circle[active="true"] {{ background: {tokens.ACCENT_TINT}; border-color: {tokens.ACCENT_EDGE}; }}
QToolButton#Circle[bar="true"], QToolButton#CirclePrimary[bar="true"] {{ border-radius: {_BAR_INNER // 2}px;
    min-width: {_BAR_INNER}px; max-width: {_BAR_INNER}px; min-height: {_BAR_INNER}px; max-height: {_BAR_INNER}px; }}
QLineEdit[bar="true"] {{ min-height: {_BAR_INNER}px; max-height: {_BAR_INNER}px; border-radius: {_BAR_INNER // 2}px; }}
/* keyboard focus: buttons take it from Tab only (never a click), so a ring means the keyboard is there */
QPushButton:focus, QToolButton:focus, #SegBtn:focus {{ border: {tokens.FOCUS_RING}px solid {tokens.ACCENT}; }}
QPushButton#Primary:focus, QToolButton#CirclePrimary:focus {{ border: {tokens.FOCUS_RING}px solid {tokens.ON_ACCENT}; }}
#Alert {{ background: {tokens.RAISED}; border: 1px solid {tokens.BORDER_STRONG}; border-radius: {RADIUS_LG}px; }}
#AlertTitle {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
QPushButton#DangerFill {{ background: {tokens.BAD_BUTTON}; border: 1px solid {tokens.BAD_BUTTON}; color: #FFFFFF; font-weight: {WEIGHT_SEMIBOLD}; }}
QPushButton#DangerFill:hover {{ background: {tokens.BAD_BUTTON}; border-color: {tokens.BAD_BUTTON}; }}
QFrame#CheckRow {{ background: {tokens.FILL}; border-radius: {RADIUS_LG}px; }}
QLabel#Due {{ color: {tokens.MUTED}; }}
QLabel#Due[tone="out"] {{ color: {tokens.WARN}; font-weight: {WEIGHT_SEMIBOLD}; }}
QLabel#Due[tone="late"] {{ color: {tokens.BAD}; font-weight: {WEIGHT_SEMIBOLD}; }}
#KeyCap {{ background: {tokens.CHIP}; color: {tokens.MUTED}; border-radius: {RADIUS_SM}px; padding: {tokens.SPACE_0_5}px {SPACE_2}px;
    font-weight: {WEIGHT_MEDIUM}; }}
#MenuHeading {{ color: {tokens.MUTED}; font-size: {TEXT_XS}px; font-weight: {WEIGHT_SEMIBOLD}; padding: {SPACE_1}px {SPACE_2}px 0 {SPACE_2}px; }}

/* ---------- fields + dropdowns: all CONTROL_H tall */
QComboBox {{ combobox-popup: 0; }}
QComboBox, QLineEdit {{  /* G.3, G.5: fill at rest (its edge kept, transparent), the field color on focus */
    background: {tokens.FILL}; border: 1px solid transparent; border-radius: {RADIUS}px;
    padding: 0 {SPACE_3}px; min-height: {_INNER}px; max-height: {_INNER}px;
    selection-background-color: {tokens.ACCENT_FILL}; selection-color: {tokens.ON_ACCENT};
}}
QComboBox:hover {{ background: {tokens.FILL_3}; }}
/* focus: the standard's 2-point ring, its padding and height giving back the extra point so nothing moves */
QLineEdit:focus, QComboBox:focus {{ background: {tokens.FIELD}; border: {tokens.FOCUS_RING}px solid {tokens.ACCENT};
    padding-left: {SPACE_3 - tokens.FOCUS_RING + 1}px; padding-right: {SPACE_3 - tokens.FOCUS_RING + 1}px;
    min-height: {CONTROL_H - 2 * tokens.FOCUS_RING}px; max-height: {CONTROL_H - 2 * tokens.FOCUS_RING}px; }}
QComboBox:focus {{ padding-right: {SPACE_5 + SPACE_1_5 - tokens.FOCUS_RING + 1}px; }}
QLineEdit[bar="true"] {{ background: {tokens.RAISED}; border-color: {tokens.GLASS_STROKE}; }}
QLineEdit[bar="true"]:focus {{ background: {tokens.FIELD}; border: {tokens.FOCUS_RING}px solid {tokens.ACCENT};
    min-height: {tokens.BAR_CTRL_H - 2 * tokens.FOCUS_RING}px; max-height: {tokens.BAR_CTRL_H - 2 * tokens.FOCUS_RING}px; }}
QComboBox {{ padding-right: {SPACE_5 + SPACE_1_5}px; }}
QComboBox::drop-down {{ border: none; width: {SPACE_5 + SPACE_1_5}px; }}
QComboBox::down-arrow {{ image: url(__UPDOWN__); width: {tokens.ICON_UPDOWN}px; height: {tokens.ICON_UPDOWN}px; }}
QComboBoxPrivateContainer {{ background: transparent; border: none; }}
QComboBox QAbstractItemView, QListView#Suggestions {{
    background: {tokens.RAISED}; border: 1px solid {tokens.BORDER_STRONG}; border-radius: {tokens.LIST_R}px;
    padding: {tokens.LIST_INSET - 1}px; outline: none;
    selection-background-color: {tokens.ACCENT_TINT}; selection-color: {tokens.ACCENT_TEXT};
}}
QComboBox QAbstractItemView::item, QListView#Suggestions::item {{
    padding: 0 {SPACE_2_5}px; min-height: {tokens.LIST_ROW_H}px; border-radius: {tokens.LIST_ROW_R}px;
    margin: {tokens.LIST_GAP // 2}px 0;
}}
QComboBox QAbstractItemView::item:hover, QListView#Suggestions::item:hover {{ background: {tokens.CARD_HOVER}; }}
QComboBox QAbstractItemView::item:selected, QListView#Suggestions::item:selected {{
    background: {tokens.ACCENT_TINT}; color: {tokens.ACCENT_TEXT};
}}
QComboBox QAbstractItemView::separator {{ height: 1px; background: {tokens.BORDER_STRONG}; margin: {SPACE_1}px {SPACE_2}px; }}

/* ---------- segmented control: CONTROL_H tall overall */
#Seg {{ background: {tokens.FILL}; border: 1px solid transparent; border-radius: {CONTROL_H // 2}px; }}
#SegBtn {{ background: transparent; border: 1px solid transparent; border-radius: {_SEG_INNER // 2}px; padding: 0 {SPACE_3}px;
    min-height: {_SEG_INNER}px; max-height: {_SEG_INNER}px; color: {tokens.TEXT}; font-weight: {WEIGHT_MEDIUM}; }}
#SegBtn:hover {{ background: {tokens.FILL_2}; }}
#SegBtn:checked, #SegBtn:checked:hover {{ background: transparent; font-weight: {WEIGHT_SEMIBOLD}; }}
#SegThumb {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; border-radius: {_SEG_INNER // 2}px; }}  /* the choice's highlight: it slides */

/* ---------- checkboxes, sliders, progress */
QCheckBox {{ spacing: {SPACE_2}px; min-height: {SMALL_H}px; }}
QCheckBox::indicator, QTreeView::indicator {{ width: {INDICATOR}px; height: {INDICATOR}px; border-radius: {RADIUS_XS}px; border: 1px solid {tokens.BORDER_CHECK}; background: {tokens.CARD}; }}
QCheckBox::indicator:checked, QTreeView::indicator:checked {{ background: {tokens.ACCENT_FILL}; border-color: {tokens.ACCENT_FILL}; image: url(__CHECK__); }}
QCheckBox:disabled {{ color: {tokens.TEXT_OFF}; }}
QSlider {{ min-height: {SMALL_H}px; }}
QSlider::groove:horizontal {{ height: {TRACK_H}px; background: {tokens.RAISED}; border-radius: {TRACK_H // 2}px; }}
QSlider::sub-page:horizontal {{ background: {tokens.ACCENT}; border-radius: {TRACK_H // 2}px; }}
QSlider::handle:horizontal {{ background: {tokens.TEXT}; width: {HANDLE}px; height: {HANDLE}px; margin: -{(HANDLE - TRACK_H) // 2}px 0; border-radius: {HANDLE // 2}px; }}
QProgressBar {{ background: {tokens.RAISED}; border: none; border-radius: {BAR_H // 2}px; max-height: {BAR_H}px; min-height: {BAR_H}px; }}
QProgressBar::chunk {{ background: {tokens.ACCENT}; border-radius: {BAR_H // 2}px; }}

/* ---------- scrolling */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: {SCROLL_W}px; margin: {SCROLL_INSET}px; }}
QScrollBar::handle:vertical {{ background: {tokens.BORDER_STRONG}; border-radius: {(SCROLL_W - 2 * SCROLL_INSET) // 2}px; min-height: {SCROLL_MIN}px; }}
QScrollBar::handle:vertical:hover {{ background: {tokens.BORDER_HOVER}; }}
QScrollBar:vertical:disabled, QScrollBar::handle:vertical:disabled {{ background: transparent; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; background: none; }}

/* ---------- cards: packages and rentals */
#Chip[tone="returned"] {{ color: {tokens.GOOD}; border-color: {tokens.GOOD}; }}
#Chip[tone="repair"] {{ color: {tokens.WARN}; border-color: {tokens.BORDER_STRONG}; }}
#Chip[tone="cancelled"], #Chip[tone="retired"] {{ color: {tokens.MUTED}; border-color: {tokens.BORDER}; }}

/* ---------- gear rows */
#RowMeta {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; }}
#Warn {{ color: {tokens.WARN}; font-size: {TEXT_SM}px; }}
QFrame#Banner {{ background: {tokens.BANNER}; border: 1px solid {tokens.BANNER_EDGE}; border-radius: {RADIUS}px;
    margin: 0 {SPACE_4}px {SPACE_2}px {SPACE_4}px; }}
#Bad {{ color: {tokens.BAD}; font-size: {TEXT_SM}px; }}
#Sum {{ color: {tokens.TEXT}; font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#SumLabel {{ color: {tokens.MUTED}; }}
#SumValue {{ font-weight: {WEIGHT_MEDIUM}; }}
/* the record pager: a glass capsule, its ‹ › clear until pointed at */
#Pager {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; border-radius: {(tokens.BAR_CTRL_H + 2 * SPACE_1) // 2}px; }}
#Pager QToolButton#Circle {{ background: transparent; border-color: transparent; }}
#Pager QToolButton#Circle:hover {{ background: {tokens.FILL}; }}
#PagerText {{ color: {tokens.MUTED}; font-weight: {WEIGHT_MEDIUM}; }}
/* the assistant's conversation (panels/assistant.py; the standard's G.25) */
#Conversation, #ConversationBody {{ background: transparent; border: none; }}
#Mine {{ background: {tokens.ACCENT_FILL}; border-radius: {tokens.BUBBLE_R}px; border-bottom-right-radius: {tokens.BUBBLE_TAIL_R}px; }}
#MineText {{ color: {tokens.ON_ACCENT}; }}
#Answer {{ color: {tokens.TEXT}; }}
#ChatNote {{ background: {tokens.FILL_2}; border-radius: {RADIUS}px; }}
#ChatNote[tone="problem"] {{ background: {tokens.WARN_SOFT}; }}
#ChatNote[tone="done"] {{ background: {tokens.GOOD_SOFT}; }}
#ChatNote QLabel {{ color: {tokens.TEXT}; }}
QToolButton#MsgAction {{ background: transparent; border: none; border-radius: {tokens.MSG_ACTION // 2}px; }}
QToolButton#MsgAction:hover {{ background: {tokens.FILL_2}; }}
#Thinking {{ color: {tokens.MUTED}; font-weight: {WEIGHT_MEDIUM}; }}
#ChangeCard {{ background: {tokens.CARD}; border: 1px solid {tokens.BORDER}; border-radius: {RADIUS_LG}px; }}
#ChangeTitle {{ color: {tokens.TEXT}; font-weight: {WEIGHT_BOLD}; }}
#Outcome {{ color: {tokens.MUTED}; }}
#Outcome[tone="done"] {{ color: {tokens.GOOD}; }}
#Composer {{ background: {tokens.FIELD}; border: 1px solid {tokens.FIELD_BORDER}; border-radius: {tokens.COMPOSER_MIN_H // 2}px; min-height: {tokens.COMPOSER_MIN_H - 2}px; }}
QPlainTextEdit#MessageBox {{ background: transparent; border: none; padding: 0; color: {tokens.TEXT}; font-size: {TEXT_MD}px;
    selection-background-color: {tokens.ACCENT_FILL}; selection-color: {tokens.ON_ACCENT}; }}
QToolButton#Send {{ background: {tokens.ACCENT_FILL}; border: none; border-radius: {tokens.SEND_D // 2}px; }}
QToolButton#Send:hover {{ background: {tokens.ACCENT_FILL_HOVER}; }}
QToolButton#Send[stop="true"] {{ background: {tokens.TEXT}; }}
QToolButton#Send:disabled {{ background: {tokens.FILL_3}; }}
#HeadGroup {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; border-radius: {CONTROL_H // 2 + 1}px; }}
#HeadGroup QToolButton#Circle {{ background: transparent; border-color: transparent; }}
#HeadGroup QToolButton#Circle:hover {{ background: {tokens.FILL}; }}
#Suggestions {{ background: {tokens.CARD}; border: 1px solid {tokens.BORDER}; border-radius: {RADIUS_LG}px; }}
QPushButton#Suggestion {{ background: transparent; border: none; border-bottom: 1px solid {tokens.BORDER}; border-radius: 0;
    text-align: left; padding: {SPACE_2_5}px {SPACE_3 + tokens.SPACE_0_5}px; min-height: {tokens.ROW_H - 2 * SPACE_2_5}px; max-height: none; color: {tokens.TEXT}; }}
QPushButton#Suggestion[last="true"] {{ border-bottom-color: transparent; }}
QPushButton#Suggestion:hover {{ background: {tokens.FILL_2}; }}
QPushButton#Suggestion:pressed {{ background: {tokens.FILL}; }}
/* Search Everything (dialogs/palette.py) */
#Palette {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; border-radius: {tokens.RADIUS_XL}px; }}
#PaletteHead {{ border-bottom: 1px solid {tokens.BORDER}; }}
QLineEdit#PaletteFind {{ background: transparent; border: none; padding: 0; font-size: {TEXT_XL}px; min-height: {tokens.PALETTE_FIND_H}px; }}
QLineEdit#PaletteFind:focus {{ background: transparent; border: none; }}
QListWidget#PaletteList {{ background: transparent; border: none; padding: {SPACE_2}px {SPACE_2_5}px {SPACE_2_5}px; }}
#PaletteNone {{ color: {tokens.MUTED}; padding: {SPACE_5}px {SPACE_3}px; }}
QPushButton#SideSearch {{ background: {tokens.FILL}; border: 1px solid transparent; border-radius: {CONTROL_H // 2}px; color: {tokens.MUTED};
    text-align: left; padding: 0 {SPACE_3}px; min-height: {_INNER}px; max-height: {_INNER}px; }}
QPushButton#SideSearch:hover {{ background: {tokens.FILL_3}; }}
#CardTitle {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#Card {{ background: {tokens.BLOCK}; border: none; border-radius: {RADIUS_LG}px; }}
QPlainTextEdit#BigName {{ font-size: {TEXT_RECORD}px; font-weight: {WEIGHT_BOLD}; color: {tokens.TEXT};
    background: transparent; border: 1px solid transparent; border-radius: {RADIUS}px; padding: 0 {SPACE_1}px;
    selection-background-color: {tokens.ACCENT_FILL}; selection-color: {tokens.ON_ACCENT}; }}
QPlainTextEdit#BigName:hover {{ background: {tokens.FILL}; }}
QPlainTextEdit#BigName:focus {{ background: {tokens.FIELD}; border-color: {tokens.ACCENT_EDGE}; }}
#Totals {{ background: transparent; border-top: 1px solid {tokens.BORDER}; }}
#TotalLabel {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#TotalValue {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_BOLD}; }}
#Totals {{ border-top: 1px solid {tokens.BORDER_STRONG}; }}
QListWidget#Picker {{ background: {tokens.CARD}; border: 1px solid {tokens.BORDER_STRONG}; border-radius: {tokens.LIST_R}px;
    padding: {tokens.LIST_INSET - 1}px; outline: none; }}
QListWidget#Picker::item {{ min-height: {tokens.LIST_ROW_H}px; border-radius: {tokens.LIST_ROW_R}px; padding: 0 {SPACE_2}px;
    margin: {tokens.LIST_GAP // 2}px 0; }}
QListWidget#Picker::item:hover {{ background: {tokens.CARD_HOVER}; }}
QListWidget#Picker::item:selected {{ background: {tokens.ACCENT_TINT}; color: {tokens.ACCENT_TEXT}; }}
QListWidget#Picker::indicator {{ width: {INDICATOR}px; height: {INDICATOR}px; border-radius: {RADIUS_XS}px;
    border: 1px solid {tokens.BORDER_CHECK}; background: {tokens.CARD}; }}
QListWidget#Picker::indicator:checked {{ background: {tokens.ACCENT_FILL}; border-color: {tokens.ACCENT_FILL}; image: url(__CHECK__); }}


/* ---------- the window: sidebar, toolbar, tables */
#Sidebar {{ background: transparent; border: none; }}
#SidebarFoot {{ border: none; }}
#ProfileCard {{ background: transparent; border-radius: {tokens.NAV_R}px; }}
#ProfileCard:hover {{ background: {tokens.CARD_HOVER}; }}
#Avatar {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {tokens.MONOGRAM_TOP}, stop:1 {tokens.MONOGRAM_BOTTOM});
    color: #FFFFFF; border-radius: {tokens.MONOGRAM // 2}px; font-size: {TEXT_MD}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#ProfileName {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#ProfileSub {{ color: {tokens.MUTED}; font-size: {TEXT_XS}px; }}
#ProfileSub[tone="problem"] {{ color: {tokens.WARN}; font-weight: {WEIGHT_SEMIBOLD}; }}
#Nav {{ background: transparent; border-radius: {tokens.NAV_R}px; }}
#Nav:hover {{ background: {tokens.ROW_HOVER}; }}
#Nav:focus, #NavHead:focus, #LineHead:focus {{ border: {tokens.FOCUS_RING}px solid {tokens.ACCENT}; }}
#Nav[selected="true"] {{ background: {tokens.ACCENT_TINT}; }}
#NavLabel {{ color: {tokens.TEXT}; font-weight: {WEIGHT_MEDIUM}; }}
#NavSub {{ color: {tokens.TEXT}; }}
QToolButton#NavArrow {{ background: transparent; border: none; padding: 0; }}
QToolButton#NavArrow:hover {{ background: {tokens.CARD_HOVER}; border-radius: {RADIUS_XS}px; }}
#NavHead {{ background: transparent; }}
#NavHead:hover #SectionLabel {{ color: {tokens.TEXT}; }}
#Nav[selected="true"] #NavLabel, #Nav[selected="true"] #NavSub {{ color: {tokens.ACCENT_TEXT}; font-weight: {WEIGHT_SEMIBOLD}; }}
#NavCount {{ color: {tokens.MUTED}; font-size: {TEXT_XS}px; }}
#NavCount[tone="out"] {{ color: {tokens.WARN}; font-weight: {WEIGHT_SEMIBOLD}; }}
#NavCount[tone="late"] {{ color: {tokens.BAD}; font-weight: {WEIGHT_SEMIBOLD}; }}
#Toolbar {{ border: none; }}
#CalTitle {{ font-size: {TEXT_XL}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#PageTitle {{ font-size: {TEXT_TITLE}px; font-weight: {WEIGHT_BOLD}; letter-spacing: {TRACK_TITLE}px; }}
#PageCount {{ color: {tokens.MUTED}; font-size: {TEXT_LG}px; }}
#Center {{ background: transparent; }}
QTreeWidget#Table {{ background: transparent; border: none; outline: none; font-size: {TEXT_MD}px; }}
QTreeWidget#Table::item {{ height: {TABLE_ROW_H - 1}px; border-bottom: 1px solid {tokens.BORDER}; padding: 0 {SPACE_2}px; }}
QTreeWidget#Table::item:hover {{ background: transparent; }}
QTreeWidget#Table::item:selected {{ background: transparent; color: {tokens.TEXT}; }}
QTreeWidget#Table::branch {{ background: transparent; border-bottom: 1px solid {tokens.BORDER}; }}
QTreeWidget#Table::branch:has-children:closed {{ image: url(__CHEVRON_RIGHT__); }}
QTreeWidget#Table::branch:has-children:open {{ image: url(__CHEVRON__); }}
QTreeWidget#Table::branch:selected {{ background: transparent; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{ background: transparent; color: {tokens.MUTED}; border: none; border-bottom: 1px solid {tokens.BORDER};
    padding: {SPACE_2_5}px {SPACE_2_5}px {SPACE_2}px {SPACE_2_5}px; font-size: {TEXT_SM}px; font-weight: {WEIGHT_MEDIUM}; }}
QHeaderView::section:hover {{ color: {tokens.TEXT}; }}
QHeaderView::up-arrow {{ image: url(__CHEVRON_UP__); width: {SORT_ARROW}px; height: {SORT_ARROW}px; padding-right: {SPACE_1}px; }}
QHeaderView::down-arrow {{ image: url(__CHEVRON__); width: {SORT_ARROW}px; height: {SORT_ARROW}px; padding-right: {SPACE_1}px; }}
QPushButton#Where {{ background: {tokens.INFO_SOFT}; border: 1px solid {tokens.INFO_EDGE}; color: {tokens.INFO}; text-align: left; }}
QPushButton#Where[tone="out"] {{ background: transparent; border-color: {tokens.WARN}; color: {tokens.WARN}; }}
QPushButton#Where[tone="late"] {{ background: {tokens.BAD_TINT}; border-color: {tokens.BAD_EDGE}; color: {tokens.BAD}; }}

/* ---------- the gear overview */

/* ---------- empty states */
#EmptyTitle {{ font-size: {TEXT_XL}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#EmptyText {{ color: {tokens.MUTED}; }}
#StartBadge {{ background: transparent; border: none; }}
#StartTile {{ background: {tokens.RAISED}; border: 1px solid {tokens.BORDER}; border-radius: {RADIUS_LG}px; }}
#StartTile:hover {{ background: {tokens.RAISED_HOVER}; border-color: {tokens.BORDER_HOVER}; }}
#StartTile:focus, #StartTile[hot="true"] {{ border-color: {tokens.ACCENT}; }}
#StartTile[hot="true"] {{ background: {tokens.ACCENT_TINT}; }}
#StartTitle {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; }}
#StartDetail {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; }}

/* ---------- details panel */
#Details {{ background: transparent; border: none; }}
/* a row in a card's list (a rental's lines, a kit's gear, what goes with a piece): hairlines between, never a card in a card */
#ItemBox {{ background: transparent; border: none; border-bottom: 1px solid {tokens.BORDER}; border-radius: 0; }}
#ItemBox[last="true"] {{ border-bottom-color: transparent; }}
#ItemBox[open="false"]:hover {{ background: {tokens.FILL_2}; border-bottom-color: transparent; border-radius: {RADIUS_SM}px; }}
#ItemBox:focus {{ border: {tokens.FOCUS_RING}px solid {tokens.ACCENT}; border-radius: {RADIUS_SM}px; }}
#ItemTitle {{ font-weight: {WEIGHT_MEDIUM}; }}
#ItemTitle[blank="true"] {{ color: {tokens.FAINT}; }}
#ItemAmount {{ color: {tokens.MUTED}; font-size: {TEXT_SM}px; }}
QPlainTextEdit#Field {{ background: {tokens.FILL}; border: 1px solid transparent; border-radius: {RADIUS}px;
    font-family: inherit; font-size: {TEXT_MD}px; color: {tokens.TEXT}; padding: {SPACE_1}px {SPACE_2}px;
    selection-background-color: {tokens.ACCENT_FILL}; selection-color: {tokens.ON_ACCENT}; }}
QPlainTextEdit#Field:focus {{ background: {tokens.FIELD}; border: {tokens.FOCUS_RING}px solid {tokens.ACCENT};
    padding: {SPACE_1 - tokens.FOCUS_RING + 1}px {SPACE_2 - tokens.FOCUS_RING + 1}px; }}
QPlainTextEdit#Field:disabled, QLineEdit:disabled, QComboBox:disabled {{ color: {tokens.TEXT_OFF}; border-color: {tokens.BORDER}; }}
/* the date field (components/datefield.py): the date in the accent's words, its month in a popover */
QLineEdit[date="true"] {{ color: {tokens.ACCENT_TEXT}; font-weight: {WEIGHT_MEDIUM}; }}
QLineEdit[date="true"]:disabled {{ color: {tokens.TEXT_OFF}; }}
#DatePop {{ background: {tokens.RAISED}; border: 1px solid {tokens.GLASS_STROKE}; border-radius: {tokens.RADIUS_XL}px; }}
#DatePopTitle {{ font-size: {TEXT_LG}px; font-weight: {WEIGHT_SEMIBOLD}; color: {tokens.TEXT}; }}
#DatePop QToolButton#Circle {{ background: transparent; border-color: transparent; }}
#DatePop QToolButton#Circle:hover {{ background: {tokens.ACCENT_TINT}; }}
#LogoThumb {{ background: {tokens.PAPER}; border: 1px solid {tokens.BORDER_STRONG}; border-radius: {RADIUS_SM}px; }}

/* ---------- preview panel */
#PreviewArea {{ background: {tokens.WELL}; }}
#PanelFoot {{ background: transparent; border: none; }}
#PanelBottom {{ background: {tokens.PANEL}; border-top: 1px solid {tokens.BORDER}; }}

/* ---------- popups */
QTextBrowser#WhatsNew {{ background: {tokens.FILL}; color: {tokens.TEXT}; border: none; border-radius: {RADIUS_LG}px; }}
QMenu {{ background: {tokens.RAISED}; border: 1px solid {tokens.BORDER_STRONG}; border-radius: {tokens.LIST_R}px;
    padding: {tokens.LIST_INSET - 1}px; }}
QMenu {{ min-width: {tokens.MENU_MIN_W}px; }}
QMenu::item {{ padding: 0 {SPACE_4}px 0 {SPACE_2_5}px; min-height: {tokens.LIST_ROW_H}px; border-radius: {tokens.LIST_ROW_R}px;
    margin: {tokens.LIST_GAP // 2}px 0; }}
QMenu::item:selected {{ background: {tokens.ACCENT_TINT}; color: {tokens.ACCENT_TEXT}; }}
/* a destructive choice (Delete…, Remove…) is red, highlighted or not: app.py makes it the menu's "default" item */
QMenu::item:default {{ color: {tokens.BAD}; font-weight: {WEIGHT_REGULAR}; }}
QMenu::item:default:selected {{ background: {tokens.BAD_TINT}; color: {tokens.BAD}; }}
QMenu::item:disabled {{ color: {tokens.TEXT_OFF}; }}
QMenu::icon {{ padding-left: {SPACE_2}px; }}
QMenu::separator {{ height: 1px; background: {tokens.BORDER}; margin: {SPACE_1}px {SPACE_2_5}px; }}
QMenu::section {{ color: {tokens.MUTED}; padding: {SPACE_2}px {SPACE_2_5}px {SPACE_1}px {SPACE_2_5}px; font-size: {TEXT_XS}px; font-weight: {WEIGHT_SEMIBOLD}; }}
"""


# Minimal line icons (Lucide-style, ISC licensed shapes redrawn).
_SVG = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "folder": '<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "x": '<path d="M18 6 6 18M6 6l12 12"/>',
    "retry": '<path d="M3 12a9 9 0 0 1 15.5-6.2L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-15.5 6.2L3 16"/><path d="M3 21v-5h5"/>',
    "reveal": '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 16v-4M12 8h.01"/>',
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "film": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M7 3v18M17 3v18M3 7.5h4M3 12h18M3 16.5h4M17 7.5h4M17 16.5h4"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    "audio": '<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
    "drop": '<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M5 21h14"/>',
    "pause": '<rect x="6" y="4" width="4" height="16" rx="1"/><rect x="14" y="4" width="4" height="16" rx="1"/>',
    "play": '<path d="M6 4l14 8-14 8z"/>',
    "chevron": '<path d="m6 9 6 6 6-6"/>',
    "captions": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 10.5a2 2 0 1 0 0 3M16 10.5a2 2 0 1 0 0 3"/>',
    "eye": '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="m7 9 3 3-3 3M13 15h4"/>',
    "more": '<circle cx="5" cy="12" r="1.2"/><circle cx="12" cy="12" r="1.2"/><circle cx="19" cy="12" r="1.2"/>',
    "chevron-left": '<path d="m15 6-6 6 6 6"/>',
    "chevron-right": '<path d="m9 6 6 6-6 6"/>',
    "chevron-up": '<path d="m6 15 6-6 6 6"/>',
    "scissors": '<circle cx="6" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M20 4 8.12 15.88M14.47 14.48 20 20M8.12 8.12 12 12"/>',
    "link": '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
    "stop": '<rect x="7" y="7" width="10" height="10" rx="2"/>',
    "trash": '<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6M14 11v6"/>',
    "list-x": '<path d="M11 12H3M16 6H3M16 18H3"/><path d="m15 10 4 4M19 10l-4 4"/>',
    "export": '<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M20 14v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5"/>',
    "printer": '<path d="M6 9V3h12v6"/><rect x="3" y="9" width="18" height="8" rx="2"/><path d="M6 14h12v7H6z"/>',
    "copy": '<rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/>',
    "clipboard": '<rect x="8" y="2" width="8" height="4" rx="1"/><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/>',
    "receipt": '<path d="M5 3h14v18l-3-2-2 2-2-2-2 2-2-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>',
    # the assistant: a sparkle, the standard's sign for AI everywhere (Lucide's "sparkles")
    "assistant": '<path d="M9.94 15.5A2 2 0 0 0 8.5 14.06l-6.14-1.58a.5.5 0 0 1 0-.96L8.5 9.94A2 2 0 0 0 9.94 8.5'
    "l1.58-6.14a.5.5 0 0 1 .96 0l1.58 6.14a2 2 0 0 0 1.44 1.44l6.14 1.58a.5.5 0 0 1 0 .96l-6.14 1.58a2 2 0 0 0"
    '-1.44 1.44l-1.58 6.14a.5.5 0 0 1-.96 0z"/><path d="M20 3v4M22 5h-4M4 17v2M5 18H3"/>',
    "sliders": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    "updown": '<path d="m8 9 4-4 4 4M8 15l4 4 4-4"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M5 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    "key": '<circle cx="8" cy="15" r="4"/><path d="M10.8 12.2 20 3M17 6l3 3M14 9l2 2"/>',
    "edit": '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
    "alert": '<path d="M12 9v4M12 17h.01"/><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/>',
    "arrow-up": '<path d="M12 19V5"/><path d="m5 12 7-7 7 7"/>',
    "arrow-down": '<path d="M12 5v14"/><path d="m19 12-7 7-7-7"/>',
    "moon": '<path d="M20.5 14.1A8.5 8.5 0 1 1 9.9 3.5a6.6 6.6 0 0 0 10.6 10.6z"/>',
    "box": '<path d="M21 8 12 3 3 8v8l9 5 9-5z"/><path d="m3 8 9 5 9-5M12 13v8"/>',
    "camera": '<path d="M3 8a2 2 0 0 1 2-2h2l2-2h6l2 2h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><circle cx="12" cy="12.5" r="3.5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    # Share: an arrow out of a tray, the Mac's sign for sending something somewhere (the page window)
    "share": '<path d="M12 3.5v10"/><path d="m8 7.5 4-4 4 4"/><path d="M6 11.5H5.5A1.5 1.5 0 0 0 4 13v5.5A1.5 1.5 0 0 0 5.5 20h13a1.5 1.5 0 0 0 1.5-1.5V13a1.5 1.5 0 0 0-1.5-1.5H18"/>',
    "cog": '<circle cx="12" cy="12" r="2.6"/><circle cx="12" cy="12" r="6.2"/>'
    '<path d="M12 2.6v3.2M12 18.2v3.2M2.6 12h3.2M18.2 12h3.2M5.4 5.4l2.2 2.2M16.4 16.4l2.2 2.2M5.4 18.6l2.2-2.2M16.4 7.6l2.2-2.2"/>',
    "keyboard": '<rect x="2.5" y="6" width="19" height="12" rx="2.5"/><path d="M6.5 10h.01M10 10h.01M14 10h.01M17.5 10h.01M8 14h8"/>',
    # a kit: a road case with its handle and latch
    "case": '<rect x="3" y="7" width="18" height="13" rx="2.5"/><path d="M9 7V5.5A1.5 1.5 0 0 1 10.5 4h3A1.5 1.5 0 0 1 15 5.5V7"/><path d="M3 12.5h7.5M13.5 12.5H21"/><rect x="10.5" y="11" width="3" height="3" rx=".8"/>',
    "tag": '<path d="M3.5 12.6V5a1.5 1.5 0 0 1 1.5-1.5h7.6a1.5 1.5 0 0 1 1.06.44l6.9 6.9a1.5 1.5 0 0 1 0 2.12l-7.6 7.6a1.5 1.5 0 0 1-2.12 0l-6.9-6.9a1.5 1.5 0 0 1-.44-1.06z"/><circle cx="8.5" cy="8.5" r="1.4"/>',
    "filter": '<path d="M4 7h16M7 12h10M10 17h4"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "mail": '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>',
    "attach": '<path d="M9 7H6a3 3 0 0 0 0 6h3M15 7h3a3 3 0 0 1 0 6h-3M8 10h8"/>',
    "unlink": '<path d="M9 7H6a3 3 0 0 0 0 6h3M15 7h3a3 3 0 0 1 0 6h-3"/>',
    "table": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M3 15h18M9 4v16"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
}


def svg_markup(name: str, color: str = "", stroke: float = ICON_STROKE) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color or tokens.TEXT}" '
        f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">'
        + _SVG[name].replace("{fill}", color or tokens.TEXT).replace("{on}", tokens.ON_ACCENT)
        + "</svg>"
    )


@lru_cache(maxsize=512)
def pixmap(
    name: str,
    size: int = ICON,
    color: str = "",
    stroke: float = ICON_STROKE,
    dpr: float = 2.0,
) -> QPixmap:
    """Drawn once per look and reused (a long list redraws the same few icons thousands of times)."""
    r = QSvgRenderer(QByteArray(svg_markup(name, color, stroke).encode()))
    pm = QPixmap(int(size * dpr), int(size * dpr))
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, size * dpr, size * dpr))
    p.end()
    pm.setDevicePixelRatio(dpr)
    return pm


# icons are asked for by color value (theme.MUTED); remember which token that was, so they follow a switch
_ICON_TOKENS = ("TEXT", "MUTED", "FAINT", "ACCENT", "ON_ACCENT", "BAD", "WARN", "GOOD", "ACCENT_HOVER")


def _token_of(color: str) -> str:
    for k in _ICON_TOKENS:
        if getattr(tokens, k) == color:
            return k
    return ""


DANGER = "bodega-destructive"  # the name a destructive menu row's icon goes by (is_danger)


def is_danger(i: QIcon) -> bool:
    """A destructive menu row's icon (menu_icon("trash")): its row's words are red too."""
    return i.name() == DANGER


class _Themed(QIconEngine):
    """Draws the icon in the current colors every time, so it follows light and dark."""

    def __init__(self, name: str, key: str, color: str, size: int, menu: bool, danger: bool = False):
        super().__init__()
        self.name, self.key, self.color, self.size, self.menu = name, key, color, size, menu
        self.danger = danger

    def iconName(self) -> str:
        return DANGER if self.danger else self.name

    def _color(self, mode) -> str:
        if self.menu and mode in (QIcon.Mode.Active, QIcon.Mode.Selected):
            return tokens.ACCENT_HOVER
        return getattr(tokens, self.key) if self.key else self.color

    def pixmap(self, size, mode, state):
        return pixmap(self.name, self.size, self._color(mode))

    def paint(self, painter, rect, mode, state):
        painter.drawPixmap(rect, pixmap(self.name, self.size, self._color(mode)))

    def clone(self):
        return _Themed(self.name, self.key, self.color, self.size, self.menu, self.danger)


def icon(name: str, color: str = "", size: int = ICON) -> QIcon:
    """An icon that looks the same however the button is hovered, focused or pressed."""
    color = color or tokens.TEXT
    return QIcon(_Themed(name, _token_of(color), color, size, False))


def menu_icon(name: str, color: str = "", size: int = ICON) -> QIcon:
    """For menu rows: on the highlighted row (the accent's tint) the icon takes the accent, like its words. A
    destructive row's icon (trash) is red, highlighted or not."""
    if name == "trash" and not color:
        return QIcon(_Themed(name, "BAD", tokens.BAD, size, False, danger=True))
    color = color or tokens.MUTED
    return QIcon(_Themed(name, _token_of(color), color, size, True))


def stylesheet(folder: Path) -> str:
    """QSS can only reference image files, so write the couple it needs into `folder`
    (Bodega's per-user data folder, overwritten each launch), one set per look."""
    try:
        folder.mkdir(parents=True, exist_ok=True)
    except OSError:  # data folder not writable: fall back to a private temp folder
        import tempfile

        folder = Path(tempfile.mkdtemp(prefix="bodega-ui-"))
    look = tokens.SCHEME
    chevron = folder / f"chevron-{look}.svg"
    chevron.write_text(svg_markup("chevron", tokens.MUTED))
    up = folder / f"chevron-up-{look}.svg"
    up.write_text(svg_markup("chevron-up", tokens.MUTED))
    right = folder / f"chevron-right-{look}.svg"
    right.write_text(svg_markup("chevron-right", tokens.MUTED))
    check = folder / f"check-{look}.svg"
    check.write_text(svg_markup("check", tokens.ON_ACCENT, 3))
    updown = folder / f"updown-{look}.svg"
    updown.write_text(svg_markup("updown", tokens.FAINT))
    return (
        _sheet()
        .replace("__UPDOWN__", updown.as_posix())
        .replace("__CHEVRON_RIGHT__", right.as_posix())
        .replace("__CHEVRON_UP__", up.as_posix())
        .replace("__CHEVRON__", chevron.as_posix())
        .replace("__CHECK__", check.as_posix())
    )


def wordmark() -> str:
    """The "bodega." wordmark as rich text, the dot in the accent."""
    return f'bodega<span style="color:{tokens.ACCENT}">.</span>'


def system_scheme() -> str:
    """ "light" or "dark", as the computer is set (dark when it can't tell)."""
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance()
    if app is None:
        return "dark"
    hints = app.styleHints()
    if hasattr(hints, "unsetColorScheme"):
        hints.unsetColorScheme()
    scheme = hints.colorScheme() if hasattr(hints, "colorScheme") else None
    return "light" if scheme == Qt.ColorScheme.Light else "dark"


def apply(app, appearance: str, folder: Path, accent: str | None = None) -> str:
    """Use the light or dark look ("system" asks the computer), in an accent (None keeps the current one).
    Returns the look in use."""
    from bodega.ui.components import access

    look = system_scheme() if appearance not in ("light", "dark") else appearance
    tokens.use(look, accent, contrast=access.more_contrast(), opaque=access.less_transparency())
    _load_colors()
    hints = app.styleHints()
    if appearance in ("light", "dark") and hasattr(hints, "setColorScheme"):  # title bars match
        hints.setColorScheme(Qt.ColorScheme.Light if look == "light" else Qt.ColorScheme.Dark)
    app.setStyleSheet(stylesheet(folder))
    return look


def font(size: int = TEXT_MD, weight: int = WEIGHT_REGULAR, tabular: bool = False):
    """The app's font at a type-scale size (TEXT_*) and weight (WEIGHT_*): the one way to make a QFont.
    `tabular`: every figure the same width, so columns of money line up digit for digit."""
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import QApplication

    f = QFont(QApplication.font())
    f.setPixelSize(size)
    f.setWeight(QFont.Weight(weight))
    if tabular:
        tabular_figures(f)
    return f


def tabular_figures(f) -> None:
    """Inter's tabular figures on this font (its "tnum" feature), for numbers that line up."""
    from PySide6.QtGui import QFont

    f.setFeature(QFont.Tag("tnum"), 1)


def use_tabular(widget) -> None:
    """A widget whose figures line up: a table, a total."""
    f = widget.font()
    tabular_figures(f)
    widget.setFont(f)


def plain_tip(text: str) -> str:
    """A tooltip that shows `text` exactly as typed (Qt would read "<b>…" in a name as formatting)."""
    import html

    return f"<p style='white-space:pre-wrap'>{html.escape(text)}</p>" if text else ""


def qcolor(value: str):
    """A token as a QColor: "#RRGGBB" or "rgba(r, g, b, a)" (QColor can't read the CSS form itself).
    Read once per value; each call gets its own copy to change."""
    from PySide6.QtGui import QColor

    return QColor(_parsed(value))


@lru_cache(maxsize=256)
def _parsed(value: str):
    import re

    from PySide6.QtGui import QColor

    m = re.match(r"rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)", value)
    if m:
        r, g, b, a = m.groups()
        return QColor(int(r), int(g), int(b), round(float(a) * 255))
    return QColor(value)
