"""
Diagnostic: find the exact byte-level discrepancy preventing Patch 2's
anchor text from matching the live models.py file.

Run: docker exec agora-backend-1 python scripts/v62_diagnose_anchor.py
"""
with open('/app/app/models/models.py', 'rb') as f:
    content = f.read()

idx = content.find(b'class StakeholderCategory')
chunk = content[idx:idx+420]
print("Raw bytes around StakeholderCategory:")
print(repr(chunk))
print()

# Also check decoded text version against the exact anchor used in the patch
text = content.decode('utf-8')
anchor = '''class StakeholderCategory(str, enum.Enum):
    POLITICAL = "POLITICAL"                # Presidency, ministers, governors, NASS, party leadership
    PUBLIC_INSTITUTION = "PUBLIC_INSTITUTION"  # Federal/state ministries, departments, agencies, regulators
    DIASPORA = "DIASPORA"                  # RTIFN, diaspora orgs, community/business leaders, professional networks
    INVESTMENT = "INVESTMENT"              # DFIs, sovereign funds, PE, impact/infrastructure investors
    INTERNATIONAL = "INTERNATIONAL"        # World Bank, AfDB, UN agencies, foreign missions, INGOs
class StakeholderRegistry(Base):'''

print("Anchor found in file:", anchor in text)
if anchor not in text:
    idx2 = text.find('class StakeholderCategory')
    real_chunk = text[idx2:idx2+len(anchor)+20]
    print()
    print("Anchor (repr):")
    print(repr(anchor))
    print()
    print("Real text at same location (repr):")
    print(repr(real_chunk))
