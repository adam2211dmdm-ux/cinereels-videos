# The Last Message / الرسالة الأخيرة

**Original drama series for CineReels — 5 episodes × 90 seconds (1:30 each)**
**Total runtime: 7:30. Format: vertical 9:16.**
**PRIMARY LANGUAGE: ENGLISH. All dialogue is spoken in English; Arabic subtitles are the translation (subtitle_default: "ar").**
**Genre: family drama / mystery. Tone: quiet, intimate, then tense — a hook in the first 5 seconds of every episode, a cliffhanger in the last 10 seconds.**

> **Language rule for the whole series:** actors speak **English**. Every line below is given **English first (the spoken line)**, then the **Arabic translation (for subtitles)**. The `.vtt` files follow the same rule: `episodeX_en.vtt` = primary English dialogue, `episodeX_ar.vtt` = Arabic translation of the same lines, same timestamps.

## Characters

| Character | EN | AR |
|---|---|---|
| Layla, 30 | Heroine. Quiet, stubborn, living alone since her mother's death. | بطلة القصة. هادئة، عنيدة، تعيش وحدها بعد وفاة أمها. |
| Mother (voice only) | Voice recording only. Warm and sad. Never appears on screen. | صوت مسجّل فقط، دافئ وحزين. لا تظهر أبدًا. |
| Omar, 34 | Layla's brother. Practical, protective, hiding things. | أخو ليلى. عملي، يخاف عليها، يخفي أشياء. |
| Father, 62 | Silent, tired, carrying a 30-year secret. | صامت، متعب، يحمل سرًا منذ 30 سنة. |
| Sara, 28 | Appears in Ep 4. A younger version of their mother. | تظهر في الحلقة 4. نسخة أصغر من الأم. |

## Story arc (one line)

Layla receives a voice message scheduled a year ago by her late mother — each message sends her one step closer to a sister she never knew existed.

**قصة مختصرة:** ليلى تستقبل رسالة صوتية مجدولة منذ سنة من أمها المتوفاة — كل رسالة تقرّبها خطوة من أخت لم تعرف بوجودها أبدًا.

## How sequential playback works

Episodes are numbered 1–5 (`episodeNumber`, `seriesId: "last-message"`). In the app, **SeriesPlayer** plays Ep 1 → on end, a 3-second countdown → Ep 2 automatically, and so on to Ep 5. No looping inside a series. Swipe up = next episode, swipe down = previous. History saves `seriesId + lastEpisode + positionSec` so **Continue** resumes where the viewer stopped. See `flutter/lib/widgets/series_player.dart` and `flutter/lib/screens/series_detail_screen.dart`.

## GitHub auto-load

The app can load these episodes (and any new videos) from a `videos.json` manifest hosted on GitHub — no app rebuild needed. See `github-videos/videos.json` and `github-videos/README_GITHUB_AR.md`. Each video in the manifest declares `"language": "en"` and `"subtitle_default": "ar"`.

## Production notes (all episodes)

- **Location:** Ep 1 Layla's flat at night; Ep 2 the old family house (dusty, one lamp); Ep 3 same house + kitchen table; Ep 4 father's house / doorway; Ep 5 the old house, morning light.
- **Props:** phone, old key under the stairs, a blue envelope, a torn family photo, a cassette / old phone, two cups of tea.
- **Look:** dark, warm lamp light, close-ups on the phone and on Layla's eyes. No music in the first 5 seconds — let the phone sound do the hook. Soft piano only under the mother's voice.
- **Language on set:** shoot in **English**. Arabic is subtitles only — do not dub or re-shoot in Arabic.
- **Shooting tip:** shoot each episode in one location, 6–8 short shots, vertical framing, actor looks into the phone camera once per episode (direct address = retention).

---

# Episode 1 — The Message / الحلقة 1 — الرسالة

**Hook:** A voice message from my mother… a year after she died.
**Hook (AR):** رسالة صوتية من أمي… بعد سنة من وفاتها.

## Timed beats (0:00–1:30)

| Time | Beat (EN) | Beat (AR) |
|---|---|---|
| 0:00–0:08 | Night. Layla alone. Phone buzzes. | ليلى وحدها في شقتها ليلًا. الهاتف يهتز على الطاولة. |
| 0:08–0:20 | She presses play. Her mother's voice. | تضغط "تشغيل". صوت أمها يملأ الغرفة. |
| 0:20–0:35 | Shock — she drops the phone. | الصدمة: الهاتف يسقط من يدها. |
| 0:35–0:50 | She calls Omar. He doesn't believe her. | تتصل بعمر. لا يصدّقها. |
| 0:50–1:05 | She checks the date: scheduled a year ago. | تفحص التاريخ: الرسالة مجدولة منذ سنة. |
| 1:05–1:20 | Mother's instruction: go back to the old house. | تعليمات الأم: ارجعي إلى البيت القديم. |
| 1:20–1:30 | **Cliffhanger:** a second message arrives from the same number. | رسالة ثانية تصل من نفس الرقم. |

