"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

interface NavItem {
  href: string;
  label: string;
  emoji: string;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Dashboard", emoji: "📈" },
  { href: "/milestones", label: "Milestones", emoji: "👶" },
  { href: "/vaccines", label: "Vaccines", emoji: "💉" },
  { href: "/assistant", label: "AI Assistant", emoji: "💬" },
];

/**
 * Mobile-first floating navigation bar.
 *
 * Pinned to the bottom of the viewport on small screens (thumb-friendly),
 * floating as a rounded pill. The links cover the four primary surfaces.
 */
export function FloatingNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Primary"
      className="fixed inset-x-0 bottom-4 z-50 mx-auto w-[min(28rem,calc(100%-1.5rem))]"
    >
      <ul className="flex items-stretch justify-between gap-1 rounded-full border border-border/60 bg-card/80 p-1.5 shadow-float backdrop-blur-lg">
        {NAV_ITEMS.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);

          return (
            <li key={item.href} className="flex-1">
              <Link
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "flex flex-col items-center gap-0.5 rounded-full px-2 py-2 text-[0.65rem] font-medium transition-all",
                  active
                    ? "bg-primary text-primary-foreground shadow-soft"
                    : "text-muted-foreground hover:bg-muted"
                )}
              >
                <span className="text-lg leading-none" aria-hidden>
                  {item.emoji}
                </span>
                <span className="leading-none">{item.label}</span>
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
