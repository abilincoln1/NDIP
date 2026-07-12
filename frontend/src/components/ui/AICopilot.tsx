"use client";
/**
 * NDIP V8 — AI Copilot Component
 * EB-007: Role resolved from /onboarding/state API (user's actual role, not hardcoded)
 * EB-012: pageData injected via CopilotContext (individual pages call useCopilotData)
 * EB-015: Conversation history displayed and persisted across turns
 * EB-020: Rate limit feedback shown to user
 */
import { useState, useEffect, useRef, useCallback, createContext, useContext } from "react";
import { usePathname } from "next/navigation";
import { MessageSquare, X, Send, Loader, Brain, Lightbulb, Minimize2, Maximize2, Trash2, History } from "lucide-react";
import api from "@/lib/api";

// ── Copilot Context — allows individual pages to inject data ─────────────
interface CopilotContextType {
  pageData: Record<string, any>;
  setPageData: (data: Record<string, any>) => void;
}

const CopilotContext = createContext<CopilotContextType>({
  pageData: {},
  setPageData: () => {},
});

export function CopilotProvider({ children }: { children: React.ReactNode }) {
  const [pageData, setPageData] = useState<Record<string, any>>({});
  return (
    <CopilotContext.Provider value={{ pageData, setPageData }}>
      {children}
    </CopilotContext.Provider>
  );
}

/**
 * EB-012: Hook for individual page components to inject their data into the Copilot.
 * Usage in a page component:
 *   const { setPageData } = useCopilotData();
 *   useEffect(() => {
 *     if (narratives && watchlist) {
 *       setPageData({ narratives, watchlist_critical_count, engagement_index, confidence });
 *     }
 *   }, [narratives, watchlist]);
 */
export function useCopilotData() {
  return useContext(CopilotContext);
}

// ── Suggested questions per page ──────────────────────────────────────────
const PAGE_SUGGESTIONS: Record<string, string[]> = {
  "/leadership-pack": [
    "What should I look at first today?",
    "Explain the top narrative",
    "What changed since yesterday?",
    "What action should I take today?",
    "Why is this risk flagged?",
  ],
  "/situation-room": [
    "What changed today?",
    "Which narrative is most urgent?",
    "Explain narrative momentum",
    "What is causing this sentiment shift?",
  ],
  "/strategic-outcome": [
    "Which opportunity should I act on first?",
    "Explain the Opportunity Score",
    "Show evidence for this score",
    "Why is this stakeholder ranked here?",
  ],
  "/watchlist": [
    "What needs my attention today?",
    "What is new since yesterday?",
    "Explain the priority tiers",
    "Which Critical items are new?",
  ],
  "/gnei": [
    "What does the GNEI score mean?",
    "Is diaspora engagement improving?",
    "What changed since yesterday?",
  ],
};

const DEFAULT_SUGGESTIONS = [
  "What should I look at first?",
  "What changed today?",
  "Explain this dashboard",
  "What action should I take?",
];

