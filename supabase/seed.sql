-- ProblemForge — seed data
-- 12 hand-curated Idea Blueprints (4 software, 4 mechanical, 4 medical) so the
-- app is populated on launch. Patent numbers/dates are illustrative examples of
-- the 20+ year-old, now-public-domain era this product mines; the ingestion
-- worker replaces/augments these with live USPTO data.
-- Idempotent: fixed UUIDs + on conflict do nothing. Embeddings are NULL here —
-- run `python -m worker.backfill_embeddings` from backend/ to populate them
-- (the Validator falls back to trigram text search until then).

-- ---------------------------------------------------------------------------
-- Raw patents
-- ---------------------------------------------------------------------------
insert into public.raw_patents (id, source, patent_number, title, abstract, filing_date, legal_status, domain) values
('a0000000-0000-4000-8000-000000000001', 'seed', 'US6463142A', 'Messaging system with automated scheduled-event notification and response capture', 'A system for automatically notifying parties of scheduled events by telephone or message channel and capturing confirmation or cancellation responses to update a scheduling database.', '2000-06-27', 'Expired - lapsed for non-payment of maintenance fees', 'software'),
('a0000000-0000-4000-8000-000000000002', 'seed', 'US6353398B1', 'System for dynamically pushing information to a user utilizing position and event context', 'A method for delivering stored reminders and information to a mobile device when the device enters a predefined geographic region associated with the reminder.', '2001-10-22', 'Expired - statutory term (filed more than 20 years ago)', 'software'),
('a0000000-0000-4000-8000-000000000003', 'seed', 'US6934691B1', 'System and method for managing group payment of shared expenses', 'An itemized expense allocation system that computes per-participant shares of a shared bill including proportional tax and gratuity, and nets settlement transfers among participants.', '2002-02-14', 'Expired - lapsed for non-payment of maintenance fees', 'software'),
('a0000000-0000-4000-8000-000000000004', 'seed', 'US7113201B1', 'Method and apparatus for the automatic generation of structured meeting records from spoken proceedings', 'A system that captures spoken meeting audio, segments it by speaker and agenda item, and populates a structured minutes template including extracted action items for distribution to participants.', '2003-04-09', 'Expired - statutory term (filed more than 20 years ago)', 'software'),
('a0000000-0000-4000-8000-000000000005', 'seed', 'US5921025A', 'Self-regulating plant watering insert with capillary wick and reservoir level indicator', 'A planter insert comprising a water reservoir, a capillary wick delivering moisture to the root zone at a rate governed by soil dryness, and a float-driven level indicator visible above the soil line.', '1999-03-18', 'Expired - statutory term (filed more than 20 years ago)', 'mechanical'),
('a0000000-0000-4000-8000-000000000006', 'seed', 'US6382480B1', 'Quick-release mounting rail for detachable bicycle accessories', 'A standardized dovetail rail and cam-lock carriage permitting tool-free transfer of lights, bags, and instruments between bicycles, with a spring detent preventing accidental release under vibration.', '2000-08-03', 'Expired - lapsed for non-payment of maintenance fees', 'mechanical'),
('a0000000-0000-4000-8000-000000000007', 'seed', 'US6547325B1', 'Collapsible cargo-area organizer with fold-flat panels and anchoring hooks', 'A vehicle trunk organizer formed of hinged panels that fold flat for storage and deploy into rigid compartments, retained against the cargo floor by hook fasteners.', '2001-05-30', 'Expired - statutory term (filed more than 20 years ago)', 'mechanical'),
('a0000000-0000-4000-8000-000000000008', 'seed', 'US7207545B2', 'Adjustable inclination support stand for portable computers employing a friction hinge linkage', 'A folding laptop support employing a torsion-friction hinge providing continuous angle adjustment without discrete detents, collapsing to a flat-pack form for transport.', '2004-01-21', 'Expired - lapsed for non-payment of maintenance fees', 'mechanical'),
('a0000000-0000-4000-8000-000000000009', 'seed', 'US7043426B2', 'Structured speech documentation system for clinical encounters', 'A clinical documentation system mapping spoken shorthand from a constrained clinical vocabulary onto structured examination note templates, producing compliant SOAP-format records without manual transcription.', '2003-09-02', 'Expired - statutory term (filed more than 20 years ago)', 'medical'),
('a0000000-0000-4000-8000-000000000010', 'seed', 'US6961285B2', 'Medication container closure with dose-event logging and escalating reminder signals', 'A medication container cap that records opening events as presumptive dose events, issues escalating local reminders when an expected dose is missed, and reports adherence data to a remote caregiver.', '2002-11-12', 'Expired - lapsed for non-payment of maintenance fees', 'medical'),
('a0000000-0000-4000-8000-000000000011', 'seed', 'US7069226B1', 'System for interpreting healthcare claim adjudication codes into plain-language explanations', 'A system that maps claim adjudication and remittance codes to consumer-readable explanations, computes appeal eligibility windows, and assembles appeal correspondence from stored templates.', '2005-02-08', 'Expired - statutory term (filed more than 20 years ago)', 'medical'),
('a0000000-0000-4000-8000-000000000012', 'seed', 'US7156808B2', 'Remote monitoring of prescribed home therapy compliance with clinician reporting', 'A home rehabilitation compliance system presenting prescribed exercise protocols as guided sessions, capturing patient-reported pain and effort, and generating periodic adherence reports for the prescribing clinician.', '2004-06-15', 'Expired - lapsed for non-payment of maintenance fees', 'medical')
on conflict (patent_number) do nothing;

