"use client";

import { useState } from "react";

import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

const CATEGORY_TONE: Record<string, string> = {
  motor: "bg-pastel-mint",
  social: "bg-pastel-blush",
  language: "bg-pastel-lavender",
  cognitive: "bg-pastel-sky",
};

export default function MilestonesPage() {
  const milestones = useFetch(() => api.listMilestones(), []);
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <main>
      <PageHeader
        emoji="👶"
        title="Milestones"
        subtitle="Tap a milestone for details & tips."
      />

      {milestones.loading ? (
        <p className="text-sm text-muted-foreground">Loading milestones…</p>
      ) : milestones.error ? (
        <p className="text-sm text-primary">
          Couldn&apos;t load milestones: {milestones.error}
        </p>
      ) : (
        <ul className="space-y-3">
          {milestones.data?.map((m) => {
            const open = openId === m.id;
            return (
              <li key={m.id}>
                <Card>
                  {/* Header row — tap to expand */}
                  <button
                    type="button"
                    onClick={() => setOpenId(open ? null : m.id)}
                    aria-expanded={open}
                    className="flex w-full items-center gap-3 p-4 text-left"
                  >
                    <span
                      className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl text-xs font-bold capitalize ${
                        CATEGORY_TONE[m.category] ?? "bg-muted"
                      }`}
                    >
                      {m.category.slice(0, 3)}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate font-semibold">{m.title}</p>
                      <p className="text-xs text-muted-foreground">
                        Around {m.typical_age_months} months · {m.category}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 text-muted-foreground transition-transform ${
                        open ? "rotate-180" : ""
                      }`}
                      aria-hidden
                    >
                      ⌄
                    </span>
                  </button>

                  {/* Expanded detail */}
                  {open ? (
                    <CardContent className="space-y-3 border-t border-border/60 pt-4">
                      <p className="text-sm leading-relaxed">{m.description}</p>
                      {m.tips.length > 0 ? (
                        <div>
                          <p className="mb-1 text-xs font-bold text-muted-foreground">
                            💡 Tips to support it
                          </p>
                          <ul className="list-disc space-y-1 pl-5 text-sm">
                            {m.tips.map((tip) => (
                              <li key={tip}>{tip}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                      <p className="text-[0.7rem] italic text-muted-foreground">
                        Every baby develops at their own pace. If you have
                        concerns, check with your pediatrician.
                      </p>
                    </CardContent>
                  ) : null}
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </main>
  );
}
