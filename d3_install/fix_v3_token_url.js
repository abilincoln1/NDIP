const fs = require('fs');

const loginPath = '/app/src/app/login/page.tsx';
let login = fs.readFileSync(loginPath, 'utf8');

// Fix: use full backend URL, not relative path
const oldFetch = `        const r3 = await fetch("/api/v3/auth/login", {`;
const newFetch = `        const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const r3 = await fetch(\`\${backendUrl}/api/v3/auth/login\`, {`;

if (login.includes(oldFetch)) {
  login = login.replace(oldFetch, newFetch);
  fs.writeFileSync(loginPath, login);
  console.log('Fixed: v3 fetch now uses full backend URL');
} else {
  // Try alternative — maybe already partially patched
  console.log('Pattern not found — showing fetch lines:');
  login.split('\n').forEach((l, i) => {
    if (l.includes('fetch') || l.includes('v3/auth')) console.log(`${i+1}: ${l}`);
  });
}