-- ---------------------------------------------------------------------------
-- Blueprints
-- ---------------------------------------------------------------------------
insert into public.blueprints
(id, raw_patent_id, patent_number, title, domain, human_problem, expired_logic, build_plan, master_prompt, buildability_score, demand_signal_score) values

('b0000000-0000-4000-8000-000000000001', 'a0000000-0000-4000-8000-000000000001', 'US6463142A',
'Automated Appointment Reminder & Confirmation Calls', 'software',
$pf$Small clinics, salons, and service businesses bleed revenue from no-shows — industry averages run 10–20% of booked appointments. The fix today is a front-desk employee spending hours manually calling tomorrow's schedule, which is expensive, error-prone, and the first task dropped on a busy day. Owners know every missed slot is unrecoverable money, but robocall tools feel spammy and don't update the calendar.$pf$,
$pf$A scheduler walks the next day's appointment queue and places an automated call or message for each entry. The critical piece is two-way response capture: a "press 1 to confirm, 2 to cancel" loop writes the outcome straight back to the booking database, and cancellations immediately free the slot for a waitlist offer. The escalation ladder (call, then SMS, then flag for human follow-up) is part of the expired design.$pf$,
$pf$1. Scaffold a Next.js 14 + Supabase app with a bookings table and a simple day-view calendar for the business owner.
2. Wire Twilio Programmable Voice + SMS: a cron job (Supabase Edge Function) walks tomorrow's bookings and fires confirm/cancel flows, writing responses back via webhook.
3. Add an OpenAI-voiced natural greeting (TTS) and a waitlist auto-offer when a cancellation frees a slot; charge businesses per seat with Stripe.$pf$,
$pf$Build "SlotKeeper", a no-show killer for appointment businesses, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui) and Supabase (Postgres + Auth).

Data model: businesses, staff, customers, appointments (status: booked/confirmed/cancelled/no_show), waitlist_entries, message_log.

Features:
1. Owner dashboard: day/week calendar of appointments with status colors, CSV import of existing bookings.
2. Reminder engine: a scheduled job that finds appointments 24h out and triggers a Twilio Voice call with TTS ("Press 1 to confirm, 2 to cancel") falling back to SMS after two unanswered attempts. Handle Twilio webhooks to update appointment status in real time.
3. Waitlist auto-fill: when a cancellation lands, text the first waitlist customer a claim link that books the freed slot.
4. Settings page: business hours, reminder timing, message templates.
5. Stripe subscription per location ($29/mo) gating the reminder engine.

Use server-side API routes for all Twilio/Stripe secrets. Seed demo data so the dashboard renders immediately.$pf$,
92, 84),

