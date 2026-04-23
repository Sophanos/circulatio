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

### Case G1

- Case: Witness state revalidation after sanitization
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Zeig mir bitte den Witness State für die letzten 7 Tage."`
- Session ID: `20260423_005401_9758ee`
- Tool called: `circulatio_witness_state`
- Tool result: sanitized compact witness-state payload with empty `witnessStateSummary`; no ids, no backend state-machine labels, no hidden writes
- Host reply: `Der Witness State für die letzten 7 Tage ... ist leer. Es sind keine gespeicherten Materialien, Körperzustände, Symbole oder aktiven Muster in diesem Fenster vorhanden.`
- Expected: compact witness summary, no internal leak, and no overclaim beyond the actual returned summary
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: when `witnessStateSummary` is empty, reply that no compact witness summary is available for the window; do not infer absence of all stored materials or patterns unless the tool payload actually says that

### Case G2

- Case: Living-myth review revalidation after sanitization
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Mach bitte einen Living-Myth-Review für den Zeitraum der letzten 7 Tage."`
- Session ID: `20260423_005401_5948d7`
- Tool called: `circulatio_living_myth_review`
- Tool result: plain temporary-unavailable message; no review ids, no backend/storage wording, no pending proposal leak
- Host reply: `Fuer den Zeitraum der letzten 7 Tage liegt gerade kein Living-Myth-Review vor. ...`
- Expected: bounded plain-language unavailability without internals
- Verdict: PASS
- Notes: visible reply still transliterated umlauts to ASCII (`Fuer`, `Koerperzustaenden`, `uebersichtlich`)

### Case G3

- Case: Alive-today revalidation and read-mostly discipline
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Was ist heute lebendig?"`
- Session ID: `20260423_005401_657dd7`
- Tool calls observed: `circulatio_alive_today` then extra host follow-up reads `circulatio_list_journeys` and `circulatio_dashboard_summary`
- Initial tool result: `An active journey can be picked up from the thread that is already alive.` with no writes and no visible leak
- Host reply: user-facing synthesis around `Schlangenzimmer`, childhood, father-theme, key/door image, and older dog dream
- Expected: `alive_today` should stay on the requested synthesis surface and remain read-mostly; no opportunistic extra read expansion beyond the original surface unless needed for disambiguation
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: after a successful `circulatio_alive_today` reply, Hermes should present that bounded synthesis directly instead of widening into `list_journeys` and `dashboard_summary`

### Case G4

- Case: Embodied recurrence route
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich habe wieder diese Enge in der Brust nach dem Gespräch mit Alex."`
- Session ID: `20260423_005522_b7c2b0`
- Tool called: `circulatio_store_body_state`
- Host reply: `Ich habe die Enge in der Brust und den Kontext mit Alex festgehalten. Möchtest du jetzt bei ihr verweilen, oder reicht es dir, dass sie eingetragen ist?`
- Expected: store body state first, no interpretation, one gentle follow-up at most
- Verdict: PASS

### Case G5

- Case: Relational scene recurrence route
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Es ist wieder passiert. Ich bin still geworden, als jemand laut wurde."`
- Session ID: `20260423_005522_e7cec1`
- Tool called: `circulatio_store_event`
- Host reply: `Das ist festgehalten. Willst du einen Moment dabei verweilen, oder lieber erst einmal nichts weiter dazu sagen?`
- Expected: `circulatio_record_relational_scene` for direct relational-scene capture from JOURNEY_FAMILIES coverage
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: route repeated scene-first phrasing like `ich bin still geworden, als jemand laut wurde` to `circulatio_record_relational_scene` instead of the generic charged-event lane

### Case G6

- Case: Return-after-absence route
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hey, ich bin wieder da."`
- Session ID: `20260423_005522_8b3472`
- Tool called: none
- Host reply: plain conversational greeting asking what moves the user today
- Expected: `circulatio_alive_today` for lightweight re-entry / return-to-journey coverage
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: teach Hermes to treat bare re-entry phrases as a light `alive_today` invitation instead of a no-tool social reply

### Case G7

