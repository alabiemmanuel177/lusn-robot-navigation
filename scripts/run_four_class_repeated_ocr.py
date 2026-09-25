"""Fixed OCR settings on the two repeated-instance captures, with wrapper pin."""
from pathlib import Path
import run_entrance_context_candidate as runner
from integrate_object_depth_candidate import ROOT,sha

runner.SOURCE=ROOT/'reports/four_class_repeated_detector_20260924_v1'
runner.OUT=ROOT/'reports/four_class_repeated_ocr_20260924_v1'
original_write=runner.write


def bound_write(path,value):
    if Path(path)==runner.OUT/'plan.json':
        value['input_sha256'][str(Path(__file__).resolve())]=sha(__file__)
    original_write(path,value)


if __name__=='__main__':
    runner.write=bound_write;runner.main()
