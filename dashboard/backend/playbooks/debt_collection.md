# WIZ.AI Debt-Collection Talkbot Playbook (IDN)

Mined from 33 real deployed WIZ.AI debt-collection bots (Indonesian). All script text below is
**verbatim from the corpus** with real PII/amounts/dates replaced by `{placeholders}`. This document is
domain knowledge for an AI bot-builder that emits wiz-builder manifests.

> **Machine-readable companion:** `debt_collection.corpus.json` (same directory) is the structured,
> prevalence-ranked source this prose is derived from — every intent, KB, script archetype, flow engine,
> stage delta, objection→handler map, and disposition-tag pattern with a `count`/`pct` across the 33 bots.
> Re-mined + re-validated 2026-07 via `analysis/debt_mine.py`; counts below match that JSON. Prefer the
> JSON for programmatic ranking; use this prose for authoring guidance.

Corpus families: GoPayLater / GoPayLaterCicil, GoPayPinjam / GoPayPinjam Modal, TokoKapital,
Tiktok Paylater, Kredivo, Indosat/IOH HiFi (telco), PT Clipan Finance, Orico Balimor Finance (auto),
BCA Digital "blu"/bluExtracash, BNI credit card (acquisition). Two shapes:
- **Compact canonical templates** (11-13 components): the clean per-product/`[RELEASED]` bots. Treat as the skeleton.
- **Sprawling multi-flow bots** (54-63 components): `1108 [Main] Due`, `[Main] Overdue DPD1-5/6-10`, `Overdue DPD1-5`, `PTP Reminder`. Same skeleton, expanded into a reason-classified multi-tier convincer ladder with heavy nested-component reuse.

---

## 1. Canonical flow skeleton

The main flow is a **linear collection funnel** built from `category:1` (Main Talk-Flow) components, with
`category:2` (Multi-Round Dialogue) components hanging off it as KB-triggered sub-dialogues. There are **no
type-13 transfer nodes anywhere in the corpus** — "escalation" is always a spoken promise of human callback
("*nanti ada staff kami yang akan menghubungi anda*") ending in an `exit`/hangup, never a live transfer.

### Main flow (category:1), ordered

```
0. Greeting & Confirm (talk)                    ── entry component
   ├─ variable_assignment: Salutation (from GenderX), Platform/ProductEnd/ProductAnda (from Product/Company)
   ├─ conditional: Judgement Male/Female (GenderX), Company (AFI/MAB/MGR…), Product (GPP/GPLC/TKPL…)
   │     → one greeting talk variant per company/product, each opening "Halo, Saya {BotName} dari {Product}.
   │       Apa betul dengan {Salutation} {Name_PERSON_NAME}?"
   ├─ branches: Correct Person → Inform ; Wrong Person → goto_kb Wrong Number ; Unclassified → Unclassified
   └─ goto_kb (type 8) into KBs for all off-script user intents; nested_component for product disambiguation

1. Inform payment (talk)                         ── state the amount + due status, ask to pay now
   "…tagihan anda sebesar {X_Nominal_AMOUNT} … jatuh tempo {Due_date}. Apa bisa dibayarkan sekarang?"
   ├─ branches: Can Pay → Positive Closing ; Cannot Pay → Convincer ; Unclassified → Unclassified
   ├─ variable_assignment: Triggered (mark node visited), Date Collected
   └─ conditional: Date Collected vs Today  → route Positive vs continue

2. Convincer (talk)                              ── objection rebuttal, re-ask to pay
   "Oh saya mengerti keadaan anda, tapi saya sarankan membayar sekarang agar akun tidak terblokir…
    Kalau tidak melunasi hari ini, anda dikenakan denda dan catatan kredit menjadi kurang baik. Bisa kan?"
   ├─ (advanced stages) → 3. Cannot Pay Convincer / Second / Third Convincer (escalating ladder)
   └─ branches: Can Pay → Positive Closing ; Cannot Pay → Negative Closing

3. Positive Closing (exit, terminal)             ── PTP secured
   "Baik, data anda sudah kami catat. Jumlah {X_Nominal_AMOUNT}. Kami tunggu pembayarannya hari ini.
    Jika belum masuk, kami dari {Product} akan menghubungi anda kembali. Terima kasih"

4. Negative Closing (exit, terminal)             ── no commitment
   "Baik, kalau begitu kami tunggu pembayarannya segera ya, agar terhindar dari resiko keterlambatan.
    Jika belum masuk, saya dari {Product} akan terus menghubungi anda. Terima kasih"

Unclassified (exit, terminal)                    ── signal-loss / no parse
   "Mohon maaf sepertinya ada masalah sinyal. Saya hanya ingin mengingatkan…"
```

### Multi-round sub-dialogues (category:2), reached from KBs via goto_kb

These are the branch targets of KB `multi_round` delegation. They speak with **talk_continue (type 5)**
(speak-then-wait, terminal, no ports) and return to the main flow via a `config.target` back-pointer
(`goto_component` back to `1. Inform payment` / `2. Convincer` — the corpus "back to chasing" pattern):

