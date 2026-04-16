"""Arctic Steel color theme for MUN Argument Builder."""

from rich.console import Console
from rich.theme import Theme

THEME = Theme({
    "header":          "bold #7eb8f7",
    "key":             "bold #9dd9c5",
    "value":           "#d4dde8",
    "warn":            "bold #f4c542",
    "error":           "bold #ff7e7e",
    "dim":             "#3a4a5e",
    "success":         "bold #9dd9c5",
    "divider":         "#3a4a5e",
    "arg.label":       "bold #7eb8f7",
    "arg.block":       "#d4dde8",
    "clause.verb":     "italic #7eb8f7",
    "severity.high":   "bold #ff7e7e",
    "severity.medium": "bold #f4c542",
    "severity.low":    "bold #7eb8f7",
    "severity.info":   "bold #9dd9c5",
})

CONSOLE = Console(theme=THEME)

# Raw hex palette — used in Style(color=...) patterns throughout the app
COLORS: dict[str, str] = {
    "header":  "#7eb8f7",
    "key":     "#9dd9c5",
    "value":   "#d4dde8",
    "warn":    "#f4c542",
    "error":   "#ff7e7e",
    "dim":     "#3a4a5e",
    "success": "#9dd9c5",
    "info":    "#7eb8f7",
}

DESIGNED_FOR_BG = "#0d1117"
