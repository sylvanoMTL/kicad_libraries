"""Single source of Phase 5 colours, spacing and shared stylesheets; plain constants, no Qt import."""

# ── Colours ─────────────────────────────────────────────────────────────────
AMBER = "#8A5200"
AMBER_TINT = "#FFF8E1"
ERROR = "#CC0000"
ERROR_TINT = "#FDECEA"
SUCCESS = "#007700"
SUCCESS_TINT = "#E6F4EA"
ACCENT = "#0078D4"
LINK = "#0057A0"
MUTED = "#595959"
SURFACE = "#F5F7FA"
SURFACE_HEADER = "#EEF1F5"
SURFACE_BASE = "#FFFFFF"  # plain button fill, and the text on a filled checked button
BORDER = "#C8C8C8"

# ── Spacing scale (px) ──────────────────────────────────────────────────────
SP_XS, SP_SM, SP_MD, SP_LG, SP_XL = 4, 8, 16, 24, 32

# ── Typography (pt) ─────────────────────────────────────────────────────────
HEADING_PT = 10
DISPLAY_PT = 12
MONO_FAMILY = "Consolas"
MONO_PT = 9

# ── Shared stylesheets ──────────────────────────────────────────────────────
PRIMARY_BUTTON_QSS = "\n".join([
    "QPushButton { background-color: #0078D4; color: white; padding: 8px 16px; "
    "font-weight: bold; min-height: 12px; }",
    "QPushButton:disabled { background-color: #E1E1E1; color: #595959; }",
])

FIELD_FRAME_QSS = "\n".join([
    "QFrame#fieldFrame { border: 2px solid transparent; border-radius: 2px; }",
    f'QFrame#fieldFrame[blocked="true"] {{ border: 2px solid {AMBER}; }}',
])