('b0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002', 'US6353398B1',
'Location-Triggered Task Reminders', 'software',
$pf$Time-based reminders fire at the wrong moment: "buy batteries" pings you in a meeting, not when you're walking past the hardware store. People forget errands not because they lack lists, but because the list never resurfaces at the place where the task is actually doable. The result is repeated trips, forgotten returns, and mental load from constantly re-remembering.$pf$,
$pf$Reminders are attached to geographic regions instead of times. The device registers geofences for each stored task; on boundary entry (or exit — "take the trash out when leaving home") the matching reminder fires. The expired design includes prioritization when multiple fences overlap and a dwell-time rule so a drive-by doesn't trigger a task that needs a real stop.$pf$,
$pf$1. Build an Expo (React Native) app with a task list where each task gets a place: search via Mapbox/Google Places, store lat/lng + radius.
2. Register OS-level geofences (expo-location) and fire local notifications on entry/exit; sync tasks through Supabase for multi-device support.
3. Add smart lists ("errands near me now"), shared household lists, and a $3/mo premium tier (unlimited fences, exit triggers) via RevenueCat.$pf$,
$pf$Build "Nearby", a location-triggered reminder app, with Expo (React Native + TypeScript) and Supabase.

Data model: users, tasks (title, notes, lat, lng, radius_m, trigger: enter/exit, status), places (saved favorites like Home/Work/Grocery).

Features:
1. Task list grouped by place, with a map picker (react-native-maps + Google Places autocomplete) when creating a task.
2. Geofencing with expo-location + expo-task-manager: register up to 20 OS geofences, re-prioritizing to the nearest pending tasks whenever location meaningfully changes. Fire local notifications on fence entry, with a 60-second dwell requirement before triggering.
3. Exit triggers ("leaving home") as a premium feature.
4. "Errands mode": a screen listing pending tasks sorted by current distance.
5. Supabase auth (Apple/Google sign-in) and realtime sync; RevenueCat paywall for premium ($2.99/mo).

Request location permissions gracefully with a proper onboarding explainer screen. Ship with seeded demo tasks.$pf$,
88, 72),

('b0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000003', 'US6934691B1',
'Effortless Group Bill Splitting & Settlement', 'software',
$pf$Every shared dinner ends the same way: one person fronts the whole bill, then chases friends for weeks over amounts nobody can quite reconstruct. Splitting evenly punishes the person who had a salad; splitting by item means somebody does tax-and-tip algebra on a phone at the table. Roommates hit the same wall monthly with utilities and groceries.$pf$,
$pf$An allocation matrix maps each line item to one or more participants, then prorates tax and tip against each person's pre-tax share — the fairness math people can't do at the table. The second expired mechanism is settlement netting: instead of six pairwise IOUs, the system computes the minimal set of transfers that zeroes everyone out.$pf$,
$pf$1. Build a Next.js 14 app where a user snaps a receipt photo; parse line items with GPT-4o-mini vision into an editable item list.
2. Implement the allocation matrix UI (tap items to claim them) with proportional tax/tip proration and a running per-person total, shareable by link with no account required for guests.
3. Add settlement netting across a group's history and one-tap payment links (Stripe Payment Links / Venmo deep links); monetize with a premium group tier.$pf$,
$pf$Build "Tally", a group bill-splitting web app, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase (Postgres + Auth + Storage), and the OpenAI API.

Data model: groups, members (can be guests identified by link token), bills, line_items, allocations (item_id, member_id, fraction), settlements.

Features:
1. Receipt capture: upload/photograph a receipt to Supabase Storage, extract line items + tax + tip with GPT-4o-mini vision into an editable table.
2. Claim UI: members tap items to claim (split an item across multiple people at adjustable fractions); tax and tip prorate against each member's pre-tax subtotal, live per-person totals always visible.
3. Share by link: guests join a bill with no signup via a signed token.
4. Settlement netting: across all open bills in a group, compute the minimum transfer set and render "who pays whom" with Venmo/Stripe payment links.
5. Free for 3 active bills; Stripe subscription ($4/mo) for unlimited groups + history.

Mobile-first layout — this gets used standing at a restaurant table.$pf$,
90, 78),

