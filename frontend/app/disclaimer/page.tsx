import { PolicyPage, Section } from "@/components/PolicyPage";
import { SITE_NAME } from "@/lib/site";
import { contactLine, getSiteSettings } from "@/lib/settings";

export const metadata = { title: "Disclaimer" };

export default async function DisclaimerPage() {
  const { footer } = await getSiteSettings();
  const contact = contactLine(footer);
  return (
    <PolicyPage title="Legal Disclaimer">
      <Section heading="1. Not legal advice">
        <p>
          Nothing on {SITE_NAME} — blueprints, validator results,
          Freedom-to-Operate reports, or any other content — is legal advice,
          a legal opinion, or a substitute for advice from a qualified patent
          attorney. No attorney–client relationship is created by using the
          service. Before making significant commercial decisions based on a
          patent&apos;s status, consult counsel.
        </p>
      </Section>

      <Section heading="2. Patent status can change">
        <p>
          We surface patents only after automated verification that they
          appear to be public domain: filed more than 20 years ago (the
          statutory term) or officially recorded as expired or lapsed. That
          verification is enforced at the database level and re-checked for
          paid reports. However, official records can contain errors, statuses
          can be contested or corrected, some lapsed patents can be reinstated
          within limited windows, and related patents (continuations, family
          members in other countries) may still be active. An expired patent
          means the claimed invention is free to use — it does not mean every
          possible implementation is free of all third-party rights.
        </p>
      </Section>

      <Section heading="3. AI-generated content">
        <p>
          Blueprints and analyses are produced by large language models. They
          can be wrong: they may oversimplify claims, misstate technical
          details, or describe a plausible-sounding mechanism that differs
          from the actual patent. Treat every blueprint as a well-organized
          starting point for your own reading of the source patent, which we
          link on every blueprint page.
        </p>
      </Section>

      <Section heading="4. Freedom-to-Operate reports">
        <p>
          Our $99 reports are AI-generated informational summaries of expiry
          evidence at a point in time. They are <strong className="text-ink">not</strong>{" "}
          a freedom-to-operate legal opinion of the kind a patent attorney
          prepares, and they do not analyze active third-party patents,
          trademarks, trade secrets, or regulatory constraints that may apply
          to your product. Every report states this on its face.
        </p>
      </Section>

      <Section heading="5. Validator results">
        <p>
          Similarity scores are statistical measures over text embeddings, not
          legal judgments of infringement or novelty. A high match means an
          expired patent described a similar problem — useful signal, not a
          clearance. Landscape caution notes are aggregate signals and are not
          a substitute for a professional prior-art search.
        </p>
      </Section>

      <Section heading="6. No warranty; your responsibility">
        <p>
          The service and its content are provided &quot;as is&quot; without
          warranties. You are responsible for what you build and how you
          commercialize it. To the extent permitted by law, we disclaim
          liability for losses arising from reliance on the service&apos;s
          content. Questions: {contact}.
        </p>
      </Section>
    </PolicyPage>
  );
}
