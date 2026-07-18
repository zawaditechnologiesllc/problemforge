// Site-wide constants used by the policy pages and footer.
// TODO before launch: set the real contact email and operating entity below,
// and have counsel review the policy pages (they are a solid starting point,
// not legal advice).
export const SITE_NAME = "ProblemForge";
export const OPERATOR_NAME = "ProblemForge"; // your registered company name
export const CONTACT_EMAIL = "support@problemforge.example"; // replace with a real inbox
export const POLICIES_EFFECTIVE_DATE = "July 17, 2026";

export const POLICY_LINKS = [
  { href: "/terms", label: "Terms of Service" },
  { href: "/privacy", label: "Privacy Policy" },
  { href: "/refunds", label: "Billing & Refunds" },
  { href: "/acceptable-use", label: "Acceptable Use" },
  { href: "/disclaimer", label: "Disclaimer" },
] as const;
