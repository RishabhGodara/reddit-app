# Reddit App

A Python desktop application that interacts with the Reddit API to display trending posts from selected subreddits. Users can upvote, downvote, and comment directly from the app. The backend API is built using Flask, and the frontend uses CustomTkinter.

## Features

- View trending posts from chosen subreddits.
- Upvote, downvote, and comment on posts.
- Scrollable frames for post content and comments.
- Persistent login using cookies.
- User preferences are saved locally and used across sessions.

## Project Structure

The project consists of two main parts:

1. **Backend API (Flask)**
2. **Frontend (CustomTkinter)**
3. **MySql Database**
### 1. Backend API (Flask)

The backend is built using Flask and handles all the API requests for the Reddit app. It communicates with Reddit's API, manages user authentication, preferences, and actions like upvoting, downvoting, and commenting.

### 2. Frontent(Customtkinter)

Frontent is buld with customtkinter

### 3. Database

MySql is used for database with preference and user table to store the information.
