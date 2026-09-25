"""Same OCR settings, all fixed development slots; source-bound wrapper."""
from pathlib import Path
import argparse
import run_entrance_context_candidate as runner
from integrate_object_depth_candidate import ROOT,sha

runner.OUT=ROOT/'reports/four_class_readiness_ocr_20260924_v1'
runner.SOURCE=ROOT/'reports/four_class_readiness_detector_20260924_v1'
original_write=runner.write


def bound_write(path,value):
    if Path(path)==runner.OUT/'plan.json':
        value['input_sha256'][str(Path(__file__).resolve())]=sha(__file__)
        value['input_sha256'][str(ROOT/'reports/world_specific_method_approval_20260924.json')]=sha(ROOT/'reports/world_specific_method_approval_20260924.json')
    original_write(path,value)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('panel',choices=('stage_a','broad','live'))
    panel=parser.parse_args().panel
    prefix={'stage_a':'four_class_readiness','broad':'four_class_broad','live':'four_class_live'}[panel]
    runner.OUT=ROOT/f'reports/{prefix}_ocr_20260924_v1'
    runner.SOURCE=ROOT/f'reports/{prefix}_detector_20260924_v1'
    runner.write=bound_write;runner.main()
