import sys, traceback
sys.path.insert(0, '/app')

print("Step 1: direct spacy import...")
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print("spaCy direct: OK", nlp)
except Exception as e:
    print("spaCy direct FAILED:")
    traceback.print_exc()

print("\nStep 2: import app models...")
try:
    from app.models import models
    print("models: OK")
except Exception as e:
    print("models FAILED:")
    traceback.print_exc()

print("\nStep 3: import nlp_enhanced fresh...")
try:
    if 'app.analytics.nlp_enhanced' in sys.modules:
        del sys.modules['app.analytics.nlp_enhanced']
    from app.analytics import nlp_enhanced
    nlp_enhanced._nlp = None
    nlp_enhanced._spacy_available = False
    result = nlp_enhanced._load_spacy()
    print("nlp_enhanced result:", result)
except Exception as e:
    print("nlp_enhanced FAILED:")
    traceback.print_exc()