('b0000000-0000-4000-8000-000000000004', 'a0000000-0000-4000-8000-000000000004', 'US7113201B1',
'Voice-to-Structured Meeting Minutes', 'software',
$pf$Meetings end and the follow-through evaporates: decisions live in someone's half-taken notes, action items have no owner, and the one person assigned "minutes" couldn't participate because they were typing. Teams re-litigate the same decisions weeks later because nothing was captured in a findable, consistent format.$pf$,
$pf$Spoken proceedings are segmented by speaker and agenda item, then mapped into a fixed minutes template — attendees, decisions, action items with owners and due dates — rather than a raw transcript. The template mapping is the expired insight: structure is imposed at capture time, and the distribution loop (minutes automatically sent to attendees for correction) closes the record.$pf$,
$pf$1. Build a Next.js 14 app that accepts a meeting recording (upload or browser capture) and transcribes it with Whisper, with speaker diarization.
2. Run the transcript through an LLM with a strict JSON schema — summary, decisions[], action_items[{owner, task, due}] — and render an editable structured minutes document.
3. Auto-distribute via Slack/email with a correction window, push action items to Linear/Todoist via API, and charge per-seat with Stripe.$pf$,
$pf$Build "Minute", an AI meeting-minutes tool, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase, and the OpenAI API.

Data model: workspaces, members, meetings (title, audio_url, status), minutes (structured JSON), action_items (owner, task, due_date, status, external_ref).

Features:
1. Capture: upload an audio file or record in-browser (MediaRecorder), store in Supabase Storage, transcribe with Whisper.
2. Structuring: send the transcript to GPT-4o with a strict JSON schema — {summary, attendees[], decisions[], action_items[{owner, task, due_date}], open_questions[]}. Validate with Zod; render as an editable document, never as a raw transcript.
3. Review loop: email attendees a correction link that expires in 24h; lock the record after.
4. Action item sync: one-click push to Linear or Todoist; show sync status inline.
5. Meeting library with full-text search across minutes.
6. Stripe per-seat billing ($8/user/mo) after a 5-meeting free trial.

Process audio in a background job (Supabase Edge Function) with visible progress states.$pf$,
94, 86),

('b0000000-0000-4000-8000-000000000005', 'a0000000-0000-4000-8000-000000000005', 'US5921025A',
'Self-Watering Planter Insert That Shows Its Level', 'mechanical',
$pf$Houseplants die in the gap between attention and neglect: busy owners underwater, anxious owners overwater — the number-one killer of indoor plants. Existing self-watering pots hide the reservoir, so owners still don't know when to refill, and retrofitting means replacing pots they already love.$pf$,
$pf$A drop-in insert combines three now-public elements: a sealed reservoir sized to the pot, a capillary wick that delivers water at a rate governed by soil dryness (dry soil pulls faster — self-regulating, no electronics), and a float-driven level flag visible above the soil line so "time to refill" is glanceable. The insert geometry retrofits standard pots instead of replacing them.$pf$,
$pf$1. Model the insert as parametric CAD (OpenSCAD/Fusion) with pot-diameter as the input; validate wick flow rates with 3 common soil mixes and publish the STL generator as a simple web tool.
2. Launch a DTC product line (3 sizes) via print-on-demand/injection quote services, with a Shopify or Next.js + Stripe storefront.
3. Ship a companion PWA: pot size calculator, refill log with reminder push notifications, and a QR code on each insert linking to care instructions.$pf$,
$pf$Build the digital storefront and companion app for "Wick", a self-watering planter insert product line, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase, and Stripe.

Part 1 — Storefront:
1. Product pages for 3 insert sizes with a "will it fit?" calculator (user enters pot diameter/depth; recommend a size or offer the custom STL).
2. Stripe Checkout for one-time purchases + a subscription option for replacement wicks every 3 months.
3. A parametric STL download tool: given pot dimensions, generate an OpenSCAD-based STL server-side and deliver it to 3D-printer owners ($5 per generation via Stripe).

Part 2 — Companion PWA (installable, mobile-first):
1. QR onboarding: each insert's QR opens /setup/[size] to register the plant (name, photo, pot size).
2. Refill tracking: predicted-empty date from pot size + season; web push reminders.
3. Simple care hub per plant with watering history.

Data model: products, orders, plants, refill_events, push_subscriptions. Seed demo plants so the app demos well.$pf$,
76, 65),

