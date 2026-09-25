import pytest
from readable_sign_reference_candidate import reference_from_text


@pytest.mark.parametrize('side',[-1,1])
def test_authoring_identity_not_fitted_offset(side):
    result=reference_from_text([4.,side*1.1],[3.,0.],template='research3-readable-corridor-sign-v1')
    assert result['map_pose']==[4.53,side*1.5]
    assert not result['general_scene_method']
    assert not result['identity_verified']


def test_reject_wrong_side_and_unknown_template():
    with pytest.raises(ValueError):reference_from_text([4.,1.1],[3.,2.],template='research3-readable-corridor-sign-v1')
    with pytest.raises(ValueError):reference_from_text([4.,1.1],[3.,0.],template='arbitrary-world')