- **Wrong Number** — re-verify identity ("*Hmm, mohon maaf, apa saya sedang berbicara dengan {Salutation} {Name_PERSON_NAME}?*"), branch Correct→resume chasing / Wrong→apology exit.
- **How to pay** — explain channels, then `talk_continue` blank + return-to-chasing.
- **Sp Circumstances** — passed-away / hospitalized / in-prison: sympathy + human callback exit.
- **KBB16 / Hotline / How to Contact** — CS email/phone, `conditional` on Company to pick the right contact.
- **Give Me More Time**, **DPD** (inject overdue-days), **Collect Time / Collect Payment Method** (PTP capture).

### Sprawling-bot expansion (mature shape, e.g. PTP Reminder / Main Overdue)

```
Opening & Inform payment
  → Collect Reason - Cannot Pay (talk: "Ada kendala apa…") classifies Reason into
       {No Time, No Money, Unfortunate, Natural Disaster, Death, General/Busy}
  → reason-specific convincer:  2.1 Busy/General · 2.2 No Money · 2.3 Unfortunate · 2.4 No Time
  → 3. Second Convincer → 4. Third Convincer     (escalating pressure ladder)
  → Collect Time / Cannot Pay - Collect Time (PTP date/time) → Collect Payment Method
  → Tag PTP (goto_kb dummy "KB Tag PTP") → Positive/Negative Closing
  Reusable nested_component subflows: "Cannot Pay - Collect Time", "Collect Time - Today days between",
  "Collect Payment Method", "[Randomize] Emphasize repayment/Convincer".
```

`goto_mr` (type 9, jump between multi-round dialogues) appears **only in the 6 sprawling bots** (1108 Main
Due, Acquisition Top-Up, Main Overdue DPD1-5/6-10, Overdue DPD1-5, PTP Reminder), used to hop between the
reason-convincer sub-dialogues.

---

## 2. Per-stage differences

Delinquency stage drives tone, the number of convincer tiers, whether PTP time/method is captured, and the
consequence language (future penalty vs. accruing penalty vs. credit-score damage).

| Stage | Greeting/Inform tone | Due language | Convincer emphasis | PTP handling | Extra components |
|---|---|---|---|---|---|
| **Predue (D-1)** | Softest; thanks for loyalty ("*kami memahami keadaannya dan terima kasih atas kesetiaan anda*"). | *"akan jatuh tempo pada {Due_date}"* (future). Asks "*rencana pembayaran dalam waktu dekat?*" | Avoid a *future* penalty: *"melunasi sebelum lewat jatuh tempo … supaya terhindar dari denda."* | Captures intended pay date only (`PAYMENT_DATE_INTERVAL`, `DateValue`); "Before Due Date" conditional. | + **Give Me More Time** MR component. No overdue-days. |
| **DPD0 (due today)** | Neutral, businesslike. | *"telah jatuh tempo hari ini. Apa bisa dibayarkan sekarang?"* | Block-account + credit-score: *"agar akun tidak terblokir … dikenakan denda dan catatan kredit menjadi kurang baik."* | Single convincer; collect "Date Collected" vs Today. | Standard 11 comps. |
| **DPD1-5** | Firmer; penalty already exists. | *"sudah lewat dari jatuh tempo sebesar {X_Nominal_AMOUNT}. Tingkat kredit akan turun dan dikenakan biaya keterlambatan tambahan."* | + freeze + hard-to-reborrow: *"akun dibekukan sementara … kedepannya sulit mengajukan kembali pinjaman."* | Adds **Collect time of payment**; 2-tier convincer. | +1-2 comps (Collect Time). |
| **DPD6-10 / DPD10-30** | Insistent, mild pressure. | *"sudah terlambat membayar dari {Overdue_Days} hari yang lalu."* | 3-tier: *"denda akan terus bertambah dan Anda akan kami terus hubungi. Kami sarankan menggunakan tabungan atau bantuan keluarga/teman."* | Full PTP: **2. CANNOT Collect time**, **3. Cannot Pay Convincer**, days-between compute. | + **DPD** MR (inject overdue days), extra convincer + closings. |
| **Overdue 90+** | Repetitive, escalating each turn; randomized convincer variants. | *"sudah lewat dari jatuh tempo. Semakin hari, denda akan semakin bertambah."* | Randomized `{Convincer_1}/{Convincer_2}` injections; may offer keringanan/restructuring gated on ≥90 DPD (see `Terms & Condition` KB). | PTP + payment method + acceleration questions. | 20+ comps; multiple `Emphasize repayment` randomizers. |
| **PTP Reminder** (promise follow-up) | "*janji bayar*"-framed: *"Ada kendala apa sehingga janji bayarnya belum dilakukan?"* | Refers to a prior promise, not first notice. | Reason-classified 4-way convincers → Second → Third; strongest. | Central: re-collect time + method, **Tag PTP > Flow Can't pay**, dummy `KB Tag PTP` to re-flag record. | 60 comps; most elaborate. |

Cross-stage constants: every stage carries the same ~15 system intents, the same identity/objection KB set,
the same closings shape, and the same "human callback" escalation (never a live transfer).

---

## 3. Intent taxonomy (USER-created intents)

`type:"user"` intents. Counts = number of bots (of 33) the exact name appears in; near-universal ones marked ★.
Keywords/user_responses are **verbatim IDN**. Note WIZ intent convention: user intents carry `isInit:1`.

