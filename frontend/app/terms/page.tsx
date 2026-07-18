import { PolicyPage, Section } from "@/components/PolicyPage";
import { OPERATOR_NAME, SITE_NAME } from "@/lib/site";
import { contactLine, getSiteSettings } from "@/lib/settings";

export const metadata = { title: "Terms of Service" };

export default async function TermsPage() {
  const { footer } = await getSiteSettings();
  const contact = contactLine(footer);
  return (
    <PolicyPage title="Terms of Service">
      <Section heading="1. Agreement">
        <p>
          These Terms of Service (&quot;Terms&quot;) govern your use of{" "}
          {SITE_NAME}, operated by {OPERATOR_NAME} (&quot;we&quot;,
          &quot;us&quot;). By creating an account, purchasing a plan or report,
          or using the site or API, you agree to these Terms and to our Privacy
          Policy, Acceptable Use Policy, Billing &amp; Refunds Policy, and
          Disclaimer, which are incorporated by reference. If you do not agree,
          do not use the service.
        </p>
      </Section>

      <Section heading="2. What the service is">
        <p>
          {SITE_NAME} identifies patents that have entered the public domain —
          because their statutory term ended or because official records mark
          them expired — and uses artificial intelligence to translate them
          into &quot;Idea Blueprints&quot;: plain-language summaries, build
          plans, and prompts for AI coding tools. We also offer a Validator
          that compares your idea against our blueprint library, and paid
          Freedom-to-Operate reports. Validator results may incorporate
          internal patent-landscape signals in addition to the public
          blueprint library.
        </p>
        <p>
          The service is informational. It is not legal advice, and nothing on
          the platform creates an attorney–client relationship. See the
          Disclaimer for important limits on what our content can and cannot
          tell you.
        </p>
      </Section>

      <Section heading="3. Accounts">
        <p>
          You must provide accurate information, keep your credentials and API
          keys secure, and be at least 18 years old (or the age of majority in
          your jurisdiction). You are responsible for activity under your
          account and API keys. Notify us promptly at {contact} if you
          suspect unauthorized access.
        </p>
      </Section>

      <Section heading="4. Plans, limits, and the API">
        <p>
          Free and paid plans include monthly usage allowances (searches,
          validator runs, and API requests) described on the Pricing page and
          enforced by the service. We may adjust allowances prospectively;
          material reductions to a paid plan will be communicated before your
          next billing cycle. API access is provided for your own applications
          — see the Acceptable Use Policy for limits on scraping, resale, and
          redistribution.
        </p>
      </Section>

      <Section heading="5. Payments">
        <p>
          Subscriptions and one-time purchases are processed by Stripe; we do
          not store card details. Billing cycles, cancellation, and refunds are
          governed by the Billing &amp; Refunds Policy.
        </p>
      </Section>

      <Section heading="6. Intellectual property">
        <p>
          The patents we surface are, to the best of our automated
          verification, in the public domain — the underlying inventions are
          free for anyone to use. Our original content (blueprint text,
          software, design, and branding) belongs to us; we grant you a
          non-exclusive license to use blueprint content, build plans, and
          master prompts in your own projects and products, including
          commercial ones. You may not resell or redistribute the blueprint
          library itself as a dataset or competing service.
        </p>
        <p>
          Anything you build from a blueprint is yours. We claim no rights in
          your applications, code, or businesses.
        </p>
      </Section>

      <Section heading="7. AI-generated content">
        <p>
          Blueprints, validator explanations, and Freedom-to-Operate analyses
          are generated with large language models and may contain errors,
          omissions, or outdated information. Verify anything you rely on.
          Patent status data comes from third-party sources and can be
          contested, corrected, or reinstated.
        </p>
      </Section>

      <Section heading="8. Termination">
        <p>
          You can close your account at any time. We may suspend or terminate
          accounts that violate these Terms or the Acceptable Use Policy, with
          notice where practicable. On termination, your right to use the
          service ends; sections that by their nature survive (IP,
          disclaimers, liability limits) survive.
        </p>
      </Section>

      <Section heading="9. Disclaimers and liability">
        <p>
          The service is provided &quot;as is&quot; and &quot;as
          available&quot; without warranties of any kind, express or implied,
          including merchantability, fitness for a particular purpose, and
          non-infringement. To the maximum extent permitted by law, our total
          liability for any claim arising out of the service is limited to the
          amounts you paid us in the twelve months before the claim arose. We
          are not liable for indirect, incidental, special, or consequential
          damages, or for decisions you make in reliance on AI-generated
          content.
        </p>
      </Section>

      <Section heading="10. Changes">
        <p>
          We may update these Terms. Material changes will be announced on the
          site or by email at least 14 days before they take effect; continued
          use after the effective date constitutes acceptance.
        </p>
      </Section>

      <Section heading="11. Contact">
        <p>
          Questions about these Terms: {contact}.
        </p>
      </Section>
    </PolicyPage>
  );
}
