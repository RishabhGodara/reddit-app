
from flask import Flask, request, jsonify, session, redirect, url_for
import praw
import prawcore
from prawcore.exceptions import NotFound
import random
from config import REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USER_AGENT, SECRET_KEY, REDDIT_REDIRECT_URL 
from db import get_connection
import json
from datetime import timedelta

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    user_agent=REDDIT_USER_AGENT,
    redirect_uri=REDDIT_REDIRECT_URL
)

@app.route('/reddit_login')
def reddit_login():
    state = "To get autorization"  # Generate a random state string
    authorization_url = reddit.auth.url(scopes=['identity', 'read', 'vote','submit'], state=state, duration='permanent')
    return redirect(authorization_url)

@app.route('/reddit_callback')
def reddit_callback():
    global code
    code = request.args.get("code")
    if code is None:
        return jsonify({"message": "Please allow the authorization"}), 400
    return jsonify({"message": "Successful Authorized"})

@app.route('/reddit_authcookie')
def reddit_auth():
        if code:
            refresh_token = reddit.auth.authorize(code)
            session['refresh_token'] = refresh_token
            session.permanent=True
            return jsonify({"message": "Authorized"})   
        return jsonify({"message" : " No token"}), 400

@app.route('/check_authorization', methods=['GET'])
def check_authorization():
    if 'refresh_token' in session:
        return jsonify({"authorized": True})
    else:
        return jsonify({"authorized": False}), 400

def refresh_reddit_instance():
    if 'refresh_token' in session:
        reddit.refresh_token = session['refresh_token']
    else:
        raise Exception("No refresh token in session. Please reauthorize.")
@app.route('/verify_login')
def verify_login():
    if 'user_id' in session:
        return jsonify({"message": "login is valid"}), 200
    else:
        return jsonify({"message": "login"}), 401


@app.route('/verify_auth')
def verify_session():
    if 'refresh_token' in session:
        return jsonify({"message": "Authorization is valid"}), 200
    else:
        return jsonify({"message": "Not Authorized"}), 401

@app.route('/login', methods=['POST'])
def login():
    data = request.form
    username = data['username']
    password = data.get('password')  # Use if storing passwords

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password FROM users WHERE username=%s", (username,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        conn.commit()
        user_id = cursor.lastrowid
        message = "User registered"
    else:
        stored_password = user[1]
        if password == stored_password:
            user_id = user[0]
            message = "Login successful"
        else:
            cursor.close()
            conn.close()
            return jsonify({"message": "Invalid username or password"}), 401
    session['user_id'] = user_id
    session.permanent = True
    cursor.close()
    conn.close()

    return jsonify({"message": message, "user_id": user_id}), 200
@app.route('/preferences', methods=['POST'])
def set_preferences():
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401

    user_id = session['user_id']
    data = request.form
    subreddits = data.get('subreddits', [])
    subreddits = json.loads(subreddits)
    valid_subreddits = []
    invalid_subreddits = []
    
    # Validate each subreddit using Reddit API
    for subreddit in subreddits:
        subreddit = subreddit.strip()  # Clean any leading/trailing spaces
        try:
            reddit.subreddits.search_by_name(subreddit, exact=True)
            valid_subreddits.append(subreddit)
        except NotFound:
            invalid_subreddits.append(subreddit)

        except Exception as e:
            return jsonify({"message": f"Error checking subreddit: {subreddit}", "error": str(e)}), 500
    if invalid_subreddits:
       
        return jsonify({"message": "Invalid subreddits", "invalid_subreddits": invalid_subreddits}), 400

    
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * from preferences where user_id = %s",(user_id,))
        check = cursor.fetchall()
        if check:
            cursor.execute("UPDATE preferences SET preferences = %s WHERE user_id = %s", (json.dumps(valid_subreddits), user_id))
        else:
            cursor.execute("INSERT INTO preferences (user_id, preferences) VALUES (%s, %s)",(user_id, json.dumps(valid_subreddits)))
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"message": "Preferences updated"})
    except:
        return jsonify({"message": "There are issues with database service"}), 503
@app.route('/check_preferences')
def check_preferences():
    try:
        user_id = session['user_id']
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * from preferences where user_id = %s",(user_id,))
        check = cursor.fetchall()
        conn.commit()
        cursor.close()
        conn.close()
        if check:
            return jsonify({"message": "Yes its already exist"})
        else:
            return  jsonify({"message": "Not exist"}), 404
    except:
        return jsonify({"message": "There are issues with database service"}), 503

@app.route('/posts', methods=['GET'])
def get_posts():
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401
    user_id = session['user_id']
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT preferences FROM preferences WHERE user_id=%s", (user_id,))
    result = cursor.fetchone()
    if result:
        subreddits = json.loads(result[0])
    else:
        subreddits = []
    posts = []
    limit = int(request.args.get('limit', 5))  # Number of posts to fetch
    offset = int(request.args.get('offset', 0))  # Starting point for posts to fetch
    try:
        for subreddit in subreddits:
            subreddit_obj = reddit.subreddit(subreddit)
            submissions = list(subreddit_obj.new(limit=limit + offset))[offset:]  # Skip posts before offset
            for submission in submissions:
                posts.append({
                    'title': submission.title,
                    'url': submission.url,
                    'id': submission.id
                })

        random.shuffle(posts)  # Randomize the order of posts
    except prawcore.exceptions.NotFound:
        return jsonify({"message": f"Subreddit not found: {subreddit}"}), 404
    except Exception as e:
        return jsonify({"message": "Error fetching posts", "error": str(e)}), 500
    cursor.close()
    conn.close()

    return jsonify({"posts": posts})

@app.route('/posts/<post_id>', methods=['GET'])
def view_post(post_id):
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401

    try:
        post = reddit.submission(id=post_id)
        post_data = {
            'title': post.title,
            'url': post.url,
            'selftext': post.selftext,
            'score': post.score,
            'num_comments': post.num_comments,
            'created_utc': post.created_utc,
            'comments': []
        }
        
        post.comments.replace_more(limit=0)
        for top_level_comment in post.comments.list():
            post_data['comments'].append({
                'author': str(top_level_comment.author),
                'body': top_level_comment.body,
                'score': top_level_comment.score,
                'created_utc': top_level_comment.created_utc
            })
        return jsonify(post_data)
    except Exception as e:
        return jsonify({"message": "Error viewing post"}), 500

@app.route('/posts/<post_id>/upvote', methods=['POST'])
def upvote_post(post_id):
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401
    try:
        refresh_reddit_instance()
        post = reddit.submission(id=post_id)
        post.upvote()
        return jsonify({"message": "Post upvoted"})
    except Exception as e:
        return jsonify({"message": "Error upvoting post"}), 500

@app.route('/posts/<post_id>/downvote', methods=['POST'])
def downvote_post(post_id):
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401
    try:
        refresh_reddit_instance()
        post = reddit.submission(id=post_id)
        post.downvote()
        return jsonify({"message": "Post downvoted"})
    except Exception as e:
        return jsonify({"message": "Error downvoting post"}), 500

@app.route('/posts/<post_id>/comment', methods=['POST'])
def comment_post(post_id):
    if 'user_id' not in session:
        return jsonify({"message": "Not logged in"}), 401
    data = request.json
    comment_text = data.get('comment') 
    if not comment_text:
        return jsonify({"message": "Comment text is required"}), 400
    try:
        refresh_reddit_instance()
        post = reddit.submission(id=post_id)
        post.reply(comment_text)
        return jsonify({"message": "Comment added"})
    except Exception as e:
        return jsonify({"message": f"Error commenting on post: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
