"use client";

import { PageHeader } from "@/components/page-header";
import { Card, CardContent } from "@/components/ui/card";
import { api, type VaccineDueItem, type VaccineStatus } from "@/lib/api";
import { useFetch } from "@/lib/hooks";

const STATUS_STYLES: Record<
  VaccineStatus,
  { badge: string; dot: string; label: string }
> = {
  OVERDUE: {
    badge: "bg-red-100 text-red-700 border border-red-200",
    dot: "bg-red-500",
    label: "Overdue",
  },
  UPCOMING: {
    badge: "bg-amber-100 text-amber-800 border border-amber-200",
    dot: "bg-amber-500",
    label: "Upcoming",
  },
  SAFE: {
    badge: "bg-emerald-100 text-emerald-700 border border-emerald-200",
    dot: "bg-emerald-500",
    label: "On track",
  },
};

function ageGroupLabel(months: number): string {
  if (months === 0) return "At birth";
  return `${months} months`;
}

function formatDue(iso: string): string {
  const d = new Date(`${iso}T00:00:00`);
  return d.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/** Personalized, birthday-relative checklist for one infant. */
function InfantChecklist({ infantId }: { infantId: string }) {
  const schedule = useFetch(() => api.infantVaccinations(infantId), [infantId]);

  if (schedule.loading) {
    return <p className="text-sm text-muted-foreground">Loading schedule…</p>;
  }
  if (schedule.error || !schedule.data) {
    return (
      <p className="text-sm text-primary">
        Couldn&apos;t load the schedule: {schedule.error}
      </p>
    );
  }

  // Group doses by milestone age for a tidy checklist.
  const groups = new Map<number, VaccineDueItem[]>();
  for (const item of schedule.data.items) {
    const bucket = groups.get(item.age_months) ?? [];
    bucket.push(item);
    groups.set(item.age_months, bucket);
  }

  return (
    <div className="space-y-5">
      {[...groups.entries()].map(([months, items]) => (
        <section key={months}>
          <h2 className="mb-2 px-1 text-sm font-bold text-muted-foreground">
            {ageGroupLabel(months)}
          </h2>
          <ul className="space-y-3">
            {items.map((item) => {
              const s = STATUS_STYLES[item.status];
              return (
                <li key={item.code}>
                  <Card>
                    <CardContent className="flex items-center gap-3 p-4">
                      <span
                        className={`h-2.5 w-2.5 shrink-0 rounded-full ${s.dot}`}
                        aria-hidden
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate font-semibold">{item.name}</p>
                        <p className="text-xs text-muted-foreground">
                          Due {formatDue(item.due_date)} · {item.code}
                        </p>
                      </div>
                      <span
                        className={`shrink-0 rounded-full px-3 py-1 text-xs font-bold ${s.badge}`}
                      >
                        {s.label}
                      </span>
                    </CardContent>
                  </Card>
                </li>
              );
            })}
          </ul>
        </section>
      ))}
    </div>
  );
}

export default function VaccinesPage() {
  // Personalized due dates require a registered infant; fall back to the
  // generic reference schedule when none exists yet.
  const infants = useFetch(() => api.listInfants(), []);
  const firstInfant = infants.data?.[0];

  return (
    <main>
      <PageHeader
        emoji="💉"
        title="Vaccines"
        subtitle={
          firstInfant
            ? `Personalized plan for ${firstInfant.name}.`
            : "The recommended immunization schedule."
        }
      />

      {infants.loading ? (
        <p className="text-sm text-muted-foreground">Loading…</p>
      ) : infants.error ? (
        <p className="text-sm text-primary">
          Couldn&apos;t reach the API: {infants.error}
        </p>
      ) : firstInfant ? (
        <InfantChecklist infantId={firstInfant.id} />
      ) : (
        <GenericSchedule />
      )}
    </main>
  );
}

/** Fallback list shown before any infant is registered. */
function GenericSchedule() {
  const schedule = useFetch(() => api.vaccineSchedule(), []);

  return (
    <div>
      <Card className="mb-4 border-none bg-pastel-sky">
        <CardContent className="p-4 text-sm">
          Register a child to see personalized due dates. Showing the general
          schedule for now.
        </CardContent>
      </Card>

      {schedule.loading ? (
        <p className="text-sm text-muted-foreground">Loading schedule…</p>
      ) : schedule.error ? (
        <p className="text-sm text-primary">
          Couldn&apos;t load the schedule: {schedule.error}
        </p>
      ) : (
        <ul className="space-y-3">
          {schedule.data?.map((v) => (
            <li key={v.code}>
              <Card>
                <CardContent className="flex items-center justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <p className="truncate font-semibold">{v.name}</p>
                    <p className="text-xs text-muted-foreground">{v.code}</p>
                  </div>
                  <span className="shrink-0 rounded-full bg-pastel-butter px-3 py-1 text-xs font-bold">
                    {v.recommended_age_months === 0
                      ? "At birth"
                      : `${v.recommended_age_months} mo`}
                  </span>
                </CardContent>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
