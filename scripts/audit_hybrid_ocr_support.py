"""Synthetic boundary test of the pinned OCR filter; never observation labels."""
import inspect
import json
from pathlib import Path
from rapidocr_onnxruntime import RapidOCR
from prepare_joint_score_protocol import ROOT,sha
from joint_score_collection import write_once
from hybrid_score_candidate import score


def main():
    plan_path=ROOT/'reports/joint_score_wave_s_primary_inference_20260924_v1/ocr/plan.json'
    plan=json.loads(plan_path.read_text())
    for path,h in plan['input_sha256'].items():
        if sha(path)!=h:raise ValueError('OCR source changed')
    # Only invoke the actual scalar filter, not inference or a model constructor.
    threshold=.5
    engine=RapidOCR.__new__(RapidOCR);engine.text_score=threshold
    inputs=[0.,.1,.499999999,.5,.500000001,.8,1.]
    boxes=list(range(len(inputs)))
    _,retained=engine.filter_result(boxes,[('LAB',p) for p in inputs])
    retained_scores=[p for _,p in retained]
    assert retained_scores==[p for p in inputs if p>=threshold]
    mapped=[score(dict(category='laboratory_entrance',raw_score=p),{})['input_score'] for p in retained_scores]
    assert mapped==retained_scores and not any(p<.5 for p in mapped)
    source=Path(inspect.getfile(RapidOCR))
    output=dict(schema_version='research3-hybrid-ocr-support-audit/v1',
        role='synthetic boundary test and inspected-source support analysis; not capture or labels',
        source_sha256={str(p):sha(p) for p in [source,plan_path,ROOT/'scripts/run_entrance_context_candidate.py',
            ROOT/'scripts/four_class_perception_candidate.py',ROOT/'scripts/hybrid_score_candidate.py',Path(__file__)]},
        configured_text_score=.5,filter_rule='retains score >= text_score',
        localization_rule='entrance raw_score copies retained OCR text score',
        upstream_rule='identity pass-through',synthetic_inputs=inputs,retained_scores=retained_scores,
        attainable_entrance_input_support=[.5,1.],required_low_bin=[0,.5],low_bin_upper_exclusive=True,
        maximum_low_bin_emissions=0,required_low_bin_emissions=5,
        conclusion='unchanged entrance filter plus raw-score pass-through cannot satisfy original C/V low-bin coverage',
        action='do not launch an unchanged campaign as a solution to this structural gate failure',
        human_labels_generated=False,model_inference_run=False)
    path=ROOT/'reports/hybrid_score_candidate_20260925_v1/ocr_support_audit.json'
    write_once(path,output);print(json.dumps(output,indent=2))


if __name__=='__main__':main()
