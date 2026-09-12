"""Synthetic wrapper isolation checks; no authorization data or ROS is used."""
from contextlib import nullcontext
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


def test_authorized_wrapper_rejects_symlink_report_parent(tmp_path, monkeypatch):
    script=Path(__file__).parents[1]/'scripts/run_authorized_heldout_episode.py'
    spec=importlib.util.spec_from_file_location('heldout_output_wrapper',script)
    wrapper=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wrapper)
    workspace=tmp_path/'workspace';workspace.mkdir()
    elsewhere=tmp_path/'elsewhere';elsewhere.mkdir()
    (workspace/'reports').symlink_to(elsewhere,target_is_directory=True)
    monkeypatch.setattr(wrapper,'ROOT',workspace)
    monkeypatch.setattr(wrapper,'exclusive_campaign_runtime',nullcontext)
    monkeypatch.setattr(wrapper,'require_research2_idle',lambda:None)
    monkeypatch.setattr(wrapper,'coexistence_headroom',lambda:None)
    monkeypatch.setattr(wrapper.os,'nice',lambda value:None)
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
        monkeypatch.setenv(name,'2')
    request={'run_id':'synthetic-safe-run','system_id':'B6'}
    def should_not_write(path,payload):
        pytest.fail('wrapper reached output writer through a symlink parent')
    runtime=SimpleNamespace(write_once=should_not_write,
                            execute=lambda *a,**k:pytest.fail('ROS execution is forbidden in this fixture'))
    monkeypatch.setattr(wrapper,'prepare_authorized',lambda *a:(None,runtime,request,None,None))
    with pytest.raises((PermissionError,ValueError),match='symlink|contain|outside'):
        wrapper.execute_authorized(tmp_path/'unused-approval','unused-sha','synthetic-slot')
    assert list(elsewhere.iterdir())==[]
