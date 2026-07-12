"""
NDIP Content Generation Service

Generates external-facing communications content from data NDIP already
computes -- no new data sources, no new analysis. Three outputs:

  1. Executive Newsletter -- derived from Leadership Pack, for RTIFN
     leadership/board distribution.
  2. Pulse Newsletter -- derived from National Pulse, a shorter, more
     frequent community-facing update.
  3. Instagram text-to-video prompts -- derived from the same underlying
     narrative/GNEI data, written as scene-by-scene prompts suitable for
     a text-to-video generation tool, not static image captions.

WhatsApp: NDIP does not send messages automatically to any external
platform. WhatsApp has no open API for posting into arbitrary groups --
only the official WhatsApp Business API (requiring Meta Business
verification and the group admin's cooperation) or unofficial automation
tools that violate WhatsApp's terms of service. This module instead
formats the newsletter content as WhatsApp-ready plain text, which a
human can paste into a group manually. If RTIFN sets up a real WhatsApp
Business API account in future, a send function can be added here against
that real, sanctioned integration.
"""
from datetime import datetime, timezone
import re


def _md_bold_to_whatsapp(text: str) -> str:
    """Converts markdown **bold** (used throughout NDIP's narrative text) to WhatsApp's single-asterisk *bold* convention."""
    return re.sub(r"\*\*(.*?)\*\*", r"*\1*", text or "")


def _strip_md_bold(text: str) -> str:
    """Strips markdown **bold** markers entirely -- used in HTML output where the surrounding paragraph is already styled."""
    return re.sub(r"\*\*(.*?)\*\*", r"\1", text or "")


def generate_executive_newsletter(leadership_pack_data: dict) -> dict:
    """
    Builds a board/leadership-facing newsletter from an already-computed
    Leadership Pack result (pass the dict returned by leadership_pack()).
    Returns both an HTML version (for email) and a plain-text version
    (for WhatsApp/Slack/manual paste).
    """
    lp = leadership_pack_data
    generated = datetime.now(timezone.utc).strftime("%d %B %Y")
    period = lp.get("period_days", 7)

    top_narratives = (lp.get("narrative_assessments") or [])[:3]
    top_risks = [r for r in (lp.get("risks") or []) if r.get("level") not in ("Information",)][:2]
    top_opportunities = (lp.get("opportunities") or [])[:2]
    stakeholders = (lp.get("key_stakeholders") or [])[:3]
    engagement_priorities = (lp.get("engagement_priorities") or [])[:3]

    # --- Plain text (WhatsApp / manual paste) ---
    lines = []
    lines.append(f"*NDIP EXECUTIVE BRIEFING* — {generated}")
    lines.append(f"_National & Diaspora Intelligence Platform · Powered by RTIFN_")
    lines.append(f"_{period}-day intelligence window_")
    lines.append("")
    lines.append("*THIS WEEK AT A GLANCE*")
    lines.append(_md_bold_to_whatsapp(lp.get("executive_summary", "")).strip())
    lines.append("")

    if top_narratives:
        lines.append("*TOP STORIES*")
        for n in top_narratives:
            lines.append(f"• *{n.get('narrative')}* ({n.get('share_of_voice')}% of discourse, {n.get('sentiment_label')}): {_md_bold_to_whatsapp(n.get('what_happened', '')).strip()}")
        lines.append("")

    if top_risks:
        lines.append("*RISKS TO WATCH*")
        for r in top_risks:
            lines.append(f"• [{r.get('level')}] {r.get('title')}")
        lines.append("")

    if top_opportunities:
        lines.append("*OPPORTUNITIES*")
        for o in top_opportunities:
            lines.append(f"• [{o.get('rank')}] {o.get('title')}")
        lines.append("")

    if stakeholders:
        lines.append("*KEY STAKEHOLDERS THIS PERIOD*")
        for s in stakeholders:
            lines.append(f"• {s.get('name')} — {s.get('mention_count')} mentions, {s.get('monitoring_priority')} priority")
        lines.append("")

    if engagement_priorities:
        lines.append("*RECOMMENDED ENGAGEMENT*")
        for s in engagement_priorities:
            lines.append(f"• Engage {s.get('name')}")
        lines.append("")

    lines.append("_NDIP — National & Diaspora Intelligence Platform · Powered by RTIFN_")
    lines.append("_Not for public distribution_")
    plain_text = "\n".join(lines)

    # --- HTML (email newsletter) ---
    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    narrative_html = "".join(
        f"""<div style="margin-bottom:16px;padding:14px;background:#f8fafc;border-radius:8px;border-left:4px solid #0C7A63;">
            <p style="margin:0 0 6px;font-weight:700;color:#0f172a;">{esc(n.get('narrative'))}
            <span style="font-weight:400;color:#64748b;font-size:13px;"> · {n.get('share_of_voice')}% · {esc(n.get('sentiment_label'))}</span></p>
            <p style="margin:0;color:#334155;font-size:14px;line-height:1.5;">{esc(_strip_md_bold(n.get('what_happened')))}</p>
        </div>"""
        for n in top_narratives
    )
    risks_html = "".join(
        f"""<li style="margin-bottom:8px;color:#334155;"><strong style="color:#b42318;">[{esc(r.get('level'))}]</strong> {esc(r.get('title'))}</li>"""
        for r in top_risks
    ) or '<li style="color:#64748b;">No critical or warning-level risks identified this period.</li>'
    opps_html = "".join(
        f"""<li style="margin-bottom:8px;color:#334155;"><strong style="color:#0C7A63;">[{esc(o.get('rank'))}]</strong> {esc(o.get('title'))}</li>"""
        for o in top_opportunities
    )
    stakeholders_html = "".join(
        f"""<tr><td style="padding:6px 10px;color:#334155;">{esc(s.get('name'))}</td>
            <td style="padding:6px 10px;color:#64748b;text-align:right;">{s.get('mention_count')} mentions</td>
            <td style="padding:6px 10px;text-align:right;"><span style="background:#0C7A6322;color:#0C7A63;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;">{esc(s.get('monitoring_priority'))}</span></td></tr>"""
        for s in stakeholders
    )

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:600px;margin:0 auto;background:#ffffff;">
  <div style="background:#0C7A63;padding:28px 32px;">
    <p style="margin:0;color:#ffffff;font-size:22px;font-weight:700;">NDIP Executive Briefing</p>
    <p style="margin:4px 0 0;color:#d1fae5;font-size:13px;">National &amp; Diaspora Intelligence Platform · Powered by RTIFN</p>
    <p style="margin:8px 0 0;color:#a7f3d0;font-size:12px;">{generated} · {period}-day window</p>
  </div>
  <div style="padding:28px 32px;">
    <h2 style="margin:0 0 10px;font-size:16px;color:#0f172a;">This Week at a Glance</h2>
    <p style="margin:0 0 24px;color:#334155;font-size:14px;line-height:1.6;">{esc(_strip_md_bold(lp.get('executive_summary')))}</p>

    <h2 style="margin:0 0 12px;font-size:16px;color:#0f172a;">Top Stories</h2>
    {narrative_html}

    <h2 style="margin:24px 0 10px;font-size:16px;color:#0f172a;">Risks to Watch</h2>
    <ul style="margin:0 0 24px;padding-left:18px;">{risks_html}</ul>

    <h2 style="margin:0 0 10px;font-size:16px;color:#0f172a;">Opportunities</h2>
    <ul style="margin:0 0 24px;padding-left:18px;">{opps_html}</ul>

    <h2 style="margin:0 0 12px;font-size:16px;color:#0f172a;">Key Stakeholders This Period</h2>
    <table style="width:100%;border-collapse:collapse;margin-bottom:24px;">{stakeholders_html}</table>

    <p style="margin:24px 0 0;padding-top:16px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:11px;">
      NDIP — National &amp; Diaspora Intelligence Platform · Powered by RTIFN · Not for public distribution
    </p>
  </div>
