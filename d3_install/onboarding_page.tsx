"use client";
/**
 * NDIP Phase D.3 — Member Onboarding Wizard (D3.10)
 * File: frontend/src/app/onboarding/page.tsx
 *
 * 10-step first-login wizard:
 *   1. Verify email
 *   2. Password confirmed (already set at registration — shown as complete)
 *   3. Upload profile photo
 *   4. Complete profile (occupation, bio)
 *   5. Select Nigeria State
 *   6. Select LGA
 *   7. Select Ward
 *   8. Confirm Chapter
 *   9. Accept platform terms
 *  10. Go to dashboard
 *
 * Displays completion percentage and step status.
 * Communicates with /api/v2/auth/onboarding and /api/v2/auth/onboarding/step.
 */

import React, { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface OnboardingState {
  member_id: string;
  current_step: number;
  email_verified: boolean;
  password_set: boolean;
  photo_uploaded: boolean;
  profile_completed: boolean;
  state_selected: boolean;
  lga_selected: boolean;
  ward_selected: boolean;
  chapter_confirmed: boolean;
  terms_accepted: boolean;
  wizard_completed: boolean;
  completion_pct: number;
}

interface Step {
  number: number;
  key: keyof OnboardingState;
  label: string;
  description: string;
}

const STEPS: Step[] = [
  { number: 1,  key: "email_verified",    label: "Verify Email",       description: "Confirm your email address to secure your account." },
  { number: 2,  key: "password_set",      label: "Password",           description: "Your password was set during registration." },
  { number: 3,  key: "photo_uploaded",    label: "Profile Photo",      description: "Upload a clear photo for your member profile." },
  { number: 4,  key: "profile_completed", label: "Complete Profile",   description: "Add your occupation and a short biography." },
  { number: 5,  key: "state_selected",    label: "Select State",       description: "Choose your state of origin in Nigeria." },
  { number: 6,  key: "lga_selected",      label: "Select LGA",         description: "Choose your Local Government Area." },
  { number: 7,  key: "ward_selected",     label: "Select Ward",        description: "Choose your ward." },
  { number: 8,  key: "chapter_confirmed", label: "Confirm Chapter",    description: "Confirm your diaspora chapter assignment." },
  { number: 9,  key: "terms_accepted",    label: "Accept Terms",       description: "Read and accept the NDIP platform terms." },
  { number: 10, key: "wizard_completed",  label: "Go to Dashboard",    description: "Your profile is complete. Access the platform." },
];

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("access_token") || sessionStorage.getItem("access_token");
}