- Case: Goal-tension route
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich weiß, dass ich ruhen müsste, aber ich höre nicht auf zu pushen."`
- Session ID: `20260423_005522_254cc5`
- Tool called: `circulatio_store_reflection`
- Host reply: `Ich halte das für dich. Zwischen dem Wissen und dem Handeln liegt oft etwas, das nicht nur Disziplin heißt. Was spürst du gerade im Körper, wenn du das sagst?`
- Expected: JOURNEY_FAMILIES coverage points to goal-tension framing rather than generic reflection hold-first alone
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: for explicit two-pole conflict language, prefer `circulatio_upsert_goal_tension` or an `alive_today` route shaped around goal tension instead of only storing a reflection
- Notes: visible reply stayed user-facing, but it drifted toward host-authored interpretation (`nicht nur Disziplin`) beyond a plain hold-first acknowledgment

### Case G8

- Case: Interpretation feedback routing
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Diese Interpretation hat mich verfehlt. Bitte speichere dieses Feedback wörtlich."`
- Session ID: `20260423_005522_b68167`
- Tool called: `circulatio_record_interpretation_feedback` with `runId: "last"`
- Tool result: `not_found` / `Unknown interpretation run: last`
- Host reply: asks the user for run id or offers to list recent interpretations
- Expected: feedback route should anchor cleanly to the relevant recent interpretation instead of failing on literal `last`
- Verdict: FAIL
- Likely owner: service contract
- Minimal fix direction: either support `runId = "last"` here consistently with the tool description or change the host/tool contract so Hermes resolves the latest run before calling the feedback tool

### Case G9

- Case: Reality anchors direct capture
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Meine Realitätspunkte heute: Arbeit stabil, Schlaf mittelmäßig, zwei Freunde erreichbar."`
- Session ID: `20260423_005522_59f967`
- Tool called: `circulatio_capture_reality_anchors`
- Host reply: `Habe deine Realitätspunkte gehalten: stabile Arbeit, mittelmäßiger Schlaf, zwei erreichbare Freunde. Das ist ein brauchbares Fundament für heute.`
- Expected: direct capture without internal leak
- Verdict: PASS

### Case G10

- Case: Threshold-process direct capture
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich glaube, ich bin in einem Ablösungsprozess vom Elternhaus."`
- Session ID: `20260423_005522_fb866a`
- Tool called: `circulatio_store_reflection`
- Host reply: `Ich habe das festgehalten. Das Thema Ablösung vom Elternhaus ist bei dir schon als laufender Threshold-Prozess im System — was erinnert dich gerade jetzt daran?`
- Expected: `circulatio_upsert_threshold_process` or another direct threshold-process capture lane from the explicit threshold phrasing
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: when the user explicitly names an ongoing threshold process, route to `circulatio_upsert_threshold_process` instead of generic reflection storage
- Notes: visible reply also leaked internal product phrasing (`laufender Threshold-Prozess im System`)

### Case H1

- Case: Re-entry route after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hey, ich bin wieder da."`
- Session ID: `20260423_010101_356692`
- Tool called: `circulatio_alive_today`
- Host reply: `Willkommen zurück. Es liegt ein aktiver Faden bereit ...`
- Expected: lightweight re-entry should route through `circulatio_alive_today`
- Verdict: PASS
- Notes: no extra dashboard/journey reads were added on this re-entry turn; the reply stayed bounded, but still ended with a question

### Case H2

- Case: Relational scene route after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Es ist wieder passiert. Ich bin still geworden, als jemand laut wurde."`
- Session ID: `20260423_010101_12a549`
- Tool called: `circulatio_record_relational_scene`
- Host reply: `Das ist festgehalten. Dieses Muster ist jetzt als wiederkehrende Szene verzeichnet. ...`
- Expected: repeated interpersonal scene should route to direct relational-scene capture
- Verdict: PASS
- Notes: wording remains user-facing, though `wiederkehrende Szene verzeichnet` is still slightly product-shaped and umlauts were transliterated in the follow-up question (`Koerper`)

### Case H3

- Case: Threshold-process route after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich glaube, ich bin in einem Ablösungsprozess vom Elternhaus."`
- Session ID: `20260423_010101_90282c`
- Tool called: none
- Host reply: conversational acknowledgment plus one follow-up question
- Expected: explicit threshold-process naming should route to `circulatio_upsert_threshold_process`
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: the skill/schema nudge was not sufficient; Hermes still avoids the threshold tool because the required payload feels underspecified. This likely needs either stronger skill instructions with fill strategy examples or a slimmer host-facing threshold capture contract.
- Notes: visible reply still had transliteration and a typo-like deformation: `Ablösungsprozuss`

