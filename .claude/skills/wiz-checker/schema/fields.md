# WIZ.AI Export Schema — Field Reference

Generated from real sample files:
- `talkbot/Test+Kinan/speech13139256226648334285.json` (400 KB, 25 top-level keys)
- `talkbot/Tiktok+Paylater+DPD0/speech4892384019254584542.json` (1.2 MB, 26 top-level keys)

**Important**: Top-level collection values are **JSON-encoded strings** (not
already-parsed arrays/objects) in real WIZ exports.  The parser calls
`json.loads()` on each value before processing.

---

## AsrScene

Stores ASR (Automatic Speech Recognition) scene configuration entries.

- Both observed files contain an empty array.
- Fields: unknown (no data observed).
- ID field: unknown. <!-- TODO: verify with WIZ.AI -->

---

## BizKnowledgeInfo

Knowledge base (FAQ/KB) node configurations attached to components.

| Field | Python type | Notes |
|---|---|---|
| allowInterrupt | int | 0/1 flag |
| answerType | int | # TODO: verify with WIZ.AI |
| branch | str | observed: `"dev"` |
| canInterruptPercent | float | e.g. 80.0 |
| conditions | str | JSON-encoded string |
| createId | int | user/creator ID |
| createTime | int | epoch-ms |
| enableUse | int | 0/1 flag |
| engineType | str | # TODO: verify with WIZ.AI |
| exclusiveKeyWords | str | JSON-encoded list |
| forceHangup | int | 0/1 flag |
| intentionJudgmentTime | float | |
| intents | str | JSON-encoded list |
| interruptRecognitionThresholdSwitch | int | 0/1 flag |
| isDelete | int | soft-delete flag |
| isInit | int | 0/1 flag |
| isTransfer | int | 0/1 flag |
| kdInfo | str | knowledge data info (JSON string) |
| kdTitle | str | knowledge node title |
| kdType | int | # TODO: verify with WIZ.AI |
| knowledgeId | int | |
| modifyId | int | |
| modifyTime | int | epoch-ms |
| nodeResponseDurationSwitch | int | |
| noticeSendType | int | |
| noticesInfo | str | JSON-encoded |
| recordNum | int | |
| repeatScriptType | int | |
| soundexMatch | int | |
| speakType | int | |
| speechId | int | FK → BizSpeechScene.speechId |
| tagList | str | JSON-encoded |
| threshold | str | |
| timeout | int | |
| valueAssignment | str | JSON-encoded |
| wordNum | int | |

ID field: `knowledgeId` (int).

---

## BizNodeHotWords

Hot-word (boosted vocabulary) lists attached to individual flow nodes.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| componentUuid | str | UUID string |
| createId | int | |
| createTime | int | epoch-ms |
| engineType | str | # TODO: verify with WIZ.AI |
| hotWords | str | JSON-encoded list of hot-word strings |
| hotWordsIndustryId | int | |
| id | int | primary key |
| isDelete | int | soft-delete flag |
| modifyId | int | |
| modifyTime | int | epoch-ms |
| nodeId | str | UUID string referencing a flow node |
| speechId | int | |
| status | int | # TODO: verify with WIZ.AI |
| templateCode | str | |

ID field: `id` (int).

---

## BizSpeechComponent

Top-level flow components (conversation branches / modules).  Each component
owns a `details` field containing the full flow graph for that branch.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| category | int | observed: `1`, `2` — see `known_component_categories` |
| componentUuid | str | UUID — primary key |
| createBy | int | |
| createTime | int | epoch-ms |
| details | str | JSON-encoded dict keyed by node-UUID (see below) |
| editStatus | int | observed: `2` |
| id | int | numeric ID |
| inboundPorts | str | JSON-encoded |
| language | int | observed: `0`, `None` (missing) |
| name | str | display name |
| nluConf | str | JSON-encoded NLU config |
| outboundPorts | str | JSON-encoded |
| parentUuid | str | UUID of parent component (or empty string) |
| routes | str | JSON-encoded routing rules |
| sortIndex | int | |
| sourceUuid | str | |
| speechId | int | |
| templateCode | str | |
| topFloorDetails | str | JSON-encoded list of top-level node data objects |
| type | int | observed: `1` |
| updateBy | int | |
| updateTime | int | epoch-ms |
| useStatus | int | observed: `1`, `2` |