### Payment — how-to-pay / already-paid / when-pay(PTP)
- **Already paid** ★ (32) — kw `[sudah bayar | sudah terbayar]`; ur: "kan saya udah bayar", "kemaren siang udah dibayar", "perasaan saya udah lunas kok", "minggu lalu udah dibayar kok", "iya semalem udah saya bayar".
- **How to pay** (16) — kw `gimana cara bayar | bisa bayar pakai apa | via apa`; ur: "cara bayarnya gimana ya", "pembayarannya bisa melalui apa", "apa aja metode pembayarannya".
- **Bank Account/ VA/ send whatsapp** ★ (32) — kw `[kode | kodenya | rekening]`; ur: "kodenya mana", "nomor registrasinya berapa", "transfer ke mana", "rekening mana".
- **Failed to pay** (31) — kw `gagal bayar | blokir | block | gangguan | failed`; ur: "gagal terus tadi pas bayar", "udah bayar kok tapi gagal", "setiap mau bayar gagal".
- **Mention time of payment** (24) — kw `[jam|siang|sore|malam|sekarang|segera|secepatnya]`; ur: "nanti malam saya bayarnya", "nanti sore saya bayar", "bentar lagi saya bayar".
- **mention later date** (17) — ur: "minggu depan deh mbak saya janji", "lusa bisanya mbak", "besok aja lah kan masih dua hari".
- **Mention Payment Method** (24) — kw `transfer | virtual account | m-banking | BCA | ovo | BNI | BRI`; ur: "mandiri", "lewat minimarket", "lewat ovo mbak", "nanti mampir ke atm".
- **Want to pay in full** (17) — ur: "mending lunas aja sekalian", "langsung semua aja saya lunasin".
- **Can I pay in installments** (31) — kw `dicicil | nyicil | cicil | minimal payment`; ur: "apa bisa dicicil", "diangsur aja ya", "kalau bayarnya cuma setengahnya gimana".
- **Will pay on due date** (11) — ur: "pas jatuh tempo saya bayar", "sesuai jatuh tempo saja".

### Objections — cannot-pay / dispute / negotiate
- **Waive** (31) — kw `pengurangan | potongan | diskon | keringanan`; ur: "saya mau minta keringanan", "boleh dibantu penghapusan bunga gak", "mau bayar tapi tanpa bunga".
- **Can you give me some more time** (31) — kw `tambah waktu | minta waktu | waktu tambahan`; ur: "kasih saya waktu lebih", "dimundurin bayarnya boleh ya", "kasih saya waktu seminggu lagi".
- **Interest too high** (31) / **Admin fee too high** (24) / **Penalty fee too high** (14) — ur: "bunganya tinggi banget sih mbak", "biaya adminnya tinggi", "nyekik leher banget dendanya".
- **Extended fee** (32) / **is that a daily fee** (17) — ur: "ada biaya perpanjangan gak", "ini denda per hari atau gimana", "kok tiap hari nambah dendanya".
- **Money and income reason cannot pay** (21) — ur: "duitnya nggak ada belum tau kapan", "masih nunggu gajian", "nunggu cair dulu ya mbak".
- **No reason cannot pay** (21) — ur: "ya intinya nggak bisa aja Mbak", "saya emang belum mau bayar aja", "gak mau bayar sekarang aja".
- **other priorities cannot pay** (17) — ur: "ada cicilan lain saya", "masih ada hutang lain", "banyak kebutuhan lain".
- **Different Amount** (31) — ur: "kok jadi lebih bayar", "jumlahnya kok beda", "nominalnya kok gak sama".
- **Not Sure** (32) / **Cannot** (17) — ur: "belum bisa kasih kepastian kapan", "saya nggak janji ya mbak", "belum bisa pastiin".

### Identity — wrong-number / not-me / third-party / deceased
- **Who are you looking for?** ★ (32) — kw `nyari siapa | cari siapa`; ur: "mau bicara sama siapa ya", "nyari bapak siapa", "atas nama siapa".
- **Wrong person** (17) / **Wrong number** (7) / **Wrong person - Wrong number** (8) — ur: "orangnya tidak ada", "salah nomor", "salah sambung mbak kayaknya".
- **Loan is not mine** (19) / **Deny Loan/Loan is not mine** (5) — ur: "saya gak ngerasa ada tagihan", "perasaan saya gak pernah pinjam", "atas nama saya tapi bukan saya yang pinjam".
- **Someone use my identity** (6) — ur: "orang lain pakai identitas saya", "kemaren ponakan yang minjem".
- **Incorrect PIC - Immediate family** (11) / **Non-immediate family** (11) / **Know the person** (11) — ur: "saya suaminya", "yang pinjam itu istri saya", "saya temannya saja mbak", "iya betul kenal kok sama ibu anu".
- **In Prison** ★ (32) — kw `bui | penjara | di tahan`; ur: "dia lagi di penjara mbak", "dia lagi dalam proses hukum".
- **Hospitalized** (32) — kw `rumah sakit | sakit | rawat inap | isoman | covid | kecelakaan`; ur: "baru aja masuk rumah sakit", "ada keluarga yang sakit".
- **passed away** (17) — kw `mati | meninggal | berpulang | berduka | makam | kubur`; ur: "sudah berpulang orang nya", "kena covid terus meninggal".
- **I give you another number** (17) — ur: "saya kasih nomor telepon orangnya ya", "hubungin nomor lain aja mbak".

