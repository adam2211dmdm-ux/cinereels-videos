# رفع فيديوهات CineReels على GitHub — وتحميلها في التطبيق أوتوماتيك

الفكرة ببساطة: الفيديوهات مش جوّه التطبيق. التطبيق بيقرأ ملف واحد اسمه `videos.json` من GitHub، وأي فيديو تضيفه أو تغيّره في الملف ده بيظهر في التطبيق عند التشغيل أو عند الضغط على **Refresh** — من غير ما نعيد بناء التطبيق (من غير APK جديد).

> اللغة الأساسية للفيديوهات: **إنجليزي**، والترجمة **عربي** (`"language": "en"`, `"subtitle_default": "ar"`).

## 1) اعمل الريبو (مرة واحدة)

1. ادخل GitHub ← **New repository** ← الاسم مثلًا `cinereels-videos` ← خليه **Public** (عشان الرابط الخام يشتغل من غير تسجيل دخول) ← Create.
2. ارفع الملفات دي في الريبو:
   - `videos.json` (الملف اللي معاك هنا — عدّل فيه اسم المستخدم أولًا، شوف الخطوة 2)
   - ملفات الفيديو، مثلًا `episode1.mp4` … `episode5.mp4` (في مجلد `videos/` أو في الجذر — المهم الرابط يطابق مكان الملف)
   - ملفات الترجمة، مثلًا `subtitles/episode1_en.vtt` و `subtitles/episode1_ar.vtt`
   - ممكن ترفع من موقع GitHub نفسه: **Add file → Upload files**، أو من التيرمينال بـ `git push`.

## 2) عدّل `videos.json` باسم المستخدم بتاعك

افتح `videos.json` وبدّل كل `<YOUR-GITHUB-USER>` باسم المستخدم بتاعك على GitHub، مثلًا `adam2211dmdm-ux`.

بعد كده رابط الملف هيبقى شكله كده:

```
https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/videos.json
```

## 3) بدّل روابط الفيديوهات بروابط GitHub بتاعتك

كل فيديو في `videos.json` ليه حقل `video_url`. دلوقتي القيمة فيه مؤقتة (فيديوهات بلندر المرخّصة). لما ترفع الحلقة بتاعتك، بدّل القيمة بالرابط الخام بتاعها:

```
https://raw.githubusercontent.com/<user>/<repo>/main/videos/episode1.mp4
```

مثال للحلقة 1 من "الرسالة الأخيرة":

```json
{
  "id": "lm-ep1",
  "series_id": "last-message",
  "episode_number": 1,
  "title_en": "The Last Message — Ep 1: The Message",
  "title_ar": "الرسالة الأخيرة — الحلقة ١: الرسالة",
  "category": "drama",
  "duration_sec": 90,
  "video_url": "https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/videos/episode1.mp4",
  "thumbnail_url": "https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/thumbs/episode1.jpg",
  "subtitles_en_url": "https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/subtitles/episode1_en.vtt",
  "subtitles_ar_url": "https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/subtitles/episode1_ar.vtt",
  "language": "en",
  "subtitle_default": "ar"
}
```

نفس الفكرة للترجمة: ارفع ملف الـ `.vtt` وحط رابطه الخام في `subtitles_en_url` / `subtitles_ar_url`.

## 4) التطبيق يلقط التغيير إزاي؟

1. في التطبيق، افتح **Admin → GitHub videos (auto-load)** والصق رابط `videos.json` الخام بتاعك في خانة Manifest URL، واضغط **Save URL**.
2. اضغط **Refresh from GitHub** — التطبيق بينزّل `videos.json` وبيحدّث الفيد.
3. بعد كده، أي تعديل تعمله في `videos.json` على GitHub (فيديو جديد، حلقة جديدة، تغيير عنوان) بيظهر في التطبيق عند **إعادة التشغيل** أو **Refresh** — من غير APK جديد.

> ملحوظة: GitHub الخام ممكن يتأخر دقيقة أو اتنين في تحديث الملف بعد الـ push (كاش). لو ضغطت Refresh ومفيش تغيير، استنى دقيقة وجرّب تاني.

## 5) حدود الطريقة دي

- **GitHub مش منصة فيديو:** ملفات الـ mp4 الكبيرة ممكن تبطّأ التحميل، وGitHub بيحدّد حجم الملف الواحد (100MB) والريبو. للحلقات القصيرة (90 ثانية) ده مقبول كبداية. لو كبرت المكتبة، انقل الفيديوهات لـ **Cloudflare R2 / Stream** وسيب `videos.json` على GitHub زي ما هو — هتغيّر بس `video_url`.
- **لازم الريبو Public** عشان الرابط الخام يشتغل من غير تسجيل دخول. لو الريبو Private، التطبيق مش هيعرف يقرأ الملف.
- **لا ترفع محتوى مش بتاعك:** ارفع بس فيديوهات أنت صوّرتها أو عندك حقوقها. "الرسالة الأخيرة" قصة أصلية، فهي آمنة.

