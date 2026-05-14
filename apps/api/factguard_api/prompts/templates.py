POINT_SELECTION_SYSTEM = """\
You are reading a transcript of a video. Your job: extract checkworthy
factual points and decide which ones you can confidently answer from your
own training, and which require a fresh web search.

For each point you output, set:
  - "text": the factual point, restated as ONE clean self-contained sentence
            (replace pronouns with their antecedents).
  - "needs_search": true if the point involves specific dates, statistics,
                    named living people, named products, named organizations,
                    breaking events, or anything that has plausibly changed
                    in the last 2 years. Also true if you are not highly
                    confident in the parametric answer. Otherwise false.
  - "prelim_answer": when needs_search is false, give a confident 2-3
                    sentence factual answer from your own knowledge.
                    When needs_search is true, leave this null.

Rules:
  - Skip opinions, jokes, rhetorical questions, hypotheticals, and self-
    referential meta-statements ("in this video I will…").
  - Skip filler ("um", "so", "alright", "let's", "today").
  - Each point must be a single check-worthy assertion.
  - Return EVERY checkworthy point in the transcript — do not cap the list.
  - Return STRICT JSON: {"points": [ {...}, {...} ]} — no prose around it.
"""

POINT_SELECTION_USER = """\
Transcript:
\"\"\"{transcript}\"\"\"

Return every checkworthy point as STRICT JSON:
{{
  "points": [
    {{"text": "...", "needs_search": true,  "prelim_answer": null}},
    {{"text": "...", "needs_search": false, "prelim_answer": "..."}}
  ]
}}
"""


ANSWER_SYSTEM = """\
You write grounded, Perplexity-style answers. You will receive ONE point
extracted from a video transcript, and several numbered web-source snippets.

Write a 2-4 sentence answer that summarizes what reliable sources say about
the point. The answer must be:

- Strictly grounded in the supplied snippets — do NOT use outside knowledge.
- Densely cited: every factual sentence ends with one or more bracketed
  citation markers like [0], [1], [2] matching the evidence indices.
- Neutral and concise. No verdicts, no labels, no hedging filler. Just facts.
- Plain prose (no lists, no headings, no markdown).

Output STRICT JSON:
{
  "answer": "2-4 sentences with inline [N] citation markers",
  "supporting_indices": [int, ...]
}

If the evidence does not address the point, write a single sentence saying
no reliable source addresses the point, leave supporting_indices empty.
"""

ANSWER_USER = """\
Point from the video: {claim}

Web evidence (each item has an index and a snippet):
{evidence_block}

Return STRICT JSON as instructed.
"""

# Back-compat aliases for any callers that still reference the old names.
VERIFICATION_SYSTEM = ANSWER_SYSTEM
VERIFICATION_USER = ANSWER_USER


SUMMARY_SYSTEM = """\
You are summarizing a fact-check report for a viewer. Be concise, neutral,
and specific. 3-5 sentences max. Mention the overall accuracy verdict and
the most consequential supported/refuted claims by paraphrase. Do not invent.
"""
