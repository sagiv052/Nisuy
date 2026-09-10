# Telegram Stream Bot 🎬

הבוט מקבל קבצי וידאו מטלגרם, יוצר קישורי סטרימינג עם Seek, ושומר קטלוג
של סרטים וסדרות. החיבור מתבצע עם טוקן בוט בלבד, ללא חשבון Telegram אישי.

הסטרימינג משתמש ב-Pyrogram וב-MTProto, ולכן אינו מוגבל למגבלת 20MB של
Bot API HTTP רגיל.

## הרצה מקומית

1. התקן Python 3.11 ומעלה, אך להפעלה מקומית השתמש ב-Python 3.11 בגלל `TgCrypto`.
2. צור סביבה: `py -3.11 -m venv .venv311`
3. התקן את התלויות: `./.venv311/Scripts/python.exe -m pip install -r requirements.txt`
4. פתח את הקובץ `.env` והכנס את הטוקן שקיבלת מ-`@BotFather`:
	`BOT_TOKEN=הטוקן_שלך`
5. הפעל את הבוט: `./.venv311/Scripts/python.exe main.py`
6. בדוק בדפדפן: `http://localhost:8000/ping`

הקובץ `.env` מקומי ומתעלמים ממנו ב-Git, ולכן הטוקן לא יעלה ל-GitHub.
אפשר להשתמש ב-`.env.example` כתבנית.

## ניהול קטלוג

התפריט הראשי מחולק ל-`🎬 סרטים` ול-`📺 סדרות`, כדי שהמסך לא יהיה עמוס.
בתוך כל חלק נמצאות פעולות ההוספה, העריכה והמחיקה:

- `➕ הוסף סרט` או `/add_movie` — פרטים, פוסטר וקובץ וידאו.
- `➕ הוסף סדרה` או `/add_series` — פרטי הסדרה.
- `/add_episode` — בחירת סדרה, עונה, פרק וקובץ וידאו.
- העלאת עונה ברצף — כתוב `סדרה: פאודה עונה 1`, שלח את קבצי הפרקים לפי הסדר,
  ולחץ `✅ סיום` בסוף. הקובץ הראשון נשמר כפרק 1 וכן הלאה.
- `✏️ ערוך סרט` או `/edit_movie`, `✏️ ערוך סדרה` או `/edit_series` — בחר אחר כך שדה אחד: שם, תקציר, שנה או פוסטר.
- `🗑️ הסר סרט` או `/remove_movie` — מחיקה עם אישור.
- כפתורי הסרה או `/remove_series`, `/remove_season`, `/remove_episode` — עם אישור לפני מחיקה.
- `📚 רשימה`, `/list` וחיפוש פשוט בצ'אט.
- `🔗 קישור סטרימינג` או `/browse` — בחירת סרט, סדרה, עונה ופרק וקבלת הקישור.
- `📖 מדריך`, `/guide` ו-`/help`.
- `/cancel` לביטול כל פעולה.

כש-TMDB מוגדר, אחרי כתיבת שם סרט או סדרה הבוט מציג תוצאות בעברית ובאנגלית.
בחירת תוצאה ממלאת אוטומטית תקציר, שנת יציאה, דירוג, פוסטר ורקע. אם אין תוצאה,
אפשר לבחור `⏭️ דלג` ולהמשיך בהזנה ידנית.

אפשר גם לשלוח קובץ עם כיתוב מלא של פרסום. הבוט יחלץ את הכותרת, השנה ועונה/פרק,
יתעלם משורות כמו איכות וז'אנר, יחפש ב-TMDB וישמור אוטומטית. לדוגמה:

```text
משפחת רעם: העימות הגדול 2026
Clash of the Thundermans
תרגום אולפנים מובנה 🇮🇱
איכות: 1080p WEB-DL
תקציר: ...
```

בסדרה אפשר להשתמש גם ב-`פאודה עונה 1 פרק 1`, `פאודה ע1 פ1`,
`Fauda Season 1 Episode 1` או `Fauda S01E01`.

הנתונים נשמרים ב-`catalog.db` מקומית. לגרסת ה-API המומלצת לאפליקציית Android משתמשים בנתיבים:

- `GET /api/v1/catalog`
- `GET /api/v1/catalog/{id}`
- `GET /api/v1/catalog/{id}/play`
- `GET /api/v1/catalog/{series_id}/episodes/{episode_id}/play`

האפליקציה מקבלת metadata ורשימת פרקים בלי קישורי סטרימינג, ומבקשת את `stream_url` רק כאשר המשתמש לוחץ על צפייה. פירוט מלא נמצא ב-`ANDROID_API.md`.

