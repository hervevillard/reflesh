# Theme & Styling

All styling lives in `ui/theme.py` as a single QSS string `DARK_WARM` (Tailwind stone + orange palette).

## Color tokens

| Token | Usage |
|---|---|
| `#0d0c0b` | Deepest background (sidebar, header, status bar) |
| `#161514` | Base background |
| `#1e1c1a` | Sidebar card surfaces |
| `#242220` | Hover background (title bar buttons) |
| `#f97316` | Accent orange (slider handles, value labels, checked checkboxes) |
| `#9a3412` | Primary button (Analyze) |
| `#14532d` | Success button (Export PNG) |
| `#c42b1c` | Close button hover |

## Frameless window styling

`MainWindow` inherits from `qframelesswindow.FramelessMainWindow` (PyPI: `PyQt6-Frameless-Window`) when available. This handles DWM native resize/snap on Windows without any `nativeEvent` override. If the library is absent, falls back to `QMainWindow` with a custom header.

Title bar min/max/close buttons are styled via QPalette (dark background) + QSS (transparent button background, `#242220` hover, `#c42b1c` close-hover) so icons are visible against the dark bar.