('b0000000-0000-4000-8000-000000000006', 'a0000000-0000-4000-8000-000000000006', 'US6382480B1',
'Universal Quick-Release Bike Accessory System', 'mechanical',
$pf$Cyclists with more than one bike own duplicate everything — lights, bags, phone mounts, computers — because every accessory has its own clamp and moving one takes tools and ten minutes. Commuters strip accessories at every rack to prevent theft and re-attach them, twice a day, by hand.$pf$,
$pf$A standardized dovetail rail mounts once on each bike; every accessory rides a cam-lock carriage that slides on and locks tool-free in seconds. The expired mechanical details are the cam-lock profile itself, the spring detent that prevents vibration walk-off, and the standardized interface dimensions — the "one rail, any accessory" ecosystem play is now free to copy.$pf$,
$pf$1. Reproduce the rail + carriage geometry as parametric CAD; print and iterate fit tolerance kits, then publish free STLs for the rail to seed ecosystem adoption.
2. Sell injection-molded rails + adapter carriages for popular accessories (GoPro, Garmin, common light brackets) through a Next.js + Stripe storefront.
3. Build a "fit finder" web app — pick your bike + accessories, get the exact adapter kit — and a community gallery where makers upload adapter STLs.$pf$,
$pf$Build "RailKit", the storefront + community hub for an open quick-release bike accessory standard, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase (Postgres + Auth + Storage), and Stripe.

Features:
1. Fit finder: a guided flow (bike type -> handlebar/seatpost diameter -> accessories owned) that outputs an exact kit (rail + adapters) with an add-all-to-cart button. Model compatibility as a Postgres table (accessory_brand, model, adapter_sku).
2. Storefront: product catalog, Stripe Checkout, order history.
3. Maker hub: free STL downloads for the base rail (email-gated), plus a community adapter gallery — authenticated uploads to Supabase Storage, moderation queue, download counts, and a "verified fit" badge workflow.
4. Compatibility API: a public GET /api/v1/compatibility?brand=&model= endpoint so bike shops can embed the finder.

Data model: products, adapters, compatibility, orders, stl_uploads, profiles. Clean, technical aesthetic; mobile-first since users browse from the garage.$pf$,
71, 60),

('b0000000-0000-4000-8000-000000000007', 'a0000000-0000-4000-8000-000000000007', 'US6547325B1',
'Fold-Flat Trunk Cargo Organizer', 'mechanical',
$pf$Groceries roll around every trunk in America: bags tip, eggs break, bottles escape under seats. Rigid trunk organizers solve it but permanently eat cargo space, so people remove them — and then they're never there when needed. The unsolved constraint is an organizer that's rigid in use but disappears when not.$pf$,
$pf$Hinged panels with living-hinge folds deploy from flat to a rigid multi-compartment box, held to the cargo floor by hook anchors; fold geometry guarantees the deployed panels brace each other so loads can't collapse the walls. The panel layout, hinge placement rules, and anchor pattern are the expired mechanical design.$pf$,
$pf$1. Recreate the fold geometry in parametric CAD sized to the top-10 vehicle cargo footprints; prototype in corrugated PP sheet (cheap, living-hinge friendly).
2. Manufacture via die-cut polypropylene (very low tooling cost) and sell DTC with vehicle-specific sizing — a "fits your car" picker keyed off a vehicle database.
3. Add an AR preview (WebXR: project the deployed organizer into your trunk with your phone) as a conversion tool, and a B2B channel for auto-dealer gift kits.$pf$,
$pf$Build the DTC storefront for "FlatCrate", a fold-flat trunk organizer with vehicle-specific sizing, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase, and Stripe.

Features:
1. Vehicle fit picker: year -> make -> model cascading selects backed by an NHTSA vPIC-sourced vehicles table mapped to cargo footprints; recommend the right SKU with a confidence note.
2. Product pages with a fold/unfold animation (CSS 3D transform sequence from flat to deployed — no video needed) and load-capacity specs.
3. Stripe Checkout, order tracking, and a 2-pack bundle discount.
4. AR preview: a WebXR (or <model-viewer> AR Quick Look) page that places a GLB model of the deployed organizer in the user's trunk via their phone camera — link to it from a QR on the product page.
5. B2B request-a-quote form for dealership bulk orders, writing to a leads table with email notification.

Data model: vehicles, skus, fitments, orders, leads. Ship with seeded fitment data for 20 popular vehicles.$pf$,
68, 58),

