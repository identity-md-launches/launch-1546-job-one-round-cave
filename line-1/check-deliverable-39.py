"""Check this round's local output contract without network or environment reads."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.run(['git', *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def jpeg_dimensions(raw):
    assert raw.startswith(b'\xff\xd8') and raw.endswith(b'\xff\xd9')
    position = 2
    while position < len(raw):
        assert raw[position] == 255
        marker = raw[position + 1]
        size = int.from_bytes(raw[position + 2:position + 4], 'big')
        assert size >= 2
        if marker == 192:
            assert raw[position + 4] == 8
            height = int.from_bytes(raw[position + 5:position + 7], 'big')
            width = int.from_bytes(raw[position + 7:position + 9], 'big')
            return [width, height]
        position += 2 + size
    raise AssertionError('baseline JPEG SOF0 missing')


def main():
    spec = importlib.util.spec_from_file_location('png39', ROOT / 'line-1/finalize-35.py')
    png = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(png)
    named = ROOT / 'artifacts/line-1/wall-v20.png'
    wall = named.read_bytes()
    assert wall == (ROOT / 'artifacts/line-1/wall.png').read_bytes()
    width, height, channels, _ = png.decode_png(wall)
    assert (width, height, channels) == (1254, 1254, 3)
    digest = hashlib.sha256(wall).hexdigest()
    record = json.loads((ROOT / 'dist/line-1/39.json').read_text())
    assert set(record) == {'name', 'image', 'attributes'}
    assert record['name'] == 'The Rooted Seed'
    assert record['image'] == 'https://api.imd.fun/artifacts/' + digest
    attributes = record['attributes']
    assert len(attributes) == 6
    assert all(set(item) == {'trait_type', 'value'} for item in attributes)
    values = {item['trait_type']: item['value'] for item in attributes}
    assert set(values) == {'Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing'}
    assert values['Cave'] == 'Base' and values['Wall'] == 'Line 1'
    assert type(values['Number']) is int and values['Number'] == 39
    assert values['Left behind'] == 'account-proof-check'
    assert values['Meaning'] and values['One thing']
    records = sorted((ROOT / 'dist/line-1').glob('[0-9][0-9].json'))
    assert len(records) == 39 and records[-1].name == '39.json'
    for old in records[:-1]:
        relative = old.relative_to(ROOT).as_posix()
        assert old.read_bytes() == git('show', 'HEAD:' + relative), relative
    goal = ROOT / 'line-1/GOAL.md'
    assert goal.read_bytes() == git('show', 'HEAD:line-1/GOAL.md')
    jpeg = (ROOT / 'dist/line-1/39.jpg').read_bytes()
    assert jpeg_dimensions(jpeg) == [512, 512] and len(jpeg) < 100000
    review = json.loads((ROOT / 'line-1/wall-review-39.json').read_text())
    assert review['wall_sha256'] == digest
    assert review['changed_pixels_outside_rectangle'] == 0
    assert review['changed_pixels'] > 0
    assert review['inherited_hand_digit_counts'] == [5, 5]
    assert review['visual_review'] != 'Pending final PNG and JPEG inspection.'
    assert not git('ls-files', '--', 'artifacts/line-1/wall-v20.png',
                   'artifacts/line-1/wall.png')
    status = git('status', '--porcelain=v1', '-z', '--untracked-files=all')
    changed = []
    for entry in status.decode().split('\0'):
        if not entry:
            continue
        flag, path = entry[:2], entry[3:]
        assert 'R' not in flag and 'C' not in flag
        assert path.startswith(('line-1/', 'dist/line-1/', 'artifacts/line-1/', 'test/scratch/')), path
        candidate = ROOT / path
        if candidate.is_file() and not path.startswith(('artifacts/', 'test/scratch/')):
            assert candidate.stat().st_size < 100000, path
        changed.append(path)
    result = {'schema': 'line1-local-check/1', 'record_number': 39,
              'wall_png_dimensions': [width, height],
              'wall_png_format': '8-bit RGB PNG', 'wall_sha256': digest,
              'jpeg_dimensions': [512, 512], 'jpeg_format': 'baseline JPEG',
              'jpeg_bytes': len(jpeg), 'older_records_unchanged': True,
              'goal_unchanged': True, 'changed_paths_in_scope': True,
              'new_nonartifact_files_under_100kb': True,
              'named_png_outputs_untracked': True,
              'visual_review': 'line-1/wall-review-39.json',
              'unmet_visual_requirements': review['unmet_visual_requirements'],
              'tool_demo': 'python3 -B line-1/tools/account-proof-check/account_proof_check.py demo',
              'checks_are_local_not_independent_certification': True}
    (ROOT / 'line-1/submission-check-39.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
