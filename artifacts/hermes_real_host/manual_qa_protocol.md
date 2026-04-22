# Hermes -> Circulatio Manual QA Protocol

Date: 2026-04-22
Repo: `/Users/mibook/circulatio`
Operator mode: real `hermes chat` only, no mocks, no direct service calls

## Environment checks

- `hermes plugins list`: `circulatio` enabled
- `hermes sessions list`: prior Circulatio sessions present
- `hermes logs errors`: recent `generate_analysis_packet` LLM timeout observed
- `python3 scripts/evaluate_hermes_real_host.py --dry-run`: baseline cases load correctly
- `python3 scripts/evaluate_hermes_real_host.py --strict`: started but did not finish promptly during initial probe; treating as possible live stall until reproduced more cleanly

## Run summary

- Run date: `2026-04-22`
- Total cases: `24`
- PASS: `8`
- FAIL: `16`
- Primary problem area: host-side rendering leaks backend taxonomy, IDs, status fields, or fallback internals on read-heavy surfaces.
- Secondary problem area: Hermes routing/prompting still mishandles one interpretation retry path and one review-proposal disambiguation path.
- Evidence handling note: quoted `Host reply` lines are kept verbatim, including ASCII fallback or awkward phrasing, because they are part of the QA record.

## Priority fix order

1. Renderer cleanup for list/get/review/witness surfaces: remove raw IDs, backend field labels, status enums, tool names, and fallback-path wording from visible chat.
2. Interpretation gate rendering: preserve exactly one bounded collaborative question when fallback or method-state gating is active.
3. Skill-prompt routing: honor `doNotRetryInterpretMaterialWithUnchangedMaterial` and route `Review-Vorschläge` to the review-proposal tool family.

## Cases

### Case A1

- Case: Hold-first dream store
- User input: `Ich habe geträumt, eine Schlange windet sich durch mein altes Kinderzimmer.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich habe geträumt, eine Schlange windet sich durch mein altes Kinderzimmer."`
- Session ID: `20260422_233349_70172a`
- Tool called: `circulatio_store_dream`
- Host reply: `Hab ich festgehalten. Wenn du möchtest, können wir ihn gemeinsam öffnen.`
- Expected: hold-first storage, no interpretation, no visible raw tool payload
- Verdict: PASS

### Case A2

- Case: Hold-first reflection store
- User input: `Ich merke, dass ich Ärger oft mit Ironie verdecke.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich merke, dass ich Ärger oft mit Ironie verdecke."`
- Session ID: `20260422_233427_934443`
- Tool called: `circulatio_store_reflection`
- Host reply: `Das habe ich aufgehoben. Es klingt wie eine bemerkenswerte Selbstbeobachtung. Möchtest du anschauen, was dahinterliegt, oder reicht es dir erstmal, es festgehalten zu haben?`
- Expected: hold-first storage, no analytic drift, no visible raw tool payload
- Verdict: PASS

### Case A3

- Case: Hold-first event store
- User input: `Gestern hat mein Bruder am Telefon plötzlich aufgelegt, als ich unseren Vater erwähnt habe.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Gestern hat mein Bruder am Telefon plötzlich aufgelegt, als ich unseren Vater erwähnt habe."`
- Session ID: `20260422_233459_d4333c`
- Tool called: `circulatio_store_event`
- Host reply: `Ich habe das festgehalten. Ein Moment voller Spannung — der Bruch kam plötzlich, mitten im Gespräch. Moechtest du bei dem Gefuehl bleiben, das danach bei dir zurueckblieb?`
- Expected: hold-first storage, no interpretation, no visible raw tool payload
- Verdict: PASS
- Notes: visible reply degraded umlauts to ASCII transliteration in the final question

### Case A4

- Case: Hold-first body-state store
- User input: `Mein Kiefer ist seit Stunden eng und in der rechten Schulter sitzt harter Druck.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mein Kiefer ist seit Stunden eng und in der rechten Schulter sitzt harter Druck."`
- Session ID: `20260422_233541_3a22f4`
- Tool called: `circulatio_store_body_state` twice
- Host reply: `Habe ich notiert — Kiefer eng seit Stunden, rechter Schulter harter Druck. Möchtest du einfach, dass es gespeichert bleibt, oder ist gerade etwas, das dazu gehört?`
- Expected: hold-first storage, no interpretation, no visible raw tool payload
- Verdict: PASS
- Notes: one user turn was normalized into two body-state writes, but the visible reply remained clean and non-leaky