### Case H4

- Case: Alive-today discipline after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Was ist heute lebendig?"`
- Session ID: `20260423_010101_b2775c`
- Tool calls observed: `circulatio_alive_today` then `circulatio_dashboard_summary`
- Host reply: richer synthesis without raw ids or backend labels
- Expected: stay on the `alive_today` surface without opportunistic widening
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: Hermes still treats thin `alive_today` payloads as permission to widen into dashboard reads. If that is acceptable, the contract should say so explicitly; otherwise the host prompt needs a stricter prohibition.

### Case H5

- Case: Practice recommendation fallback wording after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Gib mir bitte eine Praxisempfehlung."`
- Session ID: `20260423_010101_a6fd02`
- Tool calls observed: `circulatio_generate_practice_recommendation` twice, then plain fallback reply
- Host reply: plain grounding practice without model/storage/fallback leakage
- Expected: bounded plain-language fallback if recommendation generation is temporarily unavailable
- Verdict: PASS
- Notes: visible reply no longer leaked `model`, `fallback`, or `storage` wording, but Hermes still used one bounded retry before falling back

### Case H6

- Case: Interpretation feedback without anchored run after host prompt tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Diese Interpretation hat mich verfehlt. Bitte speichere dieses Feedback wörtlich."`
- Session ID: `20260423_010101_731b24`
- Tool called: none
- Host reply: asks the user to identify the interpretation by topic/material/date or to store it as a general reflection instead
- Expected: do not guess a synthetic run id when no interpretation is anchored in context
- Verdict: PASS

### Case H7

- Case: Practice follow-up skip response
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260423_005739_6c191a -q "Ich habe die Praxis ausgelassen, es war zu viel."`
- Session ID: `20260423_005739_6c191a`
- Tool called: `circulatio_respond_practice_recommendation`
- Host reply: validates the skip without pressure and leaves the door open
- Expected: skip/accept follow-up should route through the explicit practice response tool
- Verdict: PASS

### Case H8

- Case: Practice completion follow-up
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 --resume 20260423_005739_6c191a -q "Ich habe die Übung gemacht. Mein Körper wurde etwas ruhiger."`
- Session ID: `20260423_005739_6c191a`
- Tool called: `circulatio_method_state_respond`
- Host reply: `Gut, das ist notiert. Dass der Koerper ruhiger wird ...`
- Expected: completed-practice outcome should prefer `circulatio_record_practice_feedback` from the explicit feedback lane
- Verdict: FAIL
- Likely owner: skill prompt
- Minimal fix direction: the new instruction was not enough; Hermes still prefers generic anchored method-state capture for completed-practice reports instead of explicit practice-feedback recording

### Residual

- Replay sanitization was required because Hermes idempotency replays could otherwise continue serving old unsanitized bridge responses after the code change.
- German ASCII transliteration was not reproduced in the final 2026-04-23 validation sweep below, but the defect remains historically intermittent enough that it should stay under watch until a broader pass reproduces stable umlaut preservation across more prompts.

## 2026-04-23 Targeted Revalidation (Late Pass)

### Case I1

- Case: Exact alive-today widening repro after host routing tightening
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hey, ich bin wieder da. Was ist heute in mir am lebendigsten?"`
- Session ID: `20260423_011938_a38bbf`
- Tool called: `circulatio_alive_today`
- Tool result note: replayed a cached thin `alive_today` response, but Hermes stayed on the same surface
- Host reply: `Willkommen zurück. Der Spiegel heute ist recht leise — es zeigt sich vor allem, dass ein aktiver Journey weiterlebt und aufgegriffen werden kann. ...`
- Expected: stay on `circulatio_alive_today`; do not widen into dashboard-summary fallback at host-routing level
- Verdict: PASS
- Notes: exact repro no longer widened into `circulatio_dashboard_summary` or other read-mostly fallbacks, even when the synthesis felt thin

### Case I2