</div>
</body></html>"""

    return {
        "type": "executive_newsletter",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": period,
        "html": html,
        "plain_text": plain_text,
    }


def generate_pulse_newsletter(national_pulse_data: dict) -> dict:
    """
    Builds a shorter, more frequent community-facing update from an
    already-computed National Pulse result (pass the dict returned by
    national_pulse()). Lighter weight than the executive newsletter --
    intended for more frequent (e.g. weekly) community distribution.
    """
    np = national_pulse_data
    generated = datetime.now(timezone.utc).strftime("%d %B %Y")
    period = np.get("period_days", 7)
    pulse_score = np.get("pulse_score")
    pulse_label = np.get("pulse_label", "Stable")
    narratives = (np.get("narrative_components") or [])[:4]

    lines = []
    lines.append(f"*NDIP COMMUNITY PULSE* — {generated}")
    lines.append(f"_Nigeria & Diaspora discourse, {period}-day snapshot_")
    lines.append("")
    lines.append(f"*National Pulse: {pulse_score}/100 ({pulse_label})*")
    lines.append("")
    if narratives:
        lines.append("*WHAT'S BEING TALKED ABOUT*")
        for n in narratives:
            arrow = "↑" if n.get("momentum", 0) > 0 else "↓" if n.get("momentum", 0) < 0 else "→"
            lines.append(f"• {n.get('narrative')} — {n.get('share_of_voice')}% {arrow}")
        lines.append("")
    lines.append("_Powered by RTIFN — Understanding Nigeria. Understanding the Diaspora._")
    plain_text = "\n".join(lines)

    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    narrative_rows = "".join(
        f"""<tr><td style="padding:8px 10px;color:#334155;">{esc(n.get('narrative'))}</td>
            <td style="padding:8px 10px;text-align:right;color:#0C7A63;font-weight:600;">{n.get('share_of_voice')}%</td></tr>"""
        for n in narratives
    )

    html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;">
<div style="max-width:560px;margin:0 auto;background:#ffffff;">
  <div style="background:#1F2937;padding:24px 28px;">
    <p style="margin:0;color:#ffffff;font-size:20px;font-weight:700;">NDIP Community Pulse</p>
    <p style="margin:4px 0 0;color:#cbd5e1;font-size:12px;">{generated} · {period}-day snapshot</p>
  </div>
  <div style="padding:24px 28px;">
    <div style="text-align:center;padding:20px;background:#f8fafc;border-radius:10px;margin-bottom:20px;">
      <p style="margin:0;font-size:36px;font-weight:800;color:#0C7A63;">{pulse_score}<span style="font-size:18px;color:#94a3b8;">/100</span></p>
      <p style="margin:4px 0 0;color:#64748b;font-size:13px;">{esc(pulse_label)}</p>
    </div>
    <h2 style="margin:0 0 10px;font-size:15px;color:#0f172a;">What's Being Talked About</h2>
    <table style="width:100%;border-collapse:collapse;">{narrative_rows}</table>
    <p style="margin:24px 0 0;padding-top:14px;border-top:1px solid #e2e8f0;color:#94a3b8;font-size:11px;">
      Powered by RTIFN — Understanding Nigeria. Understanding the Diaspora.
    </p>
  </div>
</div>
</body></html>"""

    return {
        "type": "pulse_newsletter",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_days": period,
        "pulse_score": pulse_score,
        "html": html,
        "plain_text": plain_text,
    }


