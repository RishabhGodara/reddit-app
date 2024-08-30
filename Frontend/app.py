import customtkinter as ctk
import requests
import time
import json,os
import webbrowser
from requests.cookies import RequestsCookieJar
session = requests.Session()
class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Reddit App")
        self.geometry("600x550")
        self.cookies = {}
        self.check_for_login()
    def save_cookies(self,session):
        with open("cookie.json", 'w') as file:
            json.dump(session.cookies.get_dict(), file)  
    def load_cookies(self):
        if os.path.exists("cookie.json"):
            with open("cookie.json", 'r') as file:
                cookies = json.load(file)
                jar = RequestsCookieJar()
                for cookie in cookies:               
                    jar.set(cookie, cookies[cookie])
            session.cookies = jar         
    def check_for_login(self):
        self.load_cookies()
        response = session.get("http://127.0.0.1:5000/verify_login")
        if response.status_code == 200:
            self.check_for_authorization()
        else:
            self.switch_to_login()    
    def switch_to_login(self):
        self.clear_screen()
        login_screen = LoginScreen(self, width=250,height=250)
        login_screen.place(relx=0.5, rely=0.5, anchor="center")

    def check_for_authorization(self):
            self.load_cookies()    
            response = session.get("http://127.0.0.1:5000/check_authorization")
  
            if response.status_code == 200:
                self.switch_to_preferences()
            else:
                self.switch_to_authorization()    

    def switch_to_authorization(self):   
            self.clear_screen()
            authorization_screen = AuthorizationScreen(self,width=600,height=550)
            authorization_screen.pack()

    def switch_to_preferences(self):
        response = session.get("http://127.0.0.1:5000/check_preferences")
        if response.status_code == 200:
            self.switch_to_posts()
        else:    
            self.clear_screen()
            preferences_screen = PreferencesScreen(self,width=600,height=550)
            preferences_screen.place(relx=0.5, rely=0.5, anchor="center")

    def switch_to_posts(self):
        self.clear_screen()
        post_scrren = PostsScreen(self,width=600,height=550)
        post_scrren.pack(fill="both", expand = True)

    def clear_screen(self):
        for widget in self.winfo_children():
            widget.destroy()

class LoginScreen(ctk.CTkFrame):
    def __init__(self, root,**kwargs):
        super().__init__(root,**kwargs)
        self.root = root
        self.pack_propagate(False)
     
        self.label = ctk.CTkLabel(self, text="Username", font= ("Comic Sans MS", 18, "bold"))
        self.label.pack(pady = 10)
        self.username_entry = ctk.CTkEntry(self)
        self.username_entry.pack()

        self.label = ctk.CTkLabel(self, text="Password",font= ("Comic Sans MS", 18, "bold"))
        self.label.pack(pady=10)
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.pack()

        self.login_button = ctk.CTkButton(self, text="Login", command=self.login)
        self.login_button.pack(pady=10)

        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        response = session.post("http://127.0.0.1:5000/login", data={"username": username, "password": password})
        if response.status_code == 200:
            self.root.save_cookies(session)
            self.root.switch_to_authorization()
        else:
            self.error_label.configure(text="Invalid username or password")
        

class AuthorizationScreen(ctk.CTkFrame):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self.root = root
        self.pack_propagate(False)

        self.label = ctk.CTkLabel(self, text="Authorize with Reddit", font=("Comic Sans MS", 20, "bold"))
        self.label.pack(pady=55)

        self.auth_button = ctk.CTkButton(self, text="Authorize", command=self.authorize_reddit)
        self.auth_button.pack(pady=10)

        self.message_label = ctk.CTkLabel(self, text="Complete Authorization process within 20 seconds(It may show app not responding in between)", text_color="red")
        self.message_label.pack()

    def authorize_reddit(self):
        response =session.get("http://127.0.0.1:5000/reddit_login") 
        auth_url = response.url
        webbrowser.open(auth_url)
        time.sleep(15)   
        response = session.get("http://127.0.0.1:5000/reddit_authcookie")
        if response.status_code == 200:
            self.root.save_cookies(session)
            self.root.switch_to_preferences()
        else:
            self.root.switch_to_authorization()    
class PreferencesScreen(ctk.CTkFrame):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self.root = root
        self.pack_propagate(False)

        self.label = ctk.CTkLabel(self, text="Enter your subreddits (comma separated):", font=("Comic Sans MS", 16))
        self.label.pack(pady=10)

        self.subreddits_entry = ctk.CTkEntry(self, width=300)
        self.subreddits_entry.pack(pady=10)

        self.save_button = ctk.CTkButton(self, text="Save Preferences", command=self.save_preferences)
        self.save_button.pack(pady=10)

        self.error_label = ctk.CTkLabel(self, text="", text_color="red")
        self.error_label.pack(pady=10)

    def save_preferences(self):
        subreddits = self.subreddits_entry.get().strip()

        # Check if the input is empty
        if not subreddits:
            self.error_label.configure(text="Please enter at least one subreddit.")
            return

        response = session.post(
            "http://127.0.0.1:5000/preferences",
            data={"subreddits": json.dumps(subreddits.split(','))})

        if response.status_code == 200:
            self.root.switch_to_posts()
        elif response.status_code == 400:
            invalid_subreddits = response.json().get("invalid_subreddits", [])
            self.error_label.configure(text=f"Invalid subreddits: {', '.join(invalid_subreddits)}")
        else:
            self.error_label.configure(text="An error occurred. Please try again.")
