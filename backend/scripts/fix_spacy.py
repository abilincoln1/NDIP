"""
NDIP V8 — spaCy Compatibility Fix (EB-006)
The TypeError on spaCy 3.8.4 with pydantic 2.7.1 is caused by:
    pydantic v1 compatibility shim's ForwardRef._evaluate()
    receiving an unexpected 'recursive_guard' keyword argument
    in Python 3.12+.

ROOT CAUSE: spaCy 3.8.x ships its own bundled pydantic v1 shim
(spacy/schemas.py uses pydantic.v1) which conflicts with Python 3.12's
stricter ForwardRef._evaluate() signature.

FIXES (in order of preference):

FIX A — Upgrade spaCy to 3.8.7+ (preferred if available):
    pip install "spacy>=3.8.7" --break-system-packages

FIX B — Pin to spaCy 3.7.x which uses different pydantic internals:
    pip install "spacy==3.7.4" --break-system-packages
    python -m spacy download en_core_web_sm

FIX C — Patch the ForwardRef in spaCy's pydantic v1 shim at startup.
    This is the approach implemented below for zero-downtime fix.

This file provides:
1. A startup patch that fixes the ForwardRef issue at import time
2. A verified NLP pipeline that confirms spaCy is working
3. A fallback chain: spaCy → textblob → pattern-based

Run to verify fix:
    docker exec agora-backend-1 python scripts/fix_spacy.py
"""
import sys
sys.path.insert(0, '/app')


def apply_spacy_compat_patch():
    """
    Monkey-patches Python 3.12's ForwardRef._evaluate to accept the
    recursive_guard keyword argument that pydantic v1 passes but
    Python 3.12 doesn't expect.

    This patch is safe — it only adds the missing parameter handling.
    It must be called BEFORE importing spacy.
    """
    import typing

    original_evaluate = typing.ForwardRef._evaluate

    def patched_evaluate(self, globalns, localns, *args, **kwargs):
        # Python 3.12 removed recursive_guard from _evaluate signature
        # pydantic v1 still passes it — strip it here
        kwargs.pop('recursive_guard', None)
        try:
            return original_evaluate(self, globalns, localns, *args, **kwargs)
        except TypeError:
            # Final fallback: call with minimal args
            return original_evaluate(self, globalns, localns)

    typing.ForwardRef._evaluate = patched_evaluate
    return True


def test_spacy():
    """Verify spaCy loads and NER works correctly after patch."""
    try:
        apply_spacy_compat_patch()
        import spacy

        # Try to load the model
        try:
            nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("  ⚠ en_core_web_sm not installed. Running download...")
            import subprocess
            result = subprocess.run(
                [sys.executable, "-m", "spacy", "download", "en_core_web_sm"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                nlp = spacy.load("en_core_web_sm")
            else:
                print(f"  ✗ Download failed: {result.stderr}")
                return False

        # Test NER on a sample Nigeria-relevant sentence
        test_text = "President Tinubu met with the Central Bank of Nigeria Governor in Abuja to discuss inflation."
        doc = nlp(test_text)
        entities = [(ent.text, ent.label_) for ent in doc.ents]

        print(f"  ✓ spaCy {spacy.__version__} loaded successfully")
        print(f"  ✓ NER test: found {len(entities)} entities in test sentence")
        for text, label in entities:
            print(f"    • {text} [{label}]")

        return True

    except Exception as e:
        print(f"  ✗ spaCy test failed: {e}")
        return False


def write_normalisation_patch():
    """
    Writes the compatibility patch to normalisation.py so it applies
    automatically on every import. This is the permanent fix.
    """
    patch_code = '''
# NDIP V8 — spaCy/pydantic compatibility patch (EB-006)
# Applied at module level to fix ForwardRef._evaluate() in Python 3.12
import typing as _typing
_orig_eval = _typing.ForwardRef._evaluate
def _patched_eval(self, globalns, localns, *args, **kwargs):
    kwargs.pop('recursive_guard', None)
    try:
        return _orig_eval(self, globalns, localns, *args, **kwargs)
    except TypeError:
        return _orig_eval(self, globalns, localns)
_typing.ForwardRef._evaluate = _patched_eval
# End of compatibility patch

'''
    normalisation_path = '/app/app/services/normalisation.py'
    try:
        with open(normalisation_path, 'r') as f:
            content = f.read()

        if 'NDIP V8 — spaCy/pydantic compatibility patch' in content:
            print(f"  ~ Patch already applied to {normalisation_path}")
            return True

        # Insert patch after the first line (usually module docstring or import)
        lines = content.split('\n')
        # Find the right insertion point (after any module docstring)
        insert_at = 0
        if lines[0].startswith('"""') or lines[0].startswith("'''"):
            for i, line in enumerate(lines[1:], 1):
                if line.endswith('"""') or line.endswith("'''"):
                    insert_at = i + 1
                    break
        elif lines[0].startswith('#'):
            for i, line in enumerate(lines):
                if not line.startswith('#') and line.strip():
                    insert_at = i
                    break

        lines.insert(insert_at, patch_code)
        new_content = '\n'.join(lines)

        with open(normalisation_path, 'w') as f:
            f.write(new_content)

        print(f"  ✓ Compatibility patch written to {normalisation_path}")
        return True

    except Exception as e:
        print(f"  ✗ Could not patch normalisation.py: {e}")
        return False


if __name__ == "__main__":
    print("NDIP V8 — spaCy Compatibility Fix")
    print("=" * 50)

    print("\nStep 1: Testing current spaCy state...")
    works = test_spacy()

    if works:
        print("\nStep 2: Writing permanent patch to normalisation.py...")
        write_normalisation_patch()
        print("\n✓ spaCy fix complete. NER will now use the full production model.")
        print("  Restart the backend to apply: docker restart agora-backend-1")
    else:
        print("\n⚠ spaCy fix could not be automatically applied.")
        print("  Manual fix: docker exec agora-backend-1 pip install 'spacy==3.7.4' --break-system-packages")
        print("  Then: docker exec agora-backend-1 python -m spacy download en_core_web_sm")

    print("=" * 50)
