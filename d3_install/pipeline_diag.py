"""
NDIP Intelligence Pipeline Diagnostic
READ ONLY — NO MODIFICATIONS
Run: docker exec ndip-backend-1 python3 /tmp/pipeline_diag.py
"""
import os, sys
sys.path.insert(0, '/app')
os.environ['DATABASE_URL'] = 'postgresql://agora_user:agora_pass@db:5432/agora_db'
from sqlalchemy import create_engine, text
db = create_engine('postgresql://agora_user:agora_pass@db:5432/agora_db').connect()

print('=' * 70)
print('NDIP INTELLIGENCE PIPELINE DIAGNOSTIC — 19 September 2026')
print('READ ONLY')
print('=' * 70)

# 1. Total posts and recent acquisition
print('\n[1] POST COUNTS AND RECENT ACQUISITION')
total = db.execute(text('SELECT COUNT(*) FROM social_posts')).scalar()
total_np = db.execute(text('SELECT COUNT(*) FROM normalised_posts')).scalar()
print(f'  social_posts total:       {total:,}')
print(f'  normalised_posts total:   {total_np:,}')

# Recent posts (last 24 hours)
recent = db.execute(text("""
    SELECT COUNT(*) FROM social_posts
    WHERE created_at >= NOW() - INTERVAL '24 hours'
""")).scalar()
print(f'  social_posts (last 24h):  {recent:,}')

# Recent normalised
recent_np = db.execute(text("""
    SELECT COUNT(*) FROM normalised_posts
    WHERE created_at >= NOW() - INTERVAL '24 hours'
""")).scalar()
print(f'  normalised_posts (24h):   {recent_np:,}')

# 2. social_posts schema — understand processing flags
print('\n[2] SOCIAL_POSTS SCHEMA (processing-related columns)')
cols = db.execute(text("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name='social_posts'
    ORDER BY ordinal_position
""")).fetchall()
for c in cols:
    print(f'  {c[0]}: {c[1]}')

# 3. normalised_posts schema
print('\n[3] NORMALISED_POSTS SCHEMA')
cols_np = db.execute(text("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name='normalised_posts'
    ORDER BY ordinal_position
""")).fetchall()
for c in cols_np:
    print(f'  {c[0]}: {c[1]}')

# 4. Processing status breakdown
print('\n[4] SOCIAL_POSTS — STATUS/FLAG BREAKDOWN')
try:
    status_dist = db.execute(text("""
        SELECT
            COALESCE(is_processed::text, 'NULL') as is_processed,
            COUNT(*) as count
        FROM social_posts
        GROUP BY is_processed
        ORDER BY count DESC
    """)).fetchall()
    for r in status_dist:
        print(f'  is_processed={r[0]}: {r[1]:,}')
except Exception as e:
    print(f'  No is_processed column: {e}')

try:
    nlp_dist = db.execute(text("""
        SELECT
            COALESCE(nlp_processed::text, 'NULL') as nlp_processed,
            COUNT(*) as count
        FROM social_posts
        GROUP BY nlp_processed
        ORDER BY count DESC
    """)).fetchall()
    for r in nlp_dist:
        print(f'  nlp_processed={r[0]}: {r[1]:,}')
except Exception as e:
    print(f'  No nlp_processed column: {e}')

# 5. Source breakdown — which connectors contributed
print('\n[5] SOURCE BREAKDOWN (social_posts by source)')
sources = db.execute(text("""
    SELECT source, COUNT(*) as count
    FROM social_posts
    GROUP BY source
    ORDER BY count DESC
""")).fetchall()
for r in sources:
    print(f'  {r[0]}: {r[1]:,}')

# Recent 24h by source
print('\n  Recent 24h by source:')
recent_src = db.execute(text("""
    SELECT source, COUNT(*) as count
    FROM social_posts
    WHERE created_at >= NOW() - INTERVAL '24 hours'
    GROUP BY source
    ORDER BY count DESC
""")).fetchall()
for r in recent_src:
    print(f'  {r[0]}: {r[1]:,}')

# 6. Normalised posts — source relationship
print('\n[6] NORMALISED_POSTS — SOURCE AND NLP STATUS')
try:
    np_sources = db.execute(text("""
        SELECT source, COUNT(*) as count
        FROM normalised_posts
        GROUP BY source
        ORDER BY count DESC
        LIMIT 10
    """)).fetchall()
    for r in np_sources:
        print(f'  {r[0]}: {r[1]:,}')
except Exception as e:
    print(f'  Error: {e}')

try:
    nlp_status = db.execute(text("""
        SELECT
            COALESCE(nlp_processed::text, 'NULL') as nlp_processed,
            COUNT(*) as count
        FROM normalised_posts
        GROUP BY nlp_processed
        ORDER BY count DESC
    """)).fetchall()
    print('  NLP processed in normalised_posts:')
    for r in nlp_status:
        print(f'    nlp_processed={r[0]}: {r[1]:,}')
except Exception as e:
    print(f'  No nlp_processed in normalised_posts: {e}')

