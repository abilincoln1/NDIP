"""Check real StakeholderInfluenceLevel enum values."""
import sys; sys.path.insert(0,'/app')
from app.models.models import StakeholderInfluenceLevel
print("StakeholderInfluenceLevel values:")
for member in StakeholderInfluenceLevel:
    print(f"  {member.name} = {member.value!r}")
