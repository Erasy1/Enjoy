#  ENJOY – Movie & Series Recommendation Web Application

---

##  Project Overview

**ENJOY** is a web-based movie and TV series recommendation system built with **Flask (Python)**.

The application generates personalized recommendations using:

* A structured 10-step onboarding system
* A weighted content-based scoring algorithm
* Real-time data from the **TMDB API**

The system transforms user preferences into a structured profile and dynamically ranks movies and TV series based on similarity, quality signals, and behavioral preferences.

---

##  Problem Statement

Modern users face difficulty choosing movies due to the overwhelming number of available titles across streaming platforms.

Most platforms provide generic “Top” lists that do not reflect:

* Personal genre preferences
* Language choices
* Mood and pace preferences
* Plot complexity

### Core Problem

Users spend excessive time searching for content instead of watching it.

---

##  Project Objectives

* Implement secure user authentication (password hashing + session management)
* Collect structured user preferences via onboarding (10-step model)
* Design and implement a weighted recommendation algorithm
* Integrate the TMDB API for real-time catalog access
* Store and update user preferences efficiently in SQLite
* Apply hard filtering (blocked genres, age restriction)
* Ensure clean UI and smooth navigation
* Provide reproducible Windows deployment setup

---

##  Key Features

*  User registration & login (secure password hashing using Werkzeug)
*  10-step onboarding preference system
*  Personalized recommendations (cold start + favorites-based)
*  Movie & TV browsing via TMDB
*  Filtering by genre, language, and content type
*  Blocked genres support
*  Favorites-based similarity boost
*  Settings & preferences management
*  SQLite database with UPSERT logic
*  Hard filtering + weighted scoring formula
*  Error handling and input normalization

---

##  Technologies Used

### Backend

* Python 3.x
* Flask
* SQLite
* Requests (TMDB API)
* Werkzeug (password hashing)
* JSON serialization (stored in DB)
* Logging (optional extension)

### Frontend

* HTML
* CSS
* JavaScript
* Jinja Templates

---

##  Recommendation Method

The recommendation engine uses a **content-based weighted scoring model**.

### Step 1 — Preferences Construction

Onboarding answers are converted into a structured preference model:

* content_type (movie / tv / both)
* languages[]
* liked_genres[]
* blocked_genres[]
* pace (fast / medium / slow)
* mood (light / tense / inspiring / dark / think / mixed)
* plot_complexity (simple / medium / complex)
* age_limit
* favorite_titles[] (TMDB IDs)

Preferences are stored in `user_preferences` using:

```sql
INSERT ... ON CONFLICT(user_id) DO UPDATE
```

---

### Step 2 — Candidate Generation

Candidates are fetched from two sources:

#### A) TMDB Discover API

* with_genres
* without_genres
* with_original_language
* include_adult (based on age_limit)
* vote_count.gte = 50
* sorted by popularity

#### B) Similar to Favorite Titles

For up to 3 favorite titles:

```
/{media_type}/{id}/recommendations
```

Each appearance increases similarity weight.

---

### Step 3 — Feature Engineering

Each candidate is normalized into values between 0 and 1:

| Feature | Description                      |
| ------- | -------------------------------- |
| G       | Genre similarity (Jaccard index) |
| S       | Similarity to favorites          |
| L       | Language match                   |
| R       | Rating (vote_average / 10)       |
| P       | Popularity (log normalized)      |
| T       | Pace signal                      |
| M       | Mood signal                      |
| C       | Complexity signal                |
| Type    | Movie/TV preference match        |

---

### Step 4 — Final Scoring Formula

```
Score =
5·G +
6·S +
1·L +
2·R +
1·P +
0.7·T +
0.7·M +
0.7·C +
0.5·Type
```

Movies are sorted by score, and the top-N results are returned.

---

### Hard Filtering

* Blocked genres are removed even if the score is high.
* Age limit controls adult content.
* vote_count.gte prevents unreliable ratings.

---

### Why Audio Preference Is Not Used in Formula

TMDB does not guarantee platform-level audio/subtitle availability.
Therefore, audio preference is stored but not included in scoring.

---

##  Database Design

### users

* id (PK)
* nickname
* email (UNIQUE)
* password_hash
* created_at

### onboarding_answers

* id (PK)
* user_id (FK)
* question_key (q1–q9)
* answer (JSON or string)

### user_preferences

* user_id (PK)
* structured JSON fields
* normalized labels
* updated_at

