(
set -euo pipefail
umask 077
cd /home/vrrcelestino/model-agrologistic-hygiene-audit
/home/vrrcelestino/venv313_g14/bin/python -B -I - <<'PY'
import datetime, hashlib, importlib.metadata as md, json, pathlib, re
import shutil, subprocess, tarfile, tempfile

base = pathlib.Path.cwd()
assert str(base) == '/home/vrrcelestino/model-agrologistic-hygiene-audit'
assert not __import__('os').environ.get('SLURM_JOB_ID'), 'Execute no login node'
claim = base / '.mvp3-gurobi14-h215-compat-v1'
assert claim.is_dir() and not claim.is_symlink()
assert (claim / 'job-id.txt').read_text().strip() == '2278573'
out = pathlib.Path(tempfile.mkdtemp(prefix='gurobi14-2278573-final-', dir=base))
print('TRANSFER_DIR=' + str(out), flush=True)

account = subprocess.run(['sacct', '-j', '2278573', '--parsable2',
    '--format=JobIDRaw,State%30,ElapsedRaw,ExitCode,Start,End,ReqMem,MaxRSS,AllocCPUS,NodeList'],
    capture_output=True, check=True, timeout=30)
(out / 'sacct.txt').write_bytes(account.stdout)
(out / 'sacct.stderr').write_bytes(account.stderr)
rows = [s.split('|') for s in account.stdout.decode().splitlines() if s.startswith('2278573|')]
assert len(rows) == 1 and rows[0][1].split()[0] in {
    'FAILED','COMPLETED','CANCELLED','TIMEOUT','OUT_OF_MEMORY','NODE_FAIL',
    'PREEMPTED','BOOT_FAIL','DEADLINE','REVOKED'}, 'Contabilidade ainda nao terminal'
print(account.stdout.decode(), end='')

names = ('plan.json started.json input-receipt.json native-ready.json '
    'optimization-entry.json native-return.json independent-validation.json '
    'result.json SHA256SUMS batch-exit.json job-id.txt job.sh submission-intent.json '
    'submission.stdout submission.stderr slurm-2278573.out slurm-2278573.err').split()
receipts = out / 'original-job-receipts'
receipts.mkdir()
missing = []
for name in names:
    p = claim / name
    if p.is_file() and not p.is_symlink():
        shutil.copyfile(p, receipts / name)
    else:
        missing.append(name)
(out / 'missing-files.json').write_text(json.dumps(missing, indent=2) + '\n')

frozen = base / '.mvp3-gurobi14-environment-v1/clone-after.json'
shutil.copyfile(frozen, out / 'clone-after.original.json')
expected = {k: v['version'] for k, v in json.loads(frozen.read_bytes())['packages'].items()}
current = {}
for d in md.distributions():
    key = re.sub(r'[-_.]+', '-', d.metadata['Name']).lower()
    assert key not in current, 'Distribuicao duplicada: ' + key
    current[key] = d.version
snapshot = {'snapshot_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'scope': 'Current metadata only; not the historical inventory at job start',
    'frozen_count': len(expected), 'current_count': len(current),
    'added': {k: v for k, v in current.items() if k not in expected},
    'removed': sorted(set(expected) - set(current)),
    'changed': {k: [expected[k], current[k]] for k in expected.keys() & current.keys()
                if expected[k] != current[k]}, 'current_packages': current}
(out / 'environment-current.json').write_text(json.dumps(snapshot, indent=2) + '\n')

plan = json.loads((receipts / 'plan.json').read_bytes())
controller = pathlib.Path(plan['source_root']) / 'scripts/gurobi14_h215_compat.py'
assert controller.resolve().is_relative_to(base.resolve()) and not controller.is_symlink()
expected_code = 'cf546a9c9dcd35a52f5f758e54bf4020139b1ca68b083b6f5ae5510ac9331a1e'
code_hash = hashlib.sha256(controller.read_bytes()).hexdigest()
if code_hash == expected_code and plan['source_sha'] == '72fd9f52e1b439b46576d7d33cfaf928a63a51df':
    collected = subprocess.run(['/home/vrrcelestino/venv313_g14/bin/python', '-B', '-I',
        str(controller), 'collect', '--source-sha', plan['source_sha']],
        capture_output=True, timeout=180)
    (out / 'collector.stdout').write_bytes(collected.stdout)
    (out / 'collector.stderr').write_bytes(collected.stderr)
    (out / 'collector-exit.txt').write_text(str(collected.returncode) + '\n')
    print(collected.stdout.decode(errors='replace'))
    if collected.returncode == 0:
        report = json.loads(collected.stdout)
        p = pathlib.Path(report['transfer_dir'])
        assert p.resolve().is_relative_to(base.resolve()) and not p.is_symlink()
        shutil.copytree(p, out / 'official-collection', symlinks=True)
else:
    (out / 'collector-not-executed.json').write_text(json.dumps({
        'reason': 'Pinned source mismatch; raw receipts preserved',
        'observed_controller_sha256': code_hash}) + '\n')

files = sorted(p for p in out.rglob('*') if p.is_file() and not p.is_symlink())
with (out / 'SHA256SUMS').open('x') as ledger:
    for p in files:
        ledger.write(hashlib.sha256(p.read_bytes()).hexdigest() + '  ' + p.relative_to(out).as_posix() + '\n')
subprocess.run(['sha256sum', '--strict', '-c', 'SHA256SUMS'], cwd=out, check=True)
archive = out / 'gurobi14-2278573-final.tar.gz'
with tarfile.open(archive, 'x:gz') as tar:
    for p in files + [out / 'SHA256SUMS']:
        tar.add(p, arcname=p.relative_to(out).as_posix(), recursive=False)
checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
(out / (archive.name + '.sha256')).write_text(checksum + '  ' + archive.name + '\n')
print('ARCHIVE=' + str(archive))
print('SHA256=' + checksum)
print('FROZEN_PACKAGES=' + str(len(expected)) + '; CURRENT_PACKAGES=' + str(len(current)))
result = receipts / 'result.json'
if result.exists():
    try:
        r = json.loads(result.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError):
        print(json.dumps({'result_json_valid': False, 'bytes': result.stat().st_size,
            'collection_archive_preserved': True, 'no_recollection_required': True}))
    else:
        print(json.dumps({k: r.get(k) for k in ('stage','error','verdict','license',
            'model_built','optimization_attempts','optimization_returned','validation_status')}, indent=2))
else:
    print('RESULT_JSON_ABSENT; inspect preserved batch/slurm receipts')
print('ORIGINALS_PRESERVED; NO_INSTALL_OR_SOLVER_OR_JOB_SUBMISSION')
PY
)
