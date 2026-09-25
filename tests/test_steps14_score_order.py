import numpy as np
from audit_steps14_scores_v2 import summarize_arrays


def test_preserves_run_specific_query_order_not_sorted_dictionary():
    logits=np.array([[[2.,-4.,-5.]]])
    original=summarize_arrays(logits,['chair','doorway','background'])
    short=summarize_arrays(logits,['background','chair','doorway'])
    assert original['emitted']==['chair']
    assert short['emitted']==['background']
    assert original['maxima']['chair']==short['maxima']['background']
