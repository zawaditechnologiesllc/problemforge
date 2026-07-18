import { OPERATOR_NAME, SITE_NAME } from "@/lib/site";

export interface FooterSettings {
  company_name: string;
  product_name: string;
  tagline: string;
  address: string;
  contact_email: string;
  links: { label: string; url: string }[];
}

export const DEFAULT_FOOTER: FooterSettings = {
  company_name: OPERATOR_NAME,
  product_name: SITE_NAME,
  tagline:
    "Validated startup problems mined from expired, public-domain patents across 20 regions.",
  address: "",
  contact_email: "",
  links: [],
};

const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

/** Server-side fetch of admin-editable site settings, with safe fallbacks. */
export async function getSiteSettings(): Promise<{ footer: FooterSettings }> {
  try {
    const response = await fetch(`${API_URL}/api/v1/site-settings`, {
      next: { revalidate: 300 },
    });
    if (!response.ok) return { footer: DEFAULT_FOOTER };
    const data = await response.json();
    return { footer: { ...DEFAULT_FOOTER, ...(data?.footer ?? {}) } };
  } catch {
    return { footer: DEFAULT_FOOTER };
  }
}

/** Contact line for policy pages: real email when configured, neutral fallback otherwise. */
export function contactLine(footer: FooterSettings): string {
  return footer.contact_email || "the contact address published in our site footer";
}
