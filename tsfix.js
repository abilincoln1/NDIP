
const fs = require('fs');
const path = '/app/src/app/leadership-pack/page.tsx';
let c = fs.readFileSync(path, 'utf8');

// Add useCopilotData import
if (!c.includes('useCopilotData')) {
  c = c.replace('import api from "@/lib/api";', 'import api from "@/lib/api";\nimport { useCopilotData } from "@/components/ui/AICopilot";');
}

// Add hook
if (!c.includes('setPageData')) {
  c = c.replace('const [actions, setActions] = useState<any>(null);', 'const [actions, setActions] = useState<any>(null);\n  const { setPageData } = useCopilotData();');
}

// Add setPageData call with correct types
if (!c.includes('setPageData(')) {
  c = c.replace(
    '.then(r => setData(r.data))',
    `.then(r => { setData(r.data); if (r.data) { setPageData({ narratives: r.data.narrative_assessments || [], engagement_index: r.data.engagement_index, sentiment_score: r.data.sentiment_score, confidence: r.data.confidence_label, watchlist_critical_count: (r.data.risks || []).filter((x: any) => x.level === 'Critical').length, watchlist_high_count: (r.data.risks || []).filter((x: any) => x.level === 'Warning').length, risks: r.data.risks || [], top_opportunities: r.data.opportunities || [], significant_changes: r.data.significant_changes || [] }); } })`
  );
}

// Fix any existing incorrect filter types
c = c.replace(/\.filter\(\(x\) => x\.level/g, '.filter((x: any) => x.level');

fs.writeFileSync(path, c);
console.log('LP page patched');
