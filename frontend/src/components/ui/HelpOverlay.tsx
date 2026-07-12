"use client";
/**
 * NDIP V7 — Help Overlay ("What Am I Looking At?" Mode)
 * Activated by pressing H or clicking the ? button.
 * Provides per-widget explanations answering 6 standard questions.
 * Integrates with the Copilot for AI-escalated explanations.
 */
import { useState, useEffect } from "react";
import { HelpCircle, X, ExternalLink, ChevronRight, Database, Clock, AlertTriangle, CheckCircle } from "lucide-react";

// ── Widget explanation registry ───────────────────────────────────────────────
export interface WidgetExplanation {
  id: string;
  label: string;
  what: string;
  example: string;
  why: string;
  source: string;
  updated: string;
  interpret: string;
  trust: "High" | "Medium" | "Low";
  trusted: string;
  warnings?: string[];
  related?: string[];
}

export const WIDGET_EXPLANATIONS: Record<string, WidgetExplanation> = {
  share_of_voice: {
    id: "share_of_voice",
    label: "Narrative Share of Voice",
    what: "What percentage of all monitored conversations is about each strategic topic right now.",
    example: "Security at 34% share of voice means roughly one in three monitored conversations is about security topics.",
    why: "Tells leadership where public attention is concentrated — and whether it matches the organisation's strategic priorities.",
    source: "Computed from normalised post text, classified against 11 strategic narrative keyword templates.",
    updated: "After every ingest cycle — approximately every 24 hours. Timestamp shown at top of page.",
    interpret: "Rising share of voice + negative sentiment = potential crisis signal. Rising + positive = opportunity window. Stable + any sentiment = background noise.",
    trust: "High",
    trusted: "Yes, when source count is 4+. Check the Confidence Statement — if it shows Low, treat share of voice as indicative only.",
    warnings: ["If active source count drops below 4, all share of voice figures have reduced reliability."],
    related: ["momentum", "sentiment_score", "confidence_label"],
  },
  momentum: {
    id: "momentum",
    label: "Momentum Score",
    what: "The rate of change in discourse volume for a narrative, compared to the previous equivalent period.",
    example: "+340% momentum means this topic is generating 3.4× as many mentions as the same period last week.",
    why: "Identifies what is accelerating before it becomes dominant — giving time to respond before a story breaks.",
    source: "Calculated as (current period count − prior period count) ÷ prior period count × 100.",
    updated: "Real-time within each ingest cycle. Reflects the currently selected time window (7d, 14d, 30d).",
    interpret: "High positive + negative sentiment = early warning. High positive + positive sentiment = opportunity. High positive alone means nothing until sentiment is checked.",
    trust: "Medium",
    trusted: "Yes for direction, with caveats. A single viral post can drive 400%+ momentum on its own. Always check source count before acting.",
    warnings: [
      "Momentum can spike due to one viral story, not a structural shift.",
      "Check source count: single-source momentum spikes should not trigger escalation.",
    ],
    related: ["share_of_voice", "sentiment_score", "engagement_index"],
  },
  sentiment_score: {
    id: "sentiment_score",
    label: "Sentiment Score",
    what: "The overall emotional tone of discourse around a topic. Ranges from -1 (very negative) to +1 (very positive). 0 = neutral.",
    example: "A sentiment score of -0.72 for the Security narrative means most monitored discussion about security is negative in tone.",
    why: "Shows whether public conversation about a topic is supportive, critical, or mixed. A falling sentiment score in a high-volume topic is the most important combined signal to monitor.",
    source: "Extracted from normalised post text by NLP sentiment analysis (spaCy when available, enhanced fallback otherwise).",
    updated: "After every ingest cycle. Sentiment reflects the full selected time window.",
    interpret: "Sentiment below -0.5 in a high-share narrative = crisis risk. Sentiment above +0.3 in a rising narrative = engagement opportunity. Neutral sentiment (near 0) = monitor only.",
    trust: "Medium",
    trusted: "Yes for directional guidance. NLP sentiment is accurate for overall tone but may miss nuance in complex political statements.",
    related: ["share_of_voice", "momentum", "confidence_label"],
  },
  engagement_index: {
    id: "engagement_index",
    label: "Engagement Index",
    what: "A single composite number (0–5+) that reflects the overall intelligence intensity across all monitored topics.",
    example: "An index of 1.58 means moderate, multi-source activity. An index above 3.5 typically indicates a high-intensity national event.",
    why: "Gives a single-number health check on the intelligence environment. Very low may mean ingest problems. Very high may mean an unfolding national event.",
    source: "Computed by compute_all_metrics(): weighted composite of post volume, source diversity, sentiment intensity, and growth rate.",
    updated: "Saved with every ingest cycle. The trend graph shows the last 30 days.",
    interpret: "Context matters. An index of 0.5 during a quiet week is normal. The same score after a major event is a warning. Read the trend, not just the current value.",
    trust: "High",
    trusted: "Yes for trend monitoring. Single-point readings are less informative than the 7–30 day trend.",
    related: ["sentiment_score", "momentum"],
  },
  influence_score: {
    id: "influence_score",
    label: "Influence Score",
    what: "How prominently a stakeholder appears in monitored discourse, weighted by source quality and mention context.",
    example: "A score of 73 for a minister means they appear in 38+ sources across 4+ platforms with consistent mention patterns.",
    why: "Identifies who is driving the discourse and who should be prioritised for engagement — based on actual discourse presence, not formal title.",
    source: "Computed from: mention count (log-scaled), source diversity, momentum trajectory, and relationship strength. Stored in stakeholder_influence_profiles.",
    updated: "Updated on every ingest run (daily). Scores reflect the last 30 days of discourse.",
    interpret: "Do not confuse influence (discourse presence) with authority (formal power). A junior official with high engagement may have more discourse influence than a senior one. Scores below 10 should be treated with caution.",
    trust: "High",
    trusted: "Yes for engagement prioritisation. Treat as a signal for who is active in discourse, not a definitive power ranking.",
    warnings: ["Low mention counts (under 10) produce unreliable influence scores. Check the source count alongside the score."],
    related: ["composite_index", "momentum", "opportunity_score"],
  },
  composite_index: {
    id: "composite_index",
    label: "Composite Influence Index",
    what: "The overall stakeholder ranking score, combining five dimensions: influence, momentum, narrative impact, relationship strength, and opportunity relevance.",
    example: "Rural Electrification Agency composite index of 72.7 reflects high mention counts, strong momentum, and strong alignment with tracked energy opportunities.",
    why: "Provides a single number for stakeholder prioritisation that reflects not just how much they are mentioned, but whether that mention is strategically relevant.",
    source: "materialise_intelligence.py → materialise_influence_profiles() → composite of five sub-scores.",
    updated: "Updated daily during ingest materialisation. 25-hour TTL — if more than 25 hours since last ingest, falls back to live computation.",
    interpret: "Use this for ordering stakeholder engagement priorities. Higher composite = engage sooner. But always check whether momentum is rising (they are becoming more relevant) or falling (relevance may be peak).",
    trust: "High",
    trusted: "Yes. This is one of the most reliable metrics in the platform — based on multi-dimensional analysis of actual discourse behaviour.",
    related: ["influence_score", "opportunity_score", "alignment_score"],
  },
  opportunity_score: {
    id: "opportunity_score",
    label: "Opportunity Score",
    what: "How strong the discourse signal is for a strategic opportunity, weighted by stakeholder alignment and current readiness of conditions.",
    example: "Diaspora Investment opportunity score 78 = strong discourse signal, aligned stakeholders already identified, conditions appear ready for engagement.",
    why: "Prioritises which opportunities to pursue first. Higher scores mean more evidence, better alignment, and higher probability of traction.",
    source: "opportunity_assessments table → compute_opportunity_alignment() + compute_opportunity_readiness() → composite.",
    updated: "Detected and scored on SOI Dashboard load. Note: this is a known architectural item to be moved to ingest pipeline.",
    interpret: "Score 80+: act now. Score 60–79: conditions are good, begin preparation. Score below 40: monitor — conditions not yet ready. Always check alignment and readiness sub-scores separately.",
    trust: "Medium",
    trusted: "Yes for prioritisation. Validate with human intelligence before committing resources. New or niche opportunities may score low due to limited discourse data, not low strategic viability.",
    warnings: [
      "Score reflects discourse signal strength, not political viability.",
      "A high score on a sensitive topic may still require senior sign-off before acting.",
    ],
    related: ["alignment_score", "readiness_score", "composite_index"],
  },
  confidence_label: {
    id: "confidence_label",
    label: "Confidence Label",
    what: "A qualitative assessment (High / Medium / Low) of how reliable the surrounding intelligence is.",
    example: "Confidence: Medium means the data is based on a reasonable number of sources but would benefit from more diversity. Act on it, but note the caveat.",
    why: "Tells leadership how much weight to give a finding or recommendation. Low confidence items should inform, not drive, decisions.",
    source: "source_quality.py → get_source_quality_report() → combines source_count, processing_rate, and record_volume.",
    updated: "Recalculated on every ingest cycle. If active sources drop, confidence automatically falls.",
    interpret: "High: trust and act. Medium: trust with noted caveats. Low: treat as early signal only — do not make commitments based on Low confidence intelligence without additional validation.",
    trust: "High",
    trusted: "Yes — this is the platform's self-assessment of its own reliability. It is conservative by design.",
    related: ["share_of_voice", "engagement_index"],
  },
  watchlist_item: {
    id: "watchlist_item",
    label: "Watchlist Item",
    what: "An intelligence item that has crossed a threshold requiring leadership attention, automatically generated by the platform.",
    example: "A Critical watchlist item for 'Security — Negative Surge' means the Security narrative momentum exceeded 400% with negative sentiment and high strategic weight.",
    why: "Focuses leadership attention. The platform generates hundreds of data points — the watchlist filters to only what requires a decision.",
    source: "services/watchlist.py → generate_watchlist() → applies thresholds to narratives, risks, opportunities, and election signals.",
    updated: "Regenerated on every Leadership Pack or Watchlist page cold load.",
    interpret: "Critical = brief leadership today and consider same-day action. High = address this week. Monitor = include in weekly team review. Not all items of the same tier are equally urgent — read the rationale for each.",
    trust: "High",
    trusted: "Yes. Watchlist items are generated by conservative thresholds designed to avoid false positives.",
    warnings: ["Monitor-tier items do not require immediate action. Acting on every watchlist item wastes leadership attention."],
    related: ["momentum", "sentiment_score", "share_of_voice"],
  },
  gnei_score: {
    id: "gnei_score",
    label: "GNEI Score",
    what: "The Global Nigerian Engagement Index — a composite score measuring the intensity and sentiment of diaspora-related discourse globally.",
    example: "GNEI of 1.4 indicates moderate diaspora engagement activity. A score above 2.5 indicates high-intensity diaspora discourse, often associated with a policy announcement or community event.",
    why: "Provides a single measure of diaspora community attention and sentiment, enabling the organisation to calibrate diaspora-facing communications.",
    source: "services/gnei.py → compute_gnei_score() → composite of diaspora narrative volume, sentiment, and engagement rate.",
    updated: "Updated on every ingest cycle. Trend visible on the GNEI dashboard over 30 days.",
    interpret: "Rising GNEI + positive sentiment = diaspora community is engaged and receptive — good time for outreach. Rising GNEI + negative sentiment = community concern, intervention may be needed. Falling GNEI = declining engagement — consider re-engagement strategies.",
    trust: "High",
    trusted: "Yes, when diaspora-specific sources are active. Check source count on the GNEI dashboard.",
    related: ["engagement_index", "sentiment_score", "share_of_voice"],
  },
};