## Dialogue — ENGLISH first (spoken), Arabic translation second

> **Layla:** It's two in the morning… who messages now?
> **ليلى:** الساعة الثانية بعد منتصف الليل… من يرسل الآن؟
>
> **Layla:** A voice message… from my mother?
> **ليلى:** رسالة صوتية… من أمي؟
>
> **Mother (voice):** Layla, my love… if you're hearing this, then I'm gone.
> **الأم (صوت):** ليلى، حبيبتي… لو بتسمعي ده، يبقى أنا مش موجودة.
>
> **Mother:** I recorded this message a year before I left.
> **الأم:** أنا سجّلت الرسالة دي قبل ما أمشي بسنة.
>
> **Mother:** Don't be afraid… I'm still with you.
> **الأم:** متخافيش… أنا لسه معاكي.
>
> **Layla:** Impossible… my mother died a year ago.
> **ليلى:** مستحيل… أمي ماتت من سنة.
>
> **Layla (on the phone):** Omar, listen… that's Mama's voice, isn't it?
> **ليلى (في الهاتف):** عمر، اسمع… دي صوت ماما، مش كده؟
>
> **Omar:** It really is her voice… but this can't be happening.
> **عمر:** صوتها فعلاً… بس ده مستحيل يحصل.
>
> **Layla:** The message sent itself… scheduled a year ago.
> **ليلى:** الرسالة اتبعتت لوحدها… متجدولة من سنة.
>
> **Mother:** Go back to the old house, Layla… before it's sold.
> **الأم:** ارجعي البيت القديم يا ليلى… قبل ما يتباع.
>
> **Layla:** The house was sold two months ago… how does she know?
> **ليلى:** البيت اتباع من شهرين… إزاي عارفة؟
>
> **Mother:** There's something waiting for you there… under the stairs.
> **الأم:** فيه حاجة مستنياكي هناك… تحت السلم.
>
> **Mother:** If you heard this message… don't be late.
> **الأم:** لو سمعتي الرسالة دي… متتأخريش.
>
> **Layla:** A new message arrived… from the same number.
> **ليلى:** رسالة جديدة وصلت… من نفس الرقم.
>
> **Mother:** Layla… I'm still here.
> **الأم:** ليلى… أنا لسه هنا.

**Cliffhanger:** Who is sending the messages? And did their mother really die?
**Cliffhanger (AR):** من يرسل الرسائل؟ وهل الأم فعلًا ماتت؟

## Production notes — Ep 1

- **Location:** Layla's flat, living room, night. One lamp, phone on the table.
- **Props:** phone, a framed photo of the mother on the shelf.
- **Mood:** silence, then shock. Keep the mother's voice soft — never loud.

---

# Episode 2 — The Old House / الحلقة 2 — البيت القديم

**Hook:** The house was sold… but the door was open.
**Hook (AR):** البيت اتباع… بس الباب كان مفتوح.

## Timed beats (0:00–1:30)

| Time | Beat (EN) | Beat (AR) |
|---|---|---|
| 0:00–0:10 | Layla outside the old house at dawn. | ليلى أمام البيت القديم عند الفجر. |
| 0:10–0:22 | The door is open. She steps in. | الباب مفتوح. تدخل بحذر. |
| 0:22–0:38 | Dust, silence, her childhood room. | غبار وصمت، وغرفتها القديمة. |
| 0:38–0:52 | She looks under the stairs. A key. | تنظر تحت السلم. تجد مفتاحًا. |
| 0:52–1:08 | The key opens a small drawer. A blue envelope. | المفتاح يفتح درجًا صغيرًا. ظرف أزرق. |
| 1:08–1:20 | She opens it — a torn photo of two girls. | تفتحه — صورة ممزقة لفتاتين. |
| 1:20–1:30 | **Cliffhanger:** one of the girls is her. The other — she doesn't know. | إحدى الفتاتين هي هي. الأخرى — لا تعرفها. |

## Dialogue — ENGLISH first (spoken), Arabic translation second