class PostsScreen(ctk.CTkFrame):
    def __init__(self, root, **kwargs):
        super().__init__(root, **kwargs)
        self.root = root
        self.offset = 0
        self.limit = 5
        self.posts = []
        self.change_pref_button = ctk.CTkButton(self, text="Change Preferences", command=self.change_preferences)
        self.change_pref_button.pack(side="top", pady=10)
        # Create a canvas and a scrollbar for scrolling
        self.canvas = ctk.CTkCanvas(self, background="white")
        self.scrollbar = ctk.CTkScrollbar(self, orientation="vertical", command=self.canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(self.canvas)

        # Configure the canvas to scroll with the scroll region
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind the mouse wheel for scrolling
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)

        # Load the first batch of posts
        self.load_more_posts()

    def on_mousewheel(self, event):
        """Handle scrolling and load more posts when reaching the bottom."""
        self.canvas.yview_scroll(-1 * (event.delta // 120), "units")

        # Check if we're at the bottom of the scroll region to load more posts
        if self.canvas.yview()[1] == 1.0:  # Check if the scrollbar is at the bottom
            self.load_more_posts()

    def load_more_posts(self):
        """Fetch posts from the API and display them."""
        response = session.get(f"http://127.0.0.1:5000/posts?limit={self.limit}&offset={self.offset}")
        if response.status_code == 200:
            new_posts = response.json().get('posts', [])
            self.display_posts(new_posts)
            self.offset += self.limit

    def display_posts(self, posts):
        """Display the fetched posts in the scrollable frame."""
        for post in posts:
            post_frame = ctk.CTkFrame(self.scrollable_frame)
            
            # Title of the post with a click event
            post_label = ctk.CTkLabel(post_frame, text=post['title'], font=("Helvetica", 16), anchor="w")
            post_label.pack(side="top", fill="x", padx=10, pady=5)
            
            # Binding the click event to a function that shows post details
            post_label.bind("<Button-1>", lambda e, post_id=post['id']: self.show_post_details(post_id))

            # URL of the post
            content_label = ctk.CTkLabel(post_frame, text=post['url'], wraplength=500, anchor="w")
            content_label.pack(side="top", fill="x", padx=10, pady=5)

            post_frame.pack(fill="x", padx=10, pady=10)
            self.posts.append(post)

    def show_post_details(self, post_id):
        """Switch to the PostViewScreen with the selected post ID."""
        self.pack_forget()
        post_view_screen = PostViewScreen(self.root, post_id)
        post_view_screen.pack(fill="both", expand=True)

    def change_preferences(self):
        for widget in self.winfo_children():
            widget.destroy()
        preferences_screen = PreferencesScreen(self.root,width=600,height=550)
        preferences_screen.place(relx=0.5, rely=0.5, anchor="center")        

class PostViewScreen(ctk.CTkFrame):
    def __init__(self, root, post_id, **kwargs):
        super().__init__(root, **kwargs)
        self.root = root
        self.post_id = post_id

        # Back Button
        self.back_button = ctk.CTkButton(self, text="< Back", command=self.go_back)
        self.back_button.pack(padx=10, pady=10, anchor="w")

        # Fetch and display the post details
        self.fetch_post_details()

    def fetch_post_details(self):
        """Fetch post details and display them on the screen."""
        response = session.get(f"http://127.0.0.1:5000/posts/{self.post_id}")
        if response.status_code == 200:
            post_data = response.json()
            self.display_post(post_data)
        else:
            # Handle the error
            ctk.CTkLabel(self, text="Failed to load post", font=("Helvetica", 14)).pack(padx=10, pady=10)

    def display_post(self, post_data):
        """Display the post title, selftext, and other details."""

        # Scrollable frame for post title and content
        post_text_frame = ctk.CTkFrame(self, height=300)
        post_text_frame.pack(fill="x", padx=10, pady=(5, 10))

        post_text_canvas = ctk.CTkCanvas(post_text_frame, height=300, bg="gray17")  # Set explicit background color
        post_text_canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ctk.CTkScrollbar(post_text_frame, command=post_text_canvas.yview)
        scrollbar.pack(side="right", fill="y")

        post_text_canvas.configure(yscrollcommand=scrollbar.set)

        post_text_inner_frame = ctk.CTkFrame(post_text_canvas, fg_color="gray17")  # Set explicit color
        post_text_inner_frame.bind("<Configure>", lambda e: post_text_canvas.configure(scrollregion=post_text_canvas.bbox("all")))

        post_text_canvas.create_window((0, 0), window=post_text_inner_frame, anchor="nw")

        # Post Title
        title_label = ctk.CTkLabel(post_text_inner_frame, text=post_data['title'], font=("Helvetica", 18, "bold"), wraplength=500)
        title_label.pack(padx=10, pady=5)

        # Post Content
        text_label = ctk.CTkLabel(post_text_inner_frame, text=post_data['selftext'], wraplength=480, font=("Helvetica", 14))
        text_label.pack(padx=10, pady=5)

        # Bottom Frame for Comments and Buttons
        bottom_frame = ctk.CTkFrame(self)
        bottom_frame.pack(fill="x", expand=True, padx=10, pady=(5, 10))

        # Left side: Comments Section (Scrollable)
        comments_frame = ctk.CTkFrame(bottom_frame, width=350, height=250)
        comments_frame.pack(side="left", fill="both", expand=True)

        comments_canvas = ctk.CTkCanvas(comments_frame, width=350, height=250, bg="gray17")  # Set explicit background color
        comments_canvas.pack(side="left", fill="both", expand=True)

        comments_scrollbar = ctk.CTkScrollbar(comments_frame, command=comments_canvas.yview)
        comments_scrollbar.pack(side="right", fill="y")

        comments_canvas.configure(yscrollcommand=comments_scrollbar.set)

        comments_inner_frame = ctk.CTkFrame(comments_canvas, fg_color="gray17")  # Set explicit color
        comments_inner_frame.bind("<Configure>", lambda e: comments_canvas.configure(scrollregion=comments_canvas.bbox("all")))

        comments_canvas.create_window((0, 0), window=comments_inner_frame, anchor="nw")

        # Display Comments
        for comment in post_data['comments']:
            comment_frame = ctk.CTkFrame(comments_inner_frame)
            comment_frame.pack(fill="x", padx=5, pady=5)

            author_label = ctk.CTkLabel(comment_frame, text=f"Author: {comment['author']}", font=("Helvetica", 12, "italic"))
            author_label.pack(anchor="w")

            body_label = ctk.CTkLabel(comment_frame, text=comment['body'], wraplength=300, font=("Helvetica", 14))
            body_label.pack(anchor="w")

            score_label = ctk.CTkLabel(comment_frame, text=f"Score: {comment['score']}", font=("Helvetica", 12))
            score_label.pack(anchor="w")

        # Right side: Buttons for Upvote, Downvote, and Comment
        button_frame = ctk.CTkFrame(bottom_frame)
        button_frame.pack(side="left", fill="both", expand=True, padx=10)

        self.upvote_button = ctk.CTkButton(button_frame, text="Upvote", command=self.upvote_post)
        self.upvote_button.pack(fill="x", padx=10, pady=(0, 5))

        self.downvote_button = ctk.CTkButton(button_frame, text="Downvote", command=self.downvote_post)
        self.downvote_button.pack(fill="x", padx=10, pady=(0, 5))

        self.comment_entry = ctk.CTkEntry(button_frame, placeholder_text="Add a comment...")
        self.comment_entry.pack(fill="x", padx=10, pady=(0, 5))

        self.comment_button = ctk.CTkButton(button_frame, text="Comment", command=self.add_comment)
        self.comment_button.pack(fill="x", padx=10, pady=(0, 5))

    def go_back(self):
        """Navigate back to the posts list screen."""
        self.root.switch_to_posts()

    def upvote_post(self):
        """Upvote the post."""
        response = session.post(f"http://127.0.0.1:5000/posts/{self.post_id}/upvote")
        if response.status_code == 200:
            ctk.CTkLabel(self, text="Post upvoted!", font=("Helvetica", 14), fg_color="green").pack(padx=10, pady=10)

    def downvote_post(self):
        """Downvote the post."""
        response = session.post(f"http://127.0.0.1:5000/posts/{self.post_id}/downvote")
        if response.status_code == 200:
            ctk.CTkLabel(self, text="Post downvoted!", font=("Helvetica", 14), fg_color="green").pack(padx=10, pady=10)

    def add_comment(self):
        """Add a comment to the post."""
        comment_text = self.comment_entry.get()
        if comment_text:
            response = session.post(f"http://127.0.0.1:5000/posts/{self.post_id}/comment", json={"comment": comment_text})
            if response.status_code == 200:
                ctk.CTkLabel(self, text="Comment added!", font=("Helvetica", 14), fg_color="green").pack(padx=10, pady=10)
            else:
                ctk.CTkLabel(self, text="Failed to add comment", font=("Helvetica", 14), fg_color="red").pack(padx=10, pady=10)
        else:
            ctk.CTkLabel(self, text="Comment cannot be empty", font=("Helvetica", 14), fg_color="red").pack(padx=10, pady=10)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
