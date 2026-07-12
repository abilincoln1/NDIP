"use client";
/**
 * NDIP V7 — AI Copilot
 * Persistent intelligent assistant accessible from every page.
 * Context-aware: knows the current route, user role, and page data.
 * Role-aware: adapts language for executive, analyst, admin, campaign, diaspora users.
 */
import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname } from "next/navigation";
import {
  MessageSquare, X, Send, Loader, ChevronDown, ChevronUp,
  Brain, ArrowRight, Lightbulb, BookOpen, Minimize2, Maximize2
} from "lucide-react";
import api from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────
interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

interface SuggestedAction {
  label: string;
  route?: string;
}

interface CopilotResponse {
  response: string;
  suggested_actions: string[];
  related_pages: string[];
}

// ── Suggested questions per page ──────────────────────────────────────────────
const PAGE_SUGGESTIONS: Record<string, string[]> = {
  "/leadership-pack": [
    "What should I look at first?",
    "Explain the top narrative",
    "What action should I take today?",
    "Why is this risk flagged?",
    "Summarise today's intelligence",
  ],
  "/situation-room": [
    "What changed today?",
    "Explain narrative momentum",
    "Which narrative is most urgent?",
    "What is causing the sentiment shift?",
  ],
  "/strategic-outcome": [
    "Explain the Opportunity Score",
    "Which opportunity should I act on first?",
    "What is the Readiness Score?",
    "Why is this stakeholder ranked here?",
  ],
  "/watchlist": [
    "What needs my attention today?",
    "Explain the priority tiers",
    "What is a Critical watchlist item?",
  ],
  "/gnei": [
    "What does the GNEI score mean?",
    "Is diaspora engagement improving?",
    "What should I do if GNEI is falling?",
  ],
  "/election-centre": [
    "What electoral risks should I know about?",
    "Explain the days-to-election metric",
    "Which narratives are swinging?",
  ],
  "/decision-quality": [
    "How accurate are NDIP recommendations?",
    "What is the platform learning score?",
    "Should I trust this recommendation?",
  ],
};

const DEFAULT_SUGGESTIONS = [
  "What should I look at first?",
  "Explain this dashboard",
  "What changed today?",
  "What action should I take?",
  "How does confidence work?",
];

// ── Helper ────────────────────────────────────────────────────────────────────
function getPageSuggestions(pathname: string): string[] {
  const exact = PAGE_SUGGESTIONS[pathname];
  if (exact) return exact;
  // Partial match
  for (const [route, suggestions] of Object.entries(PAGE_SUGGESTIONS)) {
    if (pathname.startsWith(route)) return suggestions;
  }
  return DEFAULT_SUGGESTIONS;
}

function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Main Component ────────────────────────────────────────────────────────────
interface AICopilotProps {
  pageData?: Record<string, any>;  // Key metrics from the current page
  userRole?: string;
}

