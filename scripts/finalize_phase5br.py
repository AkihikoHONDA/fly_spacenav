"""Final inventory and append-only project record for bounded Phase 5B-R."""
import json,re,datetime
from pathlib import Path
from flyrendezvous.recording import write_json,sha256
O=Path('outputs/phase5br')
def main():
    result=json.loads((O/'completion.json').read_text());rounds=json.loads((O/'validation_by_round.json').read_text())['rounds'];r=rounds[-1]
    outcome=f"fresh test {result['fresh_test_success']}/8成功" if result['fresh_test_run'] else 'validation gate未達、fresh test未実行'
    addition=f"""
## Phase 5B-R：train-only dataset aggregation

fresh split（36/12/8、seed5201/5202/5203）で教師56/56成功後、同じ6候補の線形readoutを最大2roundのtrain-only追加ラベルで学習した。Flyvis・HCW・fixed camera・goal・飽和・成功条件は固定。最終Round {r['round']}のvalidationは{r['success']}/12成功、{outcome}。旧5B test8本を学習・選択・回復判定へ再利用していない。truth評価は未実行。

[Phase 5B-R報告](docs/phase5br_report.md)に各round、sample出典/cap、特徴分布、終端安定化、GPU既知prefix問題、旧成果保護を記録。{'nominal recoveryを達成したが、truth評価へ自動移行せず停止した。' if result['nominal_recovery'] else '今回の回復条件は未達。追加roundやarchitecture変更を行わず、次のtemporal/recurrent readout検討を提案して停止した。'}
"""
    for p in ['README.md','docs/project.md']:
        before=(O/(Path(p).stem+'_before.md')).read_bytes()
        expected=addition if p=='README.md' else addition.replace('(docs/phase5br_report.md)','(phase5br_report.md)')
        current=Path(p).read_bytes()
        if current==before:
            with Path(p).open('ab') as f:f.write(expected.encode('utf-8'))
        else:
            assert current==before+expected.encode('utf-8'),'Unexpected documentation edit'
    report=Path('docs/phase5br_report.md')
    for link in re.findall(r'\]\(([^)]+)\)',report.read_text()):
        if link.startswith(('https:','http:')):continue
        p=(report.parent/link).resolve()
        if p==(O/'manifest.json').resolve():continue
        assert p.is_file(),str(p)
    contract=json.loads((O/'contract.json').read_text())
    for p,h in contract['files'].items():assert sha256(p)==h
    paths=set()
    for root in ['configs/phase5br','models/phase5br','outputs/phase5br','docs/evidence_phase5br']:
        paths.update(p for p in Path(root).rglob('*') if p.is_file() and p!=O/'manifest.json')
    for root in ['src/flyrendezvous','scripts','tests']:paths.update(Path(root).glob('*phase5br*.py'))
    paths.update([Path('docs/codex_phase5br.md'),report])
    artifacts={str(p):dict(sha256=sha256(p),bytes=p.stat().st_size) for p in sorted(paths)}
    write_json(O/'manifest.json',dict(phase='5B-R',created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        result=result,contract=contract,old_data_used=False,truth_executed=False,
        parameter_sha256=json.loads((O/'data.json').read_text())['parameter_sha256'],
        protected_prior=json.loads((O/'regression.json').read_text())['protected_files'],
        documentation_append_only={p:sha256(p) for p in ['README.md','docs/project.md']},
        artifacts=artifacts,artifact_count=len(artifacts),bytes=sum(x['bytes'] for x in artifacts.values()),
        excludes_manifest_itself=True))
    print('Finalized',len(artifacts),'artifacts;',outcome)
if __name__=='__main__':main()
