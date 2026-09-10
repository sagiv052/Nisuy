# מה שודרג בגרסה הזו

הגרסה כוללת שיפורי יציבות וביצועים בלי לשנות את אופן השימוש הבסיסי בבוט.

## שינויים מרכזיים

- מימוש HTTP Range מלא יותר, כולל טווח פתוח, suffix range ותגובה תקינה ל־416.
- מגבלת זרמים פעילים עם המתנה מוגבלת ותגובה ברורה כאשר הקיבולת מלאה.
- שחרור משאבים מסודר כאשר נגן נסגר או בקשת סטרימינג מתבטלת.
- cache מסונכרן לשליפת הודעות Telegram.
- הגנה מפני עיבוד כפול של אותה העלאת Telegram.
- SQLite עם `WAL`, `busy_timeout`, `synchronous=NORMAL` ואינדקסים.
- retry עם backoff ו־cache לחיפושי TMDB.
- endpoint חדש: `/health` לבדיקת מסד הנתונים ומצב חיבור Telegram.
- Docker `HEALTHCHECK`.
- בדיקות יחידה ב־`tests/test_upgrades.py`.

## הגדרה חדשה

אפשר להגדיר את מספר הזרמים המקבילים:

```env
MAX_ACTIVE_STREAMS=8
```

ברירת המחדל היא 8. אם השירות רץ על משאבים קטנים, מומלץ להתחיל ב־2–4. אם יש מספיק CPU, זיכרון ורוחב פס, אפשר להגדיל בהדרגה.

## הרצה ובדיקה

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile main.py catalog.py tmdb.py stream_utils.py
python3 main.py
```

בדיקת שירות:

```bash
curl http://localhost:8000/ping
curl http://localhost:8000/health
```

הקוד נבדק מקומית באמצעות 4 בדיקות יחידה, וכולן עברו בהצלחה.

## הערה תפעולית

השדרוגים מטפלים בתקלות צפויות וביציבות, אך סטרימינג עדיין תלוי בזמינות Telegram, איכות הרשת ומשאבי השרת. לכן חשוב לעקוב אחרי `/health` ולשמור גיבוי של `catalog.db` אם משתמשים ב־SQLite.

## מטמון RAM לסטרימינג

נוסף מטמון LRU מוגבל לפי bytes עבור מקטעי Telegram, ללא כתיבה לדיסק. ברירת המחדל מותאמת ל־Render Free: 32MB ו־TTL של 90 שניות. המנגנון מונע הורדות כפולות כאשר כמה בקשות מבקשות את אותו מקטע במקביל. `STREAM_READ_AHEAD` נשאר כבוי כברירת מחדל כדי לא להוריד מידע שהמשתמש אולי לא יצפה בו.

```env
STREAM_CACHE_MB=32
STREAM_CACHE_TTL=90
STREAM_READ_AHEAD=0
```

המדדים מופיעים ב־`/ping` וב־`/health` תחת `cache`.