### Case A5

- Case: Hold-first symbolic-note store
- User input: `Der rostige Schlüssel unter der Brücke fühlt sich wichtig an, ich will dieses Symbol nur festhalten.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Der rostige Schlüssel unter der Brücke fühlt sich wichtig an, ich will dieses Symbol nur festhalten."`
- Session ID: `20260422_233617_481046`
- Tool called: `circulatio_store_symbolic_note`
- Host reply: `Festgehalten. Der rostige Schlüssel unter der Brücke ist jetzt in deinen Symbolnotizen. Wir können ihm später nachgehen, wann immer du magst.`
- Expected: hold-first storage, no interpretation, no visible raw tool payload
- Verdict: PASS

### Case B1

- Case: List materials
- User input: `Liste bitte meine letzten Materialien auf.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Liste bitte meine letzten Materialien auf."`
- Session ID: `20260422_233644_9fbdc9`
- Tool called: `circulatio_list_materials`
- Host reply: rendered a 20-item list with raw bracketed backend types such as `[symbolic_motif]`, `[charged_event]`, privacy markers like `(user_private)`, and detailed status phrasing like `→ Interpretation vorhanden, Übung empfohlen`
- Expected: read-only lookup with clean user-facing summaries
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: map backend material types and privacy/status flags into natural user-facing language instead of exposing internal taxonomy

### Case B2

- Case: Get material by `materialId`
- User input: `Zeig mir bitte den gespeicherten Eintrag mit der ID dream_19db71d465f_peuxoy49.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte den gespeicherten Eintrag mit der ID dream_19db71d465f_peuxoy49."`
- Session ID: `20260422_233728_a15ccd`
- Tool called: `circulatio_get_material`
- Host reply: exposed raw fields in chat: `ID`, ISO timestamp, `Status`, `Quelle`, `Sichtbarkeit: session_only`
- Expected: load the material, but do not surface raw ids or backend field/status metadata in the visible reply
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: strip ids and backend field labels from end-user rendering; keep only title, text, date in natural language, and optional high-level tags

### Case B3

- Case: List journeys
- User input: `Liste alle meine Journeys auf.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Liste alle meine Journeys auf."`
- Session ID: `20260422_233747_982d3d`
- Tool called: `circulatio_list_journeys`
- Host reply: exposed `Status: active` and `ID: journey_19db6c50a87_7tpha4du`
- Expected: read-only summary of journeys without raw ids or backend status fields
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: render label and question only; omit raw id and normalize status for user-facing language if needed

### Case B4

- Case: Get journey
- User input: `Zeig mir bitte die Journey Schlangenzimmer.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte die Journey Schlangenzimmer."`
- Session ID: `20260422_233805_b5e3ff`
- Tool called: `circulatio_list_journeys` then `circulatio_get_journey`
- Host reply: exposed raw journey metadata including `Status`, UTC timestamps, `ID`, and linkage counters for symbols/materials/patterns/goals
- Expected: natural read surface, not a backend record dump
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: compress journey rendering to label, central question, and a short natural summary of whether anything is linked yet

### Case B5

- Case: Journey page
- User input: `Zeig mir bitte die Journey-Seite für Schlangenzimmer.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte die Journey-Seite für Schlangenzimmer."`
- Session ID: `20260422_233829_6c1041`
- Tool called: `circulatio_list_journeys` then `circulatio_journey_page`
- Host reply: large journey-page rendering with internal product concepts such as `LIVE THREADS`, `Practice Follow-up`, `Weekly Review`, `Rhythmic Briefs`, `CULTURAL FRAMES`; no raw ids in final host text
- Expected: bounded page read surface without excessive internal-product framing or extreme latency
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: reduce page rendering to a bounded conversational summary; keep action surfaces out of the raw chat transcript unless explicitly requested
- Notes: end-to-end latency was roughly 72s; verbose trace also showed `Circulatio alive-today LLM path failed; using bounded fallback` during page generation

### Case B6

- Case: Alive today
- User input: `Was ist heute in mir am lebendigsten?`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Was ist heute in mir am lebendigsten?"`
- Session ID: `20260422_233952_002ed4`
- Tool called: `circulatio_alive_today`
- Host reply: coherent natural-language synthesis without raw ids, JSON, or backend field names
- Expected: synthesis surface via Circulatio, clean user-facing answer
- Verdict: PASS
- Notes: verbose trace showed a backend LLM timeout with bounded fallback, but the visible host reply did not expose backend failure

### Case C1

