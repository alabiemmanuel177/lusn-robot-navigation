"""Synthetic-only joint-score prototype. No real-data fitting or runtime admission."""
import numpy as np

FEATURES=('raw_logit_scaled','valid_depth_fraction','relative_depth_iqr','reference_distance_scaled')
PENALTY=.01
MAX_STEPS=20000
GRADIENT_TOLERANCE=1e-8


def features(raw_score, valid_fraction, relative_depth_iqr, reference_distance_m):
    values=np.array([raw_score,valid_fraction,relative_depth_iqr,reference_distance_m],dtype=float)
    if not np.isfinite(values).all():raise ValueError('finite features required')
    if not 0<raw_score<1 or not 0<=valid_fraction<=1 or relative_depth_iqr<0 or not 0<=reference_distance_m<=.9:
        raise ValueError('feature domain')
    return np.array([1.,np.clip(np.log(raw_score/(1-raw_score))/12.,-1.,1.),
                     valid_fraction,min(relative_depth_iqr,1.),reference_distance_m/.9])


def sigmoid(z):
    return np.exp(-np.logaddexp(0.,-z))


def objective_gradient(beta,x,y,weights):
    z=x@beta
    loss=float(np.sum(weights*(np.logaddexp(0.,z)-y*z))+.5*PENALTY*(beta@beta))
    gradient=x.T@(weights*(sigmoid(z)-y))+PENALTY*beta
    return loss,gradient


def fit_synthetic(x,y,weights,*,provenance):
    """Numerical test harness only. This is not the primary calibration fitter."""
    if provenance!='synthetic_unit_test':raise ValueError('real-data fitting is not admitted by this candidate')
    x=np.asarray(x,dtype=float);y=np.asarray(y,dtype=float);weights=np.asarray(weights,dtype=float)
    if x.ndim!=2 or x.shape[1]!=5 or len(x)==0 or y.shape!=(len(x),) or weights.shape!=y.shape:
        raise ValueError('aligned feature/label/weight dimensions')
    if not np.isfinite(x).all() or not np.isfinite(y).all() or not np.isfinite(weights).all():raise ValueError('finite inputs')
    if not np.all(x[:,0]==1) or np.any(abs(x)>1) or not np.isin(y,[0,1]).all() or len(set(y))!=2:
        raise ValueError('bounded features, intercept and both binary outcomes required')
    if np.any(weights<=0) or abs(weights.sum()-1)>1e-12:raise ValueError('positive normalized weights')
    # Global Hessian spectral bound for weighted logistic loss + full L2.
    lipschitz=.25*float(np.sum(weights*np.sum(x*x,axis=1)))+PENALTY
    beta=np.zeros(x.shape[1]);initial=objective_gradient(beta,x,y,weights)[0]
    for step in range(MAX_STEPS):
        loss,gradient=objective_gradient(beta,x,y,weights)
        if np.max(abs(gradient))<=GRADIENT_TOLERANCE:break
        beta=beta-gradient/lipschitz
    loss,gradient=objective_gradient(beta,x,y,weights)
    if np.max(abs(gradient))>GRADIENT_TOLERANCE:raise ValueError('fixed solver did not converge; no fallback')
    return dict(coefficients=beta.tolist(),objective=loss,initial_objective=initial,
        gradient_infinity_norm=float(np.max(abs(gradient))),iterations=step+1,
        feature_order=['intercept',*FEATURES],penalty=PENALTY,
        synthetic_only=True,calibration_eligible=False,runtime_admitted=False)
