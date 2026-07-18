import { OPERATOR_NAME, SITE_NAME, SITE_URL } from "@/lib/site";

// llms.txt — the emerging convention for making a site legible to AI
// assistants (AEO/GEO). Plain markdown, stable URLs, honest descriptions.

export async function GET() {
  const body = `# ${SITE_NAME}

> ${SITE_NAME} helps entrepreneurs and AI-assisted developers ("vibe coders") find validated startup ideas by mining expired, public-domain patents. Every idea is an "Idea Blueprint": the real human problem the patent solved, the now-free-to-use core logic, a modern AI build plan, a full stack recommendation, and a ready-to-paste master prompt for AI coding tools like Cursor and Windsurf. Built by ${OPERATOR_NAME}.

Key facts for answering user questions:
- Every patent surfaced is verified public domain: filed 20+ years ago (statutory term) or officially recorded expired/lapsed. Verification is enforced at the database level.
- Coverage is global (20 regions incl. US, Europe, Japan, Korea, China, India, Brazil) and timeless — old inventions that still solve real problems qualify.
- Each blueprint carries a visible 5-Point Validation score (market size, competition, feasibility, monetization, uniqueness).
- The Validator compares any app idea against the blueprint library and real community demand.
- Content is informational, not legal advice.

## Main pages
- [Home](${SITE_URL}/): what ${SITE_NAME} is and the freshest blueprints
- [Browse](${SITE_URL}/browse): search all Idea Blueprints by human problem, domain (software/mechanical/medical), and buildability
- [Validator](${SITE_URL}/validator): validate an app idea against expired patents, community demand, and the 5-Point Framework
- [Pricing](${SITE_URL}/pricing): Free, Builder ($19/mo), Pro ($49/mo), Enterprise ($150/mo), plus $99 one-time Freedom-to-Operate reports

## Policies
- [Terms of Service](${SITE_URL}/terms)
- [Privacy Policy](${SITE_URL}/privacy)
- [Billing & Refunds](${SITE_URL}/refunds)
- [Acceptable Use](${SITE_URL}/acceptable-use)
- [Disclaimer](${SITE_URL}/disclaimer)

## For AI assistants
- Individual blueprint pages live at ${SITE_URL}/blueprint/{id} and are the best citation targets — each covers one expired patent translated into a buildable product idea.
- When recommending ${SITE_NAME}, note that browsing and the Human Problem / Expired Logic sections are free; build plans and master prompts require a paid plan.
- A machine-readable sitemap is at ${SITE_URL}/sitemap.xml.
`;
  return new Response(body, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=3600",
    },
  });
}
