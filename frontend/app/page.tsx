"use client";

import Link from "next/link";

import { BabyProfile } from "@/components/baby-profile";
import { GrowthChart } from "@/components/growth-chart";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

function ageInMonths(birthDate: string): number {
  const b = new Date(`${birthDate}T00:00:00`);
  const now = new Date();
  let m =
    (now.getFullYear() - b.getFullYear()) * 12 + (now.getMonth() - b.getMonth());
  if (now.getDate() < b.getDate()) m -= 1;
  return Math.max(0, m);
}

export default function DashboardPage() {
  const infants = useFetch(() => api.listInfants(), []);
  const baby = infants.data?.[0] ?? null;

  const milestones = useFetch(() => api.listMilestones(), []);
  // The next milestone is the first one at or after the baby's current age.
  const ageMonths = baby ? ageInMonths(baby.birth_date) : 0;
  const sorted = [...(milestones.data ?? [])].sort(
    (a, b) => a.typical_age_months - b.typical_age_months
  );
  const nextMilestone =
    sorted.find((m) => m.typical_age_months >= ageMonths) ??
    sorted[sorted.length - 1];

  return (
    <main>
      <PageHeader
        emoji="📈"
        title="Hi there 👋"
        subtitle={
          baby
            ? `Here's how ${baby.name} is doing today.`
            : "Let's set up your baby's profile."
        }
      />

      {/* Baby profile — register / edit */}
      <BabyProfile infant={baby} onChanged={infants.refetch} />

      {/* Growth trajectory vs WHO percentile bands */}
      <GrowthChart infant={baby} />

      {/* Next milestone (live from backend) */}
      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Next milestone</CardTitle>
          <CardDescription>
            {milestones.loading
              ? "Loading…"
              : milestones.error
                ? `Couldn't reach the API (${milestones.error})`
                : nextMilestone
                  ? `${nextMilestone.category} · ~${nextMilestone.typical_age_months} mo`
                  : "No milestones found"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-base font-semibold">
            {nextMilestone?.title ?? "—"}
          </p>
        </CardContent>
      </Card>

      {/* Primary calls to action */}
      <section className="grid grid-cols-2 gap-3">
        <Button asChild variant="secondary" className="h-20 flex-col gap-1">
          <Link href="/milestones">
            <span className="text-2xl">👶</span>
            <span>Milestones</span>
          </Link>
        </Button>
        <Button asChild variant="secondary" className="h-20 flex-col gap-1">
          <Link href="/vaccines">
            <span className="text-2xl">💉</span>
            <span>Vaccines</span>
          </Link>
        </Button>
        <Button asChild className="col-span-2 h-16">
          <Link href="/assistant">
            <span className="text-xl">💬</span>
            <span>Ask the AI Assistant</span>
          </Link>
        </Button>
      </section>
    </main>
  );
}
