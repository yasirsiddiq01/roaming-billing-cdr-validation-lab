from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parent
DASHBOARD_FILE = PROJECT_ROOT / "app" / "streamlit_dashboard.py"

runpy.run_path(str(DASHBOARD_FILE), run_name="__main__")