def generate_instagram_video_prompts(national_pulse_data: dict, gnei_data: dict = None, limit: int = 3) -> list:
    """
    Generates text-to-video prompts (for tools like Runway, Pika, Sora-style
    generators) from current narrative and GNEI data. Each prompt is a
    structured scene description -- subject, setting, mood, camera
    movement, pacing -- not a static-image caption. Distinct from a social
    caption: a text-to-video tool needs to know what happens over time in
    the clip, not just what's depicted.

    Deliberately abstract/illustrative in subject matter (no real
    identifiable people, no real specific events depicted as footage) --
    these describe mood-board / data-visualisation style clips suitable
    for an institutional account, not generated "fake news footage".
    """
    narratives = (national_pulse_data.get("narrative_components") or [])[:limit]
    prompts = []

    MOOD_BY_SENTIMENT = {
        "positive": "warm, hopeful, golden-hour lighting, optimistic pacing",
        "negative": "subdued, contemplative, cooler tones, slower pacing",
        "neutral": "balanced, observational, naturalistic lighting, steady pacing",
    }

    for n in narratives:
        name = n.get("narrative", "")
        sov = n.get("share_of_voice", 0)
        sentiment = n.get("sentiment_label", "neutral")
        momentum = n.get("momentum", 0)
        direction = "rising" if momentum > 10 else "falling" if momentum < -10 else "steady"
        mood = MOOD_BY_SENTIMENT.get(sentiment, MOOD_BY_SENTIMENT["neutral"])

        prompt_text = (
            f"A 15-second data-visualisation style clip representing public conversation "
            f"about \"{name}\" among the Nigerian diaspora. "
            f"Opening shot: an abstract animated network of glowing connection points "
            f"representing global diaspora communities, slowly pulsing. "
            f"Mid-shot: the network brightens and pulses faster around nodes labelled "
            f"conceptually (not literal text) to suggest {name.lower()}, conveying that this "
            f"topic currently represents {sov}% of monitored conversation and is {direction}. "
            f"Closing shot: a calm, wide pull-back revealing the full network, ending on the "
            f"RTIFN/NDIP brand mark. "
            f"Visual style: {mood}. Clean, modern, institutional -- not literal news footage, "
            f"no real identifiable people or events depicted."
        )

        caption_suggestion = (
            f"This week, {name} is shaping diaspora conversation ({sov}% share of voice). "
            f"NDIP tracks what matters to our community, in real time."
        )

        prompts.append({
            "narrative": name,
            "share_of_voice": sov,
            "sentiment": sentiment,
            "momentum_direction": direction,
            "video_prompt": prompt_text,
            "suggested_caption": caption_suggestion,
            "suggested_hashtags": "#NDIP #RTIFN #DiasporaVoice #NigeriaDiaspora",
        })

    if gnei_data:
        score = gnei_data.get("gnei_score")
        label = gnei_data.get("gnei_label")
        if score is not None:
            gnei_prompt = (
                f"A 12-second clip visualising global Nigerian diaspora engagement. "
                f"Opening: a stylised world map with Nigeria at the centre, soft glowing "
                f"lines reaching out to diaspora hub cities (London, Houston, Toronto, Dubai). "
                f"Mid-shot: a circular progress meter animates upward to {score} out of 100, "
                f"labelled conceptually as the Global Nigerian Engagement Index, current "
                f"status \"{label}\". Closing: lines pulse once more in unison before settling, "
                f"ending on the RTIFN/NDIP brand mark. "
                f"Visual style: clean, modern, data-forward, calm confident pacing. "
                f"No real identifiable people or footage."
            )
            prompts.append({
                "narrative": "Global Nigerian Engagement Index",
                "gnei_score": score,
                "gnei_label": label,
                "video_prompt": gnei_prompt,
                "suggested_caption": f"Our Global Nigerian Engagement Index this period: {score}/100 ({label}). Tracking how the world engages with Nigeria.",
                "suggested_hashtags": "#NDIP #RTIFN #GNEI #DiasporaEngagement",
            })

    return prompts