### Logistics — call-back / busy
- **Busy** (24) — ur: "saya nggak ada waktu", "lagi kerja", "lagi salat", "masih adzan ini".
- **Busy - Call back later** (16) / **Call back later** (7) — ur: "bisa hubungi saya kembali nanti ya", "nanti aja Kak masih sekolah online", "bisa nanti di jam makan siang".
- **No Call Back Time** (17) / **Mention Call Back Time** (17) — ur: "nanti malam", "nanti ashar", "ya terserah mbak aja mau nelpon jam berapa".
- **Already contacted** ★ (32) — kw `[sudah ditelepon]`; ur: "baru aja ditelepon berapa hari yang lalu", "tadi saya udah dihubungin", "kenapa telepon terus sih".
- **Stop calling me** ★ (32) — ur: "udah jangan telpon telpon lagi", "berhenti nelponin saya bisa gak", "tolong keluarkan nomor saya dari list".
- **Will call CS/ Hotline** ★ (32) / **HotLine Number** (17) — ur: "oke saya telepon dulu saja", "ada nomor yang bisa saya hubungi".
- **How long does this call take** (4) — ur: "kira kira berapa menit", "telponnya lama nggak mbak".

### Sentiment / trust — angry / agree / suspicious
- **Will report to police/ other institution** (31) — kw `lapor | polisi | adukan | pengacara | ylki`; ur: "saya laporkan ke pihak berwajib loh", "saya laporin ke polisi ya".
- **User Complain/Curse** (8) — kw `bego | goblok | anjing | bangsat | rese`; ur: "aduh ganggu banget", "aku mau komplain".
- **Are you a robot** (17) / **Are you a bot** (15) — kw `robot | robo call`; ur: "ini ngomongnya kayak robot banget", "ini mesin ya yang ngomong", "saya lagi ngomong sama ai ya".
- **Is it Legal? / Is this legal / Is this a scam / Is this trusted** (~13 combined) — ur: "ini pinjaman tipu tipu ya", "kalian legal kan", "penipuan ya ini", "di indonesia legal kan".
- **Why do you have / Where did you get my number** (6) — ur: "dapat nomor ini dari mana ya", "kok bisa dapat data saya".
- **Clear Explanation** (17) / **Not clear explanation** (17) — ur: "oke ngerti", "jelas sekali" / "gak begitu jelas tadi", "saya masih kurang paham".
- **Forget to pay** (17) — kw `lupa | kelupaan`; ur: "aduh saya kelupaan", "oh iya saya lupa mbak maaf".
- **Natural Disaster** (9) — kw `banjir | gempa | kebakaran | longsor | bencana`; ur: "abis banjir rusak semua", "ada gempa bumi jadi saya kehilangan rumah".

**Recur in ≈every bot (build these first, prevalence-ranked from `debt_collection.corpus.json`):**
Already paid (32/33), Bank Account/VA (32), Extended fee (32), In Prison (32), Hospitalized (32),
Already contacted (32), Stop calling me (32), Will call CS/Hotline (32), Who are you looking for? (32),
Not Sure (32), Repeat Amount (32), Waive (31), Failed to pay (31), Can I pay in installments (31),
Different Amount (31), Can you give me some more time (31), Interest too high (31),
Will report to police (31).

**Telco (Indosat/IOH) & acquisition (BNI) add domain intents:** Move from Post-paid to Pre-paid, Change
Package, How to Activate Number, Never/No Longer Use Indosat HiFi, Package Info, Credit Limit, Requirements
for applying, KTP Rejected/Not Match, NIK not registered, prescreening, Interest Rate, Annual Fee.

---

## 4. KB archetypes

KBs are **intent-triggered business KBs** (`conditions:"null"`, Intent Trigger). Naming is highly regular:
`KBG#` = generic/opening KBs, `KBB#` = business/collection KBs, `KB#` = per-product variants. Two response
modes: **single-answer** (most) and **multi-round** (`answerType:2` delegate → a category:2 component that
speaks `talk_continue` then returns to chasing). `{Product}/{Platform}/{ProductEnd}` parameterize the brand.

### System KBs present in EVERY bot (12, do not re-author)
`Can not hear clearly`, `AI can not hear clearly`, `No answer`, `AI wait`, `User hesitate`, `Interrupt`,
`Global unclassified`, `Chasing statement`, `Answering Machine`, `DNC`, `Echo Monitoring`,
`Transferring to Human Agent`. Sample answers: No answer → *"Halo? Apa suara saya terdengar jelas? Saya mohon
kerjasamanya untuk membayar tagihannya hari ini…"*; Global unclassified → *"Maaf saya masih kurang jelas
boleh tolong diulang"*; Answering Machine → *"Saya hanya ingin mengingatkan anda untuk melunasi tagihan
{Product}. Kami tunggu pembayarannya paling lambat hari ini ya. Terima Kasih."*