ID field: `componentUuid` (UUID string).

### `details` sub-structure (real WIZ format)

The `details` value, when decoded, is a **dict keyed by node UUID**:

```
{
  "<node-uuid>": {
    "canvas": {
      "component": {
        "props": {
          "list": [<FlowNode>, ...],
          "text": "<node name>",
          "type": <int>
        }
      }
    },
    "data": { ... },
    "data_extra": { ... },
    "id": "<uuid>",
    "is_default": <bool>,
    "name": "<node name>",
    "type": <int>
  },
  ...
}
```

FlowNode entries inside `props.list` (see **FlowNode** section below).

**Legacy / fixture format**: the JSON string decodes to `{"list": [...]}` with
a flat array of FlowNode dicts.  The parser accepts both.

---

## BizSpeechScene

Singleton dict (not a list) with global speech configuration.

| Field | Python type | Notes |
|---|---|---|
| asrEffectHeighten | str | JSON-encoded dict |
| asrInfo | str | JSON-encoded ASR provider config |
| botSetting | str | JSON-encoded bot-level settings |
| branch | str | observed: `"dev"` |
| business | int | |
| createId | int | |
| createTime | int | epoch-ms |
| enterpriseId | int | |
| hotwordsIndustryId | int | |
| invalidateStatus | int | |
| isDelete | int | soft-delete |
| languageItem | str | # TODO: verify with WIZ.AI |
| mark | str | free-text remark |
| modifyId | int | |
| modifyTime | int | epoch-ms |
| ragLlmRange | str | (file2 only) # TODO: verify with WIZ.AI |
| ragSwitch | int | 0/1 flag for RAG |
| releaseTime | int | (file2 only) epoch-ms |
| scenarioNo | str | e.g. `"General Talkbot"` |
| semanticSimilarity | str | JSON-encoded |
| speechCode | str | template code |
| speechId | int | primary speech ID |
| speechName | str | human-readable name |
| status | int | |
| ttsInfo | str | JSON-encoded TTS provider info |
| type | int | observed: `1` |

ID field: `speechId` (int).

---

## CorrectionWord

Correction / error-word pairs for ASR post-processing.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| componentUuid | str | |
| correction | str | correct word/phrase |
| createTime | int | epoch-ms |
| errorCorrectionType | int | |
| errorWords | str | word to be corrected |
| id | int | primary key |
| isDelete | int | |
| modifyTime | int | |
| nodeIndex | str | |
| speechId | int | |
| templateCode | str | |
| type | int | # TODO: verify with WIZ.AI |

ID field: `id` (int).

---

## FlowNode (nested inside BizSpeechComponent.details)

Individual conversation steps/branches inside a component.

| Field | Python type | Notes |
|---|---|---|
| children | list | nested child FlowNode dicts (real WIZ format only) |
| componentUuid | str | UUID — matches parent component's UUID |
| editStatus | int | observed: `1`, `2` |
| hangUpRate | str | e.g. `"0.0%"` |
| hitRate | str | e.g. `"33.3%"` |
| label | str | display name / section header |
| parentId | str | UUID of parent node, or `""` for root (real WIZ); `null` in fixtures |
| sortIndex | int | ordering within parent |
| sortIndexABS | int | absolute ordering across all nodes |
| title | str | same as label in observed data |
| useStatus | int | observed: `1`, `2` |
| uuid | str | UUID — primary key |
| value | str | UUID string (same as uuid in observed data) |

ID field: `uuid` (UUID string).

Note: `parentId == ""` means no parent (root node) in real WIZ exports.
The legacy/fixture format uses `null` (Python `None`) instead.

---

## IntentionLabel

Singleton dict (not a list) with call-outcome label configuration.

| Field | Python type | Notes |
|---|---|---|
| entId | int | enterprise ID |
| intentionLabelFinal | dict | final label assignment |
| intentionLabelList | list | list of label definitions |
| intentionLabelRuleList | list | list of label rules |
| speechId | int | |
| templateCode | str | |

---

## SentenceCutKnowledge

Knowledge-base (FAQ) audio sentence cuts / recordings.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| id | str | UUID string |
| isDelete | int | |
| knowledgeId | int | |
| knowledgeRecCutId | int | |
| senRecName | str | recording name |
| sentenceText | str | TTS text |
| sentenceTextUrl | str | audio URL |
| showType | int | |
| speechId | int | |
| speechRecCutId | str | |
| type | str | # TODO: verify with WIZ.AI |

