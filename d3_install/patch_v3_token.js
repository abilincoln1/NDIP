const fs = require('fs');

// 1. Patch login/page.tsx — also fetch v3 token after v2 login
const loginPath = '/app/src/app/login/page.tsx';
let login = fs.readFileSync(loginPath, 'utf8');

const oldSubmit = `      const r = await authApi.login(email, password);
      localStorage.setItem("agora_token", r.data.access_token);
      router.push("/");`;

const newSubmit = `      const r = await authApi.login(email, password);
      localStorage.setItem("agora_token", r.data.access_token);
      // Also obtain v3 token for operational pages (Activities/Volunteers/Projects)
      try {
        const r3 = await fetch("/api/v3/auth/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password, tenant_slug: "rtifn" }),
        });
        if (r3.ok) {
          const d3 = await r3.json();
          if (d3.access_token) localStorage.setItem("agora_token_v3", d3.access_token);
        }
      } catch (_) {}
      router.push("/");`;

if (login.includes(oldSubmit)) {
  login = login.replace(oldSubmit, newSubmit);
  fs.writeFileSync(loginPath, login);
  console.log('login/page.tsx patched: v3 token fetch added');
} else {
  console.log('ERROR: login pattern not found in login/page.tsx');
  process.exit(1);
}

// 2. Patch api.ts — update interceptor to use agora_token_v3 for /api/v3/ routes
const apiPath = '/app/src/lib/api.ts';
let api = fs.readFileSync(apiPath, 'utf8');

const oldInterceptor = `  if (typeof window !== "undefined") {
    const token = localStorage.getItem("agora_token");
    if (token) config.headers.Authorization = \`Bearer \${token}\`;
  }`;

const newInterceptor = `  if (typeof window !== "undefined") {
    // Use v3 token for v3 routes, v2 token for everything else
    const isV3 = config.url && config.url.startsWith("/api/v3/");
    const token = isV3
      ? (localStorage.getItem("agora_token_v3") || localStorage.getItem("agora_token"))
      : localStorage.getItem("agora_token");
    if (token) config.headers.Authorization = \`Bearer \${token}\`;
  }`;

if (api.includes(oldInterceptor)) {
  api = api.replace(oldInterceptor, newInterceptor);
  fs.writeFileSync(apiPath, api);
  console.log('api.ts patched: v3 token routing added');
} else {
  console.log('ERROR: interceptor pattern not found in api.ts');
  process.exit(1);
}

console.log('Done — sign out and back in to get a fresh v3 token');
