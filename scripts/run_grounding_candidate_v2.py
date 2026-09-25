"""Official checkpoint compatibility update, preserving v1 startup evidence."""
import argparse
import json
from pathlib import Path
import run_grounding_candidate as runner
from integrate_object_depth_candidate import ROOT,sha,write

REVISION='e08274d3760f8fcfc53dcbb9ca3ed0a29fa9c40e'
ASSETS=ROOT/'reports/grounding_candidate_assets_20260923_v2.json'
OUT=ROOT/'reports/grounding_candidate_20260923_v2'


def assets():
    from huggingface_hub import snapshot_download
    from transformers import AutoConfig
    dest=ROOT/'.research_models/grounding-dino-tiny'/REVISION
    snapshot_download('IDEA-Research/grounding-dino-tiny',revision=REVISION,local_dir=dest,
        allow_patterns=['model.safetensors','config.json','preprocessor_config.json','tokenizer_config.json',
                        'special_tokens_map.json','tokenizer.json','vocab.txt','added_tokens.json','README.md'],max_workers=2)
    config=AutoConfig.from_pretrained(dest,local_files_only=True,trust_remote_code=False)
    record=dict(repository='IDEA-Research/grounding-dino-tiny',revision=REVISION,
        model_path=str(dest),files={p.name:sha(p) for p in dest.iterdir() if p.is_file()},
        config_load_verified=True,text_model_type=config.text_config.model_type,
        remote_code_allowed=False,pickle_weights_allowed=False,model_admitted=False)
    write(ASSETS,record);print(json.dumps(record))


def configure():
    runner.OUT=OUT;runner.ASSETS=ASSETS
    original_write=runner.write
    def bound_write(path,value):
        if Path(path)==OUT/'plan.json':
            value['model_revision']=REVISION
            value['compatibility_update']='official checkpoint; v1 failed before any inference'
            for p in (Path(__file__),ROOT/'docs/GROUNDING_COMPATIBILITY_V2_20260923.md',
                      ROOT/'reports/grounding_candidate_20260923_v1/startup_failure.json',
                      ROOT/'reports/grounding_model_load_preflight_20260923_v2.json'):
                value['input_sha256'][str(p.resolve())]=sha(p)
        original_write(path,value)
    runner.write=bound_write


def preflight():
    from transformers import AutoModelForZeroShotObjectDetection
    import torch
    torch.set_num_threads(1)
    inventory=json.loads(ASSETS.read_bytes())
    model,info=AutoModelForZeroShotObjectDetection.from_pretrained(inventory['model_path'],
        local_files_only=True,trust_remote_code=False,use_safetensors=True,output_loading_info=True)
    if any(info.get(k) for k in ('missing_keys','unexpected_keys','mismatched_keys','error_msgs')):
        raise ValueError('incomplete checkpoint load: '+str(info))
    write(ROOT/'reports/grounding_model_load_preflight_20260923_v2.json',
        dict(assets_sha256=sha(ASSETS),loading_info=info,all_checkpoint_weights_loaded=True,
             source_sha256=sha(__file__),model_type=model.config.model_type))
    print('Complete checkpoint load verified; no missing/unexpected/mismatched weights')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=('assets','preflight','prepare','run','audit'))
    action=parser.parse_args().action
    if action=='assets':assets()
    elif action=='preflight':preflight()
    else:
        configure();getattr(runner,action)()
