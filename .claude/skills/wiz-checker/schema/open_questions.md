# Open Questions for Phase B — WIZ.AI Spot-Check

These questions arise from schema discovery (Task 18) using two real WIZ sample
files.  They require confirmation from WIZ.AI documentation or support.

---

## Encoding

- [ ] Are top-level collection values **always** JSON-encoded strings in WIZ
  exports, or is this only in older export versions?  (Both 2025 sample files
  use the string-encoded format.)

---

## BizSpeechComponent

- [ ] What does `category` represent semantically?  Observed values: `1`, `2`.
  Is there a value `3` (or higher)?  What does each value mean?

- [ ] What does `type` represent?  Observed value: `1` only.

- [ ] Is `language` (int) on BizSpeechComponent the same concept as the
  `language` string field on SpeechIntent?  Observed values: `0`, absent.

- [ ] What is `editStatus`?  Observed value: `2` only.

- [ ] What is `useStatus`?  Observed values: `1`, `2`.

- [ ] `details` vs `topFloorDetails`: what is the semantic distinction?
  `details` holds the full canvas dict keyed by UUID;
  `topFloorDetails` holds a flat list of top-level node data objects.

---

## FlowNode

- [ ] Confirm: `parentId == ""` means root node (no parent) in all WIZ exports.
  (The legacy/fixture format uses JSON null for this.)

- [ ] What is `editStatus` on FlowNode?  Observed values: `1`, `2`.

- [ ] What is `useStatus` on FlowNode?  Observed values: `1`, `2`.

- [ ] `value` field on FlowNode equals `uuid` in all observed data — is this
  always so, or can `value` differ from `uuid`?

- [ ] `sortIndexABS` vs `sortIndex` — what is the difference?

---

## SpeechIntent

- [ ] Are `keyWordInIntent` and `userResponseInIntent` always JSON-encoded
  strings (never plain lists) in real WIZ exports?

- [ ] What languages besides `IDN` are actually used in production?
  `ENG` and `ZHO` were inferred but not observed in either sample file.

- [ ] Is `isInit` meaningful for required/fallback intent classification?

---

## SpeechVariable

- [ ] What do `type` values `0` and `1` mean (free-form vs enum)?

- [ ] Is `variableSource` always present, or is it optional?

- [ ] What are all valid `textType` values beyond the observed set
  (`""`, `DEFAULT`, `DATE`, `EMAIL`, `PHONE`)?

---

## SentenceCutSpeech / SentenceCutKnowledge

- [ ] What does `type` (string) mean?  Observed values: `"record"`, `"tts"`.
  Are there other values?

- [ ] Is `sentenceTextUrl` always empty for TTS entries and always populated for
  `"record"` entries?

---

## VoiceRecord

- [ ] What does `category` represent?  Observed values: `1`, `2`, `3`, `4`.
  Are there other values?

---

## BizSpeechScene

- [ ] What does `languageItem` (string) `"3"` represent?

- [ ] What does `type` value `1` represent on BizSpeechScene?

- [ ] Is `ragSwitch` always `0` (off) or can it be `1`?

---

## Intent Rules

- [ ] Confirm which intents from the "present in both files" set are truly
  **required** for a valid WIZ speech (vs project-specific).

- [ ] Is `"Unclassified"` the canonical catch-all name, or is `"Unspecified"`
  also used?  (Both were observed but not in the same file.)

- [ ] Is `"DNC"` (Do Not Call) always required for compliance?

---

## General

- [ ] Are there WIZ speech exports that do **not** include `SpeechInspection`
  or `VoiceRecord`?  (Both were non-empty in the observed files.)

- [ ] What keys can appear at the top level beyond the 25–26 observed?  In
  particular, `SpeechEntry` was absent in one file — is it always optional?

- [ ] Are there schema version indicators anywhere in the export format?
  (No version field was observed at the top level.)