אם מגדירים `ADMIN_USER_IDS` כרשימת מזהי Telegram מופרדת בפסיקים, רק המשתמשים האלה יוכלו לשנות את הקטלוג. ללא ההגדרה, מצב הפיתוח מאפשר לכל משתמש פרטי לבצע ניסויים.

## חיבור לאפליקציית הסרטים

נניח שכתובת שירות הבוט ב-Render היא:

```text
https://telegram-stream-server.onrender.com
```

### 1. קבלת הסרטים והסדרות

האפליקציה שולפת את הקטלוג:

```js
const API = "https://telegram-stream-server.onrender.com";
const response = await fetch(`${API}/api/v1/catalog?page=1&limit=30`);
const { items } = await response.json();
```

כל פריט כולל `title`, `summary`, `release_year`, `poster_url` ו-`rating`. קישור הסטרימינג מתקבל רק בקריאת `play`.
בסדרה, פותחים את המסך שלה ושולפים גם את העונות והפרקים:

```js
const response = await fetch(`${API}/api/v1/catalog/12`);
const { item, seasons, episodes } = await response.json();
```

### 2. מסך הפרטים וכפתור הפעלה

במסך הסרט מציגים את `poster_url` כפוסטר, את `summary` כתקציר ואת `release_year` כשנה.
רק בלחיצה על כפתור הצפייה מבקשים את מקור הווידאו:

```html
<video id="player" controls playsinline></video>
<button id="play">▶️ הפעל</button>
```

```js
document.querySelector("#play").onclick = async () => {
  const response = await fetch(`${API}/api/v1/catalog/${movie.id}/play`);
  const { stream_url } = await response.json();
  const player = document.querySelector("#player");
  player.src = stream_url;
  player.play();
};
```

אפשר להשתמש באותו `stream_url` גם ב-React, למשל:
`<video controls src={movie.stream_url} />`.

הקוד כבר תומך ב-HTTP Range וב-Seek, לכן נגן HTML5 יכול לדלג קדימה ואחורה.
הקישור לא “פג” לפי זמן, אך הוא יעבוד רק כל עוד הודעת Telegram קיימת והבוט פעיל.

### 3. CORS ונתוני Render

ב-Render יש להגדיר:

```text
CORS_ORIGINS=https://your-movie-app.onrender.com
```

לניסוי אפשר להשאיר `*`, אבל בפרודקשן עדיף לרשום רק את כתובת האפליקציה.
`catalog.db` הוא מסד מקומי. ב-Render Free מערכת הקבצים עלולה להימחק בפריסה מחדש,
לכן לקטלוג אמיתי צריך Persistent Disk או מסד נתונים חיצוני.

כל קובץ שנשלח נשמר מיד בטבלת ההעלאות, גם לפני שיוך לסרט או לפרק. ב-Render יש
להוסיף Persistent Disk עם Mount Path של `/var/data`; ה-Blueprint מגדיר את
`CATALOG_DB` ל-`/var/data/catalog.db`. בהרצה מקומית ברירת המחדל היא `catalog.db`.

## פריסה ל-Render

### Blueprint (מומלץ)
1. דחוף את התיקייה ל-GitHub repo
2. Render → **New → Blueprint** → חבר repo → ימולא אוטומטית מ-`render.yaml`
3. תתבקש למלא ערך אחד בלבד: `BOT_TOKEN`
4. Deploy

### Web Service ידני
1. **New → Web Service** → חבר repo, Environment: **Docker**
2. Environment Variables: `BOT_TOKEN`
3. Health Check Path: `/ping`

## משתני סביבה נדרשים

| שם | הסבר |
|---|---|
| `BOT_TOKEN` | טוקן הבוט מ-@BotFather |
| `BASE_URL` | **אופציונלי** — רק לעקיפת הגילוי האוטומטי |
| `KEEP_ALIVE_INTERVAL` | **אופציונלי** — מרווח heartbeat בשניות, ברירת מחדל `300` |
| `CORS_ORIGINS` | כתובת האפליקציה החיצונית, או `*` לניסוי |
| `TMDB_READ_ACCESS_TOKEN` | **אופציונלי** — Read Access Token של TMDB |
| `TMDB_API_KEY` | **אופציונלי** — API Key של TMDB |

> אין צורך במספר טלפון, התחברות לחשבון אישי או `SESSION_STRING`.
> הקוד משתמש בפרטי אפליקציה ציבוריים כברירת מחדל. אם תרצה להחליף אותם,
> אפשר להגדיר גם `API_ID` ו-`API_HASH` כמשתני סביבה אופציונליים.

הבוט שולח heartbeat מחזורי ל-`/ping` וגם ניסיון heartbeat אחרון בזמן shutdown.

ה-heartbeat נשלח כדי לסמן שהשירות פעיל, אך אינו חלק מחיבור האפליקציה החיצונית.
