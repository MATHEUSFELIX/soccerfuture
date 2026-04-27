"""Visual constants for the 2D viewer module.

Centralizes all visual configuration — colors, sizes, fonts, and layout —
used by the rendering functions in viewer_2d.py. No magic numbers should
appear in rendering code; import from here instead.
"""

from src.utils.constants import FIELD_LENGTH, FIELD_WIDTH

# --- Field dimensions (meters) ---
FIELD_LENGTH_M: float = FIELD_LENGTH   # 105.0
FIELD_WIDTH_M: float = FIELD_WIDTH     # 68.0

# --- Player role colors ---
ROLE_COLORS: dict[str, str] = {
    "GK": "#E63946",   # vermelho
    "CB": "#264653",   # cinza-escuro
    "LB": "#457B9D",   # azul
    "RB": "#2A9D8F",   # verde-azulado
    "CDM": "#6D597A",  # roxo-acinzentado
    "CM": "#1D3557",   # azul-escuro
    "CAM": "#E9C46A",  # amarelo
    "LW": "#F4A261",   # laranja
    "RW": "#E76F51",   # coral
    "ST": "#D62728",   # vermelho-escuro
}
DEFAULT_ROLE_COLOR: str = "#888888"

# --- Top-K branch colors ---
BRANCH_COLORS: list[str] = [
    "#1F77B4",  # azul
    "#FF7F0E",  # laranja
    "#2CA02C",  # verde
    "#D62728",  # vermelho
    "#9467BD",  # roxo
    "#8C564B",  # marrom
    "#E377C2",  # rosa
]

# --- Marker sizes ---
PLAYER_MARKER_SIZE: float = 80.0
PLAYER_MARKER_SINGLE: float = 120.0  # branch individual (maior destaque)
PLAYER_LABEL_FONTSIZE: int = 6

# --- Trajectory constants ---
TRAJECTORY_LINE_WIDTH: float = 1.5
TRAJECTORY_LINE_WIDTH_SINGLE: float = 2.5  # branch individual
ARROW_HEAD_WIDTH: float = 0.8
ARROW_HEAD_LENGTH: float = 0.6

# --- Field colors ---
FIELD_COLOR: str = "#2E7D32"
LINE_COLOR: str = "#FFFFFF"
PENALTY_AREA_COLOR: str = "#256D29"
GOAL_AREA_COLOR: str = "#1B5E20"
CENTER_CIRCLE_COLOR: str = "#FFFFFF"

# --- Line widths ---
MIDFIELD_LINE_WIDTH: float = 2.0

# --- Ball marker ---
BALL_MARKER_SIZE: float = 100.0
BALL_MARKER_COLOR: str = "#FFFFFF"

# --- Figure layout ---
FIGURE_WIDTH: float = 16.0
FIGURE_HEIGHT: float = 10.0
FIELD_AXES_RECT: list[float] = [0.02, 0.05, 0.55, 0.85]
EXPLANATION_AXES_RECT: list[float] = [0.60, 0.40, 0.38, 0.55]
TELEMETRY_AXES_RECT: list[float] = [0.60, 0.05, 0.38, 0.30]

# --- Context panel layout (shown when match context is present) ---
CONTEXT_PANEL_AXES_RECT: list[float] = [0.60, 0.05, 0.38, 0.30]
TELEMETRY_AXES_RECT_SHIFTED: list[float] = [0.60, 0.38, 0.38, 0.25]

# --- Font sizes ---
TITLE_FONTSIZE: int = 12
PANEL_TITLE_FONTSIZE: int = 10
PANEL_TEXT_FONTSIZE: int = 8