## الملفات اللي هنا

| الملف | إيه ده؟ |
|---|---|
| `videos.json` | المانيفست — 36 فيديو (8 مستقلة + 25 حلقة "الرسالة الأخيرة" + 3 حلقات "فرصة ثانية") |
| `README_GITHUB_AR.md` | الشرح ده |

## 6) التصنيف — إزاي تحط فيديو في القسم الصح

كل فيديو في `videos.json` ليه حقل `"category"` — ده اللي بيحدد القسم اللي هيظهر فيه في التطبيق. الأقسام المتاحة (10):

| `category` | الاسم | القسم في التطبيق |
|---|---|---|
| `drama` | Drama / دراما | دراما |
| `romance` | Romance / رومانسي | رومانسي |
| `action` | Action / أكشن | أكشن |
| `comedy` | Comedy / كوميدي | كوميدي |
| `horror` | Horror / رعب | رعب |
| `anime` | Anime / أنمي | أنمي |
| `movies` | Movies / أفلام | أفلام |
| `arabic-series` | Arabic Series / مسلسلات عربية | مسلسلات عربية |
| `international-series` | International Series / مسلسلات أجنبية | مسلسلات أجنبية |
| `thriller` | Thriller / إثارة | إثارة |

**لما تنزّل دراما جديدة (مثال):**
1. ارفع ملف الفيديو (مثلًا `videos/my-drama-ep1.mp4`) وملفات الترجمة في مجلد القسم: `subtitles/drama/episode1_en.vtt` و `subtitles/drama/episode1_ar.vtt`.
2. في `videos.json`، ضيف الفيديو وحط `"category": "drama"` (و `"series_id"` لو هو حلقة من مسلسل، و `"episode_number"` لرقم الحلقة).
3. لو رومانسي: نفس الخطوات بس المجلد `subtitles/romance/` و `"category": "romance"` — والتطبيق هيعرضه في قسم "رومانسي" أوتوماتيك من غير أي تعديل في الكود.

**ملحوظة عن الترجمة:** مجلدات الترجمة متقسمة حسب التصنيف: `subtitles/drama/` للدراما، `subtitles/romance/` للرومانسي، وهكذا. روابط الترجمة في `videos.json` لازم تطابق مكان الملف بالظبط، مثلًا:
`https://raw.githubusercontent.com/adam2211dmdm-ux/cinereels-videos/main/subtitles/drama/episode1_ar.vtt`

**المسلسلات والاشتراك:** كل مسلسل ليه `"free_episodes": 25` — أول 25 حلقة مجانية، والحلقات بعد كده مقفولة بالاشتراك (`"is_locked": true`). الحلقة اللي لسه متصورتش حط `"video_url": null` و `"status": "coming_soon"` وهتظهر "قريباً" من غير ما تشغّل فيديو مش موجود.

## 7) الاشتراكات — `subscribers.json`

ملف `subscribers.json` بيحفظ طلبات الاشتراك، وكل مشترك مربوط بالـ Gmail بتاعه (من غير أي كلمات سر):

- **إزاي بيشتغل:** المستخدم يعمل حساب بالـ Gmail في التطبيق، ويختار باقة (3 أيام / أسبوع / شهر)، ويدوس "طلب اشتراك" — التطبيق بيبعت الطلب، وآدم بيستلم رسالة على الواتساب، والمستخدم يحوّل على فودافون كاش.
- **الموافقة:** آدم يوافق من لوحة الأدمن في التطبيق (قسم "الاشتراكات") على الباقة اللي اتدفع تمنها — شهري أو أسبوعي أو 3 أيام — وساعتها التطبيق بيحسب تاريخ البداية وتاريخ الانتهاء أوتوماتيك، وبعد الفترة دي الاشتراك بينتهي لوحده والحلقات المقفولة بترجع مقفولة.
- **حالة كل مشترك:** `pending` (مستني الموافقة) / `active` (شغال) / `rejected` (مرفوض) / `expired` (انتهى).
- **حقول كل مشترك:** `gmail` (إيميل المشترك)، `plan` (الباقة)، `status` (الحالة)، `requested_at` (وقت الطلب)، `approved_at` (وقت الموافقة)، `starts_at` (بداية الاشتراك)، `expires_at` (نهاية الاشتراك)، `approved_by` (مين اللي وافق).
- **ممنوع تماماً** تحط في الملف ده كلمات سر أو أي بيانات دفع (أرقام بطاقات، أكواد تحويل، أو تفاصيل حسابات) — الملف فيه بس حالة الاشتراك وتواريخه، والتحقق من الدفع بيتم برّه الملف عن طريق الواتساب وفودافون كاش.
- رقم الواتساب بتاع آدم محفوظ في `admin_whatsapp`، و `vodafone_cash` و `price_egp` لكل باقة بتتعبى من لوحة الأدمن لما يجهّزهم.
