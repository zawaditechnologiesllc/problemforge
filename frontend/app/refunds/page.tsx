import { PolicyPage, Section } from "@/components/PolicyPage";
import { CONTACT_EMAIL, SITE_NAME } from "@/lib/site";

export const metadata = { title: "Billing & Refunds" };

export default function RefundsPage() {
  return (
    <PolicyPage title="Billing & Refunds Policy">
      <Section heading="1. Plans and billing cycles">
        <p>
          {SITE_NAME} offers a Free plan and paid subscriptions — Builder
          ($19/month), Pro ($49/month), and Enterprise ($150/month) — plus a
          one-time Freedom-to-Operate report ($99). All payments are processed
          by Stripe. Subscriptions renew automatically each month until
          cancelled. Prices exclude any applicable taxes, which are calculated
          at checkout.
        </p>
      </Section>

      <Section heading="2. Cancelling">
        <p>
          Cancel anytime from Account → Billing → &quot;Manage billing &amp;
          invoices&quot; (the Stripe customer portal). Cancellation takes
          effect at the end of the current billing period; you keep paid
          features until then. We do not charge cancellation fees.
        </p>
      </Section>

      <Section heading="3. Subscription refunds">
        <p>
          <strong className="text-ink">First subscription, first 14 days.</strong>{" "}
          If you are new to a paid plan and it is not what you expected, email{" "}
          {CONTACT_EMAIL} within 14 days of your first charge and we will
          refund it in full.
        </p>
        <p>
          <strong className="text-ink">Renewals.</strong> Renewal charges are
          generally non-refundable, but if you cancelled before a renewal and
          were still charged, or you have barely used the service in the new
          period, contact us — we review these case by case and err on the
          side of the customer.
        </p>
        <p>
          <strong className="text-ink">Downgrades.</strong> Take effect at the
          next billing cycle; we do not prorate partial months.
        </p>
      </Section>

      <Section heading="4. Freedom-to-Operate reports">
        <p>
          The $99 report fee is refunded automatically-on-request if: (a) the
          report fails to generate and a retry does not resolve it, or (b) you
          request cancellation before generation completes. Once a report has
          been generated and delivered, the fee is non-refundable — you are
          paying for the verification work, which is complete on delivery. If
          a report contains a material factual error (e.g. we mislabel a
          patent&apos;s status), tell us: we will regenerate it or refund it.
        </p>
      </Section>

      <Section heading="5. Billing disputes">
        <p>
          Contact us at {CONTACT_EMAIL} before opening a card dispute — we
          resolve most billing issues within two business days, which is
          faster than a chargeback for everyone involved.
        </p>
      </Section>

      <Section heading="6. Price changes">
        <p>
          If we change subscription pricing, existing subscribers get at least
          30 days&apos; notice and the new price applies from their next
          renewal after the notice period.
        </p>
      </Section>
    </PolicyPage>
  );
}
