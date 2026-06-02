# Cinema City Date Watcher - אוטומציה לאנדרואיד

מעקב אוטומטי אחרי תאריכים חדשים בסינמה סיטי ראשון לציון - סרט "אובססיה".

---

## מה האוטומציה עושה

1. נכנסת לאתר סינמה סיטי כל 5 דקות
2. בוחרת: ראשון לציון → רגיל → אובססיה
3. קוראת את רשימת התאריכים הזמינים
4. משווה לבדיקה הקודמת
5. אם יש תאריך חדש → צילום מסך + התראה בטלפון

---

## הוראות התקנה - צעד אחר צעד

### שלב 1: התקנת Termux

1. **התקן את Termux** מ-F-Droid (לא מ-Google Play - הגרסה שם ישנה):
   - כנס ל: https://f-droid.org/packages/com.termux/
   - הורד והתקן את ה-APK

2. **התקן את Termux:API** (לצורך התראות):
   - כנס ל: https://f-droid.org/packages/com.termux.api/
   - הורד והתקן את ה-APK

### שלב 2: הרשאות

פתח את ההגדרות של אנדרואיד:
1. **הגדרות → אפליקציות → Termux:**
   - סוללה → לא מוגבל (אל תאפשר אופטימיזציה)
   - אחסון → אפשר

2. **הגדרות → אפליקציות → Termux:API:**
   - התראות → אפשר
   - אחסון → אפשר

3. ב-Termux, הרץ:
   ```bash
   termux-setup-storage
   ```
   ואשר את הגישה לאחסון.

### שלב 3: התקנת דרישות

פתח את Termux והרץ:

```bash
# עדכון חבילות
pkg update -y && pkg upgrade -y

# התקנת Python
pkg install -y python python-pip

# התקנת Chromium (לגרסת Selenium)
pkg install -y chromium

# התקנת כלים נוספים
pkg install -y termux-api git

# התקנת חבילות Python
pip install selenium requests
```

### שלב 4: העתקת הקבצים לטלפון

**אפשרות א - עם Git:**
```bash
cd ~
git clone <repository-url> cinema-auto
cd cinema-auto
```

**אפשרות ב - העתקה ידנית:**
```bash
mkdir -p ~/cinema-auto
cd ~/cinema-auto
```
העתק את הקבצים דרך USB או הורד אותם ישירות.

**אפשרות ג - יצירה ידנית בטלפון:**
```bash
mkdir -p ~/cinema-auto
cd ~/cinema-auto
# העתק את התוכן של כל קובץ ידנית
```

### שלב 5: בדיקת ההתקנה

```bash
# בדיקה שהתראות עובדות
termux-notification --title "בדיקה" --content "ההתראות עובדות!" --sound

# בדיקה שנרטטט
termux-vibrate -d 500

# בדיקה ש-Python עובד
python -c "import requests; print('requests OK')"
python -c "from selenium import webdriver; print('selenium OK')"
```

### שלב 6: גילוי ה-API (חד פעמי)

```bash
cd ~/cinema-auto
python discover_api.py
```

בדוק את הפלט - הסקריפט יזהה את מבנה ה-API של האתר.
עדכן את ה-CONFIG בקובץ `cinema_watcher_api.py` בהתאם לממצאים.

### שלב 7: הרצה ראשונה (בדיקה)

```bash
cd ~/cinema-auto

# הרצת גרסת Selenium (מלאה עם דפדפן)
python cinema_watcher.py

# או: גרסת API (קלה יותר, בלי דפדפן)
python cinema_watcher_api.py
```

### שלב 8: הרצה ברקע (שוטפת)

```bash
# הפעלה ברקע
bash run_background.sh start

# בדיקת סטטוס
bash run_background.sh status

# צפייה בלוג בזמן אמת
bash run_background.sh log

# עצירה
bash run_background.sh stop
```

---

## פתרון בעיות

### "termux-notification not found"
```bash
pkg install termux-api
```
וודא שאפליקציית Termux:API מותקנת ויש לה הרשאת התראות.

### "ChromeDriver not found"
```bash
pkg install chromium
```

### האוטומציה נעצרת כשהמסך כבוי
1. הגדר את Termux ל"לא מוגבל" בהגדרות סוללה
2. הרץ עם `termux-wake-lock`:
```bash
termux-wake-lock
bash run_background.sh start
```

### האוטומציה לא מוצאת תאריכים
1. הרץ את `discover_api.py` מחדש
2. בדוק אם האתר שינה את המבנה שלו
3. אם ה-API לא עובד, השתמש בגרסת Selenium (`cinema_watcher.py`)

### לשנות תדירות בדיקה
ערוך את `CONFIG["check_interval_minutes"]` בקובץ המתאים:
```python
"check_interval_minutes": 3,  # כל 3 דקות
```

---

## קבצים בפרויקט

| קובץ | תיאור |
|-------|--------|
| `cinema_watcher.py` | גרסה מלאה עם Selenium (דפדפן) |
| `cinema_watcher_api.py` | גרסה קלה - API בלבד (ללא דפדפן) |
| `discover_api.py` | כלי לגילוי נקודות API (הרצה חד פעמית) |
| `setup_termux.sh` | סקריפט התקנה אוטומטי |
| `run_background.sh` | ניהול הרצה ברקע (start/stop/status/log) |
| `requirements.txt` | דרישות Python |

---

## פלט

הכל נשמר בתיקייה `~/CinemaCityWatcher/`:
- `last_dates.json` - מצב אחרון ידוע
- `cinema_city_new_date_found_*.png` - צילומי מסך
- `api_response_*.json` - תשובות API (לדיבאג)
- `log.txt` - לוג הרצה

---

## טיפים

- **גרסת API** (`cinema_watcher_api.py`) עדיפה - צורכת פחות סוללה ומהירה יותר
- **גרסת Selenium** (`cinema_watcher.py`) מתאימה אם ה-API לא עובד
- אם הטלפון נמצא על מטען, אפשר להוריד את מרווח הבדיקה ל-2-3 דקות
- ה-`termux-wake-lock` מונע מהמערכת להרוג את התהליך
