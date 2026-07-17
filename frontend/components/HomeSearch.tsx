"use client";

import { useRouter } from "next/navigation";
import { CategoryPills } from "@/components/CategoryPills";
import { SearchBar } from "@/components/SearchBar";

export function HomeSearch() {
  const router = useRouter();
  return (
    <div className="space-y-5">
      <SearchBar />
      <CategoryPills
        active={null}
        onSelect={(domain) =>
          router.push(domain ? `/browse?domain=${domain}` : "/browse")
        }
      />
    </div>
  );
}
