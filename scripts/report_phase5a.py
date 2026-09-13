"""Populate Phase 5A report tables from saved audit outputs."""
import json
from pathlib import Path
import numpy as np
OUT=Path('outputs/phase5a')
def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(str(x) for x in r)+' |' for r in rows])
def main():
    m=json.loads((OUT/'test00_metrics.json').read_text());rows=json.loads((OUT/'trial_summary.json').read_text())
    text=Path('docs/phase5a_report_template.md').read_text()
    windows=[]
    for label,key in [('First 10%','first10'),('First 25%','first25'),('First 50%','first50'),('Last 50%','last50'),('Last 25%','last25'),('Last 10%','last10')]:
        f=m['time_windows']['full'][key];p=m['time_windows']['post_observe'][key]
        windows.append([label,f"{f['dv_fraction']:.2%}",f"{p['dv_fraction']:.2%}",f"{p['dv_mps']:.8f}"])
    text=text.replace('{{windows}}',table(['時間window','Full基準 Δv比','Post基準 Δv比','Post Δv m/s'],windows))
    bins=[];pooled=[];labels=['0–1%','1–5%','5–10%','10–25%','25–50%','50–100%','>100%']
    for label,f,p in zip(labels,m['command_distribution']['full'],m['command_distribution']['post_observe']):
        bins.append([label,f"{f['sample_fraction']:.2%}",f"{f['time_fraction']:.2%}",f"{p['sample_fraction']:.2%}",f"{p['time_fraction']:.2%}",f"{p['dv_fraction']:.2%}"])
    text=text.replace('{{bins}}',table(['ノルム基準','Full sample比','Full time比','Post sample比','Post time比','Δv比'],bins))
    for label,b in zip(labels,json.loads((OUT/'pooled_command_distribution.json').read_text())['bins']['post_observe']):
        pooled.append([label,b['samples'],f"{b['sample_fraction']:.2%}",f"{b['time_fraction']:.2%}",f"{b['dv_fraction']:.2%}"])
    text=text.replace('{{pooled}}',table(['ノルム基準','samples','sample比','time比','Δv比'],pooled))
    phases=[]
    for label,key in [('早期quarter','early_quarter'),('中間half','middle_half'),('終端quarter','terminal_quarter'),('成功hold（終端内）','success_hold')]:
        p=m['phases'][key];phases.append([label,f"{p['start_s']:.3f}–{p['end_s']:.3f}",f"{p['dv_mps']:.6f}",f"{p['dv_fraction']:.2%}",f"{p['parallel_dv_mps']:.6f}",f"{p['perpendicular_dv_mps']:.6f}"])
    text=text.replace('{{phases}}',table(['区間','時刻 s','Δv m/s','Total比','Parallel積分','Perpendicular積分'],phases))
    sens=[]
    for key,e in m['direction_sensitivity']['post_observe'].items():
        sens.append([f'{float(key):.0%}',f"{e['active_duty_ratio']:.2%}",e['number_of_active_intervals'],e['direction_changes_45deg'],e['direction_changes_90deg']])
    text=text.replace('{{sensitivity}}',table(['閾値','Post active duty','連続active区間','≥45°','≥90°'],sens))
    trialrows=[]
    for r in rows:
        trialrows.append([r['trial_id'],r['group'],r['result'],f"{r['duration_s']:.1f}",f"{r['total_dv_mps']:.5f}",f"{r['braking_dv_fraction']:.1%}",f"{r['active_duty_5pct']:.1%}",r['direction_changes_45deg'],f"{r['final_speed_mps']:.5f}"])
    text=text.replace('{{trials}}',table(['trial','group','result','終了 s','Δv m/s','制動比','active 5%','≥45°','最終speed'],trialrows))
    parts=[[r for r in rows if r['group']=='approach'],[r for r in rows if r['group']=='near' and r['result']=='success'],[r for r in rows if r['failure_reason']]]
    grows=[]
    for key,label in [('total_dv_mps','Total Δv m/s'),('max_u_norm_mps2','Max command m/s²'),('braking_dv_fraction','Braking fraction'),('perpendicular_dv_fraction','Perpendicular fraction'),('active_duty_5pct','Active duty 5%'),('direction_changes_45deg','Direction changes ≥45°'),('min_goal_error_m','Min error m'),('final_speed_mps','Final speed m/s')]:
        grows.append([label]+[f'{np.median([r[key] for r in group]):.6g}' for group in parts])
    text=text.replace('{{groups}}',table(['trial中央値','approach成功 n=8','near成功 n=2','near失敗 n=2'],grows))
    candidates=json.loads((OUT/'phase5b_geometry_candidates.json').read_text())['candidates']
    crows=[[f"{c['radial_depth_m']:.0f}",f"{c['goal_error_m']:.0f}",f"{c['diameter_px']:.3f}",f"{c['bearing_plus_angular_radius_deg']:.3f}"] for c in candidates if c['cross_offset_abs_m']==0]
    text=text.replace('{{camera}}',table(['r0中心depth m','軸上goal error m','球直径 px','球角半径 deg'],crows))
    assert '{{' not in text
    Path('docs/phase5a_report.md').write_text(text)
if __name__=='__main__':main()
