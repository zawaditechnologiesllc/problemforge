"use client";

import { Cpu, Stethoscope, Wrench } from "lucide-react";
import clsx from "clsx";

const categories = [
  { value: "software", label: "Software Problems", icon: Cpu },
  { value: "mechanical", label: "Mechanical Upgrades", icon: Wrench },
  { value: "medical", label: "Medical Friction", icon: Stethoscope },
] as const;

export function CategoryPills({
  active,
  onSelect,
}: {
  active?: string | null;
  onSelect: (domain: string | null) => void;
}) {
  return (
    <div className="flex flex-wrap items-center justify-center gap-2.5">
      {categories.map(({ value, label, icon: Icon }) => {
        const selected = active === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onSelect(selected ? null : value)}
            className={clsx(
              "inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition",
              selected
                ? "border-accent/60 bg-accent-soft text-accent"
                : "border-edge text-muted hover:border-muted hover:text-ink"
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        );
      })}
    </div>
  );
}
