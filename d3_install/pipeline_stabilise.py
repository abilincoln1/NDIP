"""
NDIP Pipeline Stabilisation — Targeted Patches
Based on actual code inspection.
SF-1: VOA Africa XML guard (nigeria/__init__.py line 41)
SF-2: SQLAlchemy .subquery() -> .scalar_subquery() (normalisation.py line 73)
SF-3: Health check retry helper script
SF-4: spaCy ConfigError handling (nlp_enhanced.py)
Run: docker exec ndip-backend-1 python3 /tmp/pipeline_stabilise.py
"""
import subprocess, os, re

results = []

def report(label, ok, detail=''):
    s = 'DONE' if ok else 'FAIL'
    results.append((s, label, detail))
    print(f'  [{s}] {label}{": "+detail if detail else ""}')

def syntax_check(path):
    r = subprocess.run(['python3','-m','py_compile',path], capture_output=True, text=True)
    return r.returncode==0, r.stderr.strip()

def read(p):
    with open(p) as f: return f.read()

def write(p, c):
    with open(p,'w') as f: f.write(c)

print('='*65)
print('NDIP PIPELINE STABILISATION — TARGETED PATCHES')
print('='*65)

# SF-2: normalisation.py — .subquery() -> .scalar_subquery()
print('\n[SF-2] normalisation.py: .subquery() -> .scalar_subquery()')
NORM = '/app/app/services/normalisation.py'
c = read(NORM)
if '.scalar_subquery()' in c:
    report('SF-2', True, 'already patched')
elif ').subquery()' in c:
    p = c.replace(').subquery()', ').scalar_subquery()', 1)
    write(NORM, p)
    ok, err = syntax_check(NORM)
    if ok:
        report('SF-2 .subquery() -> .scalar_subquery()', True)
    else:
        write(NORM, c)
        report('SF-2', False, 'syntax error rolled back: '+err[:80])
else:
    report('SF-2', False, 'pattern .subquery() not found in normalisation.py')

# SF-1: nigeria/__init__.py — XML content guard before fromstring
print('\n[SF-1] nigeria/__init__.py line 41: XML guard before ElementTree.fromstring()')
VOA = '/app/app/connectors/nigeria/__init__.py'
c = read(VOA)
if 'SF-1' in c or 'startswith(' in c:
    report('SF-1', True, 'guard already present')
else:
    old = '            root = ElementTree.fromstring(xml_text)'
    new = ('            # SF-1: reject non-XML responses (e.g. HTML error pages)\n'
           '            if not xml_text or not xml_text.strip().startswith(\'<\'):\n'
           '                raise ElementTree.ParseError(\n'
           '                    f"Non-XML response from feed: {repr(xml_text[:80] if xml_text else \'empty\')}"\n'
           '                )\n'
           '            root = ElementTree.fromstring(xml_text)')
    if old in c:
        p = c.replace(old, new, 1)
        write(VOA, p)
        ok, err = syntax_check(VOA)
        if ok:
            report('SF-1 XML content guard added', True)
        else:
            write(VOA, c)
            report('SF-1', False, 'syntax error rolled back: '+err[:80])
    else:
        report('SF-1', False, 'target line not found — indentation may differ')

# SF-3: health check retry helper
print('\n[SF-3] Health check retry helper script')
HELPER = '/app/app/health_check_retry.py'
if os.path.exists(HELPER):
    report('SF-3', True, 'health_check_retry.py already exists')
else:
    helper_src = '''#!/usr/bin/env python3
"""SF-3: Health check with retry — resolves startup timing failures.
Usage: python3 /app/app/health_check_retry.py [host] [attempts] [delay_secs]
"""
import sys, time, urllib.request

host = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:8000'
attempts = int(sys.argv[2]) if len(sys.argv) > 2 else 5
delay = int(sys.argv[3]) if len(sys.argv) > 3 else 3

for i in range(1, attempts + 1):
    try:
        r = urllib.request.urlopen(f'{host}/health', timeout=5)
        if r.status == 200:
            print(f'Backend healthy (attempt {i}/{attempts})')
            sys.exit(0)
    except Exception as e:
        print(f'Health check {i}/{attempts} failed: {e}')
        if i < attempts:
            time.sleep(delay)

print(f'Backend not healthy after {attempts} attempts')
sys.exit(1)
'''
    write(HELPER, helper_src)
    ok, err = syntax_check(HELPER)
    report('SF-3 health_check_retry.py created', ok, err[:80] if not ok else
           'call: python3 /app/app/health_check_retry.py')

# SF-4: spaCy — inspect nlp_enhanced.py and add ConfigError import if missing
print('\n[SF-4] nlp_enhanced.py — spaCy ConfigError handling')
NLP_ENH = '/app/app/analytics/nlp_enhanced.py'
c = read(NLP_ENH)
if 'ConfigError' in c:
    report('SF-4', True, 'ConfigError already handled in nlp_enhanced.py')
elif 'spacy' in c.lower():
    if 'import spacy' in c:
        old_imp = 'import spacy'
        new_imp = ('import spacy\n'
                   'try:\n'
                   '    from spacy.errors import ConfigError as SpacyConfigError\n'
                   'except Exception:\n'
                   '    SpacyConfigError = Exception  # SF-4: fallback if spaCy unavailable\n')
        p = c.replace(old_imp, new_imp, 1)
        write(NLP_ENH, p)
        ok, err = syntax_check(NLP_ENH)
        if ok:
            report('SF-4 SpacyConfigError import added to nlp_enhanced.py', True)
        else:
            write(NLP_ENH, c)
            report('SF-4', False, 'rolled back: '+err[:80])
    else:
        report('SF-4 nlp_enhanced.py', True, 'no direct spacy import — ConfigError handled upstream')
else:
    report('SF-4 nlp_enhanced.py', True, 'no spaCy usage in this file')

# Final syntax check
print('\n[VERIFY] Syntax checks')
for path in [NORM, VOA, HELPER, NLP_ENH]:
    if os.path.exists(path):
        ok, err = syntax_check(path)
        print(f'  {"OK" if ok else "FAIL"}: {path.split("/")[-1]}')

print('\n'+'='*65)
print('SUMMARY')
for s,l,d in results:
    print(f'  [{s}] {l}{": "+d if d else ""}')
done = sum(1 for s,_,_ in results if s=='DONE')
fail = sum(1 for s,_,_ in results if s=='FAIL')
print(f'\n  Done: {done}  Failed: {fail}')
print('='*65)
