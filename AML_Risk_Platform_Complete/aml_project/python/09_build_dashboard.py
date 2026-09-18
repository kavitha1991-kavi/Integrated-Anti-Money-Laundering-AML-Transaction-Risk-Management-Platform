"""
Assembles dashboard.html from dashboard_template.html + dashboard.js +
data_marts/dashboard_data.json + a locally-vendored Chart.js build.

Run this after run_pipeline.py + 08_build_dashboard_data.py to refresh the
dashboard with new data. Chart.js is inlined (not loaded from a CDN) so the
dashboard is a single, fully offline-capable file -- no server, no internet
connection required to view it, which matters for a compliance tool that
may need to run inside a locked-down bank network.
"""
import pathlib
import subprocess
import sys
import tempfile

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent


def ensure_chartjs(dest: pathlib.Path):
    if dest.exists():
        return
    print("Fetching Chart.js via npm (one-time)...")
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["npm", "init", "-y"], cwd=tmp, check=True, capture_output=True)
        subprocess.run(["npm", "install", "chart.js@4.4.1"], cwd=tmp, check=True, capture_output=True)
        bundle = pathlib.Path(tmp) / "node_modules" / "chart.js" / "dist" / "chart.umd.js"
        dest.write_text(bundle.read_text())


def main():
    template = (BASE_DIR / "dashboard_template.html").read_text()
    data_json = (BASE_DIR / "data_marts" / "dashboard_data.json").read_text()
    js = (BASE_DIR / "dashboard.js").read_text()

    chartjs_path = BASE_DIR / "chart.umd.js"
    ensure_chartjs(chartjs_path)
    chartjs = chartjs_path.read_text()

    out = (
        template.replace("__CHARTJS_LIB__", chartjs)
        .replace("__DASHBOARD_DATA__", data_json)
        .replace("__DASHBOARD_JS__", js)
    )
    out_path = BASE_DIR / "dashboard.html"
    out_path.write_text(out)
    print(f"wrote {out_path} ({out_path.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    sys.exit(main())