### Core collection KB set (recurring, single-answer unless noted)
| KB (canonical) | Trigger intents | Representative answer |
|---|---|---|
| **KBG1/KB1. Who are you / Where calling from** | Where you calling from | *"Um, Saya {BotName} menelepon dari {ProductEnd}."* |
| **KBG3/KB3. What is this regarding / What bill** | What loan/which merchant | *"Anda pernah melakukan transaksi {Product}. Tanggal jatuh tempo tagihan anda adalah {Due_date}. Nah, saya menelepon mengenai tagihan yang belum anda bayarkan."* |
| **KBG2/KB2. Is this a scam / Legal** | Is it Legal?, Is this a scam/trusted | *"Bukan penipuan, kami sudah terdaftar dan diawasi oleh OJK"* |
| **KBG4/KB4. Are you a robot** | Are you a robot/bot | *"Hmm, saya adalah asisten {ProductEnd}."* |
| **KBG5. Wrong number** *(multi-round)* | Wrong person | re-verify identity sub-dialogue → resume/apology exit |
| **KBG6. Already called** | Already contacted | *"Oh kalau begitu kami mohon maaf. Saya Asisten Virtual {Product} mengucapkan terima kasih…"* |
| **KBG7. Busy / Call back** | Busy | *"Baik, saya Asisten Virtual {Product} akan menghubungi kembali yaa. Terima kasih"* |
| **KBB3. Forgot to pay** | Forget to pay | *"Oh kalau begitu tolong segera dibayarkan sekarang ya"* |
| **KBB5. Due date** *(mr in some)* | KB8. Due date | *"Sebenarnya jatuh temponya hari ini."* / *"…sudah terlambat membayar dari {Overdue_Days}"* |
| **KBB6. Amount due** | Repeat Amount, what is the balance | *"Total tagihan yang harus dibayar saat ini sejumlah {X_Nominal_AMOUNT}. Mohon dibayarkan sekarang…"* |
| **KBB1. Failed payment** | Failed to pay | *"Hal ini jarang terjadi, mohon login ke aplikasi {Platform} untuk mengecek tagihan dan melihat nomor Virtual Account…"* |
| **KBB10. How to pay** *(multi-round)* | kb 18 how to pay | channel explanation sub-dialogue |
| **KBB7. Waive/Discount** | Waive | *"Mohon maaf untuk saat ini kami belum bisa memberikan keringanan… Silahkan membayar penuh tagihannya."* |
| **KBB8. Penalty for non payment** | Extended fee, is that a daily fee | *"Kalau anda terlambat membayar, nanti akan ada biaya keterlambatan. Biaya keterlambatan bertambah setelah lewat 7 hari…"* |
| **KBB18. Admin/Interest too high** | Interest/Admin fee too high | *"Oh, kalau anda membayar hari ini, tidak akan terkena biaya keterlambatan…"* |
| **KBB19. Installment/Partial** | Can I pay in installments | *"Mohon maaf kami belum bisa menerima pembayaran dengan cicilan untuk saat ini."* |
| **KBB11. Already Paid** | Already paid | *"Oh Baik, mohon maaf sudah mengganggu waktu anda. Kami akan konfirmasi lagi di sistem…"* |
| **KBB4. Give me more time** *(multi-round)* | Can you give me some more time | time-negotiation sub-dialogue |
| **KBB9. Special circumstances** *(multi-round)* | passed away, Hospitalized, In Prison | sympathy + human-callback |
| **KBB13. Stop calling me** | Stop calling me | *"Oh kalau begitu saya mohon maaf. Sebagai asisten virtual, saya hanya ingin mengingatkan mengenai tagihan anda di {Product}…"* |
| **KBB14. Will report to police** | Will report to police | *"Kami memohon maaf atas ketidaknyamanan… saya sudah mencatat nomor telepon anda dan nanti ada staff kami yang akan menghubungi…"* |
| **KBB22. Deny Loan** | Loan is not mine | *"…tagihan ini terdaftar atas nama anda dan menggunakan nomor telepon anda, jadi saya hanya ingin mengingatkan untuk melakukan pembayaran…"* |
| **KBB16. Hotline/Email/How to contact** *(mr in some)* | HotLine Number, Will call CS, What's your email | *"Jika anda mengalami kesulitan apapun, mohon hubungi customer service kami lewat email {cs_email} atau chat di aplikasi…"* |
| **KBB17. Office** | KB 17 office | *"Untuk lokasi kantor, anda bisa mengunjungi website resmi {Platform}."* |
| **KBB24. Want to pay in full** | Want to pay in full | *"Oh silakan… bisa menggunakan metode pembayaran yang ada di aplikasi {Platform}, jumlah penuhnya sesuai dengan di aplikasi ya"* |
| **KBB20. Different Amount** | Different Amount | *"…tagihan yang saya sebutkan tadi adalah jumlah terbaru… bisa dikarenakan tambahan biaya keterlambatan. Staff kami akan menghubungi anda kembali ya."* |
| **Dummy KB / KB Tag PTP** | empty / "cannot pay" | dummy answer (`"a"`, `{GENDER}`, `{Customer_Category}`) — used to **tag the record as PTP** or seed variables, not to speak. |

**Multi-round KB pattern (deploy-verified):** KBG5 Wrong Number, KBB10 How to pay, KBB4 Give me more time,
KBB9/KB15 Sp Circumstances, KBB16 Hotline all delegate into category:2 components whose nodes are
`talk_continue` (speak the answer, wait), optionally ending with a `goto_component` "back to chasing"
return-target (main-flow category:1). Multi-round also used for opening splits ("opening-wrong person",
"opening-know pic") and "Cannot Pay to Trigger" / "Tag PTP" flagging.

