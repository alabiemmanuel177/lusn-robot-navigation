"""Acquire only pinned safetensors/config assets for an isolated R3 detector candidate."""
import json
from pathlib import Path
from huggingface_hub import snapshot_download
from run_stage1_feasibility import ROOT, sha, write

REVISION='57beb61adb5abda3de4a9796bc35ae60bc4b9802'
DEST=ROOT/'.research_models/owlv2-base-patch16-ensemble'/REVISION


if __name__=='__main__':
    snapshot_download('google/owlv2-base-patch16-ensemble',revision=REVISION,local_dir=DEST,
        allow_patterns=['model.safetensors','config.json','preprocessor_config.json','tokenizer_config.json',
                        'special_tokens_map.json','vocab.json','merges.txt','README.md'],max_workers=2)
    files={p.name:sha(p) for p in DEST.iterdir() if p.is_file()}
    if 'model.safetensors' not in files:raise ValueError('safe weight file missing')
    record=dict(repository='google/owlv2-base-patch16-ensemble',revision=REVISION,files=files,
        remote_code_allowed=False,pickle_weights_allowed=False,model_admitted=False)
    write(ROOT/'reports/owlv2_candidate_assets_20260923_v1.json',record)
    print(json.dumps(record))
