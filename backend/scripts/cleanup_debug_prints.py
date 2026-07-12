"""Remove the debug print statements added during diagnosis, restoring clean production code."""
path = '/app/app/services/decision_support.py'
c = open(path).read()

old1 = '''    print("ENTERED _enrich_and_track_recommendations, buckets:", list(result.keys()))
    try:
        from app.services.recommendation_tracker import record_recommendation
        print("Tracker import succeeded inside function")
    except Exception as e:
        print("TRACKER IMPORT FAILED:", type(e).__name__, str(e))
        return  # tracker not available — degrade gracefully, decision support still works'''

new1 = '''    try:
        from app.services.recommendation_tracker import record_recommendation
    except Exception:
        return  # tracker not available — degrade gracefully, decision support still works'''

count1 = c.count(old1)
if count1:
    c = c.replace(old1, new1)
    print(f"Removed entry-point debug prints ({count1} occurrence)")
else:
    print("Entry-point debug print pattern not found (already clean?)")

old2 = '''            except Exception as e:
                print('TRACKING ERROR:', type(e).__name__, str(e))
                continue'''
new2 = '''            except Exception:
                continue'''

count2 = c.count(old2)
if count2:
    c = c.replace(old2, new2)
    print(f"Removed per-action debug print ({count2} occurrence)")
else:
    print("Per-action debug print pattern not found (already clean?)")

open(path, 'w').write(c)
print("Cleanup complete")