**Telco/finance variants** substitute a hotline number for the app: e.g. Indosat KB20 →
*"…hubungi customer care kami di nomor {phone} atau melalui Whatsapp {wa}"*; Clipan → *"call center 1500-375
atau email cs@clipan.co.id"*; auto/Orico → *"021 5033 6000 … website www.obf.id"*. bluExtracash uses
`{HOTLINE}` and `{Greeting_Closing}` placeholders throughout.

---

## 5. Script archetypes (verbatim, per node ROLE)

Placeholders: `{Salutation}`/`{SALUTATION}` (Bapak/Ibu), `{Name_PERSON_NAME}`/`{CUSTOMER_PERSON_NAME}`,
`{Product}`/`{ProductEnd}`/`{ProductAnda}`/`{Platform}`, `{X_Nominal_AMOUNT}`/`{BALANCE_AMOUNT}`,
`{Due_date}`/`{DUE_DATE}`, `{Overdue_Days}`/`{NO_OF_DPD}`, `{Greetings}`, `{Convincer_1}`/`{Convincer_2}`.
`/`-separated segments in one node are **rotation variants** (WIZ picks one) — a core corpus device for
sounding non-robotic; always author 2-3 per talk node.

### Greeting + identity confirm (talk; branches Correct/Wrong Person/Unclassified)
- *"Halo, Saya Nia dari {Product}. [Apakah betul saya berbicara dengan {Salutation} {Name_PERSON_NAME}?] / [Ini dengan {Salutation} {Name_PERSON_NAME}, betul ya?] / [Apa betul dengan {Salutation} {Name_PERSON_NAME} yang berbicara?]"*
- *"{Greetings} Saya Alfa dari blu by BCA Digital. [Apakah benar ini dengan {SALUTATION} {CUSTOMER_PERSON_NAME}?] / Apakah saya berbicara dengan [{SALUTATION} {CUSTOMER_PERSON_NAME}?]"*

### Identity-verify / wrong number (talk in a category:2 sub-dialogue)
- *"Hmm, mohon maaf, apa saya sedang berbicara dengan [{Salutation} {Name_PERSON_NAME}?] / Apa benar ini dengan [{Salutation} {Name_PERSON_NAME}?]"*
- *"Baik, mohon maaf apa kenal dengan [{SALUTATION} {CUSTOMER_PERSON_NAME}?]"*

### Inform amount / due (talk; Can Pay / Cannot Pay / Unclassified)
- (DPD0) *"Baik, saya hanya ingin mengkonfirmasi, bahwa pembayaran anda sebesar {X_Nominal_AMOUNT} di {Product} telah jatuh tempo hari ini. Apa bisa dibayarkan sekarang? / Pembayaran anda belum kami terima, Bisa ya dibayar sekarang?"*
- (Predue) *"Um.. jadi, saya menelepon, hanya untuk mengingatkan mengenai tagihan anda di {Product}, yang akan jatuh tempo pada [{Due_date}, sebesar {X_Nominal_AMOUNT}.] … Apakah ada rencana pembayaran dalam waktu dekat?"*
- (DPD1-5) *"Um, jadi saya menelepon untuk memberitahukan bahwa {ProductAnda}, sudah lewat dari jatuh tempo sebesar [{X_Nominal_AMOUNT}.] Tingkat kredit Anda akan turun dan akan dikenakan biaya keterlambatan tambahan jika tagihannya tidak dibayar. Apa bisa dibayarkan sekarang?"*

### Convincer / negotiation (talk; escalating by tier)
- (Tier 1) *"Oh, saya mengerti keadaan anda, tapi saya sarankan untuk membayar sekarang agar akun {ProductAnda} tidak terblokir dan layanannya tetap bisa anda gunakan. Kalau anda tidak melunasi hari ini, anda akan dikenakan denda dan catatan kredit anda akan menjadi kurang baik…"*
- (Tier 2) *"Baik, apabila tidak dilunasi hari ini maka catatan kredit anda akan menurun dan akun anda akan dibekukan sementara. Dan kedepannya akan sulit untuk mengajukan kembali pinjamannya. Apa bisa kan ya dilunasi hari ini?"*
- (Tier 3) *"Tapi tagihan Anda sudah terlambat. Jika tidak segera dilunasi hari ini, denda akan terus bertambah dan Anda akan kami terus hubungi. Kami sarankan mencoba menggunakan tabungan atau bantuan keluarga/teman. Bisa diusahakan untuk dibayar hari ini?"*
- (Overdue 90+, randomized) *"Oh begitu, tapi tagihannya sudah jatuh tempo. Supaya denda tidak semakin besar, [Apa bisa dibayarkan hari ini {SALUTATION_2}] / {Convincer_1} / {Convincer_2}"*

### Collect commitment / PTP (talk)
- *"Hmm kalau begitu, kira-kira anda akan melakukan pembayaran tanggal berapa ya? / Kira-kira akan dibayarkan tanggal berapa ya?"*
- *"Bisa di infokan nanti pembayarannya akan melalui apa? / Pembayarannya akan dilakukan melalui apa ya?"*
- (PTP reminder) *"Ada kendala apa sehingga janji bayarnya belum dilakukan? / Um, ada kendala apa ya yang menghambat pembayarannya?"*

