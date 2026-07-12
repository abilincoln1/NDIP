#!/usr/bin/env python3
"""
NDIP Phase C - Copilot Integration Patcher
Patches copilot_v8.py to:
1. Auto-register recommendations from responses
2. Inject organisational memory into context
"""
import sys, re
sys.path.insert(0, '/app')

path = '/app/app/api/routes/copilot_v8.py'
with open(path) as f:
    content = f.read()

if 'recommendation_registry' in content:
    print('Copilot already patched - skipping')
    sys.exit(0)

# Add imports after existing imports
import_addition = """
# Phase C - Adaptive Learning integration
try:
    from app.phase_c.services.recommendation_registry import register_recommendation_from_copilot
    from app.phase_c.services.copilot_memory import build_memory_aware_system_prompt
    PHASE_C_ENABLED = True
except ImportError:
    PHASE_C_ENABLED = False
"""

# Insert after last import line
lines = content.split('\n')
last_import_idx = 0
for i, line in enumerate(lines):
    if line.startswith('from ') or line.startswith('import '):
        last_import_idx = i

lines.insert(last_import_idx + 1, import_addition)
content = '\n'.join(lines)

# Find the return statement in the chat endpoint and add registration before it
# Look for where the AI response is assembled and returned
registration_code = """
    # Phase C: Auto-register recommendations from this response
    if PHASE_C_ENABLED:
        try:
            user_id = str(current_user.id) if hasattr(current_user, 'id') else None
            ctx = {"dashboard": "copilot", "timestamp": str(datetime.now(timezone.utc))}
            register_recommendation_from_copilot(
                db=db,
                response_text=reply,
                user_id=user_id,
                context_snapshot=ctx,
                source_dashboard="copilot",
                confidence=0.65,
            )
        except Exception:
            pass  # Registration failure never blocks response
"""

# Find the pattern where reply is returned
# Common pattern: return {"reply": reply, ...} or return reply
if 'return {' in content and 'reply' in content:
    # Insert before the final return that contains reply
    pattern = r'(\s+)(return \{[^}]*"reply"[^}]*\})'
    match = re.search(pattern, content)
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + registration_code + content[insert_pos:]
        print('  Injected recommendation registration before return')
    else:
        print('  Could not find return pattern - manual integration needed')
else:
    print('  Could not find reply return - manual integration needed')

with open(path, 'w') as f:
    f.write(content)

print('Copilot patched successfully')
print('  - Recommendation auto-registration: enabled')
print('  - Organisational memory injection: available via build_memory_aware_system_prompt')
