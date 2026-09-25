"""Hash-bind component tests and diagnostic evidence; never grants launch authority."""
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from prepare_joint_score_protocol import ROOT, sha
from joint_score_collection import write_once
from snapshot_expansion_instrumentation import validate


def main():
    out = ROOT/'reports/joint_score_components_handoff_20260924_v1'
    xml = ROOT/'reports/joint_score_components_regression_20260924_v2.xml'
    suites = list(ET.parse(xml).getroot().iter('testsuite'))
    totals = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
              for key in ('tests', 'errors', 'failures', 'skipped')}
    if not suites or totals['failures'] or totals['errors']:
        raise ValueError('completed passing regression required')
    readiness_path = ROOT/'reports/four_class_perception_readiness_20260924_v1/manifest.json'
    readiness = json.loads(readiness_path.read_text())
    for path, expected in readiness['input_sha256'].items():
        if sha(ROOT/path) != expected:
            raise ValueError('frozen readiness changed: '+path)
    v8 = validate(str(ROOT/'reports/expansion_instrumentation_snapshot_20260922_v8/snapshot.json'))
    transport = ROOT/'reports/joint_score_ros_transport_20260924_v2'
    test = json.loads((transport/'transport_test.json').read_text())
    if test['passed'] is not True or test['wave_s_launched'] or test['simulator_launched']:
        raise ValueError('bounded synthetic transport evidence required')
    events = [json.loads(p.read_text()) for p in sorted(transport.glob('event-*.json'))]
    select = next(e for e in events if e['kind'] == 'select')
    close = next(e for e in events if e['kind'] == 'close')
    arm = next(e for e in events if e['kind'] == 'arm')
    if close['monotonic']-select['monotonic'] < 2. or select['stamp_ns'] <= arm['arm_stamp_ns']:
        raise ValueError('post-arm selection and fixed TF delay must be evidenced')
    files = [xml, readiness_path, ROOT/'reports/joint_score_component_replay_20260924_v1.json',
             ROOT/'reports/joint_score_protocol_20260924_v1/review_decision_CONVERSATION_FINAL.json',
             ROOT/'reports/joint_score_protocol_20260924_v1/schedule.json',
             ROOT/'docs/SCORE_LEARNING_COLLECTION_PROTOCOL_20260924.md',
             ROOT/'docs/JOINT_SCORE_COMPONENTS_IMPLEMENTATION_20260924.md']
    files += [ROOT/'scripts'/name for name in (
        'joint_score_components.py', 'joint_score_collection.py', 'joint_score_ros_capture.py',
        'joint_score_pipeline.py', 'joint_score_wave_s_admission.py', 'fit_joint_score_wave_s.py',
        'audit_joint_score_components.py', 'check_joint_score_ros_transport.py',
        'build_joint_score_components_handoff.py')]
    files += [ROOT/'tests'/name for name in (
        'test_joint_score_components.py', 'test_joint_score_collection.py',
        'test_joint_score_pipeline.py', 'test_fit_joint_score_wave_s.py', 'test_joint_score_admission.py')]
    files += [p for p in transport.iterdir() if p.is_file()]
    pins = {str(p.relative_to(ROOT)): sha(p) for p in sorted(files)}
    out.mkdir(exist_ok=False)
    result = dict(schema_version='research3-jsc-components-handoff/v1', input_sha256=pins,
        tests=totals, passed_tests=totals['tests']-totals['skipped'],
        component_implementation_tested=True, synthetic_ros_transport_passed=True,
        actual_wave_s_gazebo_preflight_passed=False, wave_s_launched=False,
        wave_s_execution_authorized=False, real_score_models_fitted=0,
        human_labels_generated=False, validation_labels_read=False, protected_worlds_read=False,
        frozen_v8_sha256=v8, runtime_admitted=False,
        remaining_prelaunch=['source-bound driver/completion-export wiring and execution manifest',
                             'actual-world clearance checks and isolated Gazebo one-frame preflight',
                             'separate manifest-bound Wave S execution authorization'])
    write_once(out/'manifest.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'input_sha256'}, indent=2))


if __name__ == '__main__':
    main()
