"""
Master orchestrator - runs the full AML platform pipeline end-to-end:

  Step 1  ingest + clean + feature-engineer   (01_ingest_and_clean, 02_feature_engineering)
  Step 3  rule-based fraud detection          (03_fraud_detection)
  Step 4  customer risk profiling             (04_customer_profiling)
  Step 5  compliance & sanctions monitoring   (05_compliance_monitoring)
  Step 6  bank risk comparison                (06_bank_comparison)
  Step 7  unified KPI summary + alerts        (07_unified_kpis_and_alerts)

Usage:
    python run_pipeline.py [path_to_folder_with_the_4_source_csvs]

If no path is given, it defaults to ../raw_data relative to this file
(see db_utils.RAW_DATA_DIR).
"""
import sys
import time

import importlib


STEPS = [
    ("01_ingest_and_clean", "main"),
    ("02_feature_engineering", "main"),
    ("03_fraud_detection", "main"),
    ("04_customer_profiling", "main"),
    ("05_compliance_monitoring", "main"),
    ("06_bank_comparison", "main"),
    ("07_unified_kpis_and_alerts", "main"),
    ("08_build_dashboard_data", "main"),
    ("09_build_dashboard", "main"),
]


def main():
    source_dir = sys.argv[1] if len(sys.argv) > 1 else None
    t0 = time.time()
    for i, (mod_name, fn_name) in enumerate(STEPS, 1):
        print(f"\n{'='*78}\nSTEP {i}/{len(STEPS)}: {mod_name}\n{'='*78}")
        mod = importlib.import_module(mod_name)
        fn = getattr(mod, fn_name)
        if mod_name == "01_ingest_and_clean":
            fn(source_dir)
        else:
            fn()
    print(f"\nPipeline complete in {time.time()-t0:.1f}s. See data_marts/ and reports/.")


if __name__ == "__main__":
    main()
