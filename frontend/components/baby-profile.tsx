"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ApiError, api, type Gender, type Infant } from "@/lib/api";

const todayISO = () => new Date().toISOString().slice(0, 10);

function ageLabel(birthDate: string): string {
  const b = new Date(`${birthDate}T00:00:00`);
  const now = new Date();
  let months =
    (now.getFullYear() - b.getFullYear()) * 12 + (now.getMonth() - b.getMonth());
  if (now.getDate() < b.getDate()) months -= 1;
  if (months < 0) months = 0;
  const y = Math.floor(months / 12);
  const m = months % 12;
  if (y === 0) return `${m} month${m === 1 ? "" : "s"} old`;
  if (m === 0) return `${y} year${y === 1 ? "" : "s"} old`;
  return `${y}y ${m}m old`;
}

const GENDER_EMOJI: Record<Gender, string> = {
  male: "👦",
  female: "👧",
  other: "👶",
};

/** Register or edit the child's profile (name, birth date, gender). */
export function BabyProfile({
  infant,
  onChanged,
}: {
  infant: Infant | null;
  onChanged: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [gender, setGender] = useState<Gender>("female");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const showForm = editing || infant === null;

  function startEdit() {
    setName(infant?.name ?? "");
    setBirthDate(infant?.birth_date ?? "");
    setGender(infant?.gender ?? "female");
    setError(null);
    setEditing(true);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !birthDate) return;
    setLoading(true);
    setError(null);
    try {
      const payload = { name: name.trim(), birth_date: birthDate, gender };
      if (infant) await api.updateInfant(infant.id, payload);
      else await api.registerInfant(payload);
      setEditing(false);
      onChanged();
    } catch (err: unknown) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.message}`
          : err instanceof Error
            ? err.message
            : "Unknown error"
      );
    } finally {
      setLoading(false);
    }
  }

  // --- Saved profile (summary) ---
  if (!showForm && infant) {
    return (
      <Card className="mb-4 border-none bg-pastel-peach/60">
        <CardContent className="flex items-center gap-3 p-4">
          <span
            className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl bg-card/70 text-2xl shadow-soft"
            aria-hidden
          >
            {GENDER_EMOJI[infant.gender]}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-lg font-extrabold">{infant.name}</p>
            <p className="text-xs text-muted-foreground">
              {ageLabel(infant.birth_date)} · born {infant.birth_date}
            </p>
          </div>
          <Button variant="outline" size="sm" onClick={startEdit}>
            Edit
          </Button>
        </CardContent>
      </Card>
    );
  }

  // --- Registration / edit form ---
  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle>{infant ? "Edit baby profile" : "Add your baby 👶"}</CardTitle>
        <CardDescription>
          {infant
            ? "Update your child's details."
            : "Enter your child's details to personalize growth, vaccines & tips."}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-3">
          <label className="block text-xs font-semibold">
            Baby&apos;s name
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Ali"
              className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>

          <label className="block text-xs font-semibold">
            Date of birth
            <input
              type="date"
              value={birthDate}
              max={todayISO()}
              onChange={(e) => setBirthDate(e.target.value)}
              className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
          </label>

          <label className="block text-xs font-semibold">
            Gender
            <select
              value={gender}
              onChange={(e) => setGender(e.target.value as Gender)}
              className="mt-1 w-full rounded-xl border border-border bg-card/80 px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              <option value="female">Girl 👧</option>
              <option value="male">Boy 👦</option>
              <option value="other">Prefer not to say 👶</option>
            </select>
          </label>

          {error ? <p className="text-xs text-primary">{error}</p> : null}

          <div className="flex gap-2 pt-1">
            <Button type="submit" disabled={loading || !name.trim() || !birthDate}>
              {loading ? "Saving…" : infant ? "Save changes" : "Save baby"}
            </Button>
            {infant ? (
              <Button
                type="button"
                variant="ghost"
                onClick={() => setEditing(false)}
              >
                Cancel
              </Button>
            ) : null}
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