### Handle cannot-pay / collect reason (talk → classify Reason)
- *"Mohon konfirmasi apakah ada alasan khusus yang menyebabkan belum bisa melakukan pembayaran? / Boleh saya tahu alasannya kenapa belum bisa membayar?"*

### Handle already-paid (KB answer / exit)
- *"Oh Baik, mohon maaf sudah mengganggu waktu anda. Kami akan konfirmasi lagi di sistem. Saya Asisten Virtual dari {Product} mengucapkan terima kasih dan selamat beraktifitas kembali"*

### Wrong number / not-me (exit)
- *"Oh, mohon maaf sudah mengganggu waktu Anda, terima kasih dan semoga hari anda menyenangkan."*
- (deny loan) *"…Namun tagihan ini terdaftar atas nama anda dan menggunakan nomor telepon anda, jadi saya hanya ingin mengingatkan untuk melakukan pembayaran agar anda tidak dikenakan biaya keterlambatan…"*

### Escalation / human callback (there is NO live transfer — this is the substitute)
- *"Oh baik, untuk mengenai hal ini, saya sebagai asisten virtual {Product} sudah mencatat nomor telepon anda dan nanti ada staff kami yang akan menghubungi anda segera ya. Terima kasih"*
- (deceased) *"Baik, saya turut berduka cita mendengar kabar tersebut ya. Mohon hubungi ke call center kami agar bisa dibantu lebih lanjut, karena kami perlu informasi mengenai siapa yang akan melanjutkan pembayaran tagihan ini. Terimakasih."*

### Positive closing (exit, terminal)
- *"Baik, data anda sudah kami catat ya. Jumlah yang harus anda bayarkan saat ini adalah sebesar {X_Nominal_AMOUNT}. Kami tunggu pembayarannya hari ini. Jika pembayarannya belum masuk, kami dari {Product} akan menghubungi anda kembali. Terima kasih"*

### Negative closing (exit, terminal)
- *"Baik, kalau begitu kami tunggu pembayarannya segera ya, agar terhindar dari resiko keterlambatan. Jika pembayarannya belum masuk, saya dari {Product} akan terus menghubungi anda kembali. Terima kasih"*

### Unclassified / signal-loss (exit, terminal)
- *"Mohon maaf sepertinya ada masalah sinyal. Saya hanya ingin mengingatkan anda untuk melunasi tagihan {ProductAnda}. Kami tunggu pembayarannya paling lambat hari ini ya. Kalau belum ada pembayaran masuk kami akan menghubungi kembali. Terima kasih."*

---

## 6. Routing / variable conventions

Node-type census across the 33 bots (why routing dominates): `variable_assignment` 880, `conditional` 748,
`goto_component` 615, `exit_port` 472, `talk` 366, `exit` 275, `talk_continue` 229, `nested_component` 163,
`goto_kb` 101, `goto_mr` 19, **`transfer` 0**.

### Recurring variables (by frequency)
- **`Date Collected` (583), `Today` (413), `Time Collected` (274), `Date Collected 2`/`Time Collected 2`, `Days between` / `Days between Can Pay` (109/96)** — the **PTP capture + horizon engine**. Pattern: capture the promised date/time into `Date Collected`, then a `conditional` compares `Date Collected` vs `Today` (branches `Today` / `Not Today` / `IsNull`) and computes `Days between` to decide Positive-close-now vs collect-more vs escalate. Reused via nested components `Cannot Pay - Collect Time` and `Collect Time - Today days between`.
- **`Triggered` (120), `Convincer` / `2nd Convincer` / `3rd Convincer` / `CONV_C1/CONV_C2`** — visited-flags and convincer-tier counters so the ladder advances once per objection and doesn't repeat.
- **`Payment Method` (98), `Collect Payment` (24)** — captured channel; conditional `Check if Payment Method Exists` gates whether to ask.
- **`Salutation`/`SALUTATION` (93/73), `Name_PERSON_NAME`/`CUSTOMER_PERSON_NAME`, `GenderX`/`GENDER`** — an `assign` sets `Salutation`="Bapak"/"Ibu" from a `conditional` on `GenderX` (Male/Female/Default) before the greeting.
- **`Product`/`ProductEnd`/`ProductAnda`/`Platform`/`Company`** — brand routing. `conditional` on `Company` (AFI/MAB/MGR) or `Product` (GPP/GPLC/TKPL) picks the greeting variant and CS-contact string; an `assign` block sets the `Platform/ProductEnd/ProductAnda` trio per brand.
- **`Reason` (88)** — cannot-pay reason class {No Time, No Money, Unfortunate, Natural Disaster, Death, General/Busy}; a `conditional` on `Reason` fans out to the matching convincer sub-flow.
- **`PTP` (36), `Next Week Payment`/`Next Month Payment` (26 each), `PAYMENT_DATE_INTERVAL`/`DateValue`, `Payment date interval`** — promise bucketing / PTP tag.
- **`Greeting_Bahasa` (65), `Greeting_Time`/`Greeting_Closing`, `Call Time`** — time-of-day greeting; a "Custom Greeting Time Range" component conditionals on `Call Time` → Morning/Afternoon/Evening/Default.
- **`X_Nominal_AMOUNT` / `BALANCE_AMOUNT`, `Due_date`/`DUE_DATE`, `Overdue_Days`/`NO_OF_DPD`, `Customer_ID`, `Random Value`** — injected system/collected fields (amount, dates, DPD, random for A/B rotation).

