"""Deterministic train-only aggregation selection; physics and learner unchanged."""
import numpy as np
CATASTROPHIC={'range_exit','field_of_view_exit','collision'}
def ensure_unique(fresh,old,tol=1e-12):
    a=np.asarray(fresh,float);b=np.asarray(old,float)
    if not np.isfinite(a).all():raise ValueError('Nonfinite initial state')
    d=np.max(np.abs(a[:,None]-a[None,:]),axis=2);np.fill_diagonal(d,np.inf)
    if np.any(d<=tol) or (len(b) and np.any(np.max(np.abs(a[:,None]-b[None,:]),axis=2)<=tol)):
        raise ValueError('Duplicate initial state within absolute 1e-12')
def stratum(error):
    # Boundary convention: [0,.5), [.5,2), [2,5), [5,10], (10,infinity).
    x=np.asarray(error)
    return np.where(x>10,4,np.where(x>=5,3,np.where(x>=2,2,np.where(x>=.5,1,0))))
def stratified_indices(error,cap):
    if cap<0:raise ValueError('Negative cap')
    if len(error)<=cap:return np.arange(len(error),dtype=int)
    bins=stratum(error);groups=[np.flatnonzero(bins==i) for i in range(5)]
    quotas=np.zeros(5,int)
    for _ in range(cap):
        eligible=[i for i,g in enumerate(groups) if quotas[i]<len(g)]
        chosen=min(eligible,key=lambda i:(quotas[i],i));quotas[chosen]+=1
    out=[]
    for g,n in zip(groups,quotas):
        if n:out.extend(g[np.floor((np.arange(n)+.5)*len(g)/n).astype(int)])
    return np.sort(np.asarray(out,int))
def select_samples(d,m,cfg,round_number):
    if m['split']!='train' or not m['id'].startswith('train_'):raise ValueError('Aggregation is train-only')
    if round_number not in [1,2]:raise ValueError('Only rounds 1 and 2')
    t=d['observation_time'];state=d['states'][:-1];k=d['sample_id'];post=t>=cfg['observe_seconds']
    goal=np.array(cfg['goal_direction'])*cfg['standoff_radius_m']
    err=np.linalg.norm(state[:,:2]-goal,axis=1);speed=np.linalg.norm(state[:,2:],axis=1)
    safety=np.zeros(len(t),bool)
    if m['termination_reason'] in CATASTROPHIC:
        safety=(t>=m['final_time_s']-10)&(t<m['final_time_s'])
    critical=(err<2)|(speed<.03)|safety
    reasons=[]
    if round_number==1:
        primary=np.flatnonzero(post&(k%4==0))
        primary=primary[stratified_indices(err[primary],300)]
        extra=np.setdiff1d(np.flatnonzero(post&critical),primary)
        extra=extra[stratified_indices(err[extra],max(0,450-len(primary)))]
        chosen=np.sort(np.r_[primary,extra])
    else:
        eligible=((err>=5)&(k%4==0))|((err>=2)&(err<5)&(k%2==0))|critical
        idx=np.flatnonzero(post&eligible);chosen=idx[stratified_indices(err[idx],600)]
    for i in chosen:
        why=[]
        if round_number==1 and k[i]%4==0:why.append('primary_2s')
        if round_number==2 and err[i]>=5 and k[i]%4==0:why.append('far_2s')
        if round_number==2 and 2<=err[i]<5 and k[i]%2==0:why.append('middle_1s')
        if err[i]<2:why.append('goal_error_lt_2m')
        if speed[i]<.03:why.append('speed_lt_0.03')
        if safety[i]:why.append('within_10s_of_safety_failure')
        reasons.append(why)
    return chosen,err[chosen],speed[chosen],reasons
def selection_key(r):
    return (-r['success'],r['catastrophic_exits'],r['median_final_goal_error'],
        r['median_final_speed'],r['median_total_dv'],r['validation_mse'],r['lag'],r['regularization'])
def validation_gate(r):
    return bool(r['success']>=10 and r['catastrophic_exits']<=1 and
        r['median_final_goal_error']<=.50 and r['median_final_speed']<=.015)
def require_test_allowed(selected,lock_exists,started):
    if not validation_gate(selected) or not lock_exists:raise RuntimeError('Validation gate/model lock required')
    if started:raise RuntimeError('Fresh test already started; never repeat')

def check_locked_files(files):
    from .recording import sha256
    for path,expected in files.items():
        if sha256(path)!=expected:raise RuntimeError('Model lock changed: '+str(path))