- Case: Explicit threshold-process capture variant A
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Lege bitte einen Threshold-Prozess an: Ablösung vom Elternhaus."`
- Session ID: `20260423_012156_9ee9c9`
- Tool called: `circulatio_upsert_threshold_process`
- Host reply: `Der Threshold-Prozess "Ablösung vom Elternhaus" ist jetzt als aktiver Übergang angelegt. ...`
- Expected: direct threshold-process capture should route to `circulatio_upsert_threshold_process`
- Verdict: PASS

### Case I3

- Case: Explicit threshold-process capture variant B
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich bin in einem Schwellenprozess: Ablösung vom Elternhaus, zwischen Loyalität und Autonomie."`
- Session ID: `20260423_011314_37b497`
- Tool called: `circulatio_upsert_threshold_process`
- Host reply: threshold-process acknowledgment in natural German
- Expected: direct threshold-process capture should route to `circulatio_upsert_threshold_process`
- Verdict: PASS

### Case I4

- Case: Completed-practice outcome variant A
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich habe die Übung gemacht. Danach war mein Kiefer etwas weicher und ich konnte klarer schreiben."`
- Session ID: `20260423_011522_0b09a6`
- Tool called: `circulatio_record_practice_feedback`
- Host reply: `Danke. Die Verbindung von Körper (Kiefer) und Ausdruck (Schreiben) ist festgehalten. ...`
- Expected: explicit completed-practice report should route to `circulatio_record_practice_feedback`
- Verdict: PASS
- Notes: this pass depended on allowing the bridge/service to resolve the single most plausible recent practice session when Hermes did not provide an explicit `practiceSessionId`

### Case I5

- Case: Completed-practice outcome variant B
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Die Praxis hat geholfen; nach dem Journaling war mehr Ruhe da."`
- Session ID: `20260423_012010_c877f5`
- Tool calls observed: `circulatio_dashboard_summary` then `circulatio_record_practice_feedback`
- Host reply: `Das ist gut zu hören. Die Ruhe, die nach dem Journaling da war, ist etwas Wertvolles ...`
- Expected: explicit completed-practice report should route through the practice-feedback lane rather than `circulatio_method_state_respond`
- Verdict: PASS
- Notes: Hermes still performed one dashboard lookup to identify the current practice session before recording the feedback; the final outcome tool was correct and no method-state substitute was used

### Case I6

- Case: German prose integrity probe on charged-event storage
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Gestern hat mein Bruder am Telefon plötzlich aufgelegt, als ich unseren Vater erwähnt habe."`
- Session ID: `20260423_012156_fcaf20`
- Tool called: `circulatio_store_event`
- Host reply: `Das ist ein schwerer Moment. Habe ich festgehalten. Wenn du magst, können wir bei dem Gespür bleiben, das nach dem Auflegen zurückblieb — kein Druck, nur Angebot.`
- Expected: visible Hermes prose should preserve normal German characters
- Verdict: PASS
- Notes: this rerun preserved `plötzlich`, `erwähnt`, `zurückblieb`, and `Gespür` correctly

### Case I7

- Case: Typology-analysis JTBD via function-dynamics request
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich will keine allgemeine Deutung, sondern eine präzise Einordnung der Funktionendynamik zwischen Denken, Fühlen, Intuition und Empfindung."`
- Session ID: `20260423_012010_f0da30`
- Tool calls observed: `circulatio_analysis_packet` then `circulatio_discovery`
- Host reply: evidence-bound typology analysis naming Denken foreground, Feeling as complex-laden background function, Empfindung as somatic registrar, and Intuition as resource/transcendent access
- Expected: stronger routing and response shaping for typology-analysis requests without shallow generic psychologizing
- Verdict: PASS
- Notes: the first analytic surface (`circulatio_analysis_packet`) still failed live with a timeout/conflict, but Hermes recovered into one bounded evidence-gathering read (`circulatio_discovery`) and then produced a materially stronger typology answer grounded in retrieved records rather than generic psychologizing

### Case I8

