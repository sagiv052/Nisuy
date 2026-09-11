# API לממשק Android – Telegram Stream Bot

מסמך זה מתאר את ה-API של השרת שמספק לממשק Android את הקטלוג, קישורי סטרימינג, ופרטי פרקים/עונות. המטרה היא להקל על פיתוח אפליקציית Android, לבדוק ידנית את ה-endpoints, ולדעת בדיוק מה מחזיר כל request.

---

## Deployment / Render

השרת הפעיל כעת ב-Render עם ה-URL הבא:

- Live URL: https://tvalon.onrender.com/
- Service ID: `srv-dahjpqm7bikc73eg6or0`
- Dashboard: https://dashboard.render.com/web/srv-dahjpqm7bikc73eg6or0/compute
- Deploy link: https://dashboard.render.com/web/srv-dahjpqm7bikc73eg6or0/deploys/dep-dai09q3tqb8s73cdk4kg
- GitHub branch/reference: `sagiv052 / nisuymain` at commit `37bacf88c9bd62813e1f526a19fb2e4a9a0efcb6`

> זהו המידע העדכני של הפרויקט שעלה ל-Render ומוכן לשימוש/בדיקה חיצונית.

---

> שים לב: המסמך מתייחס ל-API ה-versioned של השרת, כלומר הממשק המיועד לאפליקציה הוא בעיקר:
>
> - `GET /api/v1/catalog`
> - `GET /api/v1/catalog/{item_id}`
> - `GET /api/v1/catalog/{item_id}/play`
> - `GET /api/v1/catalog/{series_id}/episodes/{episode_id}/play`
>
> בנוסף יש גם endpoints תומכים כמו `/stream/{chat_id}/{message_id}` ו-`/api/v1/playback/{chat_id}/{message_id}`.

---

## 1. סקירה כללית

השרת הוא FastAPI שמפעיל את הבוט של Telegram ומספק גם API HTTP חיצוני. האפליקציה Android צריכה להשתמש ב-API של הקטלוג כדי לשנות/לקרוא פריטים מתוך SQLite של השרת.

השרת מספק:

- רשימת פריטים (סרטים/סדרות)
- פרטי פריט בודד
- קישורי סטרימינג
- פרטי פרקים לעונה/סדרה
- מידע על מצב השרת (`/health`, `/ping`)
- סטרימינג ישירות מ-Telegram עם תמיכה ב-Range requests

---

## 2. נתיב בסיסי

ה-API פועל בדרך כלל על ה-BASE_URL שהוגדר בסביבה, למשל:

```text
https://tvalon.onrender.com
```

אם השרת רץ המקומית, יכול להיות:

```text
http://localhost:8000
```

בכל מקרה, כל endpoint מתחיל מ-BASE_URL של השרת.

---

## 3. עקרונות עבודה של ה-API

### 3.1 פורמט תשובה

רוב ה-endpoints מחזירים JSON. פורמט התשובה הוא בדרך כלל:

```json
{
  "api_version": 1,
  "items": [],
  "summary": {
    "movie_count": 0,
    "series_count": 0,
    "episode_count": 0,
    "upload_count": 0
  }
}
```

### 3.2 pagination

ל-`GET /api/v1/catalog` יש תמיכה ב-pagination:

- `page` — מספר עמוד, מתחיל מ-1
- `limit` — כמה פריטים להחזיר, מקסימום 100

### 3.3 חיפוש

יש אפשרות לסנן לפי:

- `kind`: `movie` או `series`
- `q`: חיפוש טקסט חופשי לפי כותרת/תקציר

### 3.4 Cache ו-ETag

ה-endpoints של הקטלולוג מחזירים:

- `ETag` — כדי לאפשר cache יעיל
- `Cache-Control: max-age=15`

כלומר, האפליקציה יכולה להחזיק cache מקומי למשך 15 שניות לפני שה-API מתעדכן.

---

## 4. Endpoints עיקריים

## 4.1 `GET /api/v1/catalog`

### מטרת endpoint

מחזיר רשימת פריטי הקטלוג, עם אפשרות לסינון וחיפוש.

### פרמטרים

```text
GET /api/v1/catalog?kind=movie&q=matrix&page=1&limit=20
```

פרמטרים אפשריים:

- `kind` — אופציונלי (`movie`, `series`)
- `q` — אופציונלי; חיפוש טקסט חופשי
- `page` — אופציונלי, ברירת מחדל 1
- `limit` — אופציונלי, ברירת מחדל 50, מקסימום 100

### תשובה מוצלחת