ID field: `id` (UUID string).

---

## SentenceCutMultiple

Multi-language / multiple-option sentence cuts.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| componentUuid | str | UUID |
| id | str | UUID |
| isDelete | int | |
| senRecName | str | |
| sentenceCutId | int | |
| sentenceText | str | |
| sentenceTextUrl | str | |
| showType | int | |
| sortIndex | int | |
| speechId | int | |
| speechRecCutId | str | |
| type | str | # TODO: verify with WIZ.AI |

ID field: `id` (UUID string).

---

## SentenceCutSpeech

Bot dialogue sentence cuts (spoken utterances per component node).

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| componentUuid | str | UUID — links back to a BizSpeechComponent |
| id | str | UUID — primary key |
| isDelete | int | soft-delete flag |
| senRecName | str | recording name |
| sentenceCutId | int | numeric cut ID |
| sentenceText | str | TTS text; may contain `{VariableName}` refs |
| sentenceTextUrl | str | audio file URL |
| showType | int | |
| sortIndex | int | ordering within the component |
| speechId | int | |
| speechRecCutId | str | |
| type | str | observed: `"record"`, `"tts"` # TODO: verify with WIZ.AI |

ID field: `id` (UUID string).

---

## SpeechAudio

Audio profiles (voice/recording settings) for the speech.

| Field | Python type | Notes |
|---|---|---|
| audioId | int | primary key |
| audioName | str | e.g. `"Nirmala"`, `"Female"` |
| branch | str | observed: `"dev"` |
| createBy | int | |
| createTime | int | epoch-ms |
| isDenoise | int | 0/1 |
| isEnable | int | 0/1 |
| isSilence | int | 0/1 |
| recorderName | str | |
| speechId | int | |
| templateCode | str | |
| ttsInfo | str | JSON-encoded TTS settings per language |
| updateBy | int | |
| updateTime | int | epoch-ms |
| version | str | |

ID field: `audioId` (int).

---

## SpeechDictionary

Custom pronunciation dictionaries.

| Field | Python type | Notes |
|---|---|---|
| allCount | int | total entry count |
| branch | str | observed: `"dev"` |
| createBy | int | |
| createTime | int | epoch-ms |
| dictName | str | dictionary name |
| dictType | int | # TODO: verify with WIZ.AI |
| enableState | int | 0/1 |
| enterpriseId | int | |
| id | int | primary key |
| isDelete | int | |
| recordingCount | int | |
| speechId | int | |
| templateCode | str | |
| updateBy | int | |
| updateTime | int | epoch-ms |

ID field: `id` (int).

---

## SpeechEntity

Custom NER entity types.  Both observed files: empty list.  Fields unknown.
<!-- TODO: verify with WIZ.AI -->

---

## SpeechEntityData

Training data for custom NER entities.  Both observed files: empty list.
<!-- TODO: verify with WIZ.AI -->

---

## SpeechEntityNer

Named-entity recognition configuration.  Both observed files: empty list.
<!-- TODO: verify with WIZ.AI -->

---

## SpeechEntry

Dictionary entries (only present in Tiktok+Paylater+DPD0 file; absent in
Test+Kinan file).

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| createBy | int | |
| createTime | int | epoch-ms |
| delete | int | soft-delete flag |
| dictId | int | FK → SpeechDictionary.id |
| entryName | str | the word/phrase entry |
| id | int | primary key |
| recordUrl | str | pronunciation audio URL |
| updateBy | int | |
| updateTime | int | epoch-ms |

ID field: `id` (int).

---

## SpeechFunction

Custom function definitions (e.g. regexes, API calls).

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| createId | int | |
| createTime | int | epoch-ms |
| funcCode | str | function code identifier |
| funcId | str | UUID string |
| funcName | str | |
| funcOutput | str | JSON-encoded |
| funcRegex | str | regex pattern |
| funcType | str | # TODO: verify with WIZ.AI |
| id | int | numeric ID |
| name | str | |
| params | str | JSON-encoded |
| status | int | |
| templateCode | str | |
| updateId | int | |
| updateTime | int | epoch-ms |

ID field: `id` (int) or `funcId` (UUID string). <!-- TODO: verify with WIZ.AI -->