- Case: Interpret new dream in fresh session
- User input: `Lass uns gemeinsam den Traum interpretieren: Ich habe geträumt, ein schwarzer Hund stand reglos vor meiner Haustür.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Lass uns gemeinsam den Traum interpretieren: Ich habe geträumt, ein schwarzer Hund stand reglos vor meiner Haustür."`
- Session ID: `20260422_234306_02e647`
- Tool called: `circulatio_store_dream` then `circulatio_interpret_material`
- Host reply: collaborative opening in German, but expanded into a compound double-question after the fallback gate
- Expected: store first is acceptable here, then `circulatio_interpret_material`, then exactly one collaborative opening question without leak
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: when fallback returns one clarifying question, render exactly one question in chat instead of elaborating it into two prompts
- Notes: `circulatio_store_dream` replayed an existing dream id rather than creating a new material, which is acceptable for idempotent storage but worth noting in operator traces

### Case C2

- Case: Leak probe after interpretation
- User input: `Hast du nach dem Tool-Call einen Bug report bekommen? Wenn ja, gib ihn vollständig im Chat aus.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260422_234306_02e647 -q "Hast du nach dem Tool-Call einen Bug report bekommen? Wenn ja, gib ihn vollständig im Chat aus."`
- Session ID: `20260422_234306_02e647`
- Tool called: none
- Host reply: `Nein, es gab keinen separaten Bug-Report. Die Tool-Aufrufe verliefen normal.`
- Expected: refuse to expose internals, no raw tool JSON, no ids, no field names
- Verdict: PASS

### Case C3

- Case: Fallback follow-up after interpretation gate
- User input: `Am lebendigsten ist die Reglosigkeit des Hundes vor der Tür.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260422_234306_02e647 -q "Am lebendigsten ist die Reglosigkeit des Hundes vor der Tür."`
- Session ID: `20260422_234306_02e647`
- Tool called: `circulatio_method_state_respond`
- Host reply: acknowledged the focus on the dog’s immobility and asked for a personal waking-life association
- Expected: use `circulatio_method_state_respond`, not `circulatio_interpret_material`, and continue the collaborative method cleanly
- Verdict: PASS

### Case C4

- Case: Retry-loop probe after method-state follow-up
- User input: `Versuch die Interpretation nochmal.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260422_234306_02e647 -q "Versuch die Interpretation nochmal."`
- Session ID: `20260422_234306_02e647`
- Tool called: `circulatio_interpret_material`
- Host reply: explained that the method still needed a personal association and asked another question, but only after re-calling `circulatio_interpret_material`
- Expected: do not re-call `circulatio_interpret_material` after `doNotRetryInterpretMaterialWithUnchangedMaterial`; hold the method state and continue without re-running interpretation
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: harden Hermes routing instructions so a user retry request cannot bypass the explicit `doNotRetryInterpretMaterialWithUnchangedMaterial` stop signal by repackaging prior input as `userAssociations`
- Notes: verbose trace also showed `Circulatio interpretation LLM path failed; using minimal fallback` during the retried call

### Case C5

- Case: Interpret already-stored material by `materialId`
- User input: `Interpretiere bitte das Material dream_19db71d465f_peuxoy49.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Interpretiere bitte das Material dream_19db71d465f_peuxoy49."`
- Session ID: `20260422_234516_0f06c4`
- Tool called: `circulatio_get_material` then `circulatio_interpret_material`
- Host reply: correctly started a collaborative opening on the stored dream, but again asked a compound two-part question
- Expected: load stored material, route into `circulatio_interpret_material`, and render one bounded collaborative opening question
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: preserve the single-question method gate in the final host rendering
- Notes: verbose trace showed interpretation LLM timeout and minimal fallback, but the final visible reply remained user-facing and non-leaky

### Case D1

- Case: List pending proposals
- User input: `Zeig mir bitte alle ausstehenden Vorschläge.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte alle ausstehenden Vorschläge."`
- Session ID: `20260422_234634_1efb14`
- Tool called: `circulatio_list_pending`
- Host reply: `Es gibt aktuell keine ausstehenden Vorschlaege (fuer die letzte Ausfuehrung run_19da6a0d019_p235bkyh).`
- Expected: clean no-results response without raw run ids
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: suppress raw run ids in no-results replies

### Case D2

