#!/usr/bin/env python3
"""Offline output, scope, source provenance and gallery checks for Gathering 19."""
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def jpeg_size(data):
    require(data[:2] == b'\xff\xd8' and data[-2:] == b'\xff\xd9', 'JPEG signature')
    pos = 2
    while pos < len(data):
        require(data[pos] == 255, 'JPEG marker')
        marker = data[pos + 1]; pos += 2
        length = int.from_bytes(data[pos:pos+2], 'big')
        if marker == 0xc0:
            return struct.unpack('>HH', data[pos+3:pos+7])[::-1]
        if marker == 0xda:
            break
        pos += length
    raise ValueError('baseline JPEG dimensions missing')


class Gallery(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sections = {}; self.wall = None; self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'section':
            self.wall = attrs['id']; self.sections[self.wall] = []
        if tag == 'article':
            self.sections[self.wall].append(int(attrs['data-number']))
        if tag == 'script': self.scripts += 1


def main():
    baseline = json.loads((ROOT / 'gathering/round-19-line-hashes.json').read_text())
    actual = {str(p.relative_to(ROOT)): sha(p) for n in range(1, 5)
              for p in (ROOT / f'line-{n}').rglob('*') if p.is_file()}
    require(actual == baseline, 'original line file sets or bytes changed')
    changed = subprocess.run(['git', 'diff', '--name-only'], cwd=ROOT,
                             capture_output=True, text=True, check=True).stdout.splitlines()
    added = subprocess.run(['git', 'ls-files', '--others', '--exclude-standard'], cwd=ROOT,
                           capture_output=True, text=True, check=True).stdout.splitlines()
    require(all(p.startswith(('gathering/', 'shared/', 'dist/', 'artifacts/gathering/',
                              'test/scratch/')) for p in changed + added), 'out-of-scope path')
    for raw in changed + added:
        p = ROOT / raw
        if p.is_file() and not raw.startswith(('artifacts/', 'test/scratch/')):
            require(p.stat().st_size <= 100000, 'file exceeds 100 KB: ' + raw)
    wall = ROOT / 'artifacts/gathering/wall-v20.png'
    raw = wall.read_bytes()
    require(raw[:8] == b'\x89PNG\r\n\x1a\n', 'PNG signature')
    require(struct.unpack('>IIBB', raw[16:26]) == (1254, 1254, 8, 2), 'PNG dimensions/format')
    require(raw == (wall.parent / 'wall.png').read_bytes(), 'continuation differs')
    from make_thumbnail import png_rgb
    width, height, rows = png_rgb(raw)
    require((width,height,len(rows)) == (1254,1254,1254), 'PNG decoding')
    jpeg = ROOT / 'dist/gathering/19.jpg'
    require(jpeg_size(jpeg.read_bytes()) == (512, 512), 'JPEG size')
    review = json.loads((ROOT / 'gathering/checks/round-19/image-preservation.json').read_text())
    require(review['wall_sha256'] == sha(wall), 'image review digest differs')
    require(review['changed_pixels_outside_rectangle'] == 0, 'outside pigment changes')
    require(review['inherited_hand_digit_counts'] == [5, 5], 'hand digit review')
    require(review['unmet_visual_requirements'] == [], 'unmet visual requirements')
    record = json.loads((ROOT / 'dist/gathering/19.json').read_text())
    require(set(record) == {'name', 'image', 'attributes'}, 'record shape')
    expected = ['Cave', 'Wall', 'Number', 'Left behind', 'Meaning', 'One thing']
    require([a['trait_type'] for a in record['attributes']] == expected, 'record traits')
    require(all(set(a) == {'trait_type', 'value'} for a in record['attributes']), 'trait shape')
    traits = {a['trait_type']: a['value'] for a in record['attributes']}
    require(traits['Cave'] == 'Base' and traits['Wall'] == 'Gathering' and
            type(traits['Number']) is int and traits['Number'] == 19 and
            traits['One thing'] == 'Gathering', 'record identity')
    require(record['image'] == 'https://api.imd.fun/artifacts/' + sha(wall), 'record digest')
    goals = [{'line': n, 'goal': (ROOT / f'line-{n}/GOAL.md').read_text().strip()}
             for n in range(1, 5)]
    require(json.loads((ROOT / 'dist/goals.json').read_text()) == goals, 'goal index differs')
    gallery = Gallery(); gallery.feed((ROOT / 'dist/index.html').read_text())
    count = 0
    for folder in ['line-1', 'line-2', 'line-3', 'line-4', 'gathering']:
        painted = []; pending = []
        for p in sorted((ROOT / 'dist' / folder).glob('[0-9][0-9].json'), reverse=True):
            obj = json.loads(p.read_text()); count += 1
            waiting = obj['name'] == 'Not painted yet'
            (pending if waiting else painted).append(int(p.stem))
            if waiting:
                require(not p.with_suffix('.jpg').exists(), 'placeholder JPEG exists')
        require(gallery.sections[folder] == painted + pending, 'gallery order/coverage')
    require(gallery.scripts == 0, 'unexpected gallery script')
    require((ROOT / 'dist/index.html').stat().st_size < 100000, 'gallery size')
    base = ROOT / 'shared/proof-handoff'
    provenance = json.loads((base / 'PROVENANCE.json').read_text())
    for entry in provenance['dependencies'] + [provenance['workspace_io']]:
        require(sha(ROOT / entry['source']) == entry['source_sha256'], 'source provenance')
        require(sha(base / entry['copy']) == entry['copy_sha256'], 'copy provenance')
    suites = json.loads((ROOT / 'gathering/checks/round-19/tool-checks.json').read_text())
    require(all(r['exit'] == 0 for r in suites), 'line check failure')
    require(sum(r['kind'] == 'suite' for r in suites) == 58, 'missing suite')
    require(sum(r['tests_run'] for r in suites) == 779, 'test count differs')
    require('Ran 13 tests' in (ROOT / 'gathering/checks/round-19/shared-tests.txt').read_text()
            and (ROOT / 'gathering/checks/round-19/shared-tests.txt').read_text().rstrip().endswith('OK'),
            'integration checks did not pass')
    native = json.loads((ROOT / 'gathering/checks/round-19/native-proof-handoff-review.json').read_text())
    require(native['selected_checks_passed'] is True, 'native handoff review failed')
    require(not any(p.startswith(('line-1/', 'line-2/', 'line-3/', 'line-4/',
                                  'dist/line-1/', 'dist/line-2/', 'dist/line-3/', 'dist/line-4/'))
                    for p in changed + added), 'line source or record modified')
    require(not any(p.startswith('artifacts/') for p in subprocess.run(
        ['git', 'ls-files', 'artifacts/gathering'], cwd=ROOT, capture_output=True,
        text=True, check=True).stdout.splitlines()), 'named output must remain untracked')
    require((ROOT / 'gathering/COINS.md').read_text().splitlines()[0] == 'none', 'coin decision')
    for name in ('coin-order.json', 'deploy-order.json'):
        require(not (ROOT / 'gathering' / name).exists(), 'unexpected order')
    result = {'status': 'passed', 'line_files_unchanged': len(actual), 'records': count,
              'line_suites': sum(r['kind'] == 'suite' for r in suites),
              'line_tests_attempted': sum(r['tests_run'] for r in suites),
              'native_test_limitations': [],
              'offline_commands': sum(r['kind'] == 'demo' for r in suites),
              'png_dimensions': [1254, 1254], 'png_format': '8-bit RGB PNG',
              'jpeg_dimensions': [512, 512], 'jpeg_format': 'baseline JPEG',
              'wall_sha256': sha(wall), 'unmet_visual_requirements': [], 'shared_integration_tests': 13,
              'review_limit': 'Structural checks plus recorded local visual review; not artistic certification.'}
    (ROOT / 'gathering/checks/round-19/deliverable.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
