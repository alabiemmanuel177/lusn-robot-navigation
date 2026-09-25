"""Download only pinned safe assets for a separate offline R3 candidate."""
import json
from huggingface_hub import snapshot_download
from integrate_object_depth_candidate import ROOT, sha, write

REVISION='25b0b43915cfc9e5dcb573031e99514eb7838d57'
DEST=ROOT/'.research_models/grounding-dino-tiny'/REVISION

if __name__=='__main__':
    snapshot_download('IDEA-Research/grounding-dino-tiny',revision=REVISION,local_dir=DEST,
        allow_patterns=['model.safetensors','config.json','preprocessor_config.json','tokenizer_config.json',
                        'special_tokens_map.json','tokenizer.json','vocab.txt','added_tokens.json','README.md'],max_workers=2)
    files={p.name:sha(p) for p in DEST.iterdir() if p.is_file()}
    if 'model.safetensors' not in files:raise ValueError('missing safe weights')
    record=dict(repository='IDEA-Research/grounding-dino-tiny',revision=REVISION,files=files,
        model_path=str(DEST),remote_code_allowed=False,pickle_weights_allowed=False,model_admitted=False)
    write(ROOT/'reports/grounding_candidate_assets_20260923_v1.json',record)
    print(json.dumps(record))
