"""
NDIP V6.2 Phase A -- Wire materialise_intelligence into daily_ingest.py,
inserting the call between run_daily_ingest() and clear_cache() so that:
  Ingest → Materialise → Clear Redis → Prewarm (reads materialised data)

Anchor fetched fresh via live sed extraction this session.

Run: docker exec agora-backend-1 python scripts/v62_wire_materialisation.py
"""
PATH = "/app/scripts/daily_ingest.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''if __name__ == "__main__":
    asyncio.run(run_daily_ingest())
    clear_cache()'''

new = '''if __name__ == "__main__":
    asyncio.run(run_daily_ingest())
    # V6.2 Phase A -- materialise intelligence before clearing Redis, so
    # the prewarm step that follows reads from persisted data rather than
    # recomputing everything from scratch on every request.
    _mat_db = SessionLocal()
    try:
        from app.services.materialise_intelligence import run_full_materialisation
        run_full_materialisation(_mat_db)
    except Exception as e:
        print(f"Materialisation error (non-fatal): {e}")
    finally:
        _mat_db.close()
    clear_cache()'''

count = content.count(old)
print(f"Anchor found {count} time(s).")

if count != 1:
    print(f"Expected exactly 1, found {count} -- aborting.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: run_full_materialisation() now called after ingest, before cache clear.")
