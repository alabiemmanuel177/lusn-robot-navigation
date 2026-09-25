"""Synthetic transport evidence only; never human judgments or campaign data."""
import json
import pytest
from bind_wave_s_execution import inspect_transport, sha


def put(path, value):
    path.write_text(json.dumps(value))


@pytest.fixture
def transport(tmp_path):
    config = tmp_path/'config.json'; put(config, {})
    rows = []
    for i, category in enumerate(('chair', 'doorway', 'laboratory_entrance', 'office_entrance')):
        folder = tmp_path/f'view-{i:02}'; folder.mkdir()
        (folder/'image.bin').write_bytes(b'synthetic')
        summary = dict(status='captured', attempt_id='preflight-'+category,
                       launch_monotonic=1., deadline_monotonic=91.)
        put(folder/'summary.json', summary); rows.append(summary)
        put(folder/'execution.json', dict(failure=None, owned_launches_exited=True,
            owned_launch_pids=[1, 2], motion_dispatched=False, source_checked_after_capture=True,
            cleanup=dict(forced_kill_count=0)))
        put(folder/'plan.json', dict(preflight_only=True, primary_eligible=False,
            seed=29, partition='development', input_sha256={str(config): sha(config)}))
        image = dict(file='image.bin', sha256=sha(folder/'image.bin'), frame_id='camera')
        put(folder/'frame-000.json', dict(rgb_stamp_ns=200, depth_stamp_ns=200,
            rgb=image, depth=image, camera_to_map=dict(header=dict(frame_id='map',
                stamp=dict(sec=0, nanosec=200)), child_frame_id='camera')))
        for j, event in enumerate([
            dict(kind='arm', arm_stamp_ns=100, monotonic=2.),
            dict(kind='select', stamp_ns=200, monotonic=3.),
            dict(kind='close', monotonic=5.),
            dict(kind='localization_ready', no_spawn_contact=True, amcl_converged=True),
        ]): put(folder/f'event-{j:03}.json', event)
    put(tmp_path/'capture_audit.json', dict(transport_passed=True, primary_eligible=False,
        config_sha256=sha(config), rows=rows))
    return tmp_path, config


def test_complete_transport(transport):
    root, config = transport
    assert len(inspect_transport(root, config)) == 4


@pytest.mark.parametrize('file,key,value', [
    ('execution.json', 'failure', 'failed'),
    ('execution.json', 'owned_launches_exited', False),
    ('execution.json', 'motion_dispatched', True),
    ('plan.json', 'primary_eligible', True),
    ('plan.json', 'seed', 101),
    ('frame-000.json', 'depth_stamp_ns', 201),
    ('event-002.json', 'monotonic', 4.),
    ('event-002.json', 'monotonic', 91.),
])
def test_transport_fail_closed(transport, file, key, value):
    root, config = transport
    path = root/'view-00'/file
    item = json.loads(path.read_text()); item[key] = value; put(path, item)
    with pytest.raises(ValueError): inspect_transport(root, config)


def test_rejects_changed_image(transport):
    root, config = transport
    (root/'view-00/image.bin').write_bytes(b'changed')
    with pytest.raises(ValueError, match='image integrity'): inspect_transport(root, config)