---

## SpeechInspection

Quality-inspection rule sets for call review.

| Field | Python type | Notes |
|---|---|---|
| bizInspectionRuleDetailEntities | list | nested rule detail objects |
| defaultType | int | |
| id | int | primary key |
| inspectionJson | str | JSON-encoded inspection rules |
| name | str | ruleset name |
| priority | int | |
| speechId | int | |
| type | int | # TODO: verify with WIZ.AI |

ID field: `id` (int).

---

## SpeechInspectionResultType

List of strings naming possible call-inspection outcomes.

Observed values across both files: `"PT Checked"`, `"Complain"`, `"Answering Machine"`.

---

## SpeechIntent

NLU intent definitions used across the dialogue.

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| createTime | int | epoch-ms |
| intentId | int | primary key |
| intentName | str | display name |
| isDelete | int | soft-delete flag |
| isInit | int | 0/1 — system/init intent flag |
| keyWordInIntent | str | JSON-encoded list of keyword strings |
| language | str | e.g. `"IDN"` — see `known_intent_languages` |
| nodeId | str | UUID string |
| speechId | int | |
| templateCode | str | |
| updateTime | int | epoch-ms |
| userResponseInIntent | str | JSON-encoded list of user response strings |

ID field: `intentId` (int).

Note: `keyWordInIntent` and `userResponseInIntent` are JSON-encoded strings in
real WIZ exports (the parser decodes them automatically).

---

## SpeechRules

Global dialogue flow rules (e.g. escalation, redirection).

| Field | Python type | Notes |
|---|---|---|
| branch | str | observed: `"dev"` |
| createBy | int | |
| createTime | int | epoch-ms |
| id | int | primary key |
| intentCode | str | intent identifier |
| name | str | rule name |
| priority | int | |
| ruleJson | str | JSON-encoded rule logic |
| speechId | int | |
| status | int | |
| type | int | # TODO: verify with WIZ.AI |

ID field: `id` (int).

---

## SpeechTag

Call-tagging configuration (post-call labels).

| Field | Python type | Notes |
|---|---|---|
| bizTagPropertyDTOS | list | nested tag-property objects |
| createTime | int | epoch-ms |
| entId | int | enterprise ID |
| id | int | primary key |
| isMutex | int | 0/1 — mutually-exclusive flag |
| modifyTime | int | epoch-ms |
| name | str | tag name |
| tagProperty | int | # TODO: verify with WIZ.AI |
| type | int | # TODO: verify with WIZ.AI |

ID field: `id` (int).

---

## SpeechVariable

Variable definitions used in bot utterances and logic.

| Field | Python type | Notes |
|---|---|---|
| beInit | int | 0/1 — whether variable should be initialized |
| branch | str | observed: `"dev"` |
| createTime | int | epoch-ms |
| enumVariable | int | 0/1 — whether variable is enum-type |
| id | int | primary key |
| name | str | variable name (used in `{Name}` refs) |
| remark | str | (optional) human description |
| speechId | int | |
| templateCode | str | |
| textType | str | observed: `""`, `"DATE"`, `"DEFAULT"`, `"EMAIL"`, `"PHONE"` |
| type | int | observed: `0`, `1` # TODO: verify with WIZ.AI |
| userId | int | |
| variableSource | int | (optional) # TODO: verify with WIZ.AI |
| varialbeFuncAssign | dict | (optional) function assignment config |

ID field: `id` (int).

---

## SpeechVariableH5

H5/web-channel variable definitions.  Both observed files: empty list.
<!-- TODO: verify with WIZ.AI -->

---

## VoiceRecord

Recording metadata linking audio files to script cuts.

| Field | Python type | Notes |
|---|---|---|
| audioId | int | FK → SpeechAudio.audioId |
| branch | str | observed: `"dev"` |
| category | int | observed: `1`, `2`, `3`, `4` # TODO: verify with WIZ.AI |
| cutId | str | UUID string |
| id | int | primary key |
| recordName | str | |
| recordUrl | str | audio file URL |
| speechId | int | |
| templateCode | str | |
| type | str | observed: `"record"`, `"tts"` |
| version | str | |

ID field: `id` (int).

---

## kbTag

List of knowledge-base tag IDs (integers).  File1: empty list.
File2: list of 4 integers (tag IDs referencing SpeechTag.id).
