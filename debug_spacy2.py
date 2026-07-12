import sys, traceback
sys.path.insert(0, '/app')

# Import app models first (same as ingest does)
from app.models import models
print("models: OK")

# Now try to load spacy with full traceback
try:
    import spacy
    nlp = spacy.load('en_core_web_sm')
    print("spaCy after models: OK", nlp)
except Exception as e:
    print("spaCy after models FAILED:")
    traceback.print_exc()

# Now try nlp_enhanced with verbose exception
if 'app.analytics.nlp_enhanced' in sys.modules:
    del sys.modules['app.analytics.nlp_enhanced']

# Patch nlp_enhanced to show full traceback
import app.analytics.nlp_enhanced as n

# Manually call what _load_spacy does
print("\nManual spacy load attempt:")
try:
    import spacy as sp2
    try:
        nlp2 = sp2.load("en_core_web_md")
        print("en_core_web_md loaded")
    except OSError:
        try:
            nlp2 = sp2.load("en_core_web_sm")
            print("en_core_web_sm loaded:", nlp2)
        except OSError as e2:
            print("OSError:", e2)
except Exception as e:
    print("Exception type:", type(e).__name__)
    traceback.print_exc()
