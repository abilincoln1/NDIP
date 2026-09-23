const fs = require('fs');
const path = '/app/src/app/login/page.tsx';
let c = fs.readFileSync(path, 'utf8');

// Replace process.env pattern with browser-safe constant
const old = 'const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";';
const neu = 'const backendUrl = "http://localhost:8000";';

if (c.includes(old)) {
  c = c.replace(old, neu);
  fs.writeFileSync(path, c);
  console.log('Fixed: backendUrl is now hardcoded browser-safe constant');
} else {
  console.log('Pattern not found — current fetch lines:');
  c.split('\n').forEach((l,i) => {
    if (l.includes('backendUrl') || l.includes('fetch') || l.includes('v3/auth')) {
      console.log(`${i+1}: ${l}`);
    }
  });
}
