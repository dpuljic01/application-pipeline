"use client";

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Plus, X } from "lucide-react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { getProfile, updateProfile, ApiError } from "@/lib/api";
import type { LanguageEntry, Profile, Seniority } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { TagInput } from "@/components/ui/tag-input";

const SENIORITY_OPTIONS: { value: Seniority; label: string }[] = [
  { value: "junior", label: "Junior" },
  { value: "mid", label: "Mid" },
  { value: "senior", label: "Senior" },
  { value: "staff", label: "Staff" },
];

export default function ProfilePage() {
  const router = useRouter();
  const { idToken, isAuthenticated, isRestoring, logout } = useAuth();

  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  const [yearsExperience, setYearsExperience] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [languages, setLanguages] = useState<LanguageEntry[]>([]);
  const [targetSeniorities, setTargetSeniorities] = useState<Seniority[]>([]);
  const [minSalary, setMinSalary] = useState("");
  const [idealSalary, setIdealSalary] = useState("");
  const [homeLocation, setHomeLocation] = useState("");

  function handleUnauthorized() {
    logout();
    router.push("/login");
  }

  function applyProfile(p: Profile) {
    setProfile(p);
    setYearsExperience(p.years_experience?.toString() ?? "");
    setSkills(p.skills);
    setLanguages(p.languages);
    setTargetSeniorities(p.target_seniorities);
    setMinSalary(p.min_salary_chf?.toString() ?? "");
    setIdealSalary(p.ideal_salary_chf?.toString() ?? "");
    setHomeLocation(p.home_location ?? "");
  }

  useEffect(() => {
    if (isRestoring) return;
    if (!isAuthenticated) {
      router.push("/login");
      return;
    }
    if (!idToken) return;

    getProfile(idToken)
      .then(applyProfile)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          handleUnauthorized();
        }
      })
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idToken, isAuthenticated, isRestoring]);

  function toggleSeniority(value: Seniority) {
    setTargetSeniorities((prev) =>
      prev.includes(value) ? prev.filter((s) => s !== value) : [...prev, value],
    );
  }

  function updateLanguage(index: number, field: keyof LanguageEntry, value: string) {
    setLanguages((prev) =>
      prev.map((entry, i) => (i === index ? { ...entry, [field]: value } : entry)),
    );
  }

  function addLanguage() {
    setLanguages((prev) => [...prev, { language: "", level: "" }]);
  }

  function removeLanguage(index: number) {
    setLanguages((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!idToken) return;
    setSaving(true);
    setError(null);
    setSaved(false);
    try {
      const updated = await updateProfile(idToken, {
        years_experience: yearsExperience ? Number(yearsExperience) : null,
        skills,
        languages: languages.filter((l) => l.language.trim() && l.level.trim()),
        target_seniorities: targetSeniorities,
        min_salary_chf: minSalary ? Number(minSalary) : null,
        ideal_salary_chf: idealSalary ? Number(idealSalary) : null,
        home_location: homeLocation || null,
      });
      applyProfile(updated);
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        handleUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not save profile");
    } finally {
      setSaving(false);
    }
  }

  if (isRestoring || !isAuthenticated) {
    return null;
  }

  const isIncomplete =
    profile &&
    (skills.length === 0 || targetSeniorities.length === 0 || !minSalary || !idealSalary);

  return (
    <div className="flex min-h-screen flex-col bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="size-3.5" />
            Back to applications
          </Link>
        </div>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-6 py-8">
        {loading ? (
          <p className="text-xs text-muted-foreground">Loading…</p>
        ) : (
          <Card className="rounded-[3px]">
            <CardHeader>
              <CardTitle className="text-lg">Your profile</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                Used to score how well each job posting fits you. Nothing here is
                shared — it only powers the match score on your applications.
              </p>
            </CardHeader>
            <CardContent>
              {isIncomplete && (
                <p className="mb-4 rounded-[3px] border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
                  Complete your profile for more accurate match scores.
                </p>
              )}

              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="space-y-1.5">
                  <Label htmlFor="years_experience" className="text-xs text-muted-foreground">
                    Years of experience
                  </Label>
                  <Input
                    id="years_experience"
                    type="number"
                    min={0}
                    max={60}
                    value={yearsExperience}
                    onChange={(e) => setYearsExperience(e.target.value)}
                    className="max-w-32"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Skills</Label>
                  <TagInput
                    value={skills}
                    onChange={setSkills}
                    placeholder="Type a skill and press Enter…"
                  />
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">Languages</Label>
                  <div className="space-y-2">
                    {languages.map((entry, index) => (
                      <div key={index} className="flex items-center gap-2">
                        <Input
                          value={entry.language}
                          onChange={(e) => updateLanguage(index, "language", e.target.value)}
                          placeholder="Language"
                          className="flex-1"
                        />
                        <Input
                          value={entry.level}
                          onChange={(e) => updateLanguage(index, "level", e.target.value)}
                          placeholder="Level (e.g. B1, fluent)"
                          className="flex-1"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => removeLanguage(index)}
                          aria-label="Remove language"
                        >
                          <X className="size-3.5" />
                        </Button>
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={addLanguage}
                    >
                      <Plus className="size-3" />
                      Add language
                    </Button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label className="text-xs text-muted-foreground">
                    Target seniority
                  </Label>
                  <div className="flex gap-2">
                    {SENIORITY_OPTIONS.map((option) => {
                      const active = targetSeniorities.includes(option.value);
                      return (
                        <Button
                          key={option.value}
                          type="button"
                          variant={active ? "default" : "outline"}
                          size="sm"
                          className="h-7 text-xs"
                          onClick={() => toggleSeniority(option.value)}
                        >
                          {option.label}
                        </Button>
                      );
                    })}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-1.5">
                    <Label htmlFor="min_salary" className="text-xs text-muted-foreground">
                      Absolute floor (CHF)
                    </Label>
                    <Input
                      id="min_salary"
                      type="number"
                      min={0}
                      step={1000}
                      value={minSalary}
                      onChange={(e) => setMinSalary(e.target.value)}
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="ideal_salary" className="text-xs text-muted-foreground">
                      Ideal (CHF)
                    </Label>
                    <Input
                      id="ideal_salary"
                      type="number"
                      min={0}
                      step={1000}
                      value={idealSalary}
                      onChange={(e) => setIdealSalary(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="home_location" className="text-xs text-muted-foreground">
                    Home location
                  </Label>
                  <Input
                    id="home_location"
                    value={homeLocation}
                    onChange={(e) => setHomeLocation(e.target.value)}
                    placeholder="e.g. Thalwil, Switzerland"
                  />
                  <p className="text-xs text-muted-foreground">
                    Only used to let the AI flag onsite commute concerns in a
                    job&apos;s fit assessment — never geocoded or used for anything
                    else.
                  </p>
                </div>

                {error && (
                  <p className="font-mono text-xs text-destructive" role="alert">
                    {error}
                  </p>
                )}

                <div className="flex items-center gap-3 border-t border-border pt-4">
                  <Button type="submit" disabled={saving}>
                    {saving ? "Saving…" : "Save profile"}
                  </Button>
                  {saved && !saving && (
                    <p className="text-xs text-muted-foreground">Saved.</p>
                  )}
                </div>
              </form>
            </CardContent>
          </Card>
        )}
      </main>
    </div>
  );
}
