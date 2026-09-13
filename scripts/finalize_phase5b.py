"""Finalize a machine-readable inventory, without modifying any trial or model."""
import json,re,datetime
from pathlib import Path
from flyrendezvous.recording import sha256,write_json
O=Path('outputs/phase5b')
def main():
    contract=json.loads((O/'contract.json').read_text());lock=json.loads((O/'model_lock.json').read_text())
    for p,h in {**contract['files'],**lock['source_files']}.items():assert sha256(p)==h,p
    assert sha256(lock['readout'])==lock['readout_sha256']
    report=Path('docs/phase5b_report.md')
    # Manifest itself is created below; all other report links must already resolve.
    links=[]
    for match in re.finditer(r'\]\(([^)]+)\)',report.read_text()):
        link=match.group(1)
        if link.startswith(('http://','https://')):continue
        target=(report.parent/link).resolve()
        if target== (O/'manifest.json').resolve():continue
        assert target.is_file(),str(target)
        links.append(str(target.relative_to(Path.cwd())))
    # Capture provenance still resolves after removing a misleading legacy "hold" filename.
    capture=json.loads(Path('docs/evidence_phase5b/H0/screenshots_demo.json').read_text())
    for frame in capture['screenshots']+[capture['terminal_frame']]:
        assert sha256(frame['file'])==frame['sha256']
    video=json.loads((O/'mp4/H0_verification.json').read_text())
    assert sha256(video['file'])==video['sha256']
    assert sha256(O/'demo/H0/demo.rrd')==video['source_rrd_sha256']
    phase_paths=set()
    for root in ['configs/phase5b','models/phase5b','outputs/phase5b','docs/evidence_phase5b']:
        phase_paths.update(p for p in Path(root).rglob('*') if p.is_file() and p!=O/'manifest.json')
    phase_paths.update(Path(p) for p in ['docs/codex_phase5b.md','docs/phase5b_report.md'])
    for root in ['scripts','src/flyrendezvous','tests']:
        phase_paths.update(p for p in Path(root).glob('*phase5b*.py'))
    records={str(p):dict(sha256=sha256(p),bytes=p.stat().st_size) for p in sorted(phase_paths)}
    statuses=json.loads((O/'completion.json').read_text())
    reg=json.loads((O/'regression.json').read_text())
    write_json(O/'manifest.json',dict(phase='5B',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        status=statuses['status'],objective_fully_achieved=False,
        executed_stages=['coordinate_force_tests','numerical_physics_validation','teacher_gate','data','train_validation','H0','saved_H0_analysis_and_playback'],
        no_truth_closed_loop=True,main_demo_fixed_before_results='test_00',
        main_demo_result='H0 field_of_view_exit at 456.5 s; E0/RM3 not run',
        withheld_conditions=statuses['withheld_conditions'],model=lock,preregistration=contract,
        units=dict(position='m',velocity='m/s',acceleration='m/s^2',dv='m/s',time='physical s',image='pixels'),
        artifact_count=len(records),artifact_total_bytes=sum(x['bytes'] for x in records.values()),
        artifacts=records,documentation_append_only={p:sha256(p) for p in ['README.md','docs/project.md']},
        report_local_links_checked=len(links),protected_prior_files=reg['total_protected'],
        test_summary=statuses['tests'],no_post_test_tuning=True,no_next_phase=True,
        inventory_note='Manifest excludes itself. Command log files and native frame evidence are included.'))
    print('Manifest:',len(records),'artifacts;',len(links),'report links resolved; old files protected:',reg['total_protected'])
if __name__=='__main__':main()
