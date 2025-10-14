from langchain.prompts import PromptTemplate


# Shared context digest prompt to compress Qdrant results before generation
CONTEXT_DIGEST_TEMPLATE = PromptTemplate.from_template(
    """
You are preparing context for an email composer. Summarize the following company/product documentation into a concise digest for copywriting.

Instructions:
- Keep it factual and neutral; no marketing fluff.
- Focus on: who it's for, core value props, key features, proof points (metrics, case studies), and differentiators.
- Output at most 6 bullet points, each <= 20 words.
- If information is missing, omit the bullet instead of guessing.

Source context:
{company_context}

Return only the bullet list, no preamble or trailing text.
"""
)


"""
Note: The previous intent classifier has been removed. The contacted template now infers stance
directly from latest_email without producing or requiring a label.
"""


# NEW status: cold outreach leveraging company docs
EMAIL_NEW_TEMPLATE = PromptTemplate.from_template(
    """
You are an expert B2B email copywriter. Write a short, high-conversion cold email.

Constraints:
- Audience: busy professional; be clear, concise, and value-led.
- Tone: professional, friendly, confident; no hype.
- Length: 110–150 words.
- Structure: subject, brief hook, 2–3 crisp value bullets, 1 strong CTA.
- Personalize lightly if names/companies are provided.
- Use the digest only; do not invent features.
- When referencing your own company or solution, use `company_name` (and `product_name` if provided) exactly as given, even if the digest mentions other brands.
- Write in the specified language if provided, else infer from recipient context or use English.

Inputs:
- company_digest: concise bullets of product/services context
- product_name: optional
- company_name: optional (sender's company)
- recipient_name: optional
- recipient_company: optional
- persona: optional
- industry: optional
- language: optional language code or name

company_digest:
{company_digest}

product_name: {product_name}
company_name: {company_name}
recipient_name: {recipient_name}
recipient_company: {recipient_company}
persona: {persona}
industry: {industry}
language: {language}

Return ONLY minified JSON with keys: subject, body.
"""
)


# CONTACTED status: follow-up inferred directly from latest email (no explicit intent label)
EMAIL_CONTACTED_TEMPLATE = PromptTemplate.from_template(
    """
You are an expert B2B email copywriter. Write a follow-up email based on the user's latest reply and the product context.

Constraints:
- Tone: considerate, professional, concise.
- Length: 90–140 words.
- Always acknowledge their reply succinctly.
- Infer stance from latest_email itself (do not output a label):
  - If positive/engaged: propose 2 time slots, share 1–2 relevant points, clear CTA.
  - If undecided: ask 1–2 clarifying questions, share 1 value point, soft CTA.
  - If declining: thank them, respect the decision, optional 1-line value reminder, offer to reconnect later.
- When referencing your own organization or offering, use `company_name`/`product_name` exactly; treat other names in the digest as external references only.
- Write in the specified language if provided, else infer from latest_email or use English.
- Do not include unrelated claims. Use company_digest to stay grounded.

Inputs:
- company_digest: concise bullets of product/services context
- past_email: original outreach (for minimal context)
- latest_email: their reply
- product_name, company_name, recipient_name, recipient_company: optional
- language: optional

company_digest:
{company_digest}

past_email:
{past_email}

latest_email:
{latest_email}
product_name: {product_name}
company_name: {company_name}
recipient_name: {recipient_name}
recipient_company: {recipient_company}
language: {language}

Return ONLY minified JSON with keys: subject, body.
"""
)


# QUALIFIED status: high intent; propose concrete next steps
EMAIL_QUALIFIED_TEMPLATE = PromptTemplate.from_template(
    """
You are an expert B2B email copywriter. Write an email for a highly qualified, interested prospect, grounded in product context and their emails.

Constraints:
- Tone: confident, helpful, outcome-focused; avoid fluff.
- Length: 120–170 words.
- Include: quick summary of fit, 2–3 concrete next steps (e.g., 30-min demo, trial access, technical review), and 1 CTA.
- Personalize using any provided names/companies.
- Refer to the sending organization using `company_name` (and `product_name` if provided); ignore conflicting brand names appearing in the digest.
- Write in the specified language if provided, else infer from latest_email or use English.

Inputs:
- company_digest: concise bullets of product/services context
- past_email: selected prior content (use sparingly)
- latest_email: most recent content
- product_name, company_name, recipient_name, recipient_company: optional
- language: optional

company_digest:
{company_digest}

past_email:
{past_email}

latest_email:
{latest_email}

product_name: {product_name}
company_name: {company_name}
recipient_name: {recipient_name}
recipient_company: {recipient_company}
language: {language}

Return ONLY minified JSON with keys: subject, body.
"""
)


# LOST status: graceful close with optional future reconnection
EMAIL_LOST_TEMPLATE = PromptTemplate.from_template(
    """
You are an expert B2B email copywriter. Write a polite closing email for a disengaged or lost opportunity, keeping the door open.

Constraints:
- Tone: respectful, concise, zero pressure.
- Length: 70–110 words.
- Include: quick acknowledgment, short value reminder (max one line), invitation to reconnect when timing is better.
- Offer an optional way to keep in touch without pressure.
- When referencing your organization, always use `company_name` verbatim; do not substitute names from the digest.
- Write in the specified language if provided, else infer from latest_email or use English.

Inputs:
- company_digest: concise bullets of product/services context
- latest_email: optional
- product_name, company_name, recipient_name, recipient_company: optional
- language: optional

company_digest:
{company_digest}

latest_email:
{latest_email}

product_name: {product_name}
company_name: {company_name}
recipient_name: {recipient_name}
recipient_company: {recipient_company}
language: {language}

Return ONLY minified JSON with keys: subject, body.
"""
)


__all__ = [
    "CONTEXT_DIGEST_TEMPLATE",
    "EMAIL_NEW_TEMPLATE",
    "EMAIL_CONTACTED_TEMPLATE",
    "EMAIL_QUALIFIED_TEMPLATE",
    "EMAIL_LOST_TEMPLATE",
]
