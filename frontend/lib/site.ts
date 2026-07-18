// Site-wide constants. Editable content (footer address, contact email,
// links) lives in the database (site_settings) and is managed from the admin
// panel — see lib/settings.ts. Nothing user-facing is hardcoded here beyond
// safe defaults.
export const SITE_NAME = "ProblemForge";
export const OPERATOR_NAME = "Zawadi Technologies LLC";
export const SITE_URL = (
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"
).replace(/\/$/, "");
export const POLICIES_EFFECTIVE_DATE = "July 17, 2026";

export const POLICY_LINKS = [
  { href: "/terms", label: "Terms of Service" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/refunds", label: "Billing & Refunds" },
  { href: "/acceptable-use", label: "Acceptable Use" },
  { href: "/disclaimer", label: "Disclaimer" },
] as const;