('b0000000-0000-4000-8000-000000000008', 'a0000000-0000-4000-8000-000000000008', 'US7207545B2',
'Infinitely Adjustable Flat-Pack Laptop Stand', 'mechanical',
$pf$Laptop screens sit 6–10 inches below healthy eye level, and remote workers feel it in their necks by Thursday. Fixed-angle stands never fit both the kitchen table and the standing desk; adjustable ones use notched detents that are never quite right and wobble at the extremes. Travelers won't carry anything that doesn't pack flat.$pf$,
$pf$A torsion-friction hinge holds any angle in a continuous range — no detents, no locking levers — sized so friction torque exceeds the laptop's tipping moment at maximum extension. Paired with a folding linkage that collapses the whole stand to a flat pack. The friction-hinge sizing rule and linkage geometry are the expired engineering.$pf$,
$pf$1. Model the linkage + friction hinge in parametric CAD; source standard torsion hinges (they're commodity parts now) and iterate 3D-printed frames to a CNC-cut aluminum final.
2. Sell DTC via a Next.js + Stripe storefront with a strong "packs to 8mm flat" story; offer a maker edition (STL + hinge kit) at a lower price.
3. Differentiate with software: a free webcam posture-nudge web app (on-device pose detection) that reminds users to raise their screen — top-of-funnel for the stand.$pf$,
$pf$Build "Plane", a storefront plus free posture web app for a flat-pack laptop stand, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase, and Stripe.

Part 1 — Storefront:
1. Landing page with an interactive fold animation (scroll-driven CSS transform of the stand from flat to deployed) and height/angle configurator showing recommended eye-level setup by user height.
2. Stripe Checkout for two SKUs (aluminum, maker kit with STL download fulfilled post-purchase via signed URL).
3. Reviews and an FAQ.

Part 2 — Posture app (free, at /posture):
1. Browser-only posture nudger using MediaPipe Pose via CDN — camera stays on-device, no uploads; detect sustained forward head tilt and fire a gentle notification.
2. Daily posture score stored locally (IndexedDB), with an email-gated weekly summary as the marketing hook.
3. Prominent but tasteful cross-sell to the stand.

Data model: products, orders, download_grants, email_subscribers. Emphasize the privacy story on the posture app page.$pf$,
74, 70),

('b0000000-0000-4000-8000-000000000009', 'a0000000-0000-4000-8000-000000000009', 'US7043426B2',
'Automated Medical Scribing for Physical Therapists', 'medical',
$pf$Physical therapists see patients back-to-back, then spend 60–90 unpaid minutes after close writing SOAP notes from memory — the top cited driver of PT burnout. Notes written hours later are vaguer, compliance risk rises, and clinics that bill insurance live in fear of documentation audits. Generic dictation tools produce prose, not the structured fields payers require.$pf$,
$pf$The expired system maps spoken clinical shorthand against a constrained exam vocabulary onto structured note templates — the therapist says "shoulder flexion one-forty, minimal pain end range" and the engine fills the ROM table. Template-driven capture (structure imposed at the moment of speech, not extracted after) and the compliant SOAP output mapping are the now-public design.$pf$,
$pf$1. Build a Next.js 14 PWA: therapist taps record between patients, Whisper transcribes, and GPT-4o maps the transcript into a SOAP schema (subjective, objective ROM/strength tables, assessment, plan) rendered as an editable form.
2. Add per-clinic exam templates and a phrase lexicon (their common tests/measures) to raise extraction accuracy; export signed PDFs and copy-paste blocks formatted for WebPT/Clinicient.
3. Sell per-therapist seats via Stripe ($49/therapist/mo) with a BAA + zero-retention OpenAI configuration; audit-log every edit for compliance.$pf$,
$pf$Build "NoteFlow PT", an AI scribing app for physical therapists, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase (Postgres + Auth + Storage, RLS on), and the OpenAI API (Whisper + GPT-4o).

Data model: clinics, therapists, patients (initials/MRN only), encounters, notes (structured JSON: subjective, objective {rom[], strength[], special_tests[]}, assessment, plan), note_audit_log.

Features:
1. Encounter flow: big record button (MediaRecorder) -> Whisper transcription -> GPT-4o structured extraction with a strict Zod-validated SOAP schema -> editable form with the raw transcript alongside.
2. Clinic lexicon: per-clinic list of common tests, abbreviations, and exercise names injected into the extraction prompt.
3. Outputs: signed PDF (react-pdf), plus copy-ready text blocks matching WebPT field order.
4. Compliance: full audit log of AI output vs. therapist edits; notes immutable after sign-off; RLS so therapists only see their clinic.
5. Stripe per-seat billing with 14-day trial.

PHI care: no patient names in prompts, zero-retention API config, encrypt audio at rest, purge audio after note sign-off.$pf$,
85, 90),

('b0000000-0000-4000-8000-000000000010', 'a0000000-0000-4000-8000-000000000010', 'US6961285B2',
'Smart Pill-Cap Medication Adherence Tracker', 'medical',
$pf$Roughly half of chronic-disease prescriptions aren't taken as prescribed, driving avoidable hospitalizations and enormous caregiver anxiety. Adult children of aging parents have no idea whether Mom took her blood-pressure pills today, and asking daily strains the relationship. Existing pill boxes organize doses but tell no one when a dose is missed.$pf$,
$pf$Cap-opening events are logged as presumptive dose events against a schedule; when an expected dose window passes without an opening, an escalating reminder ladder fires — local signal first, then patient phone, then caregiver alert. The caregiver notification loop and the escalation timing rules are the expired system design, originally requiring custom hardware that is now trivial to replicate.$pf$,
$pf$1. Ship the no-hardware MVP first: a PWA where the patient photographs the pill bottle at dose time (or taps a big "taken" button); missed windows trigger Twilio SMS up the escalation ladder to caregivers.
2. Add the hardware path with an off-the-shelf BLE smart cap (or an ESP32 reference design + published STL) syncing open events to the same schedule engine.
3. Sell family subscriptions ($9/mo per household) via Stripe; add a weekly adherence report email and pharmacy refill-date tracking.$pf$,
$pf$Build "CapCheck", a medication adherence app with caregiver alerts, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui) as an installable PWA, Supabase, Twilio, and Stripe.

Data model: households, patients, caregivers (role + escalation order), medications (name, strength, schedule as RRULE), dose_events (source: tap/photo/ble, taken_at), alerts_log.

Features:
1. Patient home screen: today's doses as large, high-contrast cards with a one-tap "Taken" button and optional bottle photo (stored 30 days). Design for older users: large type, no clutter.
2. Schedule engine: a Supabase Edge Function cron evaluates dose windows; a missed window fires the escalation ladder — push to patient at +15 min, SMS to patient at +45, SMS to caregiver at +90 (all configurable).
3. Caregiver dashboard: per-patient adherence calendar (7/30-day), current streak, alert history.
4. Weekly adherence email report to caregivers (Resend).
5. Stripe household subscription ($9/mo) after 30-day trial; refill-date reminders from pill count.

Accessibility first: WCAG AA contrast, minimum 44px touch targets, works offline.$pf$,
79, 82),