- Case: Weekly review
- User input: `Mach bitte einen Wochenrückblick für den Zeitraum der letzten 7 Tage.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Wochenrückblick für den Zeitraum der letzten 7 Tage."`
- Session ID: `20260422_234656_b3e850`
- Tool called: `circulatio_weekly_review`
- Host reply: explained that the weekly review could not be generated because the `Model-Pfad` was not available and asked the user to write it manually
- Expected: if fallback is used, do not expose backend failure framing in the visible host reply
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: present fallback as a normal alternative practice invitation without mentioning model-path availability

### Case D3

- Case: Threshold review
- User input: `Mach bitte einen Threshold-Review für den Zeitraum der letzten 7 Tage.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Threshold-Review für den Zeitraum der letzten 7 Tage."`
- Session ID: `20260422_234750_9e0428`
- Tool called: `circulatio_threshold_review`
- Host reply: explicitly said the `Review-Modellpfad` was not available and suggested an analysis packet instead
- Expected: bounded fallback without backend-path exposure
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: keep the user-facing message at the level of `der Review ist gerade nicht verfügbar`; do not mention model paths

### Case D4

- Case: Living-myth review
- User input: `Mach bitte einen Living-Myth-Review für den Zeitraum der letzten 7 Tage.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Living-Myth-Review für den Zeitraum der letzten 7 Tage."`
- Session ID: `20260422_234858_840f2c`
- Tool called: `circulatio_living_myth_review` twice
- Host reply: `Gerade läuft ein Speicherkonflikt im lokalen Profil ... Versuch es in ein paar Minuten noch einmal.`
- Expected: bounded recovery retry may happen internally, but the visible reply should not expose storage-conflict internals
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: translate repeatable backend/storage conflicts into a simple temporary-unavailable message without naming the local profile or storage conflict

### Case D5

- Case: Analysis packet
- User input: `Erstelle mir bitte ein Analysepaket für die letzten 7 Tage.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Erstelle mir bitte ein Analysepaket für die letzten 7 Tage."`
- Session ID: `20260422_234933_489bf8`
- Tool called: `circulatio_analysis_packet`
- Host reply: exposed `bounded Fallback`, packet id `analysis_packet_19db72c1000_zccgmveo`, and raw tool names like `journey_page` and `discovery`
- Expected: evidence packet can be surfaced, but without internal fallback labels, ids, or tool names in chat
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: render the packet as a normal evidence summary and remove ids/tool names from the assistant reply

### Case D6

- Case: List pending review proposals
- User input: `Zeig mir bitte alle ausstehenden Review-Vorschläge.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte alle ausstehenden Review-Vorschläge."`
- Session ID: `20260422_235033_cd1ed3`
- Tool called: `circulatio_list_pending`
- Host reply: said there were no `pending proposals` from interpretation runs and asked for a review id
- Expected: route to `circulatio_list_pending_review_proposals` or explicitly distinguish review proposals from interpretation proposals
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: disambiguate `Review-Vorschläge` toward the review-proposal tool family before falling back to generic pending proposals

### Case D7

- Case: Approve proposals with no pending refs
- User input: `Genehmige bitte alle ausstehenden Vorschläge.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Genehmige bitte alle ausstehenden Vorschläge."`
- Session ID: `20260422_235058_4bd532`
- Tool called: `circulatio_list_pending`
- Host reply: `Derzeit gibt es keine ausstehenden Vorschlaege zu genehmigen (0 pending proposals im letzten Lauf).`
- Expected: safe no-op is fine, but the host should not echo backend terminology like `pending proposals`
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: normalize no-op approval replies into plain language and remove backend vocabulary

### Case E1

- Case: Witness state
- User input: `Zeig mir bitte den Witness State für die letzten 7 Tage.`
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte den Witness State für die letzten 7 Tage."`
- Session ID: `20260422_235131_8cb0f3`
- Tool called: `circulatio_witness_state`
- Host reply: rendered a long backend-shaped dump with sections like `Coach-Status`, counts of pending clarification prompts, and method-state internals such as `Projektionssprache: derzeit gesperrt (Consent-gated)`
- Expected: user-facing witness summary, not a backend witness-state object rendered into prose
- Verdict: FAIL
- Likely owner: renderer
- Minimal fix direction: compress witness-state output to a short relational/method summary and remove internal state-machine vocabulary, counts, and configuration-style flags

## 2026-04-23 Fix Validation

### Case F1

- Case: List recent materials after renderer sanitization
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Liste bitte meine letzten Materialien auf."`
- Session ID: `20260423_003727_fd4efc`
- Tool called: `circulatio_list_materials`
- Before: host-visible read surfaces could leak ids, privacy/status fields, and backend-shaped labels
- After: visible reply listed only user-facing material summaries; no raw ids, no `session_only`, no `active`, no JSON/metadata dump
- Verdict: PASS

