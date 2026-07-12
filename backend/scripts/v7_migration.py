"""
NDIP V7 — Database Migration
Creates the user_onboarding_state table required for the adoption layer.
Run once after deploying V7 backend code.

Usage:
    docker exec agora-backend-1 python scripts/v7_migration.py
"""
import sys
sys.path.insert(0, '/app')

from sqlalchemy import text
from app.db.database import engine, SessionLocal

def run_migration():
    print("NDIP V7 — Onboarding Database Migration")
    print("=" * 50)

    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'user_onboarding_state'
            )
        """))
        exists = result.scalar()

        if exists:
            print("✓ user_onboarding_state table already exists — skipping creation")
        else:
            print("  Creating user_onboarding_state table...")
            conn.execute(text("""
                CREATE TABLE user_onboarding_state (
                    id SERIAL PRIMARY KEY,
                    user_email VARCHAR(255) UNIQUE NOT NULL,
                    role VARCHAR(50) DEFAULT 'executive',
                    onboarding_complete BOOLEAN DEFAULT FALSE,
                    current_step INTEGER DEFAULT 0,
                    completed_tours JSONB DEFAULT '[]'::jsonb,
                    completed_modules JSONB DEFAULT '[]'::jsonb,
                    visited_pages JSONB DEFAULT '[]'::jsonb,
                    dismissed_tooltips JSONB DEFAULT '[]'::jsonb,
                    certification_level VARCHAR(50) DEFAULT 'none',
                    help_overlay_enabled BOOLEAN DEFAULT TRUE,
                    first_login_at TIMESTAMPTZ DEFAULT NOW(),
                    last_active_at TIMESTAMPTZ DEFAULT NOW(),
                    total_sessions INTEGER DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE INDEX idx_user_onboarding_email 
                ON user_onboarding_state(user_email)
            """))
            conn.commit()
            print("  ✓ user_onboarding_state table created")

        # Verify copilot route will work — check settings for anthropic key
        try:
            from app.core.config import get_settings
            s = get_settings()
            has_key = hasattr(s, 'anthropic_api_key') and bool(getattr(s, 'anthropic_api_key', None))
            if has_key:
                print("  ✓ ANTHROPIC_API_KEY found — AI Copilot will use live API")
            else:
                print("  ⚠ ANTHROPIC_API_KEY not set — AI Copilot will use graceful fallback mode")
                print("    To enable full Copilot: add ANTHROPIC_API_KEY=... to your .env file")
        except Exception as e:
            print(f"  ⚠ Could not check API key: {e}")

    print("=" * 50)
    print("Migration complete.")
    print("")
    print("NEXT STEPS:")
    print("1. Ensure copilot.py and onboarding.py are in /app/app/api/routes/")
    print("2. Add these lines to /app/app/main.py:")
    print("   from app.api.routes import copilot, onboarding")
    print("   app.include_router(copilot.router)")
    print("   app.include_router(onboarding.router)")
    print("3. Copy frontend components to /app/src/components/ui/")
    print("4. Add <AICopilot /> to the layout component")
    print("5. Restart the backend: docker restart agora-backend-1")

if __name__ == "__main__":
    run_migration()
