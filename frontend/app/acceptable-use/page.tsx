import { PolicyPage, Section } from "@/components/PolicyPage";
import { CONTACT_EMAIL, SITE_NAME } from "@/lib/site";

export const metadata = { title: "Acceptable Use Policy" };

export default function AcceptableUsePage() {
  return (
    <PolicyPage title="Acceptable Use Policy">
      <Section heading="1. The short version">
        <p>
          Use {SITE_NAME} to research problems and build things. Don&apos;t
          abuse the platform, don&apos;t bulk-extract our library, and
          don&apos;t use our content to mislead anyone about patent rights.
        </p>
      </Section>

      <Section heading="2. You may">
        <p>
          Use blueprints, build plans, and master prompts in your own projects
          and commercial products; share individual blueprints with teammates;
          build applications on the developer API within your plan&apos;s
          limits; and export data (Enterprise) for internal analysis.
        </p>
      </Section>

      <Section heading="3. You may not">
        <p>
          <strong className="text-ink">Bulk extraction &amp; resale.</strong>{" "}
          Scrape the site, circumvent rate limits or plan quotas, share or
          resell API keys, or redistribute the blueprint library (or a
          substantial part of it) as a dataset, mirror, or competing service.
        </p>
        <p>
          <strong className="text-ink">Misrepresentation.</strong> Present our
          content as legal advice; use Freedom-to-Operate reports to claim a
          legal guarantee to third parties, investors, or courts; or
          misrepresent expired-patent material as your own patented invention.
        </p>
        <p>
          <strong className="text-ink">Platform abuse.</strong> Probe or
          disrupt the service, attempt to access other users&apos; data,
          reverse-engineer non-public APIs, submit malicious content, or use
          the service to violate any law, including export controls and
          sanctions.
        </p>
        <p>
          <strong className="text-ink">Account sharing.</strong> A subscription
          is for one person (Enterprise seats per your agreement). Don&apos;t
          share logins to circumvent per-seat pricing.
        </p>
      </Section>

      <Section heading="4. API-specific rules">
        <p>
          Keep API keys server-side and secret; rotate them if exposed.
          Respect HTTP 429 responses with backoff. Cache responsibly for your
          own application&apos;s use, not to reconstruct the library. We may
          throttle or revoke keys that degrade service for others.
        </p>
      </Section>

      <Section heading="5. Enforcement">
        <p>
          Violations may lead to throttling, feature suspension, or account
          termination, with notice where practicable. Where a violation is
          also unlawful, we may report it. To report abuse or ask whether a
          use is okay: {CONTACT_EMAIL}.
        </p>
      </Section>
    </PolicyPage>
  );
}