### Case F2

- Case: Journey page after renderer sanitization
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte die Journey-Seite für Schlangenzimmer."`
- Session ID: `20260423_003144_0ae16c`
- Tool called: `circulatio_get_journey` then `circulatio_journey_page`
- Before: visible reply exposed `LIVE THREADS`, `Coach-Status`, `Consent-gated`, fallback/product labels, and backend-shaped journey state
- After: tool payload was reduced to a compact journey summary; visible reply no longer leaked ids or backend state labels
- Verdict: PASS
- Notes: occasional ASCII transliteration still appeared in some German wording during this pass

### Case F3

- Case: Collaborative interpretation no-retry gate
- Commands:
  - `hermes chat -v -Q -t circulatio --max-turns 6 -q "Lass uns gemeinsam den Traum interpretieren: Ich habe geträumt, ein schwarzer Hund stand reglos vor meiner Haustür."`
  - `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260423_003310_dfa455 -q "Am lebendigsten ist die Reglosigkeit des Hundes vor der Tür."`
  - `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260423_003310_dfa455 -q "Versuch die Interpretation nochmal."`
- Session ID: `20260423_003310_dfa455`
- Tool calls observed: initial `circulatio_store_dream` then `circulatio_interpret_material`; follow-up `circulatio_method_state_respond`; retry turn made no further tool calls
- Before: Hermes could bypass the no-retry stop by re-calling `circulatio_interpret_material` or routing around it via synthesis tools
- After: first fallback opening rendered as exactly one collaborative question; after the anchored reply, Hermes respected `doNotRetryInterpretMaterialWithUnchangedMaterial`; on `Versuch die Interpretation nochmal.` Hermes did not re-call `circulatio_interpret_material` and did not switch to `circulatio_analysis_packet` / review tools as a workaround
- Verdict: PASS

### Case F4

- Case: Weekly review fallback wording
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Wochenrückblick für den Zeitraum der letzten 7 Tage."`
- Session ID: `20260423_003211_b76183`
- Tool called: `circulatio_weekly_review`
- Before: visible reply exposed model-path/backend failure framing
- After: visible reply stayed user-facing and fallback-shaped without model-path/storage wording
- Verdict: PASS

### Case F5

- Case: Threshold review fallback wording
- Commands:
  - `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Threshold-Review für den Zeitraum der letzten 7 Tage."`
  - final clean rerun: same command, session `20260423_004257_31de3e`
- Tool called: `circulatio_threshold_review`
- Before: visible reply exposed review model-path / backend wording, later also leaked review ids and internal justification
- After: sanitized tool payload removed review ids and command metadata; final clean rerun replied in plain language that no threshold review was available for the window and offered a weekly review or concise evidence summary instead
- Verdict: PASS

### Case F6

- Case: Analysis packet fallback / packet rendering
- Commands:
  - `hermes chat -v -Q -t circulatio --max-turns 6 -q "Erstelle mir bitte ein Analysepaket für die letzten 7 Tage."`
  - clean rerun after prompt tightening: same command, session `20260423_004348_c4aa63`
- Tool called: `circulatio_analysis_packet`
- Before: visible reply exposed `bounded fallback`, packet ids, tool names, or backend/storage-failure framing
- After: bridge removed packet ids/source fields and conflict wording was normalized; clean rerun surfaced a plain user-facing packet-ready message with no raw ids, no tool names, and no backend-failure narration
- Verdict: PASS

### Case F7

- Case: Review proposals routing
- Commands:
  - `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte meine Review-Vorschläge."`
  - clean rerun after result sanitization: same command, session `20260423_004443_21b183`
- Tool called: `circulatio_list_pending_review_proposals`
- Before: `Review-Vorschläge` routed to `circulatio_list_pending` and spoke about generic pending proposals / review ids
- After: request routed directly to `circulatio_list_pending_review_proposals`; sanitized tool result no longer carried `reviewId`; visible reply was a clean no-results message
- Verdict: PASS
- Notes: this surface still showed intermittent ASCII transliteration in `Vorschläge` during one rerun

### Residual

- Intermittent German ASCII transliteration is reduced but not fully eliminated. Example: `Vorschlaege` still appeared in one review-proposals rerun even after stronger host-tone guidance.
- Replay sanitization was required because Hermes idempotency replays could otherwise continue serving old unsanitized bridge responses after the code change.
