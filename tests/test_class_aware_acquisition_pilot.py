import importlib
from collections import Counter
import class_aware_acquisition_pilot as pilot
import distance_lighting_pilot as old


def test_fixed_class_aware_panel():
    rows=pilot.build_rows()
    assert len(rows)==len({r['candidate_id'] for r in rows})==96
    assert Counter(r['category'] for r in rows)==dict(chair=24,doorway=24,laboratory_entrance=24,office_entrance=24)
    for row in rows:
        assert row['simulator_seed']==17 and not row['calibration_eligible']
        assert row['human_verdict'] is None
        if row['category']=='doorway':
            assert row['acquisition_family']=='near_oblique'
            assert row['yaw_offset_rad'] in (-.95,.95) and row['source_view_index'] in (0,3)
        else:
            assert row['acquisition_family']=='midpoint_far' and row['distance_fraction'] in (.5,1.)
    assert rows==pilot.build_rows()


def test_import_and_temporary_binding_restore_historical_driver():
    output,rows,args=old.OUTPUT,old.rows,old.arguments
    importlib.reload(pilot)
    assert old.OUTPUT==output and old.rows is rows and old.arguments is args
    with pilot.bound_engine():assert old.OUTPUT==pilot.OUTPUT
    assert old.OUTPUT==output and old.rows is rows and old.arguments is args


def test_exact_seed_capture_only():
    args=pilot.arguments(pilot.build_rows()[0],100)
    assert args[args.index('--simulation-seed')+1]=='17'
    assert '--capture-only' in args and '--calibration' not in args
