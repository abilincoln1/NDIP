#!/usr/bin/env python3
"""
NDIP Phase C - Checkpoint Scheduler
Runs daily. Marks overdue checkpoints, emits events.
Integrated into scheduler_v8.sh
"""
import sys
sys.path.insert(0, '/app')
from app.db.database import SessionLocal
from sqlalchemy import text
from datetime import datetime, timezone

def run_checkpoint_check():
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    
    print(f"[Phase C] Checkpoint check — {now.strftime('%Y-%m-%d %H:%M UTC')}")
    
    # Find overdue pending checkpoints
    overdue = db.execute(text("""
        SELECT oc.id, oc.recommendation_id, oc.checkpoint_number,
               oc.due_date, r.title, r.created_by
        FROM outcome_checkpoints oc
        JOIN recommendations r ON r.id = oc.recommendation_id
        WHERE oc.status = 'pending'
          AND oc.due_date < NOW()
          AND oc.reminder_sent = FALSE
    """)).fetchall()
    
    reminded = 0
    for cp in overdue:
        # Emit checkpoint due event
        db.execute(text("""
            INSERT INTO platform_events
                (event_type, source_domain, source_entity_type,
                 source_entity_id, actor_id, payload)
            VALUES
                ('OutcomeCheckpointDue', 'adaptive_learning',
                 'outcome_checkpoint', :checkpoint_id, :actor_id,
                 :payload::jsonb)
        """), {
            "checkpoint_id": str(cp.id),
            "actor_id": str(cp.created_by) if cp.created_by else None,
            "payload": f\'\\{"recommendation_id": "\' + str(cp.recommendation_id) + \'\\", "checkpoint_number": \' + str(cp.checkpoint_number) + \', "recommendation_title": "\' + str(cp.title)[:100] + \'\\"}\',
        })
        
        # Mark reminder sent
        db.execute(text("""
            UPDATE outcome_checkpoints
            SET reminder_sent = TRUE, reminder_sent_at = NOW()
            WHERE id = :id
        """), {"id": str(cp.id)})
        
        reminded += 1
        print(f"  [CHECKPOINT] Due: {cp.title[:60]} (checkpoint {cp.checkpoint_number})")
    
    db.commit()
    
    # Stats
    total_pending = db.execute(text(
        "SELECT COUNT(*) FROM outcome_checkpoints WHERE status = 'pending'"
    )).scalar()
    total_overdue = db.execute(text(
        "SELECT COUNT(*) FROM outcome_checkpoints WHERE status = 'pending' AND due_date < NOW()"
    )).scalar()
    
    print(f"  Pending checkpoints: {total_pending} total, {total_overdue} overdue, {reminded} notified")
    db.close()

if __name__ == "__main__":
    run_checkpoint_check()