# 7. Narrative trends
print('\n[7] NARRATIVE TRENDS')
try:
    nt_count = db.execute(text('SELECT COUNT(*) FROM narrative_trends')).scalar()
    print(f'  Total narrative_trends rows: {nt_count}')
    recent_nt = db.execute(text("""
        SELECT COUNT(*) FROM narrative_trends
        WHERE created_at >= NOW() - INTERVAL '24 hours'
    """)).scalar()
    print(f'  Recent 24h narrative_trends: {recent_nt}')
    # Schema
    nt_cols = db.execute(text("""
        SELECT column_name, data_type FROM information_schema.columns
        WHERE table_name='narrative_trends' ORDER BY ordinal_position
    """)).fetchall()
    print('  Columns:')
    for c in nt_cols:
        print(f'    {c[0]}: {c[1]}')
    # Sample
    sample = db.execute(text("""
        SELECT * FROM narrative_trends ORDER BY created_at DESC LIMIT 3
    """)).fetchall()
    print('  Sample rows (latest 3):')
    for r in sample:
        print(f'    {dict(r._mapping)}')
except Exception as e:
    print(f'  Error: {e}')

# 8. Analytics snapshots
print('\n[8] ANALYTICS SNAPSHOTS')
try:
    snap_count = db.execute(text('SELECT COUNT(*) FROM analytics_snapshots')).scalar()
    print(f'  Total snapshots: {snap_count}')
    recent_snap = db.execute(text("""
        SELECT created_at, snapshot_type, record_count
        FROM analytics_snapshots
        ORDER BY created_at DESC LIMIT 3
    """)).fetchall()
    for r in recent_snap:
        print(f'  {r[0]} | type={r[1]} | records={r[2]}')
except Exception as e:
    print(f'  Error: {e}')

# 9. Ingestion jobs
print('\n[9] INGESTION JOBS (last 5)')
try:
    jobs = db.execute(text("""
        SELECT started_at, status, source, total_fetched, total_new, total_duplicate
        FROM ingestion_jobs
        ORDER BY started_at DESC LIMIT 5
    """)).fetchall()
    for r in jobs:
        print(f'  {r[0]} | {r[1]} | src={r[2]} | fetched={r[3]} new={r[4]} dup={r[5]}')
except Exception as e:
    print(f'  Error: {e}')

# 10. Inspect normalisation service for the counter
print('\n[10] NORMALISATION SERVICE — KEY CODE INSPECTION')
try:
    with open('/app/app/services/normalisation.py') as f:
        norm_src = f.read()
    # Find normalised counter
    lines = norm_src.split('\n')
    for i, line in enumerate(lines):
        if 'normalised' in line.lower() and ('count' in line.lower() or '+=' in line or 'return' in line.lower()):
            print(f'  Line {i+1}: {line.strip()}')
    print(f'  File size: {len(norm_src)} bytes')
    # Find the SAWarning-related query
    for i, line in enumerate(lines):
        if 'Subquery' in line or 'in_()' in line or '.in_(' in line or 'IN' in line:
            start = max(0, i-2)
            end = min(len(lines), i+3)
            print(f'  Potential SAWarning area around line {i+1}:')
            for j in range(start, end):
                print(f'    {j+1}: {lines[j]}')
except Exception as e:
    print(f'  Error reading normalisation.py: {e}')

# 11. Scheduler/ingestion job log
print('\n[11] SCHEDULER JOB LOG (last 5)')
try:
    jobs = db.execute(text("""
        SELECT job_name, started_at, completed_at, status, result_summary
        FROM scheduler_job_log
        ORDER BY started_at DESC LIMIT 5
    """)).fetchall()
    for r in jobs:
        print(f'  {r[1]} | {r[0]} | {r[3]} | {str(r[4])[:100]}')
except Exception as e:
    print(f'  Error: {e}')

# 12. Health endpoint inspection
print('\n[12] HEALTH ENDPOINT')
try:
    with open('/app/app/api/routes/health_v2.py') as f:
        health_src = f.read()
    lines = health_src.split('\n')
    for i, line in enumerate(lines):
        if 'health' in line.lower() or 'readiness' in line.lower() or 'startup' in line.lower():
            print(f'  Line {i+1}: {line.strip()[:100]}')
except Exception as e:
    print(f'  Error: {e}')

# 13. Duplicate detection
print('\n[13] DUPLICATE ANALYSIS')
try:
    dups = db.execute(text("""
        SELECT COUNT(*) FROM social_posts sp
        WHERE EXISTS (
            SELECT 1 FROM social_posts sp2
            WHERE sp2.id != sp.id
            AND sp2.url = sp.url
            AND sp.url IS NOT NULL
        )
    """)).scalar()
    print(f'  Posts with duplicate URLs: {dups}')
except Exception as e:
    print(f'  Error: {e}')

db.close()
print('\n' + '=' * 70)
print('DIAGNOSTIC COMPLETE — NO CHANGES MADE')
print('=' * 70)