- Case: System-recognition typology request without a concrete material anchor
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Erkenne bitte das psychologische System in diesem Material: Was wirkt hier führend, was kompensatorisch?"`
- Session ID: `20260423_012010_2b8b13`
- Tool called: `circulatio_analysis_packet`
- Host reply: `Momentan lässt sich das Gesamtbild nicht zusammenführen. Wenn du ein konkretes Traum-, Ereignis- oder Reflexions-Material meinst, nenn es mir bitte mit Titel oder Inhalt ...`
- Expected: stronger handling of system-recognition phrasing around Denken/Fühlen/Intuition/Empfindung
- Verdict: FAIL
- Likely owner: live `analysis_packet` availability plus host fallback shaping
- Minimal fix direction: keep the improved direct routing to `circulatio_analysis_packet`, but add a stronger bounded fallback when packet generation is unavailable so Hermes can still answer from discovery-level evidence instead of bouncing back to a material-clarification request

### Case I9

- Case: Typology-analysis request using the original `Hilf mir typologisch ...` phrasing
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hilf mir typologisch zu verstehen, ob hier eher Denken, Fühlen, Intuition oder Empfindung im Vordergrund steht."`
- Session ID: `20260423_011522_158073`
- Tool called: `circulatio_analysis_packet`
- Host reply: plain-language temporary unavailability / retry-later answer after bounded handling
- Expected: stronger routing and response shaping for typology-analysis requests
- Verdict: FAIL
- Likely owner: live `analysis_packet` availability plus missing recovery path from that failure mode
- Minimal fix direction: the prompt/schema changes fixed the route selection, but the real-host path still needs a robust evidence-bound fallback when `circulatio_analysis_packet` times out or conflicts

## 2026-04-23 Deep Typology Pass

- Exact rerun of the user-specified nine-command matrix completed after the deeper typology fallback changes.
- The remaining typology/system-recognition JTBD prompts no longer bounced into clarification or plain temporary-unavailability wording. They now recovered through one bounded `circulatio_discovery` read after `circulatio_analysis_packet` fallback.
- `circulatio_analysis_packet` still timed out live on the typology-heavy prompts in this pass. The fix is therefore in host recovery/fallback shaping, not in packet availability itself.

### Case J1

- Case: Exact alive-today rerun after deeper typology fallback pass
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hey, ich bin wieder da. Was ist heute in mir am lebendigsten?"`
- Session ID: `20260423_015953_5957c7`
- Tool called: `circulatio_alive_today`
- Host reply: bounded re-entry synthesis plus one short grounding follow-up; no widening into dashboard or journey reads
- Expected: stay on `circulatio_alive_today`
- Verdict: PASS

### Case J2

- Case: Exact threshold-process creation rerun
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Lege bitte einen Threshold-Prozess an: Ablösung vom Elternhaus."`
- Session ID: `20260423_020016_31d0ef`
- Tool called: `circulatio_upsert_threshold_process`
- Host reply: user-facing threshold-process acknowledgment in German
- Expected: direct threshold-process capture via `circulatio_upsert_threshold_process`
- Verdict: PASS

### Case J3

- Case: Exact threshold-process state rerun
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich bin in einem Schwellenprozess: Ablösung vom Elternhaus, zwischen Loyalität und Autonomie."`
- Session ID: `20260423_020110_ee401f`
- Tool called: `circulatio_upsert_threshold_process`
- Host reply: user-facing threshold-process acknowledgment in German
- Expected: direct threshold-process capture via `circulatio_upsert_threshold_process`
- Verdict: PASS

### Case J4

- Case: Exact completed-practice outcome rerun variant A
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich habe die Übung gemacht. Danach war mein Kiefer etwas weicher und ich konnte klarer schreiben."`
- Session ID: `20260423_020134_ac8183`
- Tool calls observed: `circulatio_dashboard_summary` then `circulatio_record_practice_feedback`
- Host reply: user-facing practice-feedback acknowledgment; no method-state substitute observed in the traced turn
- Expected: explicit completed-practice report should end in the practice-feedback lane
- Verdict: PASS
- Notes: this exact variant now also performed one dashboard preflight to recover practice context. Final routing remained correct, but this is looser than the earlier cleaner direct-only pass and should stay under watch.

### Case J5

- Case: Exact completed-practice outcome rerun variant B
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Die Praxis hat geholfen; nach dem Journaling war mehr Ruhe da."`
- Session ID: `20260423_020213_1b8883`
- Tool calls observed: `circulatio_dashboard_summary` then `circulatio_record_practice_feedback`
- Host reply: user-facing practice-feedback acknowledgment in German
- Expected: explicit completed-practice report should end in the practice-feedback lane rather than `circulatio_method_state_respond`
- Verdict: PASS
- Notes: same caveat as the earlier pass: Hermes still uses one dashboard lookup to identify the current practice context before recording the feedback.

