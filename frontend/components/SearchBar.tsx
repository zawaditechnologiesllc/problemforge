"use client";

import { Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

export function SearchBar({
  initialQuery = "",
  autoFocus = false,
  onSearch,
}: {
  initialQuery?: string;
  autoFocus?: boolean;
  onSearch?: (q: string) => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState(initialQuery);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const q = query.trim();
    if (onSearch) onSearch(q);
    else router.push(q ? `/browse?q=${encodeURIComponent(q)}` : "/browse");
  }

  return (
    <form onSubmit={submit} className="relative flex w-full items-center">
      <Search className="pointer-events-none absolute left-4 text-muted" size={18} />
      <input
        className="input rounded-xl py-3.5 pl-11 pr-28 text-[15px]"
        placeholder="Search by human frustration (e.g., medical billing delays, physical inventory)..."
        value={query}
        autoFocus={autoFocus}
        onChange={(event) => setQuery(event.target.value)}
        aria-label="Search blueprints"
      />
      <button type="submit" className="btn-accent absolute right-1.5 h-9 px-4 py-0">
        Search
      </button>
    </form>
  );
}
