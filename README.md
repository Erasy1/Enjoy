1. Project Overview

ENJOY is a web-based movie and TV series recommendation system built with Flask.
The application helps users discover relevant content based on their preferences, onboarding answers, and interaction history.

The system integrates the TMDB API for real-time movie data and uses a personalized recommendation algorithm to improve user experience.

2. Problem Statement

Modern users face difficulty choosing movies due to the overwhelming number of available titles across platforms.
Most platforms provide generic recommendations that do not reflect individual preferences.

Problem:
Users spend excessive time searching for content instead of watching it.

3. Project Objectives

Implement secure user authentication.

Collect user preferences through onboarding questions.

Generate personalized movie and series recommendations.

Provide filtering (genre, year, country).

Integrate external API (TMDB).

Store user data securely in a database.

Ensure clean UI and smooth navigation.

Provide deployable and reproducible project setup.

4. Features

User registration and login (secure password hashing)

Onboarding system (10-step preference form)

Personalized recommendations

Movie and series browsing

Search and filtering (genre, year, country)

Watchlist / user preferences

Settings page (profile management)

TMDB API integration

Error handling and input validation

5. Technologies Used
Backend

Python

Flask

SQLite

TMDB API

Werkzeug (password hashing)

Logging module

Frontend

HTML

CSS

JavaScript

6. Recommendation Method

The recommendation system is based on a content-based scoring approach.

Logic:

User answers onboarding questions (genres, pace, mood, etc.).

Preferences are converted into weighted genre vectors.

Movies fetched from TMDB are scored based on:

Genre match

Popularity

Rating

Year (optional weight)

Highest scored movies are returned as recommendations.

Future improvement may include:

TF-IDF vectorization of movie descriptions

Cosine similarity for advanced content-based filtering

7. Database Design

Main tables:

users

id (PK)

nickname

email (unique)

password_hash

created_at

onboarding_answers

id (PK)

user_id (FK)

answers (JSON format)

The database is automatically initialized on first run.