// ── Component ─────────────────────────────────────────────────────────────────
interface HelpOverlayProps {
  enabled?: boolean;
  onToggle?: (enabled: boolean) => void;
}

export function HelpOverlayToggle({ enabled = false, onToggle }: HelpOverlayProps) {
  return (
    <button
      onClick={() => onToggle?.(!enabled)}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-150 border ${
        enabled
          ? "bg-blue-600/20 text-blue-300 border-blue-600/40 hover:bg-blue-600/30"
          : "bg-slate-800 text-slate-400 border-slate-700 hover:text-white hover:border-slate-600"
      }`}
      title="Press H to toggle help overlay"
    >
      <HelpCircle size={12} />
      {enabled ? "Help ON" : "Help"}
    </button>
  );
}

interface WidgetHelpProps {
  widgetId: string;
  children: React.ReactNode;
  overlayEnabled?: boolean;
}

export function WidgetHelp({ widgetId, children, overlayEnabled = false }: WidgetHelpProps) {
  const [panelOpen, setPanelOpen] = useState(false);
  const explanation = WIDGET_EXPLANATIONS[widgetId];

  if (!overlayEnabled || !explanation) {
    return <>{children}</>;
  }

  return (
    <div className="relative group">
      {children}

      {/* Help ring */}
      <button
        onClick={() => setPanelOpen(true)}
        className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-blue-600 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-150 shadow-lg z-10 animate-pulse"
        title={`Help: ${explanation.label}`}
      >
        <span className="text-white text-xs font-bold">?</span>
      </button>

      {/* Help panel */}
      {panelOpen && (
        <WidgetHelpPanel
          explanation={explanation}
          onClose={() => setPanelOpen(false)}
        />
      )}
    </div>
  );
}

interface WidgetHelpPanelProps {
  explanation: WidgetExplanation;
  onClose: () => void;
}

function WidgetHelpPanel({ explanation, onClose }: WidgetHelpPanelProps) {
  const trustColor = explanation.trust === "High"
    ? "text-teal-400 bg-teal-500/10 border-teal-600/30"
    : explanation.trust === "Medium"
    ? "text-amber-400 bg-amber-500/10 border-amber-600/30"
    : "text-red-400 bg-red-500/10 border-red-600/30";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-lg max-h-[85vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 sticky top-0 bg-slate-900 rounded-t-2xl">
          <div className="flex items-center gap-2">
            <HelpCircle size={16} className="text-blue-400" />
            <span className="font-semibold text-white">{explanation.label}</span>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white">
            <X size={16} />
          </button>
        </div>

        {/* Content */}
        <div className="px-5 py-4 space-y-4">

          {/* Q1: What is this */}
          <QASection
            q="What is this?"
            a={explanation.what}
            icon="📊"
          />

          {/* Example */}
          <div className="bg-blue-500/10 border border-blue-600/20 rounded-lg px-3 py-2.5">
            <p className="text-xs text-blue-400 font-semibold mb-1">Plain English example</p>
            <p className="text-sm text-blue-100">{explanation.example}</p>
          </div>

          {/* Q2: Why it matters */}
          <QASection q="Why does it matter?" a={explanation.why} icon="💡" />

          {/* Q3: Data source */}
          <QASection q="Where does this data come from?" a={explanation.source} icon="🗄️" extraClass="text-slate-400" />

          {/* Q4: When updated */}
          <div className="flex items-start gap-2">
            <Clock size={14} className="text-slate-500 mt-0.5 shrink-0" />
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-0.5">When is it updated?</p>
              <p className="text-sm text-slate-300">{explanation.updated}</p>
            </div>
          </div>

          {/* Q5: How to interpret */}
          <QASection q="How should leadership interpret it?" a={explanation.interpret} icon="🎯" />

          {/* Q6: Trust level */}
          <div>
            <p className="text-xs text-slate-500 font-semibold mb-1.5">Can this be trusted?</p>
            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-semibold ${trustColor}`}>
              <CheckCircle size={11} />
              {explanation.trust} confidence
            </div>
            <p className="text-sm text-slate-300 mt-1.5">{explanation.trusted}</p>
          </div>

          {/* Warnings */}
          {explanation.warnings && explanation.warnings.length > 0 && (
            <div className="bg-amber-500/10 border border-amber-600/20 rounded-lg px-3 py-2.5">
              <div className="flex items-center gap-1.5 mb-1.5">
                <AlertTriangle size={12} className="text-amber-400" />
                <p className="text-xs text-amber-400 font-semibold">Watch out for</p>
              </div>
              {explanation.warnings.map((w, i) => (
                <p key={i} className="text-sm text-amber-200 mb-1 last:mb-0">• {w}</p>
              ))}
            </div>
          )}

          {/* Related */}
          {explanation.related && explanation.related.length > 0 && (
            <div>
              <p className="text-xs text-slate-500 font-semibold mb-1.5">Related metrics</p>
              <div className="flex flex-wrap gap-1.5">
                {explanation.related.map(r => (
                  <span key={r} className="text-xs px-2 py-0.5 bg-slate-800 border border-slate-700 rounded-full text-slate-400">
                    {r.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-slate-700 bg-slate-800/50 rounded-b-2xl">
          <p className="text-xs text-slate-500 text-center">
            Press <kbd className="px-1 py-0.5 bg-slate-700 rounded text-xs">H</kbd> to toggle help overlay on all elements
          </p>
        </div>
      </div>
    </div>
  );
}

function QASection({
  q, a, icon, extraClass = "text-slate-200"
}: { q: string; a: string; icon: string; extraClass?: string }) {
  return (
    <div>
      <p className="text-xs text-slate-500 font-semibold mb-0.5">{q}</p>
      <p className={`text-sm leading-relaxed ${extraClass}`}>{a}</p>
    </div>
  );
}