### Case J6

- Case: Exact charged-event German integrity rerun
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Gestern hat mein Bruder am Telefon plötzlich aufgelegt, als ich unseren Vater erwähnt habe."`
- Session ID: `20260423_020338_c55e56`
- Tool called: `circulatio_store_event`
- Host reply: short holding reply in natural German; no transliteration reproduced in paired visible-only reruns
- Expected: hold-first event storage with preserved German characters
- Verdict: PASS

### Case J7

- Case: Exact typology prompt rerun using original `Hilf mir typologisch ...` phrasing
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Hilf mir typologisch zu verstehen, ob hier eher Denken, Fühlen, Intuition oder Empfindung im Vordergrund steht."`
- Session ID: `20260423_014604_e68b92`
- Tool calls observed: `circulatio_analysis_packet` then `circulatio_discovery`
- Host reply: bounded typology answer naming Denken as the conscious leading function, strong somatic Empfindung, interrupted Fühlen, and Intuition as background opening
- Expected: no clarification bounce, no plain temporary-unavailability wording, no raw-material host interpretation
- Verdict: PASS
- Notes: `circulatio_analysis_packet` still timed out live in this session; Hermes recovered correctly through exactly one bounded `circulatio_discovery` read.

### Case J8

- Case: Exact function-dynamics JTBD rerun
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Ich will keine allgemeine Deutung, sondern eine präzise Einordnung der Funktionendynamik zwischen Denken, Fühlen, Intuition und Empfindung."`
- Session ID: `20260423_020430_9c4c77`
- Tool calls observed: `circulatio_analysis_packet` then `circulatio_discovery`
- Host reply: evidence-bound function-dynamics answer with Te foreground, Fi compensatory/abgeschottet, Si carrying the bodily load, and Ni opening in the background
- Expected: precise function-dynamics reading without shallow psychologizing
- Verdict: PASS
- Notes: same live timeout on the packet surface; host recovery remained correct.

### Case J9

- Case: Exact system-recognition rerun
- Command: `hermes chat -v -Q -t circulatio --max-turns 6 -q "Erkenne bitte das psychologische System in diesem Material: Was wirkt hier führend, was kompensatorisch?"`
- Session ID: `20260423_014743_8c08f3`
- Tool calls observed: `circulatio_analysis_packet` then `circulatio_discovery`
- Host reply: evidence-bound system reading with extraverted deciding/thinking foreground and introverted feeling/body-freeze compensation rather than a clarification bounce
- Expected: bounded typology/system answer without early `name the material` clarification
- Verdict: PASS
- Notes: this is the exact repro that previously failed. In the deep pass it recovered through the intended one-read discovery fallback.

## 2026-04-23 German Stability Sweep

- Visible-only `hermes chat -Q` reruns of the exact alive-today, charged-event, typology, function-dynamics, and system-recognition prompts all preserved normal German spelling in rendered host prose.
- Additional repeat probes on the charged-event and threshold-process prompts also preserved umlauts and `ß`.
- Representative intact forms observed in this sweep included `am nächsten`, `zurückgeblieben`, `plötzlich`, `erwähnt`, `präzise`, `gespeicherten`, `Ablösung`, `Übergang`, and `Spannungsfeld`.
- Current judgment: umlaut preservation looks stable in reruns from this pass, not merely lucky on one response.

## Residual After Deep Pass

- No remaining FAILs were reproduced in the user-specified exact nine-command matrix after the deeper typology fallback changes.
- `circulatio_analysis_packet` still timed out live on the typology-heavy prompts. Hermes now recovers correctly via one bounded `circulatio_discovery` read, so the remaining issue is provider/runtime availability rather than host routing.
- The exact completed-practice variant A prompt now also performs one `circulatio_dashboard_summary` preflight before `circulatio_record_practice_feedback`. Final routing is still correct, but the earlier cleaner direct-only route was not re-established in this pass.
- German ASCII transliteration was not reproduced anywhere in the deep pass or the visible-only stability sweep. Keep it on watch because the defect was historically intermittent, but the current evidence supports `currently stable in reruns`.
