import tkinter as tk
from tkinter import messagebox
import hashlib

# Import the database and main app classes from your renamed file
from pos_system import POSDatabase, POSApp

class LoginApp:
    def __init__(self, root):
        self.root = root
        self.root.title("System Login")
        self.root.geometry("400x300")
        self.root.configure(bg="#222")
        
        # Initialize the database connection from the imported class
        self.db = POSDatabase()
        
        # --- UI Elements ---
        tk.Label(root, text="POS LOGIN", font=("Arial", 20, "bold"), bg="#222", fg="white", pady=20).pack()
        
        tk.Label(root, text="Username:", font=("Arial", 12), bg="#222", fg="white").pack()
        self.entry_username = tk.Entry(root, font=("Arial", 14), justify="center")
        self.entry_username.pack(pady=5)
        
        tk.Label(root, text="Password:", font=("Arial", 12), bg="#222", fg="white").pack()
        self.entry_password = tk.Entry(root, show="*", font=("Arial", 14), justify="center")
        self.entry_password.pack(pady=5)
        
        tk.Button(root, text="Login", command=self.attempt_login, bg="#4CAF50", fg="white", font=("Arial", 14, "bold"), width=15).pack(pady=20)
        
        # Allow hitting 'Enter' key to log in
        self.root.bind('<Return>', lambda event: self.attempt_login())

    def attempt_login(self):
        username = self.entry_username.get().strip()
        password = self.entry_password.get().strip()
        
        # Verify login now returns user data (id, username, role)
        user_info = self.db.verify_login(username, password)
        
        if user_info:
            self.root.destroy() # Close the login window
            
            # Launch the main POS application and pass the user info
            main_root = tk.Tk()
            app = POSApp(main_root, current_user=user_info)
            main_root.mainloop()
        else:
            messagebox.showerror("Login Failed", "Invalid username or password.\n\nHint: Use admin / admin123")

if __name__ == "__main__":
    # This ensures the login window is the first thing that opens
    root = tk.Tk()
    app = LoginApp(root)
    root.mainloop()