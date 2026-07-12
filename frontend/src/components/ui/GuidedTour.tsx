"use client";
/**
 * NDIP V7 — Guided Tour Component
 * Contextual step-by-step walkthroughs for each flagship dashboard.
 * Fetches tour steps from the backend. Tracks completion in user state.
 * Launches automatically on first visit; re-launchable from Help menu.
 */
import { useState, useEffect, useCallback } from "react";
import { usePathname } from "next/navigation";
import { ChevronRight, ChevronLeft, X, BookOpen, CheckCircle } from "lucide-react";
import api from "@/lib/api";

interface TourStep {
  step: number;
  element: string;
  title: string;
  content: string;
}

interface Tour {
  id: string;
  title: string;
  steps: TourStep[];
}

interface GuidedTourProps {
  autoLaunch?: boolean;   // Launch automatically if user hasn't completed it
  onComplete?: () => void;
}

export default function GuidedTour({ autoLaunch = true, onComplete }: GuidedTourProps) {
  const pathname = usePathname();
  const [tour, setTour] = useState<Tour | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [visible, setVisible] = useState(false);
  const [completedTours, setCompletedTours] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // Load tour data and user state
  useEffect(() => {
    if (!pathname) return;

    const loadTour = async () => {
      setLoading(true);
      try {
        // Get tour for this page
        const route = pathname.replace(/^\//, "");
        const [tourRes, stateRes] = await Promise.all([
          api.get(`/onboarding/tours/${route}`).catch(() => ({ data: { tour: null } })),
          api.get("/onboarding/state").catch(() => ({ data: { completed_tours: [] } })),
        ]);

        const tourData = tourRes.data?.tour;
        const state = stateRes.data;

        setCompletedTours(state?.completed_tours || []);

        if (tourData) {
          setTour(tourData);
          setCurrentStep(0);

          // Auto-launch if not yet completed
          const alreadyDone = (state?.completed_tours || []).includes(tourData.id);
          if (autoLaunch && !alreadyDone) {
            // Small delay so the page renders first
            setTimeout(() => setVisible(true), 800);
          }
        }
      } catch {
        // Tour load failure is non-critical — page still works
      } finally {
        setLoading(false);
      }
    };

    loadTour();
  }, [pathname, autoLaunch]);

  const handleNext = useCallback(async () => {
    if (!tour) return;
    if (currentStep < tour.steps.length - 1) {
      setCurrentStep(s => s + 1);
    } else {
      // Tour complete
      setVisible(false);
      try {
        await api.post("/onboarding/update", {
          action: "complete_tour",
          value: tour.id,
        });
        setCompletedTours(prev => [...prev, tour.id]);
        onComplete?.();
      } catch {
        // State save failure is non-critical
      }
    }
  }, [tour, currentStep, onComplete]);

  const handlePrev = () => {
    if (currentStep > 0) setCurrentStep(s => s - 1);
  };

  const handleSkip = async () => {
    setVisible(false);
    if (tour) {
      try {
        await api.post("/onboarding/update", {
          action: "complete_tour",
          value: tour.id,
        });
        setCompletedTours(prev => [...prev, tour.id]);
      } catch {}
    }
  };

  const handleRelaunch = () => {
    setCurrentStep(0);
    setVisible(true);
  };

  if (!tour) return null;

  const step = tour.steps[currentStep];
  const isLast = currentStep === tour.steps.length - 1;
  const isCompleted = completedTours.includes(tour.id);

  return (
    <>
      {/* Re-launch button — shown after tour is dismissed/completed */}
      {!visible && isCompleted && (
        <button
          onClick={handleRelaunch}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
          title="Relaunch guided tour"
        >
          <BookOpen size={12} />
          Take tour again
        </button>
      )}

      {/* Launch button — shown before tour is ever taken */}
      {!visible && !isCompleted && (
        <button
          onClick={() => { setCurrentStep(0); setVisible(true); }}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-600/20 border border-blue-600/30 text-blue-300 text-xs font-medium hover:bg-blue-600/30 transition-colors"
        >
          <BookOpen size={12} />
          Take a tour of this page
        </button>
      )}

      {/* Tour overlay */}
      {visible && (
        <div
          className="fixed inset-0 z-50 flex items-end sm:items-center justify-center sm:justify-end p-4 sm:p-8 pointer-events-none"
        >
          {/* Semi-transparent background tint */}
          <div
            className="fixed inset-0 bg-slate-950/40 pointer-events-auto"
            onClick={handleSkip}
          />

          {/* Tour card */}
          <div className="relative z-10 w-full max-w-sm bg-slate-900 border border-blue-600/40 rounded-2xl shadow-2xl pointer-events-auto">
            {/* Progress bar */}
            <div className="h-1 bg-slate-800 rounded-t-2xl overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all duration-300"
                style={{ width: `${((currentStep + 1) / tour.steps.length) * 100}%` }}
              />
            </div>

            {/* Header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-700">
              <div className="flex items-center gap-2">
                <BookOpen size={14} className="text-blue-400" />
                <span className="text-xs font-semibold text-blue-300">{tour.title}</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-500">
                  {currentStep + 1} / {tour.steps.length}
                </span>
                <button
                  onClick={handleSkip}
                  className="p-1 text-slate-500 hover:text-white transition-colors"
                  title="Skip tour"
                >
                  <X size={14} />
                </button>
              </div>
            </div>

            {/* Step content */}
            <div className="px-4 py-4">
              <h3 className="font-semibold text-white mb-2">{step.title}</h3>
              <p className="text-sm text-slate-300 leading-relaxed">{step.content}</p>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between px-4 py-3 border-t border-slate-700">
              <button
                onClick={handlePrev}
                disabled={currentStep === 0}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={14} />
                Previous
              </button>

              <button
                onClick={handleSkip}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                Skip tour
              </button>

              <button
                onClick={handleNext}
                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  isLast
                    ? "bg-teal-600 hover:bg-teal-500 text-white"
                    : "bg-blue-600 hover:bg-blue-500 text-white"
                }`}
              >
                {isLast ? (
                  <>
                    <CheckCircle size={12} />
                    Finish tour
                  </>
                ) : (
                  <>
                    Next
                    <ChevronRight size={12} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// ── Standalone tour launcher hook ─────────────────────────────────────────────
export function useTourLauncher(pageRoute: string) {
  const launchTour = useCallback(async () => {
    // Posts to reset tour completion so it launches again
    try {
      await api.post("/onboarding/update", {
        action: "reset_tour",
        value: pageRoute,
      });
    } catch {}
  }, [pageRoute]);

  return { launchTour };
}
