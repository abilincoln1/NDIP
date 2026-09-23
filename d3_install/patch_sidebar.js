const fs = require('fs');
const p = '/app/src/components/layout/Sidebar.tsx';
let c = fs.readFileSync(p, 'utf8');

if (c.includes('OPERATIONAL')) {
  console.log('Already patched');
  process.exit(0);
}

const insert = [
  ',',
  '  {',
  '    label: "OPERATIONAL",',
  '    items: [',
  '      { href: "/activities", label: "Activities", icon: Activity },',
  '      { href: "/volunteers", label: "Volunteers", icon: Users },',
  '      { href: "/projects",   label: "Projects",   icon: Cpu },',
  '    ],',
  '  }'
].join('\n');

const target = '  {\n    label: "ANALYTICS"';
if (!c.includes(target)) {
  console.log('ERROR: ANALYTICS section not found — check Sidebar.tsx');
  process.exit(1);
}

c = c.replace(target, insert + '\n' + target);
fs.writeFileSync(p, c);
console.log('Done — OPERATIONAL section added before ANALYTICS');
console.log('Verify:', c.includes('OPERATIONAL') ? 'PASS' : 'FAIL');
