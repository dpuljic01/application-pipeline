"use client";

import { useRef, useState } from "react";
import { FileUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { extractProfileFromCv, ApiError } from "@/lib/api";
import type { CVExtraction } from "@/lib/types";

// Fills the profile form from a CV; the parent merges the result into its
// form state and the user still has to press Save. The CV is never stored.
export function CvImport({
  idToken,
  onExtracted,
  onUnauthorized,
}: {
  idToken: string;
  onExtracted: (extraction: CVExtraction) => void;
  onUnauthorized: () => void;
}) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [pasteMode, setPasteMode] = useState(false);
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(input: { file: File } | { text: string }) {
    setLoading(true);
    setError(null);
    try {
      onExtracted(await extractProfileFromCv(idToken, input));
      setText("");
      setPasteMode(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setError(err instanceof Error ? err.message : "Could not read the CV");
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <div className="mb-5 rounded-[3px] border border-dashed border-border px-4 py-3">
      <div className="flex flex-wrap items-center gap-3">
        <input
          ref={fileRef}
          type="file"
          accept="application/pdf,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void run({ file });
          }}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={loading}
          onClick={() => fileRef.current?.click()}
        >
          <FileUp className="size-3.5" />
          {loading ? "Reading CV…" : "Import from CV (PDF)"}
        </Button>
        <button
          type="button"
          onClick={() => setPasteMode((v) => !v)}
          className="text-xs text-muted-foreground underline decoration-border underline-offset-2 hover:text-foreground hover:decoration-foreground"
        >
          {pasteMode ? "Cancel" : "or paste text"}
        </button>
      </div>
      <p className="mt-2 text-xs text-muted-foreground">
        Fills in skills, experience and languages for you to review. The CV
        itself isn&apos;t stored.
      </p>

      {pasteMode && (
        <div className="mt-3 space-y-2">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste your CV here…"
            rows={6}
            className="max-h-64"
          />
          <Button
            type="button"
            size="sm"
            disabled={loading || !text.trim()}
            onClick={() => void run({ text })}
          >
            {loading ? "Reading CV…" : "Extract"}
          </Button>
        </div>
      )}

      {error && (
        <p className="mt-2 font-mono text-xs text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
