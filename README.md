# Telegram Stream Bot 🎬

בוט טלגרם שמקבל סרטים/סדרות, יוצר קישורי סטרימינג עם Seek, ומנהל קטלוג של פריטים, עונות ופרקים.
הוא עובד עם טוקן בוט בלבד, ללא חשבון Telegram אישי.

## מה הבוט יכול לעשות
- קבלה ואחסון של סרטים וסדרות מהצ'אט.
- יצירת קישורי סטרימינג ו-Seek מלא באמצעות Pyrogram / MTProto.
- ניהול קטלוג: הוספה, עריכה, מחיקה, צפייה וניווט בין פרקים.
- פענוח כיתובים מצורפים לקבצים: תקציר, זאנר, שנת יציאה ואיכות.
- תמיכה ב-`פאודה עונה 1 פרק 1`, `Fauda S01E01` ופורמטים דומים.

## ניהול קטלוג
- `🎬 סרטים` / `📺 סדרות` עם תפריטים נוחים.
- `/add_movie`, `/add_series`, `/add_episode`.
- `/list`, `/browse`, `/guide`, `/help`, `/cancel`.
- אפשר גם להעלות קובץ עם כיתוב מלא; הבוט יחלץ כותרת, עונה/פרק, תקציר, זאנר, שנה ואיכות.

## API בסיסי
- `GET /api/v1/catalog`
- `GET /api/v1/catalog/{id}`
- `GET /api/v1/catalog/{id}/play`
- `GET /api/v1/catalog/{series_id}/episodes/{episode_id}/play`

## משתני סביבה
- `BOT_TOKEN` — חובה
- `BASE_URL` — אופציונלי
- `CORS_ORIGINS` — אופציונלי
- `TMDB_READ_ACCESS_TOKEN` / `TMDB_API_KEY` — אופציונלי, לשילוב עם TMDB
- `CLOUDINARY_URL` — אופציונלי; כשהוא מוגדר, כל קובץ חדש מועלה לאחסון Cloudinary
- לחלופין ב-Render אפשר להגדיר `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET` ו-`CLOUDINARY_CLOUD_NAME`; הקוד מחבר אותם אוטומטית
- `CLOUDINARY_FOLDER` — אופציונלי; ברירת מחדל `telegram-stream-bot`
- `CATALOG_SYNC_INTERVAL` — אופציונלי; מרווח בשניות לסנכרון הקטלוג, ברירת מחדל `60`

## הערות
- קבצי מדיה חדשים נשמרים ב-Cloudinary כש-`CLOUDINARY_URL` מוגדר; במקרה של כשל ההעלאה הבוט ממשיך עם סטרימינג מטלגרם.
- הקטלוג וההרשאות נשמרים בזמן הריצה ב-SQLite זמני, ומסונכרנים כ-snapshot ל-Cloudinary. בהפעלה מחדש ה-snapshot האחרון משוחזר אוטומטית.
- אם מוגדר `ADMIN_USER_IDS`, רק מנהלים יכולים לשנות את הקטלוג.
