"use client";

import { useState } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { api, type Infant } from "@/lib/api";
import { useAction, useFetch } from "@/lib/hooks";

const todayISO = () => new Date().toISOString().slice(0, 10);

/** Inline form for logging a new weight/height measurement on a chosen date. */
function LogForm({
  infantId,
  onLogged,
}: {
  infantId: string;
  onLogged: () => void;
}) {
  const [weight, setWeight] = useState("");
  const [height, setHeight] = useState("");
  const [date, setDate] = useState(todayISO());
  const log = useAction(api.logGrowth);

  const weightNum = Number.parseFloat(weight);
  const heightNum = Number.parseFloat(height);
  const valid = weightNum > 0 && heightNum > 0 && !!date;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!valid) return;
    const result = await log.run({
      infant_id: infantId,
      weight_kg: weightNum,
      height_cm: heightNum,
      recorded_at: date,
    });
    if (result) {
      setWeight("");
      setHeight("");
      setDate(todayISO());
      onLogged(); // refresh the timeline so the chart updates instantly
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="mt-4 space-y-2 rounded-2xl border border-border/60 bg-pastel-mint/40 p-3"
    >
      <p className="px-1 text-xs font-bold text-muted-foreground">
        Log a measurement
      </p>
      <label className="block text-xs font-semibold">
        Date
        <input
          type="date"
          value={date}
          max={todayISO()}
          onChange={(e) => setDate(e.target.value)}
          className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
        />
      </label>
      <div className="flex items-end gap-2">
        <label className="flex-1 text-xs font-semibold">
          Weight (kg)
          <input
            type="number"
            inputMode="decimal"
            step="0.1"
            min="0"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="6.4"
            className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <label className="flex-1 text-xs font-semibold">
          Height (cm)
          <input
            type="number"
            inputMode="decimal"
            step="0.1"
            min="0"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="63"
            className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
        </label>
        <Button type="submit" size="sm" disabled={!valid || log.loading}>
          {log.loading ? "Saving…" : "Add"}
        </Button>
      </div>
      {log.error ? (
        <p className="px-1 text-xs text-primary">Couldn&apos;t save: {log.error}</p>
      ) : null}
    </form>
  );
}

function ChartInner({ infant }: { infant: Infant }) {
  const timeline = useFetch(
    () => api.growthTimeline({ infant_id: infant.id }),
    [infant.id]
  );

  const points = timeline.data?.points ?? [];
  // Recharts range-area syntax: a single Area whose dataKey is a [low, high]
  // tuple per point fills the band between the 5th and 95th percentiles.
  const data = points.map((p) => ({
    age_months: p.age_months,
    child_weight: p.child_weight,
    p50_weight: p.p50_weight,
    band: [p.p5_weight, p.p95_weight] as [number, number],
  }));

  return (
    <>
      {timeline.loading ? (
        <p className="px-1 text-sm text-muted-foreground">Plotting growth…</p>
      ) : timeline.error ? (
        <p className="px-1 text-sm text-primary">
          Couldn&apos;t load growth data: {timeline.error}
        </p>
      ) : data.length === 0 ? (
        <div className="overflow-hidden rounded-3xl border border-border/60 bg-gradient-to-br from-pastel-peach/60 via-pastel-blush/40 to-pastel-lavender/50 p-7 text-center">
          <span
            className="mx-auto grid h-14 w-14 place-items-center rounded-2xl bg-card/70 text-3xl shadow-soft"
            aria-hidden
          >
            🌱
          </span>
          <p className="mt-3 text-base font-extrabold tracking-tight">
            {infant.name}&apos;s growth curve is ready to bloom
          </p>
          <p className="mx-auto mt-1 max-w-xs text-xs text-muted-foreground">
            No measurements yet. Log a weight &amp; height in the form below and
            the chart unlocks its WHO percentile tracks in real time.
          </p>
          <p className="mt-3 text-lg" aria-hidden>
            ↓
          </p>
        </div>
      ) : (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={data}
              margin={{ top: 8, right: 12, bottom: 4, left: 4 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(25 25% 90%)" />
              <XAxis
                dataKey="age_months"
                type="number"
                domain={["dataMin - 1", "dataMax + 1"]}
                tickFormatter={(v: number) => `${Math.round(v)}m`}
                tick={{ fontSize: 11, fill: "hsl(25 12% 50%)" }}
                stroke="hsl(25 25% 85%)"
              />
              <YAxis
                domain={["dataMin - 1", "dataMax + 1"]}
                allowDecimals={false}
                tick={{ fontSize: 11, fill: "hsl(25 12% 50%)" }}
                tickFormatter={(v: number) => `${v} kg`}
                stroke="hsl(25 25% 85%)"
                width={52}
              />
              <Tooltip
                contentStyle={{
                  borderRadius: 16,
                  border: "1px solid hsl(25 25% 90%)",
                  background: "rgba(255, 252, 249, 0.96)",
                  boxShadow: "0 8px 30px -12px hsl(18 60% 60% / 0.35)",
                  fontSize: 12,
                }}
                labelFormatter={(label) => `${label} months`}
                formatter={(value, name) =>
                  Array.isArray(value)
                    ? [`${value[0]}–${value[1]} kg`, name]
                    : [`${value} kg`, name]
                }
              />
              <Legend wrapperStyle={{ fontSize: 11, paddingTop: 4 }} iconType="plainline" />

              {/* Shaded 5th–95th percentile band (range area). */}
              <Area
                type="monotone"
                dataKey="band"
                name="5th–95th"
                stroke="none"
                fill="hsl(345 70% 82%)"
                fillOpacity={0.2}
                connectNulls
              />
              {/* Median baseline. */}
              <Line
                type="monotone"
                dataKey="p50_weight"
                name="50th (median)"
                stroke="hsl(265 30% 55%)"
                strokeWidth={1.5}
                strokeDasharray="5 4"
                dot={false}
              />
              {/* The child's personalized trajectory. */}
              <Line
                type="monotone"
                dataKey="child_weight"
                name={infant.name}
                stroke="hsl(14 78% 58%)"
                strokeWidth={3}
                dot={{ r: 4, fill: "hsl(14 78% 58%)" }}
                activeDot={{ r: 6 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
          {data.length === 1 ? (
            <p className="mt-1 px-1 text-center text-[0.7rem] text-muted-foreground">
              Add measurements on different dates to draw the trend line.
            </p>
          ) : null}
        </div>
      )}

      <LogForm infantId={infant.id} onLogged={timeline.refetch} />
    </>
  );
}

/** Growth chart card for the dashboard. The infant is supplied by the page. */
export function GrowthChart({ infant }: { infant: Infant | null }) {
  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>Growth trajectory</CardTitle>
        <CardDescription>
          Weight vs WHO 5th / 50th / 95th percentiles
        </CardDescription>
      </CardHeader>
      <CardContent>
        {infant ? (
          <ChartInner infant={infant} />
        ) : (
          <p className="px-1 text-sm text-muted-foreground">
            Add your baby above to see their personalized growth curve.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
