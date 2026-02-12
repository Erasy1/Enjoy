ENJOY – Movie & Series Recommendation Web Application
1. Project Overview

ENJOY is a web-based movie and TV series recommendation system developed using Flask (Python).
The application generates personalized recommendations based on user onboarding answers and content data retrieved from the TMDB API.

The system implements a weighted content-based recommendation algorithm with hard filtering and multi-factor scoring.

2. Problem Statement

Users often experience difficulty selecting movies or TV series due to the large amount of available content. Generic recommendation systems do not always reflect individual preferences.

Goal:
To design and implement a personalized recommendation engine that adapts to user preferences collected during onboarding.

3. Project Objectives

Implement secure user authentication.

Collect structured onboarding data (10-step system).

Build a personalized preference model.

Integrate TMDB API for real-time content.

Design a weighted scoring algorithm.

Store and update user preferences in a relational database.

Provide a clean and responsive UI.

Ensure deployable and reproducible environment.

4. Technologies Used
Backend

Python

Flask

SQLite

Requests

Logging

JSON storage in database

TMDB API

Frontend

HTML

CSS

JavaScript

5. System Architecture

User registers/logs in.

User completes 10-step onboarding.

Preferences are transformed into structured data.

Candidates are fetched from TMDB (Discover + Similar).

Weighted scoring formula ranks content.

Top N results are returned.

6. Recommendation Algorithm

The system uses a content-based weighted scoring model.

6.1 User Preference Model

After onboarding, preferences are stored in user_preferences:

content_type (movie/tv/both)

languages

liked_genres

blocked_genres

pace

mood

plot_complexity

age_limit

favorite_titles (TMDB IDs)

Preferences are updated using UPSERT logic (ON CONFLICT DO UPDATE).

6.2 Candidate Generation

Two main sources:

A) Discover API

TMDB /discover/{media_type} with:

with_genres (liked genres)

without_genres (blocked genres)

with_original_language

include_adult (based on age limit)

vote_count.gte = 50

sorted by popularity

B) Similar to Favorite Titles

For up to 3 favorite titles:

/{media_type}/{id}/recommendations

Each appearance increases similarity score.

6.3 Feature Engineering

Each candidate item is represented by normalized features in range [0, 1].

(1) Genre Similarity (G)

Using Jaccard similarity:

𝐺
=
∣
𝐺
𝑒
𝑛
𝑟
𝑒
𝑠
(
𝑖
𝑡
𝑒
𝑚
)
∩
𝐺
𝑒
𝑛
𝑟
𝑒
𝑠
(
𝑢
𝑠
𝑒
𝑟
)
∣
∣
𝐺
𝑒
𝑛
𝑟
𝑒
𝑠
(
𝑖
𝑡
𝑒
𝑚
)
∪
𝐺
𝑒
𝑛
𝑟
𝑒
𝑠
(
𝑢
𝑠
𝑒
𝑟
)
∣
G=
∣Genres(item)∪Genres(user)∣
∣Genres(item)∩Genres(user)∣
	​

(2) Similarity to Favorites (S)
𝑆
=
𝑐
𝑙
𝑎
𝑚
𝑝
(
𝑠
𝑖
𝑚
𝐶
𝑜
𝑢
𝑛
𝑡
3
)
S=clamp(
3
simCount
	​

)
(3) Language Match (L)
𝐿
=
{
1
,
	
if language matches


0
,
	
otherwise
L={
1,
0,
	​

if language matches
otherwise
	​

(4) Rating Score (R)
𝑅
=
𝑣
𝑜
𝑡
𝑒
_
𝑎
𝑣
𝑒
𝑟
𝑎
𝑔
𝑒
10
R=
10
vote_average
	​

(5) Popularity Score (P)

Log normalization:

𝑃
=
ln
⁡
(
1
+
𝑝
𝑜
𝑝
𝑢
𝑙
𝑎
𝑟
𝑖
𝑡
𝑦
)
ln
⁡
(
1
+
1000
)
P=
ln(1+1000)
ln(1+popularity)
	​

(6) Pace / Mood / Complexity Signals (T, M, C)

Since TMDB does not provide direct metadata for pace or mood, the system uses heuristic genre-based signal sets.

If user selects:

medium pace → T = 0.5

mixed mood → M = 0.5

medium complexity → C = 0.5

(7) Content Type Preference (Type)
𝑇
𝑦
𝑝
𝑒
=
{
1
,
	
if matches user choice


0
,
	
if mismatch


0.5
,
	
if both selected
Type=
⎩
⎨
⎧
	​

1,
0,
0.5,
	​

if matches user choice
if mismatch
if both selected
	​

6.4 Final Scoring Formula
𝑆
𝑐
𝑜
𝑟
𝑒
=
5.0
𝐺
+
6.0
𝑆
+
1.0
𝐿
+
2.0
𝑅
+
1.0
𝑃
+
0.7
𝑇
+
0.7
𝑀
+
0.7
𝐶
+
0.5
𝑇
𝑦
𝑝
𝑒
Score=5.0G+6.0S+1.0L+2.0R+1.0P+0.7T+0.7M+0.7C+0.5Type

Where:

G — genre similarity

S — similarity to favorites

L — language match

R — rating

P — popularity

T — pace signal

M — mood signal

C — complexity signal

Type — media type preference

Candidates are sorted in descending order and top N results are returned.

6.5 Hard Filtering

If an item contains blocked genres, it is removed from results even if its score is high.

7. Database Design
users

id (PK)

nickname

email (unique)

password_hash

created_at

onboarding_answers

user_id

question_key

answer

user_preferences

user_id (PK)

structured JSON fields

updated_at