export default function AICopilot({ pageData, userRole = "executive" }: AICopilotProps) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = getPageSuggestions(pathname || "/");

  // Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Focus input when opened
  useEffect(() => {
    if (open && !minimized) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [open, minimized]);

  // Welcome message when first opened
  useEffect(() => {
    if (open && messages.length === 0) {
      const pageName = getPageName(pathname || "/");
      setMessages([{
        role: "assistant",
        content: `Hello! I'm the NDIP Copilot. I can see you're on the **${pageName}**.\n\nI can help you understand what you're looking at, explain any metric, recommend next actions, or answer questions about the platform. What would you like to know?`,
        timestamp: new Date(),
      }]);
    }
  }, [open]);

  const getPageName = (path: string): string => {
    const names: Record<string, string> = {
      "/leadership-pack": "Leadership Pack",
      "/situation-room": "Situation Room",
      "/strategic-outcome": "SOI Dashboard",
      "/watchlist": "Leadership Watchlist",
      "/national-pulse": "National Pulse",
      "/gnei": "GNEI Dashboard",
      "/election-centre": "Election Intelligence",
      "/decision-quality": "Decision Support",
      "/intelligence": "Entity Intelligence",
      "/": "Overview Dashboard",
    };
    for (const [route, name] of Object.entries(names)) {
      if (path.startsWith(route) && route !== "/") return name;
    }
    return names[path] || "Dashboard";
  };

  const sendMessage = useCallback(async (messageText: string) => {
    if (!messageText.trim() || loading) return;

    const userMessage: Message = {
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setShowSuggestions(false);

    try {
      const response = await api.post<CopilotResponse>("/copilot/ask", {
        message: messageText,
        page_route: pathname || "/",
        role: userRole,
        data_context: pageData || {},
      });

      const assistantMessage: Message = {
        role: "assistant",
        content: response.data.response,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: "I'm having trouble connecting right now. Please try again in a moment. If the problem persists, check with your administrator that the AI Copilot is configured.",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  }, [loading, pathname, userRole, pageData]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const clearHistory = () => {
    setMessages([]);
    setShowSuggestions(true);
  };

  // Keyboard shortcut: press C to open/close
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "c" && (e.metaKey || e.ctrlKey) && !e.shiftKey) {
        // Don't intercept Ctrl+C copy
        return;
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      {/* Trigger button — always visible */}
      <button
        onClick={() => { setOpen(true); setMinimized(false); }}
        className={`fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full shadow-lg transition-all duration-200 ${
          open
            ? "bg-slate-700 text-white"
            : "bg-teal-600 hover:bg-teal-500 text-white"
        }`}
        title="Open AI Copilot (Ctrl+K)"
        aria-label="Open AI Copilot"
      >
        <Brain size={18} />
        <span className="text-sm font-medium hidden sm:block">
          {open ? "Copilot open" : "Ask Copilot"}
        </span>
      </button>

      {/* Copilot panel */}
      {open && (
        <div
          className={`fixed bottom-20 right-6 z-50 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl transition-all duration-200 flex flex-col ${
            minimized ? "w-72 h-14" : "w-96 h-[600px] max-h-[80vh]"
          }`}
          role="dialog"
          aria-label="NDIP AI Copilot"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700 rounded-t-2xl bg-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-teal-600 flex items-center justify-center">
                <Brain size={14} className="text-white" />
              </div>
              <div>
                <span className="text-sm font-semibold text-white">NDIP Copilot</span>
                <div className="flex items-center gap-1">
                  <div className="w-1.5 h-1.5 rounded-full bg-teal-400" />
                  <span className="text-xs text-teal-400">Active on {getPageName(pathname || "/")}</span>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setMinimized(!minimized)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition-colors"
                title={minimized ? "Expand" : "Minimise"}
              >
                {minimized ? <Maximize2 size={14} /> : <Minimize2 size={14} />}
              </button>
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-slate-700 transition-colors"
                title="Close"
              >
                <X size={14} />
              </button>
            </div>
          </div>

          {!minimized && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 scrollbar-thin scrollbar-track-slate-800 scrollbar-thumb-slate-600">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] rounded-xl px-3 py-2.5 text-sm leading-relaxed ${
                        message.role === "user"
                          ? "bg-teal-600 text-white"
                          : "bg-slate-800 text-slate-100 border border-slate-700"
                      }`}
                    >
                      {/* Render markdown bold */}
                      <p
                        dangerouslySetInnerHTML={{
                          __html: message.content
                            .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                            .replace(/\n/g, "<br/>"),
                        }}
                      />
                      <div className={`text-xs mt-1.5 ${message.role === "user" ? "text-teal-200" : "text-slate-500"}`}>
                        {formatTime(message.timestamp)}
                      </div>
                    </div>
                  </div>
                ))}

                {/* Loading indicator */}
                {loading && (
                  <div className="flex justify-start">
                    <div className="bg-slate-800 border border-slate-700 rounded-xl px-3 py-2.5 flex items-center gap-2">
                      <Loader size={14} className="text-teal-400 animate-spin" />
                      <span className="text-sm text-slate-400">Copilot is thinking...</span>
                    </div>
                  </div>
                )}

                {/* Suggestions */}
                {showSuggestions && messages.length <= 1 && !loading && (
                  <div className="space-y-2">
                    <p className="text-xs text-slate-500 font-medium">Suggested questions:</p>
                    {suggestions.map((suggestion, i) => (
                      <button
                        key={i}
                        onClick={() => sendMessage(suggestion)}
                        className="w-full text-left text-xs px-3 py-2 rounded-lg bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white hover:border-teal-600 transition-all duration-150 flex items-center gap-2"
                      >
                        <Lightbulb size={11} className="text-amber-400 shrink-0" />
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Clear history */}
              {messages.length > 2 && (
                <div className="px-4 pb-1">
                  <button
                    onClick={clearHistory}
                    className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
                  >
                    Clear conversation
                  </button>
                </div>
              )}

              {/* Input */}
              <div className="px-4 py-3 border-t border-slate-700">
                <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 focus-within:border-teal-600 transition-colors">
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything about this dashboard..."
                    className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 outline-none"
                    disabled={loading}
                  />
                  <button
                    onClick={() => sendMessage(input)}
                    disabled={!input.trim() || loading}
                    className="p-1.5 rounded-lg bg-teal-600 hover:bg-teal-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                    title="Send message"
                  >
                    <Send size={12} className="text-white" />
                  </button>
                </div>
                <p className="text-xs text-slate-600 mt-1.5 text-center">
                  Responses are based on current platform data only
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