```json
{
  "api_version": 1,
  "page": 1,
  "limit": 20,
  "total": 2,
  "items": [
    {
      "id": 1,
      "kind": "movie",
      "title": "Die My Love",
      "summary": "A dramatic film",
      "release_year": 2024,
      "poster_url": "",
      "backdrop_url": "",
      "quality": "1080P BluRay remux",
      "genre": "Drama",
      "rating": 7.8,
      "tmdb_id": null,
      "created_at": "2026-09-11T17:00:00+00:00",
      "updated_at": "2026-09-11T17:00:00+00:00"
    }
  ],
  "summary": {
    "movie_count": 1,
    "series_count": 1,
    "episode_count": 0,
    "upload_count": 0
  }
}
```

### הערות

- `items` מחזיר רק פריטי הקטלוג, בלי `stream_url` כברירת מחדל.
- אם אתה צריך קישור סטרימינג, יש להשתמש ב-endpoint של play.
- `tmdb_id` נשמר לשימוש היסטורי/תאימות, אך ה-API אינו מבקש ממנו שום פעולה בפועל.

---

## 4.2 `GET /api/v1/catalog/{item_id}`

### מטרת endpoint

מחזיר את פרטי פריט בודד.

### דוגמה

```text
GET /api/v1/catalog/12
```

### תשובה מוצלחת

```json
{
  "api_version": 1,
  "item": {
    "id": 12,
    "kind": "series",
    "title": "Fauda",
    "summary": "A tense espionage drama",
    "release_year": 2015,
    "poster_url": "",
    "backdrop_url": "",
    "quality": "",
    "genre": "Drama",
    "rating": null,
    "tmdb_id": null,
    "created_at": "2026-09-11T16:30:00+00:00",
    "updated_at": "2026-09-11T16:30:00+00:00"
  },
  "seasons": [
    {
      "id": 5,
      "series_id": 12,
      "season_number": 1
    }
  ],
  "episodes": [
    {
      "id": 8,
      "season_number": 1,
      "episode_number": 1,
      "title": "Episode 1"
    }
  ]
}
```

### הערות

- אם `kind == "series"`, ה-endpoint מחזיר גם `seasons` ו-`episodes`.
- `episodes` מחזירים את מספר העונה, מספר הפרק, הכותרת, ולא כולל `stream_url`.
- אם אין פריט, מוחזר `404`.

---

## 4.3 `GET /api/v1/catalog/{item_id}/play`

### מטרת endpoint

מחזיר קישור סטרימינג עבור סרט.

### דוגמה

```text
GET /api/v1/catalog/12/play
```

### תשובה מוצלחת

```json
{
  "api_version": 1,
  "type": "movie",
  "item_id": 12,
  "stream_url": "https://your-domain.example.com/stream/123/456"
}
```

### מקרים חריגים

- אם הפריט לא קיים: `404`
- אם זה לא סרט (`kind != "movie"`): `400`
- אם אין `stream_url` עדיין: `409`

### איך להשתמש בזה באפליקציה

1. קרא `/api/v1/catalog`
2. בחר סרט/סדרה
3. עבור סרטים, קרא `/api/v1/catalog/{item_id}/play`
4. עבור סדרות, קרא ל-endpoint של פרק ספציפי

---

## 4.4 `GET /api/v1/catalog/{series_id}/episodes/{episode_id}/play`

### מטרת endpoint

מחזיר קישור סטרימינג לפרק בתוך סדרה.

### דוגמה

```text
GET /api/v1/catalog/12/episodes/9/play
```

### תשובה מוצלחת

```json
{
  "api_version": 1,
  "type": "episode",
  "series_id": 12,
  "episode_id": 9,
  "season_number": 1,
  "episode_number": 2,
  "title": "Episode 2",
  "stream_url": "https://your-domain.example.com/stream/123/456"
}
```

### מקרים חריגים

- אם הסדרה לא קיימת: `404`
- אם הפרק לא נמצא: `404`
- אם אין סטרים עדיין: `409`

---

## 5. Endpoints נוספים

## 5.1 `GET /stream/{chat_id}/{message_id}`

זהו endpoint ישיר ל-stream עצמו, המשמש למימוש ה-Range requests.

### מה הוא מחזיר

- `200 OK` עם media stream רגיל
- `206 Partial Content` אם יש `Range` header
- `Content-Disposition` לפי שם הקובץ
- `Accept-Ranges: bytes`

### שימוש טיפוסי

```text
GET /stream/-100123456789/3456
```

### מה חשוב לדעת

- זה endpoint שמקבל אכן media מתוך Telegram
- תומך ב-Range requests, מה שמאפשר Seek/Resume playback
- זהו ה-endpoint שמומלץ לשימוש בתוך Android player אם יש לך control על ה-HTTP layer

