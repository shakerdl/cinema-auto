# Cinema City Date Watcher 🎬

מעקב אוטומטי אחרי תאריכי הקרנות חדשים באתר סינמה סיטי.  
כשמופיע תאריך חדש — מקבלים התראה מיידית בטלפון.

## מה זה עושה

- נכנס לאתר סינמה סיטי כל X דקות
- בוחר קולנוע, סוג הקרנה, וסרט
- קורא את רשימת התאריכים הזמינים
- אם מופיע תאריך חדש → צילום מסך + התראת push

## התקנה מהירה

### Android (Termux)

```bash
pkg update -y && pkg upgrade -y
pkg install -y python python-pip chromium termux-api
pip install selenium requests

git clone https://github.com/<YOUR_USER>/cinema-auto.git
cd cinema-auto
python watcher.py
```

### PC (לבדיקה)

```bash
pip install selenium requests
python watcher.py
```

> נדרש Chrome + [ChromeDriver](https://chromedriver.chromium.org/downloads) מותקנים.

## שימוש

```bash
python watcher.py        # ממשק אינטראקטיבי
```

תפריט מובנה (Enter תוך כדי המתנה):
- הוספה/הסרה של סרטים
- שינוי תדירות בדיקה
- בדיקה מיידית
- איפוס מצב

### הרצה ברקע

```bash
bash run_background.sh start    # הפעלה
bash run_background.sh status   # סטטוס
bash run_background.sh log      # צפייה בלוג
bash run_background.sh stop     # עצירה
```

## קבצים

| קובץ | תיאור |
|-------|--------|
| `watcher.py` | ממשק ראשי אינטראקטיבי |
| `cinema_watcher.py` | גרסת Selenium (headless) |
| `cinema_watcher_api.py` | גרסת API קלה (ללא דפדפן) |
| `discover_api.py` | גילוי API endpoints (חד-פעמי) |
| `setup_termux.sh` | סקריפט התקנה ל-Termux |
| `run_background.sh` | ניהול הרצה ברקע |

## הגדרות

הקונפיגורציה נשמרת ב-`~/CinemaCityWatcher/config.json`:

```json
{
  "cinema": "ראשון לציון",
  "movie_type": "רגיל",
  "movies": ["אובססיה"],
  "check_interval_minutes": 5,
  "headless": true
}
```

## דרישות

- Python 3.8+
- Chrome / Chromium
- Termux:API (להתראות באנדרואיד)

## רישיון

MIT
