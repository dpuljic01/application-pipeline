"use client";

import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { X } from "lucide-react";
import { Input } from "@/components/ui/input";

export function TagInput({
  value,
  onChange,
  placeholder,
}: {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
}) {
  const [draft, setDraft] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function commitDraft() {
    const tag = draft.trim();
    if (tag && !value.includes(tag)) {
      onChange([...value, tag]);
    }
    setDraft("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter" || event.key === ",") {
      event.preventDefault();
      commitDraft();
      // Mobile keyboards often show "Next" and jump focus to the next form
      // field on Enter, unlike desktop's plain keydown - force focus back
      // so typing another tag works the same way on both.
      requestAnimationFrame(() => inputRef.current?.focus());
    } else if (event.key === "Backspace" && draft === "" && value.length > 0) {
      onChange(value.slice(0, -1));
    }
  }

  function removeTag(tag: string) {
    onChange(value.filter((t) => t !== tag));
  }

  return (
    <div className="flex min-h-8 flex-wrap items-center gap-1.5 rounded-lg border border-input px-2 py-1.5">
      {value.map((tag) => (
        <span
          key={tag}
          className="inline-flex items-center gap-1 rounded-[3px] border border-border bg-muted px-1.5 py-0.5 font-mono text-[11px] text-foreground"
        >
          {tag}
          <button
            type="button"
            onClick={() => removeTag(tag)}
            aria-label={`Remove ${tag}`}
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-3" />
          </button>
        </span>
      ))}
      <Input
        ref={inputRef}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={handleKeyDown}
        onBlur={commitDraft}
        enterKeyHint="enter"
        placeholder={value.length === 0 ? placeholder : undefined}
        className="h-6 w-auto min-w-[100px] flex-1 border-none px-1 shadow-none focus-visible:ring-0"
      />
    </div>
  );
}