---

## 5.2 `GET /api/v1/playback/{chat_id}/{message_id}`

### מטרת endpoint

מחזיר JSON עם פרטי stream בסיסיים, כולל URL ישיר ו-`supports_range` / `supports_seek`.

### דוגמה

```text
GET /api/v1/playback/-100123456789/3456?mode=auto
```

### תשובה דוגמה

```json
{
  "api_version": 1,
  "source": {
    "chat_id": -100123456789,
    "message_id": 3456,
    "size": 123456789,
    "mime_type": "video/mp4"
  },
  "direct": {
    "url": "https://your-domain.example.com/stream/-100123456789/3456",
    "supports_range": true,
    "supports_seek": true
  },
  "selected": {
    "mode": "direct",
    "url": "https://your-domain.example.com/stream/-100123456789/3456"
  }
}
```

### הערות

- `mode` יכול להיות `auto` או `direct`
- endpoint זה נועד במיוחד למערכות שמחפשות מידע על אופן ה-streaming לפני שמתחילים להפעיל player

---

## 5.3 `GET /health`

### מטרת endpoint

בדיקת בריאות כללית של השרת.

### דוגמה

```text
GET /health
```

### תשובה דוגמה

```json
{
  "status": "ok",
  "database": "ok",
  "database_error": null,
  "telegram": "connected",
  "active_streams": 0,
  "stream_capacity": 5,
  "cache": {
    "size": 0,
    "entries": 0
  }
}
```

### אפשרויות מצב

- `status: "ok"` — הכל תקין
- `status: "degraded"` — הבוט או מסד הנתונים לא תקין/לא מוכן
- HTTP status code יכול להיות `200` או `503` בהתאם לסטטוס

---

## 5.4 `GET /ping`

### מטרת endpoint

בדיקת חיות פשוטה של השרת.

### דוגמה

```text
GET /ping
```

### תשובה דוגמה

```json
{
  "status": "ok",
  "active_streams": 0,
  "cache": {
    "size": 0,
    "entries": 0
  }
}
```

---

## 6. מבנה JSON של פריט קטלוג

להלן כל השדות האפשריים בכל פריט שמוחזר על ידי ה-API:

```json
{
  "id": 1,
  "kind": "movie",
  "title": "Title",
  "summary": "Summary",
  "release_year": 2024,
  "poster_url": "",
  "backdrop_url": "",
  "quality": "",
  "genre": "",
  "rating": 8.4,
  "tmdb_id": null,
  "created_at": "2026-09-11T00:00:00+00:00",
  "updated_at": "2026-09-11T00:00:00+00:00"
}
```

### פירוש שדות

- `id` — מזהה פנימי ב-SQLite
- `kind` — `movie` או `series`
- `title` — כותרת שנשמרה בקטלוג
- `summary` — תקציר/תיאור
- `release_year` — שנת יציאה
- `poster_url` — תמונת פוסטר
- `backdrop_url` — תמונת רקע
- `quality` — איכות סרט/פרק
- `genre` — זאנר
- `rating` — דירוג
- `tmdb_id` — שדה legacy/compatibility
- `created_at`, `updated_at` — תאריכים

---

## 7. מבנה JSON של פרק

כאשר מבקשים פרטי סדרה, ה-API מחזיר גם episodes, למשל:

```json
{
  "id": 55,
  "season_number": 1,
  "episode_number": 3,
  "title": "Episode 3",
  "stream_url": ""
}
```

### התנהגות

- `stream_url` לא נשלח בדרך כלל ב-`GET /api/v1/catalog/{item_id}` עבור סדרות
- כדי לקבל stream_url לפרק, צריך לקרוא את endpoint מיוחד של play

---

## 8. דפוסי שימוש מומלצים באפליקציה

### 8.1 טעינת רשימת פריטים

```http
GET /api/v1/catalog?kind=movie&page=1&limit=20
```

### 8.2 טעינת פריט ספציפי

```http
GET /api/v1/catalog/15
```

### 8.3 פתיחת סרט

```http
GET /api/v1/catalog/15/play
```

### 8.4 פתיחת פרק של סדרה

```http
GET /api/v1/catalog/8/episodes/12/play
```

### 8.5 בדיקת health

```http
GET /health
```

---

## 9. דוגמאות קוד באפליקציית Android

## 9.1 Kotlin – Retrofit