### Branch-name conventions
Talk out-ports are almost always a subset of **`Positive` / `Negative` / `Unclassified`** relabeled to the
local decision: `Correct Person` / `Wrong Person` / `Unclassified`; `Can Pay` / `Cannot Pay` / `Unclassified`;
`Clear` / `Not Clear` / `Unclassified`. `conditional` ports use domain names + a `Default` fallback port
(`Today`/`Not Today`/`Default`, `Male`/`Female`/`Default`, `AFI`/`MAB`/`MGR`/`Default`, per-Reason). `assign`
has a single `Default` out-port.

### Hot-words (global, ASR boost)
Every bot ships a **global** `BizNodeHotWords` row (empty nodeId). The standard debt lexicon:
`Legal, OJK, call center, hotline, jatuh tempo, deadline, jatoh tempo, denda, bayar, uang, tagihan, nyicil,
cicil, hutang, ngutang, utang, virtual account, va, banking, bca, brimo, brilink, alfamart, indomart,
tokopedia, bukalapak`, plus **brand names** (atome, paylater, tiktok, gojek, kredivo, blu) and **payment
channels**. Acquisition/telco bots add domain terms (`bpjs, npwp, sim, paspor, ijazah, tenor, limit, approve,
prescreening`). Spelled-letter forms appear as spaced tokens (`o j k`, `b c a`, `v a`).

---

## 7. Builder-manifest implications (for wiz-builder YAML)

A mature per-stage debt manifest should contain:

**Canvases (category:1 main flow):** `0. Greeting & Confirm` (entry) → `1. Inform payment` → `2. Convincer`
(+ `3. Cannot Pay Convincer` / `Second` / `Third` for DPD≥6) → `Positive Closing` → `Negative Closing` →
`Unclassified`. For overdue stages add reason routing: a `Collect Reason` talk + `conditional` on `Reason`
fanning to per-reason convincer canvases, then `Collect Time` / `Collect Payment Method`. Every canvas needs
its own terminal `exit` (WIZ107); wire all Positive/Negative/Unclassified branches.

**Node types actually used (author these; note the two heavy specials):**
- `talk` with **2-3 `/`-separated rotation variants** per prompt; ports limited to **Positive/Negative/Unclassified** (relabeled).
- `conditional` for every routing decision (gender→salutation, company/product→greeting+contact, Date Collected vs Today, Reason fan-out) — always include a `Default` branch.
- `assign` to set `Salutation`, the `Platform/ProductEnd/ProductAnda` trio, `Triggered`/convincer counters, and captured `Date Collected`/`Payment Method`. Remember: a `conditional` may only branch on a var that was assigned earlier or is system/collected.
- `goto_kb` (type 8) from the greeting/inform nodes into the KB set for all off-script intents.
- **`talk_continue` (type 5)** — the body of every multi-round KB sub-dialogue (speak answer, wait), optionally with `config.target` = a main-flow canvas to "return to chasing". Heavy use.
- **`goto_mr` (type 9)** — only for large bots that hop between multi-round reason-convincer sub-dialogues.
- `nested_component` + `exit_port` for reusable subflows (Collect Time, Collect Payment Method, Emphasize/Convincer randomizer).
- **No `transfer` (type 13)** — model escalation as a spoken "staff will call you back" + `exit`.

**custom_intents:** declare the ~17 near-universal user intents from §3 with their verbatim IDN
`keywords` (comma) and `user_responses` (semicolon). Do **not** redeclare the 15 baseline system intents
(User hesitate, AI wait, Positive, Interrupt, Negative, Echo Monitoring, Reject, Chasing statement,
Unclassified, Transferring to Human Agent, Can not hear clearly, DNC, No answer, AI can not hear clearly,
Answering Machine).

**knowledge_bases:** author the KBG#/KBB# collection set (§4) as intent-triggered
(`conditions:"null"`, custom intents `isInit:1`). Single-answer for most; `multi_round: <canvas>` for Wrong
Number, How to pay, Give me more time, Sp Circumstances, Hotline. Do not redeclare the 12 baseline system KBs.
Parameterize brand/amount/date via `{Product}/{Platform}/{X_Nominal_AMOUNT}/{Due_date}` etc.

**Stage tuning (§2):** swap the due-language and consequence-emphasis strings and the number of convincer
tiers; Predue = softest + future-penalty + Give-More-Time; DPD0 = neutral + block/credit; DPD1-5 = penalty
exists + freeze; DPD6-30 = accruing denda + "tabungan/keluarga/teman" + overdue-days injection; 90+/PTP =
randomized convincers + keringanan gate + PTP re-tag.

**hot_words:** one global list (§6). **IDN only** (`node_language "3"`), matching the corpus.

**Corpus gotchas to preserve:** talk ports are Positive/Negative/Unclassified only; the `/`-rotation-variant
convention is essential for naturalness; the PTP engine is `Date Collected`+`Today`+`Days between` conditionals
(reuse via nested components); brand routing is `Company`/`Product` conditionals feeding an `assign` trio;
"Tag PTP"/"Dummy KB" are deliberate dummy-answer KBs used to flag records, not to speak.