> **Layla:** The house was sold two months ago… why is the door open?
> **ليلى:** البيت اتباع من شهرين… ليه الباب مفتوح؟
>
> **Layla:** Mama… I'm here. Like you asked.
> **ليلى:** ماما… أنا جيت. زي ما طلبتي.
>
> **Layla:** Everything is just as it was… even the smell of the house.
> **ليلى:** كل حاجة زي ما هي… حتى ريحة البيت.
>
> **Layla:** Under the stairs… she said under the stairs.
> **ليلى:** تحت السلم… قالت تحت السلم.
>
> **Layla:** A key? What is this key for?
> **ليلى:** مفتاح؟ مفتاح إيه ده؟
>
> **Layla:** The small drawer… it never opened when I was little.
> **ليلى:** الدرج الصغير… عمره ما اتفتح وأنا صغيرة.
>
> **Layla:** A blue envelope… in Mama's handwriting.
> **ليلى:** ظرف أزرق… بخط ماما.
>
> **Mother (voice message):** Open it, Layla… and read to the end.
> **الأم (صوت من الرسالة):** افتحيه يا ليلى… واقري للآخر.
>
> **Layla:** A photo… torn in half.
> **ليلى:** صورة… ممزقة من النص.
>
> **Layla:** That's me… when I was seven.
> **ليلى:** دي أنا… وأنا عندي سبع سنين.
>
> **Layla:** And the girl next to me… who is she?
> **ليلى:** والبنت اللي جنبي… مين دي؟
>
> **Mother:** She is your sister, Layla.
> **الأم:** هي أختك يا ليلى.

**Cliffhanger:** Layla has a sister she never heard of — who is she?
**Cliffhanger (AR):** ليلى لها أخت لم تسمع عنها أبدًا — من هي؟

## Production notes — Ep 2

- **Location:** old family house, hallway + stairs, morning light through a dusty window.
- **Props:** old key, small drawer, blue envelope, torn photo.
- **Mood:** nostalgia turning to unease. Shoot the stairs from below — the key in close-up.

---

# Episode 3 — The Secret / الحلقة 3 — السر

**Hook:** "You have a sister… her name is Sara."
**Hook (AR):** "ليكي أخت… اسمها سارة."

## Timed beats (0:00–1:30)

| Time | Beat (EN) | Beat (AR) |
|---|---|---|
| 0:00–0:10 | Layla reads the letter at the kitchen table. | ليلى تقرأ الرسالة على طاولة المطبخ. |
| 0:10–0:25 | The letter: her mother hid a daughter. | الرسالة: أمها أخفت ابنة. |
| 0:25–0:40 | Flash of memory: a girl at the window, years ago. | ومضة ذكرى: فتاة عند النافذة منذ سنوات. |
| 0:40–0:55 | Layla calls Omar — he goes silent. | تتصل بعمر — يصمت فجأة. |
| 0:55–1:10 | Omar: "Dad said no one must know." | عمر: "بابا قال محدش يعرف." |
| 1:10–1:20 | The letter's last line: an address. | السطر الأخير في الرسالة: عنوان. |
| 1:20–1:30 | **Cliffhanger:** Layla looks up the address — Sara lives 10 minutes away. | تبحث عن العنوان — سارة تسكن على بعد عشر دقائق. |

## Dialogue — ENGLISH first (spoken), Arabic translation second

> **Layla (reading):** "You have a sister… her name is Sara."
> **ليلى (تقرأ):** "ليكي أخت… اسمها سارة."
>
> **Layla:** Sara? I never heard that name in my life.
> **ليلى:** سارة؟ أنا عمري ما سمعت الاسم ده.
>
> **Mother (in the letter):** Sara was born two years before you… and lived far from us.
> **الأم (في الرسالة):** سارة اتولدت قبلِك بسنتين… وعاشت بعيد عننا.
>
> **Mother:** Not because we didn't love her… because we were afraid for her.
> **الأم:** مش لأننا محبيناهاش… لأننا خفنا عليها.
>
> **Layla:** Afraid for her from what? From whom?
> **ليلى:** خفتوا عليها من إيه؟ من مين؟
>
> **Layla (on the phone):** Omar… there's something you have to tell me. Now.
> **ليلى (في الهاتف):** عمر… فيه حاجة لازم تقولهالي. دلوقتي.
>
> **Omar:** Layla… I know. I've known for a long time.
> **عمر:** ليلى… أنا عارف. من زمان.
>
> **Omar:** Dad said no one must know… not even you.
> **عمر:** بابا قال محدش يعرف… حتى انتي.
>
> **Layla:** My sister is alive… and you hid her from me for 30 years?
> **ليلى:** أختي عايشة… وانتوا خبيتوا عليّا 30 سنة؟
>
> **Mother:** Forgive me, Layla… I was a coward.
> **الأم:** سامحيني يا ليلى… أنا كنت جبانة.
>
> **Layla:** The address… it's written here. The last line.
> **ليلى:** العنوان… مكتوب هنا. آخر سطر.
>
> **Layla:** Ten minutes from here… Sara lives ten minutes from here.
> **ليلى:** عشر دقائق من هنا… سارة ساكنة عشر دقائق من هنا.