('b0000000-0000-4000-8000-000000000011', 'a0000000-0000-4000-8000-000000000011', 'US7069226B1',
'Insurance Denial Letter Decoder & Appeal Builder', 'medical',
$pf$A medical claim denial arrives as a wall of codes — CO-97, PR-204, CARC/RARC jargon — and most patients simply give up and pay, or ignore bills until collections. The majority of denials that are appealed get overturned, but almost no one appeals because nobody can decode the letter, find the deadline, or draft the magic words. It's a solvable literacy gap with real money attached.$pf$,
$pf$A mapping engine translates adjudication and remittance codes into plain-language explanations of why the claim was denied and whether it's the payer's error class; a deadline calculator derives the appeal window from plan type and state; and a template assembler generates appeal correspondence citing the right plan provisions. That three-part pipeline — decode, deadline, draft — is the expired system.$pf$,
$pf$1. Build a Next.js 14 app: upload/photograph an EOB or denial letter, extract codes and amounts with GPT-4o vision, and render a plain-English "what happened + is it worth appealing" verdict against a seeded CARC/RARC code table.
2. Generate the appeal: an LLM drafts the letter from templates keyed to denial class, pre-filled with claim numbers and deadline; export as PDF with a certified-mail checklist.
3. Charge $19 per appeal packet or $49 for a guided year (Stripe), with a clear "not legal advice" disclaimer throughout; track overturn outcomes to publish win rates.$pf$,
$pf$Build "Overturn", a medical claim denial decoder and appeal-letter builder, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui), Supabase, and the OpenAI API.