```kotlin
interface TelegramStreamApi {
    @GET("/api/v1/catalog")
    suspend fun getCatalog(
        @Query("kind") kind: String? = null,
        @Query("q") query: String = "",
        @Query("page") page: Int = 1,
        @Query("limit") limit: Int = 20
    ): CatalogResponse

    @GET("/api/v1/catalog/{itemId}")
    suspend fun getCatalogItem(@Path("itemId") itemId: Int): CatalogItemResponse

    @GET("/api/v1/catalog/{itemId}/play")
    suspend fun getMoviePlay(@Path("itemId") itemId: Int): MoviePlayResponse

    @GET("/api/v1/catalog/{seriesId}/episodes/{episodeId}/play")
    suspend fun getEpisodePlay(
        @Path("seriesId") seriesId: Int,
        @Path("episodeId") episodeId: Int
    ): EpisodePlayResponse
}
```

## 9.2 דוגמת model

```kotlin
data class CatalogItem(
    val id: Int,
    val kind: String,
    val title: String,
    val summary: String,
    val release_year: Int?,
    val poster_url: String,
    val backdrop_url: String,
    val quality: String,
    val genre: String,
    val rating: Double?,
    val tmdb_id: Int?,
    val created_at: String,
    val updated_at: String
)
```

---

## 10. ניהול שגיאות

### 10.1 HTTP status codes נפוצים

- `200 OK` — ביצוע הצליח
- `400 Bad Request` — פרמטר לא חוקי
- `404 Not Found` — אין פריט/סדרה/פרק
- `409 Conflict` — אין stream_url עדיין
- `503 Service Unavailable` — השרת/מסד נתונים לא תקין

### 10.2 מה לעשות ב-Android

- אם קיבלת `404`, הצג "פריט לא נמצא"
- אם קיבלת `409`, הצג "הפריט עדיין לא נגיש ל-stream"
- אם קיבלת `503`, הצג "השרת לא זמין כרגע"
- אם קיבלת `400`, בדוק ש-`kind` הוא `movie` או `series`

---

## 11. המלצות למימוש Android

### 11.1 Cache

- השתמש ב-ETag/Cache-Control
- טען רשימה מחדש כל 15 שניות אם נדרש
- שמור את ה-list המקומית בתור cache ל-10–30 שניות

### 11.2 Player

- אם קיבלת `stream_url`, התחל stream באמצעות ExoPlayer, Media3, או player מתאים
- אם יש `Range` capability, עדיף להפעיל Stream עם `supports_seek` ו-`supports_range`

### 11.3 UI

- `catalog_v1` מתאים ל-list screen
- `catalog_v1_item` מתאים ל-screen של פריט
- `play` endpoints מתאימים למעבר ישיר ל-streaming

---

## 12. הערות מיוחדות

### 12.1 `tmdb_id`

ה-API עדיין כולל שדה בשם `tmdb_id` כיוון שהוא נשמר ב-SQLite, אבל אין בו שימוש פעיל בזרימת ה-Android הנוכחית. זהו שדה legacy/compatibility.

### 12.2 `stream_url`

ב-endpoints של הקטלוג, `stream_url` לא תמיד מועבר ב-JSON משם. למטרת streaming, עדיף להשתמש ב-endpoints המיועדים ל-play עבור סרט/פרק.

### 12.3 `Range` support

ל-`/stream/{chat_id}/{message_id}` יש תמיכה מלאה ב-Range requests, ולכן הוא מתאים מאוד ל-Seek / resume playback.

---

## 13. דוגמת flow מלא

```text
1. Android calls GET /api/v1/catalog?kind=movie
2. Server returns list of items
3. Android selects item id 5
4. Android calls GET /api/v1/catalog/5/play
5. Server returns stream_url
6. Android opens stream with player
```

לסדרה:

```text
1. Android calls GET /api/v1/catalog?kind=series
2. Android calls GET /api/v1/catalog/8
3. Android gets seasons and episodes
4. Android calls GET /api/v1/catalog/8/episodes/12/play
5. Server returns stream_url for that specific episode
```

---

## 14. סיכום

לממשק Android, ה-API העיקרי הוא:

- `GET /api/v1/catalog` — רשימת פריטים
- `GET /api/v1/catalog/{item_id}` — פריט/סדרה/עונות/פרקים
- `GET /api/v1/catalog/{item_id}/play` — סטרים לסרט
- `GET /api/v1/catalog/{series_id}/episodes/{episode_id}/play` — סטרים לפרק
- `GET /api/v1/playback/{chat_id}/{message_id}` — פרטי playback
- `GET /stream/{chat_id}/{message_id}` — stream ישיר עם Range support

אם תרצה, אפשר להוסיף למסמך גם:

- גרסת OpenAPI/Swagger (JSON/YAML)
- דוגמאות של curl מלאות
- תיעוד של כל `Catalog.summary()` ו-`Catalog.integrity_report()`
- עמוד שקשור ל-Android UI flow של Search / Details / Play