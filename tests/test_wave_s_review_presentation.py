import numpy as np
from build_wave_s_human_review import optical_forward
from candidate_rendering_transform import described_mounts


def test_optical_forward_is_positive_z_not_right_axis():
    _, rendered = described_mounts()
    assert np.allclose(optical_forward(rendered),[1.,0.,0.])
    assert not np.allclose(optical_forward(rendered),rendered[:3,0])
