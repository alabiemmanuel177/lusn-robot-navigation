"""Relocate the actual kit and decode every UI frame without making judgments."""
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
import zipfile
from class_aware_acquisition_pilot import OUTPUT
from run_stage1_feasibility import sha, write

CHECK = r'''
import io, json
from pathlib import Path
from PIL import Image
import review
root = Path.cwd()
review.activate()
manifest = review.verify_kit(root)
assert manifest['dataset_role'] == 'design_feasibility'
assert manifest['calibration_eligible'] is False
assert not (root / 'review_output').exists()
store = review._UI.ReviewStore(root/'inventory.json', root/'qa.jsonl', root/'preview.jsonl',
    evidence=root/'evidence.json', policy=root/'policy.draft.json')
state = store.state()
assert len(store.items) == manifest['targets'] > 0
assert all(not item['joint_policy_approved'] for item in state['items'])
dimensions = []
for i in range(len(store.items)):
    png = store.png(i)
    with Image.open(io.BytesIO(png)) as image:
        image.load()
        assert image.format == 'PNG'
        dimensions.append(list(image.size))
assert len(store.events()) == 1  # unlabelled journal header only
assert not (root/'review_output').exists()
print(json.dumps(dict(targets=len(store.items),decoded_ui_images=len(dimensions),
    image_dimensions=sorted({tuple(d) for d in dimensions}),all_preview_only=True,
    human_labels_generated=False,approval_generated=False,relocation_verified=True)))
'''


def main():
    packet = OUTPUT / 'review_packet'
    kit = packet / 'research3_class_aware_design_review_kit_v1.zip'
    with tempfile.TemporaryDirectory(prefix='r3-design-kit-relocation-') as temporary:
        root = Path(temporary)
        with zipfile.ZipFile(kit) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('duplicate ZIP member')
            for name in names:
                path = PurePosixPath(name)
                if path.is_absolute() or '..' in path.parts or '\\' in name:
                    raise ValueError('unsafe ZIP member')
            archive.extractall(root)
        response = subprocess.run([sys.executable, '-c', CHECK], cwd=root, text=True,
                                  capture_output=True, check=True, timeout=180)
        result = json.loads(response.stdout)
    result.update(kit_sha256=sha(kit),integrity_passed=True,calibration_eligible=False)
    write(packet / 'relocation_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
