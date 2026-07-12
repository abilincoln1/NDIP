"""
NDIP V6.2 -- Fix: stakeholder_type field was never actually added to
StakeholderRegistry's class body.

Root cause: the original Patch 2 (in v62_patch_models.py /
v62_patch_models_fixed.py) only inserted the new StakeholderType enum
class ABOVE StakeholderRegistry -- it never touched the inside of the
StakeholderRegistry class body to add the actual field. This went
undetected because the verification command checked
len(list(models.StakeholderType)) (confirming the enum itself works)
but never checked StakeholderRegistry.stakeholder_type as a real mapped
column.

This script inserts the missing field directly after the `category`
field definition, using the exact, confirmed-real text from the live
file as the anchor.

Run: docker exec agora-backend-1 python scripts/v62_fix_missing_field.py
"""
PATH = "/app/app/models/models.py"

with open(PATH, "r") as f:
    content = f.read()

old = '''    category: Mapped[str] = mapped_column(
        SAEnum(StakeholderCategory, native_enum=False), index=True, nullable=False
    )
    sector: Mapped[Optional[str]] = mapped_column(String(100))      # e.g. "Energy", "Climate", "Diaspora"
    role_description: Mapped[Optional[str]] = mapped_column(Text)
    # Aliases/keywords used to match this stakeholder in discourse text —'''

new = '''    category: Mapped[str] = mapped_column(
        SAEnum(StakeholderCategory, native_enum=False), index=True, nullable=False
    )
    # V6.2 Phase A/B -- granular stakeholder typing, additive to category
    # above (kept for backward compatibility). Nullable: not every
    # stakeholder needs the more specific type, and existing rows predate
    # this field.
    stakeholder_type: Mapped[Optional[str]] = mapped_column(
        SAEnum(StakeholderType, native_enum=False), nullable=True, index=True
    )
    sector: Mapped[Optional[str]] = mapped_column(String(100))      # e.g. "Energy", "Climate", "Diaspora"
    role_description: Mapped[Optional[str]] = mapped_column(Text)
    # Aliases/keywords used to match this stakeholder in discourse text —'''

count = content.count(old)
print(f"Anchor found {count} time(s) in the live file.")

if count != 1:
    print(f"Expected exactly 1 occurrence, found {count} -- aborting without changes for safety.")
else:
    content = content.replace(old, new, 1)
    with open(PATH, "w") as f:
        f.write(content)
    print("Patched successfully: stakeholder_type field added to StakeholderRegistry's class body.")

    # Verify the patch landed exactly once, no duplication
    with open(PATH, "r") as f:
        verify = f.read()
    field_count = verify.count("stakeholder_type: Mapped[Optional[str]] = mapped_column(")
    print(f"\nField definition now appears {field_count} time(s) in the file (expected: 1).")
