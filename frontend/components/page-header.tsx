interface PageHeaderProps {
  emoji: string;
  title: string;
  subtitle?: string;
}

/** Consistent warm page header used across every route. */
export function PageHeader({ emoji, title, subtitle }: PageHeaderProps) {
  return (
    <header className="mb-6">
      <div className="flex items-center gap-3">
        <span
          className="grid h-12 w-12 place-items-center rounded-2xl bg-pastel-peach text-2xl shadow-soft"
          aria-hidden
        >
          {emoji}
        </span>
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight">{title}</h1>
          {subtitle ? (
            <p className="text-sm text-muted-foreground">{subtitle}</p>
          ) : null}
        </div>
      </div>
    </header>
  );
}