// ── Types ─────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  hadHistoricalData?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────
function getPageName(path: string): string {
  const names: Record<string, string> = {
    "/leadership-pack": "Leadership Pack",
    "/situation-room": "Situation Room",
    "/strategic-outcome": "SOI Dashboard",
    "/watchlist": "Leadership Watchlist",
    "/national-pulse": "National Pulse",
    "/gnei": "GNEI Dashboard",
    "/election-centre": "Election Intelligence",
    "/": "Overview Dashboard",
  };
  for (const [route, name] of Object.entries(names)) {
    if (path.startsWith(route) && route !== "/") return name;
  }
  return names[path] || "Dashboard";
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Main Component ────────────────────────────────────────────────────────
export default function AICopilot() {
  const pathname = usePathname();
  if (pathname === "/login") return null;
  const { pageData } = useContext(CopilotContext);

  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [userRole, setUserRole] = useState<string>("executive");
  const [rateLimited, setRateLimited] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = PAGE_SUGGESTIONS[pathname || "/"] || DEFAULT_SUGGESTIONS;

  // EB-007: Resolve role from user's actual onboarding state
  useEffect(() => {
    api.get("/onboarding/state")
      .then(r => {
        if (r.data?.role) setUserRole(r.data.role);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (open && !minimized) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open, minimized]);

  // Welcome message on first open
  useEffect(() => {
    if (open && messages.length === 0) {
      const pageName = getPageName(pathname || "/");
      const hasData = Object.keys(pageData).length > 0;
      setMessages([{
        role: "assistant",
        content: `Hello. I'm the NDIP Copilot. I can see you're on the **${pageName}**.\n\n${hasData ? "I have your current dashboard data loaded — I can give you specific insights about what you're seeing right now." : "Ask me to explain any metric, recommend next actions, or compare today with yesterday."}\n\nWhat would you like to know?`,
        timestamp: new Date(),
      }]);
    }
  }, [open]);

  // Reset suggestions when page changes
  useEffect(() => {
    setShowSuggestions(true);
  }, [pathname]);

  const sendMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim() || loading || rateLimited) return;

    const userMsg: Message = { role: "user", content: messageText, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setLoading(true);
    setShowSuggestions(false);

    try {
      const response = await api.post("/copilot/ask", {
        message: messageText,
        page_route: pathname || "/",
        // EB-007: role resolved server-side from auth — no need to pass it
        data_context: Object.keys(pageData).length > 0 ? pageData : undefined,
      });

      const assistantMsg: Message = {
        role: "assistant",
        content: response.data.response,
        timestamp: new Date(),
        hadHistoricalData: response.data.had_historical_data,
      };
      setMessages(prev => [...prev, assistantMsg]);

    } catch (error: any) {
      if (error?.response?.status === 429) {
        setRateLimited(true);
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "You've reached the Copilot usage limit (20 requests per hour). Please try again in a little while.",
          timestamp: new Date(),
        }]);
      } else {
        setMessages(prev => [...prev, {
          role: "assistant",
          content: "I'm having trouble connecting right now. Please try again in a moment.",
          timestamp: new Date(),
        }]);
      }
    } finally {
      setLoading(false);
    }
  }, [loading, pathname, pageData, rateLimited]);

  const clearHistory = async () => {
    try {
      await api.post("/copilot/clear-history");
    } catch {}
    setMessages([]);
    setShowSuggestions(true);
    setRateLimited(false);
  };

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape" && open) setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  const hasPageData = Object.keys(pageData).length > 0;

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => { setOpen(true); setMinimized(false); }}
        className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full shadow-lg transition-all duration-200 ${
          open ? "bg-slate-700 text-white" : "bg-teal-600 hover:bg-teal-500 text-white"
        }`}
        title="Open AI Copilot"
        aria-label="Open AI Copilot"
      >
        <Brain size={18} />
        <span className="text-sm font-medium hidden sm:block">
          {open ? "Copilot open" : "Ask Copilot"}
        </span>
        {hasPageData && !open && (
          <span className="w-2 h-2 bg-teal-300 rounded-full animate-pulse" title="Live data loaded" />
        )}
      </button>

      {/* Panel */}
      {open && (
        <div className={`fixed bottom-20 right-6 z-50 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl transition-all duration-200 flex flex-col ${
          minimized ? "w-72 h-14" : "w-96 h-[600px] max-h-[80vh]"
        }`}>
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 rounded-t-2xl bg-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center">
                <Brain size={14} className="text-white" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white">NDIP Copilot</span>
                <div className="flex items-center gap-1.5">
                  <div className={`w-1.5 h-1.5 rounded-full ${hasPageData ? "bg-teal-400" : "bg-slate-500"}`} />
                  <span className="text-xs text-slate-400">
                    {getPageName(pathname || "/")}
                    {hasPageData && " · data loaded"}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button onClick={() => setMinimized(!minimized)} className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition-colors">
                {minimized ? <Maximize2 size={14} /> : <Minimize2 size={14} />}
              </button>
              <button onClick={() => setOpen(false)} className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition-colors">
                <X size={14} />
              </button>
            </div>
          </div>

          {!minimized && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
                {messages.map((message, index) => (
                  <div key={index} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] rounded-xl px-3 py-2.5 text-sm leading-relaxed ${
                      message.role === "user"
                        ? "bg-teal-600 text-white"
                        : "bg-slate-800 text-slate-100 border border-slate-700"
                    }`}>
                      <p dangerouslySetInnerHTML={{
                        __html: message.content
                          .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                          .replace(/\n/g, "<br/>"),
                      }} />
                      <div className={`text-xs mt-1.5 flex items-center gap-1.5 ${message.role === "user" ? "text-teal-200" : "text-slate-500"}`}>
                        {formatTime(message.timestamp)}
                        {message.hadHistoricalData && (
                          <span className="flex items-center gap-0.5 text-teal-400">
                            <History size={10} />
                            historical data
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 flex items-center gap-2">
                      <Loader size={14} className="text-teal-400 animate-spin" />
                      <span className="text-sm text-slate-400">Thinking...</span>
                    </div>
                  </div>
                )}

                {showSuggestions && messages.length <= 1 && !loading && (
                  <div className="space-y-2">
                    <p className="text-xs text-slate-500 font-medium">Suggested questions:</p>
                    {suggestions.map((s, i) => (
                      <button key={i} onClick={() => sendMessage(s)}
                        className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-teal-600 transition-all flex items-center gap-2">
                        <Lightbulb size={11} className="text-amber-400 shrink-0" />
                        {s}
                      </button>
                    ))}
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Footer actions */}
              {messages.length > 2 && (
                <div className="px-4 pb-1">
                  <button onClick={clearHistory} className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1">
                    <Trash2 size={10} />
                    Clear conversation
                  </button>
                </div>
              )}

              {/* Input */}
              <div className="px-4 py-3 border-t border-slate-700">
                {rateLimited ? (
                  <p className="text-xs text-amber-400 text-center">Rate limit reached. Resets in 1 hour.</p>
                ) : (
                  <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 focus-within:border-teal-600 transition-colors">
                    <input
                      ref={inputRef}
                      type="text"
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } }}
                      placeholder="Ask about this dashboard..."
                      className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none"
                      disabled={loading}
                    />
                    <button
                      onClick={() => sendMessage(input)}
                      disabled={!input.trim() || loading}
                      className="p-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-40 transition-colors"
                    >
                      <Send size={12} className="text-white" />
                    </button>
                  </div>
                )}
                <p className="text-xs text-slate-600 mt-1.5 text-center">
                  {hasPageData ? "Responding with live dashboard data" : "Responding based on page context"}
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
