"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { ALLOWED_TRANSITIONS } from "@/lib/types";
import type { Application, ApplicationStage } from "@/lib/types";
import { changeApplicationStage, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export function StageChangeMenu({
  application,
  onChanged,
  onUnauthorized,
}: {
  application: Application;
  onChanged: (updated: Application) => void;
  onUnauthorized: () => void;
}) {
  const { idToken } = useAuth();
  const [pending, setPending] = useState(false);
  const nextStages = ALLOWED_TRANSITIONS[application.stage];

  async function handleSelect(stage: ApplicationStage) {
    if (!idToken) return;
    setPending(true);
    try {
      const updated = await changeApplicationStage(idToken, application.id, stage);
      onChanged(updated);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
      }
    } finally {
      setPending(false);
    }
  }

  if (nextStages.length === 0) {
    return (
      <Button
        variant="outline"
        size="sm"
        disabled
        title="Terminal stage — no further transitions"
        className="h-7 text-xs"
      >
        Change stage
        <ChevronDown className="size-3" />
      </Button>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        render={<Button variant="outline" size="sm" disabled={pending} className="h-7 text-xs" />}
      >
        Change stage
        <ChevronDown className="size-3" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {nextStages.map((stage) => (
          <DropdownMenuItem key={stage} onClick={() => handleSelect(stage)}>
            <span className="font-mono text-xs">{stage}</span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
