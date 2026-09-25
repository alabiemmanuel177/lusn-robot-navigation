"""Pin current official converted weights after rejecting two legacy checkpoints."""
import argparse
import json
from pathlib import Path
import run_grounding_candidate as runner
from integrate_object_depth_candidate import ROOT,sha,write

REVISION='a2bb814dd30d776dcf7e30523b00659f4f141c71'
ASSETS=ROOT/'reports/grounding_candidate_assets_20260923_v3.json'
OUT=ROOT/'reports/grounding_candidate_20260923_v3'
PREFLIGHT=ROOT/'reports/grounding_model_load_preflight_20260923_v3.json'


def assets():
    from huggingface_hub import snapshot_download
    dest=ROOT/'.research_models/grounding-dino-tiny'/REVISION
    snapshot_download('IDEA-Research/grounding-dino-tiny',revision=REVISION,local_dir=dest,
        allow_patterns=['model.safetensors','config.json','preprocessor_config.json','tokenizer_config.json',
                        'special_tokens_map.json','tokenizer.json','vocab.txt','added_tokens.json','README.md'],max_workers=2)
    write(ASSETS,dict(repository='IDEA-Research/grounding-dino-tiny',revision=REVISION,
        model_path=str(dest),files={p.name:sha(p) for p in dest.iterdir() if p.is_file()},
        remote_code_allowed=False,pickle_weights_allowed=False,model_admitted=False))


def preflight():
    from transformers import AutoModelForZeroShotObjectDetection
    import torch
    torch.set_num_threads(1)
    inventory=json.loads(ASSETS.read_bytes())
    model,info=AutoModelForZeroShotObjectDetection.from_pretrained(inventory['model_path'],
        local_files_only=True,trust_remote_code=False,use_safetensors=True,output_loading_info=True)
    if any(info.get(k) for k in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')):
        raise ValueError('incomplete checkpoint load: '+str(info))
    write(PREFLIGHT,dict(assets_sha256=sha(ASSETS),loading_info=info,all_checkpoint_weights_loaded=True,
                        source_sha256=sha(__file__),model_type=model.config.model_type))
    print('Complete checkpoint load verified; no missing/unexpected/mismatched weights')


def configure():
    runner.OUT=OUT;runner.ASSETS=ASSETS;original_write=runner.write
    def bound_write(path,value):
        if Path(path)==OUT/'plan.json':
            proof=json.loads(PREFLIGHT.read_bytes())
            if proof['assets_sha256']!=sha(ASSETS) or not proof['all_checkpoint_weights_loaded']:raise ValueError('preflight binding')
            value['model_revision']=REVISION
            value['compatibility_update']='official converted checkpoint; legacy revisions rejected before inference'
            for p in (Path(__file__),PREFLIGHT,ROOT/'docs/GROUNDING_COMPATIBILITY_V3_20260923.md',
                      ROOT/'reports/grounding_legacy_startups_20260923.json',
                      ROOT/'scripts/integrate_grounding_candidate.py'):
                value['input_sha256'][str(p.resolve())]=sha(p)
        original_write(path,value)
    runner.write=bound_write


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('assets','preflight','prepare','run','audit'))
    action=parser.parse_args().action
    if action=='assets':assets()
    elif action=='preflight':preflight()
    else:configure();getattr(runner,action)()
