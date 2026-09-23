const fs = require('fs');
const p = '/app/src/components/layout/Sidebar.tsx';
let c = fs.readFileSync(p, 'utf8');

// The patch added the OPERATIONAL section but missed the trailing comma
// Fix: ensure every object in the NAV_GROUPS array is followed by a comma
// The error is: }  {  instead of },  {

// Replace the specific missing comma between OPERATIONAL and ANALYTICS
c = c.replace(
  '    ],\n  }\n  {\n    label: "ANALYTICS"',
  '    ],\n  },\n  {\n    label: "ANALYTICS"'
);

fs.writeFileSync(p, c);

// Verify
const check = c.includes('  },\n  {\n    label: "ANALYTICS"');
console.log('Fix applied:', check ? 'PASS' : 'FAIL - pattern not found');

// Show the relevant section
const idx = c.indexOf('OPERATIONAL');
if (idx > -1) {
  console.log('Context around OPERATIONAL:');
  console.log(c.slice(idx - 10, idx + 200));
}