async function apiFetch(path: string, opts: RequestInit = {}): Promise<unknown> {
  const token = getToken();
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers || {}),
    },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error((err as {detail?: string}).detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export default function OnboardingPage() {
  const router = useRouter();
  const [state, setState] = useState<OnboardingState | null>(null);
  const [loading, setLoading] = useState(true);
  const [activeStep, setActiveStep] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Step-specific form state
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [occupation, setOccupation] = useState("");
  const [biography, setBiography] = useState("");
  const [states, setStates] = useState<{id: number; name: string}[]>([]);
  const [lgas, setLgas] = useState<{id: number; name: string}[]>([]);
  const [wards, setWards] = useState<{id: number; name: string}[]>([]);
  const [selectedState, setSelectedState] = useState<number | null>(null);
  const [selectedLga, setSelectedLga] = useState<number | null>(null);
  const [selectedWard, setSelectedWard] = useState<number | null>(null);
  const [termsRead, setTermsRead] = useState(false);

  const loadState = useCallback(async () => {
    try {
      const resp = await apiFetch("/api/v2/auth/onboarding") as {data: OnboardingState};
      setState(resp.data);
      // Advance to first incomplete step
      const firstIncomplete = STEPS.find(s => !resp.data[s.key]);
      setActiveStep(firstIncomplete?.number ?? 10);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load onboarding state");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadState();
    // Load Nigerian states
    apiFetch("/api/v2/geography/states")
      .then(data => setStates((data as {id: number; name: string}[])))
      .catch(() => {});
  }, [loadState]);

  useEffect(() => {
    if (selectedState) {
      apiFetch(`/api/v2/geography/lgas/${selectedState}`)
        .then(data => setLgas((data as {id: number; name: string}[])))
        .catch(() => {});
    }
  }, [selectedState]);

  useEffect(() => {
    if (selectedLga) {
      apiFetch(`/api/v2/geography/wards/${selectedLga}`)
        .then(data => setWards((data as {id: number; name: string}[])))
        .catch(() => {});
    }
  }, [selectedLga]);

  const advanceStep = async (stepKey: string) => {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/v2/auth/onboarding/step", {
        method: "POST",
        body: JSON.stringify({ step: stepKey }),
      });
      await loadState();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Step update failed");
    } finally {
      setBusy(false);
    }
  };

  const handleEmailVerify = async () => {
    setBusy(true);
    setError(null);
    try {
      if (!state) return;
      await apiFetch("/api/v2/auth/verify-email/request", {
        method: "POST",
        body: JSON.stringify({ member_id: state.member_id }),
      });
      setError(null);
      alert("Verification email sent. Check your inbox, then return to this page.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to send verification email");
    } finally {
      setBusy(false);
    }
  };

  const handlePhotoUpload = async () => {
    if (!photoFile) { setError("Please select a photo"); return; }
    setBusy(true);
    setError(null);
    try {
      const formData = new FormData();
      formData.append("file", photoFile);
      formData.append("asset_type", "image");
      formData.append("entity_type", "member_profile");
      const token = getToken();
      const res = await fetch(`${API}/api/v2/members/photo`, {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });
      if (!res.ok) throw new Error("Upload failed");
      await advanceStep("photo_uploaded");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Photo upload failed");
    } finally {
      setBusy(false);
    }
  };

  const handleProfileSave = async () => {
    if (!occupation.trim() || !biography.trim()) {
      setError("Please fill in occupation and biography"); return;
    }
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/api/v2/members/me", {
        method: "PUT",
        body: JSON.stringify({ occupation, biography }),
      });
      await advanceStep("profile_completed");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Profile save failed");
    } finally {
      setBusy(false);
    }
  };

  const handleGeographySave = async (stepKey: string, value: unknown) => {
    setBusy(true);
    setError(null);
    try {
      const fieldMap: Record<string, string> = {
        state_selected: "state_of_origin_id",
        lga_selected: "lga_of_origin_id",
      };
      if (fieldMap[stepKey]) {
        await apiFetch("/api/v2/members/me", {
          method: "PUT",
          body: JSON.stringify({ [fieldMap[stepKey]]: value }),
        });
      }
      await advanceStep(stepKey);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const handleComplete = async () => {
    await advanceStep("wizard_completed");
    router.push("/dashboard");
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-blue-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading your onboarding status...</p>
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center text-red-600">
          <p>Failed to load onboarding. Please refresh the page.</p>
          {error && <p className="mt-2 text-sm">{error}</p>}
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-3xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Welcome to NDIP</h1>
          <p className="text-gray-500 mt-2">Complete your member profile to access the platform</p>
        </div>

        {/* Progress bar */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Profile Completion</span>
            <span className="text-sm font-bold text-blue-600">{state.completion_pct}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all duration-500"
              style={{ width: `${state.completion_pct}%` }}
            />
          </div>
        </div>

        {/* Step list */}
        <div className="space-y-3 mb-6">
          {STEPS.map((step) => {
            const completed = state[step.key] as boolean;
            const isCurrent = step.number === activeStep;
            return (
              <div
                key={step.number}
                className={`bg-white rounded-xl shadow-sm border-2 transition-all ${
                  isCurrent ? "border-blue-500" : completed ? "border-green-400" : "border-gray-200"
                }`}
              >
                <div
                  className="flex items-center gap-4 p-4 cursor-pointer"
                  onClick={() => !completed && setActiveStep(step.number)}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0 ${
                    completed ? "bg-green-500" : isCurrent ? "bg-blue-600" : "bg-gray-300"
                  }`}>
                    {completed ? "✓" : step.number}
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold text-gray-800">{step.label}</div>
                    <div className="text-sm text-gray-500">{step.description}</div>
                  </div>
                  {completed && <span className="text-green-600 text-sm font-medium">Complete</span>}
                  {isCurrent && !completed && <span className="text-blue-600 text-sm font-medium">Active</span>}
                </div>

                {/* Step content */}
                {isCurrent && !completed && (
                  <div className="border-t border-gray-100 p-4">
                    {error && (
                      <div className="mb-3 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                        {error}
                      </div>
                    )}

                    {/* Step 1: Email verification */}
                    {step.number === 1 && (
                      <div>
                        <p className="text-sm text-gray-600 mb-3">
                          Click below to receive a verification email. After clicking the link in the email, return here and refresh the page.
                        </p>
                        <button
                          onClick={handleEmailVerify}
                          disabled={busy}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Sending..." : "Send Verification Email"}
                        </button>
                        <button
                          onClick={loadState}
                          className="ml-3 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
                        >
                          I have verified — Refresh
                        </button>
                      </div>
                    )}

                    {/* Step 2: Password (auto-complete) */}
                    {step.number === 2 && (
                      <div>
                        <p className="text-sm text-gray-600 mb-3">Your password was set when you registered.</p>
                        <button
                          onClick={() => advanceStep("password_set")}
                          disabled={busy}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          Continue
                        </button>
                      </div>
                    )}

                    {/* Step 3: Photo upload */}
                    {step.number === 3 && (
                      <div className="space-y-3">
                        <input
                          type="file"
                          accept="image/jpeg,image/png,image/webp"
                          onChange={e => setPhotoFile(e.target.files?.[0] || null)}
                          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700"
                        />
                        {photoFile && <p className="text-sm text-gray-600">Selected: {photoFile.name}</p>}
                        <button
                          onClick={handlePhotoUpload}
                          disabled={busy || !photoFile}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Uploading..." : "Upload Photo"}
                        </button>
                        <button
                          onClick={() => advanceStep("photo_uploaded")}
                          disabled={busy}
                          className="ml-3 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
                        >
                          Skip for now
                        </button>
                      </div>
                    )}

                    {/* Step 4: Profile */}
                    {step.number === 4 && (
                      <div className="space-y-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Occupation</label>
                          <input
                            type="text"
                            value={occupation}
                            onChange={e => setOccupation(e.target.value)}
                            placeholder="e.g. Software Engineer, Doctor, Entrepreneur"
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Biography</label>
                          <textarea
                            value={biography}
                            onChange={e => setBiography(e.target.value)}
                            placeholder="Tell us a bit about yourself..."
                            rows={3}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                          />
                        </div>
                        <button
                          onClick={handleProfileSave}
                          disabled={busy}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Saving..." : "Save Profile"}
                        </button>
                      </div>
                    )}

                    {/* Step 5: State */}
                    {step.number === 5 && (
                      <div className="space-y-3">
                        <select
                          onChange={e => setSelectedState(Number(e.target.value))}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        >
                          <option value="">Select your state of origin</option>
                          {states.map(s => <option key={s.id} value={s.id}>{s.name}</option>)}
                        </select>
                        <button
                          onClick={() => selectedState && handleGeographySave("state_selected", selectedState)}
                          disabled={busy || !selectedState}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Saving..." : "Confirm State"}
                        </button>
                      </div>
                    )}

                    {/* Step 6: LGA */}
                    {step.number === 6 && (
                      <div className="space-y-3">
                        <select
                          onChange={e => setSelectedLga(Number(e.target.value))}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                          disabled={!selectedState}
                        >
                          <option value="">Select your LGA</option>
                          {lgas.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
                        </select>
                        <button
                          onClick={() => selectedLga && handleGeographySave("lga_selected", selectedLga)}
                          disabled={busy || !selectedLga}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Saving..." : "Confirm LGA"}
                        </button>
                      </div>
                    )}

                    {/* Step 7: Ward */}
                    {step.number === 7 && (
                      <div className="space-y-3">
                        <select
                          onChange={e => setSelectedWard(Number(e.target.value))}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                          disabled={!selectedLga}
                        >
                          <option value="">Select your ward</option>
                          {wards.map(w => <option key={w.id} value={w.id}>{w.name}</option>)}
                        </select>
                        <button
                          onClick={() => advanceStep("ward_selected")}
                          disabled={busy || !selectedWard}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "Saving..." : "Confirm Ward"}
                        </button>
                        <button
                          onClick={() => advanceStep("ward_selected")}
                          disabled={busy}
                          className="ml-3 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-200"
                        >
                          Skip for now
                        </button>
                      </div>
                    )}

                    {/* Step 8: Chapter */}
                    {step.number === 8 && (
                      <div>
                        <p className="text-sm text-gray-600 mb-3">
                          Your chapter assignment is based on your location. Contact your Chapter Admin if it is incorrect.
                        </p>
                        <button
                          onClick={() => advanceStep("chapter_confirmed")}
                          disabled={busy}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "..." : "Confirm Chapter"}
                        </button>
                      </div>
                    )}

                    {/* Step 9: Terms */}
                    {step.number === 9 && (
                      <div className="space-y-3">
                        <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 h-40 overflow-y-auto text-sm text-gray-700">
                          <p className="font-semibold mb-2">NDIP Platform Terms of Use</p>
                          <p className="mb-2">By using the National & Diaspora Intelligence Platform (NDIP), you agree to:</p>
                          <ul className="list-disc list-inside space-y-1">
                            <li>Provide accurate and truthful information in your profile and reports</li>
                            <li>Not share your login credentials with any other person</li>
                            <li>Not use the platform for any unlawful or unauthorised purpose</li>
                            <li>Respect the privacy and confidentiality of other members</li>
                            <li>Report any suspected security issues to the platform administrator</li>
                            <li>Accept that your engagement data may be used for diaspora impact analysis</li>
                            <li>Comply with all applicable laws in your country of residence</li>
                          </ul>
                          <p className="mt-2">These terms are subject to change. Continued use of the platform constitutes acceptance of any revised terms.</p>
                        </div>
                        <label className="flex items-center gap-2 cursor-pointer">
                          <input
                            type="checkbox"
                            checked={termsRead}
                            onChange={e => setTermsRead(e.target.checked)}
                            className="w-4 h-4 text-blue-600"
                          />
                          <span className="text-sm text-gray-700">I have read and accept the NDIP Platform Terms of Use</span>
                        </label>
                        <button
                          onClick={() => advanceStep("terms_accepted")}
                          disabled={busy || !termsRead}
                          className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
                        >
                          {busy ? "..." : "Accept & Continue"}
                        </button>
                      </div>
                    )}

                    {/* Step 10: Complete */}
                    {step.number === 10 && (
                      <div className="text-center py-4">
                        <div className="text-5xl mb-4">🎉</div>
                        <p className="text-gray-700 mb-4 font-medium">Your profile is {state.completion_pct}% complete.</p>
                        <p className="text-sm text-gray-500 mb-6">You can complete any remaining steps from your profile page at any time.</p>
                        <button
                          onClick={handleComplete}
                          disabled={busy}
                          className="px-8 py-3 bg-blue-600 text-white rounded-xl text-base font-semibold hover:bg-blue-700 disabled:opacity-50 shadow-md"
                        >
                          {busy ? "..." : "Go to Dashboard →"}
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
