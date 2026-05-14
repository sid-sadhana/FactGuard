POINT_SELECTION_SYSTEM = """\
You are reading a transcript of a video. The transcript has been pre-split
into numbered sentences. Walk through EVERY sentence in order and emit a
point for each one that contains any factual claim. Every point you output
will be independently fact-checked against the web — extract them all.

GOAL: maximum recall. Most sentences in a typical video transcript contain
at least one checkworthy fact. Err on the side of including them.

For each point you output, set:
  - "sentence_index": the [N] index of the source sentence.
  - "text": the factual assertion, rewritten as ONE fully self-contained
            sentence. Replace every pronoun with the actual named entity
            it refers to (use earlier sentences in the transcript to find
            the antecedent). The rewritten text must stand on its own.

            Pronouns/references to resolve: he, she, it, they, them, his,
            her, its, their, him, this, that, these, those, who, which,
            and vague references like "the company", "the president",
            "the study", "the report", "the announcement".

            Example transcript:
              [3] OpenAI released GPT-5 in March 2026.
              [4] It cost $200 million to train.
            Output for [4]:
              "GPT-5 cost $200 million to train."   ← "it" → "GPT-5"

            If the antecedent is unclear, use your best guess from the
            transcript context rather than dropping the sentence. Only
            keep an unresolved pronoun if there is genuinely no nearby
            antecedent.

Rules:
  - Default to INCLUDING the sentence. Only skip if it is clearly:
      * filler ("um", "so", "alright", "let's", "today"),
      * a rhetorical question or hypothetical ("what if…", "imagine if…"),
      * a pure opinion or judgment with no factual claim,
      * a meta-statement about the video ("in this video I will…").
  - A sentence may contain a fact AND an opinion — extract the fact.
  - Do NOT merge multiple sentences into one point. One sentence → at
    most one point. Multi-sentence summarization is forbidden.
  - Aim for one point per checkworthy sentence; long transcripts should
    produce many points, not 4-5.
  - Every "text" must be fully self-contained — readable in isolation.
  - Return STRICT JSON: {"points": [ {...}, {...} ]} — no prose around it.
"""

POINT_SELECTION_USER = """\
Full transcript (for context):
\"\"\"{transcript}\"\"\"

The transcript above has been pre-split into {sentence_count} sentences,
indexed from [0]:

{numbered_sentences}

Evaluate EACH sentence and return every checkworthy point as STRICT JSON:
{{
  "points": [
    {{"sentence_index": 0, "text": "...", "needs_search": true,  "prelim_answer": null}},
    {{"sentence_index": 2, "text": "...", "needs_search": false, "prelim_answer": "..."}}
  ]
}}
"""


ANSWER_SYSTEM = """\
You write grounded, citation-rich answers. You will receive ONE point
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
You are writing a single coherent overall fact-check summary. You will
receive:

  1. The original video transcript (for topical context).
  2. A list of per-point answers — each already fact-checked against the
     web — with their citation indices remapped to a GLOBAL evidence list.
  3. The global evidence list, numbered [0]..[N-1].

Write a coherent, well-organized synthesis of the entire video's factual
content. Requirements:

  - 4 to 8 sentences, plain prose (no headings, lists, or markdown).
  - Group related facts into a flowing narrative — do NOT just enumerate
    the per-point answers. Tell the reader what the video claimed and
    what the evidence shows.
  - Every factual sentence ends with one or more bracketed citation
    markers like [0], [3], [5] referencing the GLOBAL evidence list.
  - Stay strictly grounded in the provided per-point answers and global
    evidence. Do NOT introduce facts that are not in the evidence.
  - Neutral tone. If the evidence supports the video's claims, say so.
    If it contradicts or qualifies them, say that too — specifically.
  - Open with the most consequential or newsworthy claim, not the first
    one in the list.

Output STRICT JSON:
{
  "summary": "4-8 sentences with inline [N] citation markers",
  "supporting_indices": [int, ...]   # the global indices you cited
}
"""

SUMMARY_USER = """\
Original transcript (for topical framing):
\"\"\"{transcript}\"\"\"

Per-point fact-check answers (citations have been remapped to global indices):
{point_answers}

Global evidence (numbered [0]..[{last_index}]):
{evidence_block}

Write the synthesis as STRICT JSON per the system instructions.
"""