**Cliffhanger:** Does Layla go to Sara now, or confront her father first?
**Cliffhanger (AR):** هل تذهب ليلى إلى سارة الآن، أم تواجه أباها أولًا؟

## Production notes — Ep 3

- **Location:** old house kitchen, one table, the blue envelope, tea gone cold.
- **Props:** letter (handwritten, blue ink), phone, the torn photo.
- **Mood:** the letter is the scene — hold the camera on Layla's hands shaking.

---

# Episode 4 — The Confrontation / الحلقة 4 — المواجهة

**Hook:** "Dad… who is Sara?"
**Hook (AR):** "بابا… مين سارة؟"

## Timed beats (0:00–1:30)

| Time | Beat (EN) | Beat (AR) |
|---|---|---|
| 0:00–0:10 | Layla at her father's door. He opens, sees the photo. | ليلى على باب أبيها. يفتح، يرى الصورة. |
| 0:10–0:25 | Father goes pale. "Where did you get this?" | وجه الأب يشحب. "جبتي دي منين؟" |
| 0:25–0:45 | The truth, piece by piece: Sara's mother died; Sara went to her aunt. | الحقيقة قطعة قطعة: أم سارة ماتت؛ سارة عاشت عند خالتها. |
| 0:45–1:00 | Layla: "Why did you leave her alone?" Father breaks. | ليلى: "ليه سبتوها لوحدها؟" الأب ينهار. |
| 1:00–1:15 | A knock. A young woman at the door — Sara. | طرق على الباب. شابة تقف هناك — سارة. |
| 1:15–1:30 | **Cliffhanger:** Sara: "I know you're Layla… Mama sent me a message too." | سارة: "أنا عارفة إنك ليلى… ماما بعتتلي رسالة برضه." |

## Dialogue — ENGLISH first (spoken), Arabic translation second

> **Layla:** Dad… who is Sara?
> **ليلى:** بابا… مين سارة؟
>
> **Father:** Where did you get this photo? Who gave it to you?
> **الأب:** منين جبتي الصورة دي؟ مين ادهالك؟
>
> **Layla:** Mama… from the message. Mama told me.
> **ليلى:** ماما… من الرسالة. ماما اللي قالتلي.
>
> **Father:** Your mother… loved you both. More than herself.
> **الأب:** أمك… كانت بتحبكوا انتوا الاتنين. أكتر من نفسها.
>
> **Father:** Sara's mother died giving birth to her… and Sara went to her aunt.
> **الأب:** أم سارة ماتت وهي بتولدها… وسارة راحت لخالتها.
>
> **Layla:** And why did no one tell me? Why did I live 30 years alone?
> **ليلى:** وليه محدش قالّي؟ ليه عشت 30 سنة لوحدي؟
>
> **Father:** We were afraid… afraid of losing you too.
> **الأب:** خفنا… خفنا نخسرك انتي كمان.
>
> **Layla:** You lost me… and you lost Sara.
> **ليلى:** انتوا خسرتوني… وخسرتوا سارة.
>
> **Father:** Forgive me, my daughter… I'm tired of this secret.
> **الأب:** سامحني يا بنتي… أنا تعبت من السر ده.
>
> **Layla:** Someone's at the door…
> **ليلى:** فيه حد على الباب…
>
> **Sara:** I'm Sara… your sister.
> **سارة:** أنا سارة… أختك.
>
> **Sara:** I know you're Layla… Mama sent me a message too.
> **سارة:** أنا عارفة إنك ليلى… ماما بعتتلي رسالة برضه.

**Cliffhanger:** The messages weren't only for Layla — Sara got one too. What did it say?
**Cliffhanger (AR):** الرسائل لم تكن لليلى وحدها — سارة تلقّت رسالة أيضًا. ماذا قالت لها؟

## Production notes — Ep 4

- **Location:** father's house, doorway + living room, evening.
- **Props:** torn photo, two cups of tea (one untouched — for Sara), father's old jacket on the chair.
- **Mood:** the loudest episode — raised voices, then total silence when Sara appears. Let Sara's entrance be quiet.

