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
| `videos.json` | المانيفست — 13 فيديو (8 مستقلة + 5 حلقات "الرسالة الأخيرة") |
| `README_GITHUB_AR.md` | الشرح ده |