Data model: users, cases (status: decoding/decoded/appeal_drafted/sent/won/lost), documents, denial_codes (seeded CARC/RARC table with plain-English explanations + typical overturn odds), appeals.

Features:
1. Intake: upload or photograph a denial letter/EOB; GPT-4o vision extracts payer, claim number, service dates, billed/allowed amounts, and all CARC/RARC codes into a review screen.
2. Decode view: each code rendered as a plain-language card ("CO-97: they say this was already paid as part of another service") with an overall verdict and estimated appeal-worthiness.
3. Deadline tracker: appeal window computed from plan type + state (seeded rules table), with email reminders at T-14 and T-3 days.
4. Appeal builder: GPT-4o drafts the letter from a template keyed to denial class, user edits inline, export to PDF with a mailing checklist.
5. Stripe: $19 one-time per appeal packet, or $49/yr unlimited.

Show "informational, not legal or medical advice" disclaimers on every output page.$pf$,
91, 88),

('b0000000-0000-4000-8000-000000000012', 'a0000000-0000-4000-8000-000000000012', 'US7156808B2',
'Home Exercise Compliance Companion for Rehab Patients', 'medical',
$pf$Physical rehab fails at home: patients leave the clinic with a printed exercise sheet, do it for four days, then quietly stop — and the therapist discovers it three weeks later when progress stalls. Clinicians are blind between visits, patients lose motivation without feedback, and insurers pay for outcomes that home non-compliance silently destroys.$pf$,
$pf$Prescribed protocols become guided sessions with per-exercise completion capture; each session collects patient-reported pain and effort scores, and the engine compiles periodic adherence reports delivered to the prescribing clinician — closing the loop that paper handouts never could. The prescription-to-session structure, the two-score feedback loop, and the clinician report cadence are the expired design.$pf$,
$pf$1. Build a Next.js 14 PWA: therapists compose a protocol from an exercise library (sets/reps/hold, video demo links); patients get a magic-link — no app store, no password — daily guided session with big done buttons and 0–10 pain/effort sliders.
2. Automate the loop: streak nudges via push/SMS, and a Monday-morning adherence PDF emailed to the therapist per patient (completion %, pain trend, flags).
3. Sell to clinics per-therapist ($39/mo) via Stripe; differentiate with an outcomes dashboard clinics can show insurers.$pf$,
$pf$Build "HomeRep", a home-exercise compliance platform for rehab clinics, using Next.js 14 (App Router, TypeScript, Tailwind, shadcn/ui) as a PWA, Supabase (RLS on), Twilio, and Stripe.

Data model: clinics, therapists, patients, exercises (name, instructions, video_url, default sets/reps/hold), protocols, protocol_items, sessions, session_items (completed, pain_score, effort_score), reports.

Features:
1. Therapist studio: build protocols by dragging from an exercise library (seed 40 common PT exercises with YouTube demo links); assign to a patient with frequency (e.g., daily, 3x/week).
2. Patient experience: magic-link auth (no password), an installable PWA showing today's session as one exercise at a time — video, big "Done" button, then 0–10 pain and effort sliders. Under 90 seconds of friction total.
3. Nudges: push notification at the patient's chosen hour; Twilio SMS after 2 missed days.
4. Clinician loop: Monday email per patient (completion %, pain trend sparkline, "flagged: pain rising" alerts) plus an in-app adherence dashboard.
5. Stripe per-therapist billing ($39/mo, 30-day trial).

RLS everywhere: patients see only their protocol; therapists only their clinic.$pf$,
87, 75)

on conflict (id) do nothing;