---

# Episode 5 — The Truth / الحلقة 5 — الحقيقة

**Hook:** The last message… wasn't only for Layla.
**Hook (AR):** الرسالة الأخيرة… لم تكن لليلى وحدها.

## Timed beats (0:00–1:30)

| Time | Beat (EN) | Beat (AR) |
|---|---|---|
| 0:00–0:12 | The two sisters sit together. Sara plays her message. | الأختان تجلسان معًا. سارة تشغّل رسالتها. |
| 0:12–0:30 | Mother's voice, to both: "You are my family." | صوت الأم، للاثنتين: "انتوا عيلتي." |
| 0:30–0:50 | The mother's plan: the house is for both of them. | خطة الأم: البيت لهما معًا. |
| 0:50–1:05 | Layla and Sara hold the torn photo — together it is whole. | تمسكان الصورة الممزقة — معًا تصبح كاملة. |
| 1:05–1:20 | Father and Omar arrive. Silence, then an embrace. | يصل الأب وعمر. صمت، ثم عناق. |
| 1:20–1:30 | **Final line:** Layla, to camera: "The last message… arrived." | ليلى للكاميرا: "الرسالة الأخيرة… وصلت." |

## Dialogue — ENGLISH first (spoken), Arabic translation second

> **Sara:** Mama sent me the same message… but in a different voice. A laughing voice.
> **سارة:** ماما بعتتلي نفس الرسالة… بس بصوت مختلف. بصوت بيضحك.
>
> **Mother (voice):** Sara… Layla… if you're hearing this together, then my plan worked.
> **الأم (صوت):** سارة… ليلى… لو انتوا سامعين ده مع بعض، يبقى خطتي نجحت.
>
> **Mother:** You are my family… both of you. Not just one.
> **الأم:** انتوا عيلتي… انتوا الاتنين. مش واحدة بس.
>
> **Mother:** The old house is not for sale… the house is for both of you.
> **الأم:** البيت القديم مش للبيع… البيت ليكوا انتوا الاتنين.
>
> **Layla:** She planned all of this… a year ago.
> **ليلى:** هي خططت لكل ده… من سنة.
>
> **Sara:** She knew we'd find each other… even if she wasn't here.
> **سارة:** هي كانت عارفة إننا هنلاقي بعض… حتى لو هي مش هنا.
>
> **Layla:** The photo… if we put the two halves together…
> **ليلى:** الصورة… لو حطينا النصين جنب بعض…
>
> **Sara:** It's whole. Just like us.
> **سارة:** بتبقى كاملة. زيّنا بالظبط.
>
> **Omar:** I'm sorry… I'm sorry to both of you.
> **عمر:** أنا آسف… أنا آسف ليكوا انتوا الاتنين.
>
> **Father:** Your mother was the bravest of us all.
> **الأب:** أمكوا كانت أشجع واحدة فينا.
>
> **Mother:** Don't forget each other… ever.
> **الأم:** متنسوش بعض… أبدًا.
>
> **Layla (to camera):** The last message… arrived.
> **ليلى (للكاميرا):** الرسالة الأخيرة… وصلت.

**Ending (not a cliffhanger — a closing):** The family gathers in the old house and the messages stop. Open ending for Season 2: "Mama left one last message… for Omar."
**Ending (AR):** العائلة تجتمع في البيت القديم، والرسائل تتوقف. النهاية مفتوحة لموسم ثانٍ: "ماما سابت رسالة أخيرة… لعمر."

## Production notes — Ep 5

- **Location:** old house, morning light, all four characters in one frame at the end.
- **Props:** the two halves of the photo taped together, two cups of tea, the blue envelope (empty now).
- **Mood:** quiet, warm, tears allowed. Final shot: the sisters' hands holding the whole photo, camera pulls up slowly.

---

## Subtitle files

All dialogue above is also shipped as WebVTT in `subtitles/`:
`episode1_ar.vtt`, `episode1_en.vtt`, … `episode5_ar.vtt`, `episode5_en.vtt` — timestamps 00:00–01:30, matching this script line for line.
**`episodeX_en.vtt` = primary English dialogue (what the actors say). `episodeX_ar.vtt` = Arabic translation of the same lines (subtitles only).** The app's default subtitle language for this series is Arabic (`subtitle_default: "ar"`), switchable to English or Off.

## Copyright note

This is an **original** story written for CineReels. No copyrighted film, series or music is used. The demo video files in the app are Blender open movies (CC-licensed) standing in for the filmed episodes — replace them with your own filmed 90-second episodes when you shoot them.
