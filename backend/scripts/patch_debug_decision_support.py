"""One-time debug patch: reveal the real exception in the recommendation tracking loop."""
path = '/app/app/services/decision_support.py'
c = open(path).read()

old = '''            except Exception:
                continue'''
new = '''            except Exception as e:
                print('TRACKING ERROR:', type(e).__name__, str(e))
                continue'''

if old in c:
    c = c.replace(old, new, 1)
    open(path, 'w').write(c)
    print('Patched successfully — exception will now print')
else:
    print('Pattern not found — no changes made')
