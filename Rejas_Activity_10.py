import tkinter as tk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os

class ProfileManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Student Profile Manager")
        self.root.geometry("800x600")
        
        # Database (In-memory dictionary. Key = Student Number)
        self.profiles = {}
        self.current_image_path = None
        self.default_image = None # Placeholder for when no image is selected

        self.setup_ui()

    def setup_ui(self):
        # --- Left Panel: List of Profiles ---
        left_frame = tk.Frame(self.root, width=250, bg="#f0f0f0", padx=10, pady=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(left_frame, text="Registered Profiles", bg="#f0f0f0", font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        self.profile_listbox = tk.Listbox(left_frame, font=("Arial", 10))
        self.profile_listbox.pack(fill=tk.BOTH, expand=True)
        self.profile_listbox.bind('<<ListboxSelect>>', self.view_profile)

        # --- Right Panel: Profile Details Form ---
        right_frame = tk.Frame(self.root, padx=20, pady=20)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Form Fields Data Variables
        self.vars = {
            "First Name": tk.StringVar(),
            "Last Name": tk.StringVar(),
            "Student Number": tk.StringVar(),
            "Age": tk.StringVar(),
            "Address": tk.StringVar(),
            "Contact Number": tk.StringVar(),
            "Year Level": tk.StringVar(),
            "Course": tk.StringVar()
        }

        # Image Display Label
        self.img_label = tk.Label(right_frame, text="No Image", bg="gray", width=15, height=7)
        self.img_label.grid(row=0, column=0, rowspan=3, padx=10, pady=10, sticky="n")

        tk.Button(right_frame, text="Upload Image", command=self.upload_image).grid(row=3, column=0, pady=5)

        # Create Form Entries dynamically
        row = 0
        for i, (label_text, var) in enumerate(self.vars.items()):
            # Shift rows down for fields that appear next to/below the image
            grid_row = i if i >= 3 else i
            grid_col = 1 if i < 3 else 0
            
            if i >= 3:
                grid_row += 1

            tk.Label(right_frame, text=f"{label_text}:", font=("Arial", 10, "bold")).grid(row=grid_row, column=grid_col if i<3 else 0, sticky="e", pady=5, padx=5)
            tk.Entry(right_frame, textvariable=var, width=30).grid(row=grid_row, column=(grid_col+1) if i<3 else 1, sticky="w", pady=5, padx=5)

        # --- Action Buttons ---
        button_frame = tk.Frame(right_frame, pady=20)
        button_frame.grid(row=10, column=0, columnspan=3)

        tk.Button(button_frame, text="Add Profile", bg="#4CAF50", fg="white", width=12, command=self.add_profile).grid(row=0, column=0, padx=5)
        tk.Button(button_frame, text="Update/Edit", bg="#2196F3", fg="white", width=12, command=self.edit_profile).grid(row=0, column=1, padx=5)
        tk.Button(button_frame, text="Delete", bg="#f44336", fg="white", width=12, command=self.delete_profile).grid(row=0, column=2, padx=5)
        tk.Button(button_frame, text="Clear Form", bg="#9e9e9e", fg="white", width=12, command=self.clear_form).grid(row=0, column=3, padx=5)

    # --- Methods ---

    def upload_image(self):
        filepath = filedialog.askopenfilename(
            title="Select Profile Image",
            filetypes=(("Image files", "*.jpg *.jpeg *.png"), ("All files", "*.*"))
        )
        if filepath:
            self.current_image_path = filepath
            self.display_image(filepath)

    def display_image(self, path):
        try:
            img = Image.open(path)
            img = img.resize((120, 120), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(img)
            self.img_label.config(image=photo, text="")
            self.img_label.image = photo # Keep a reference to prevent garbage collection
        except Exception as e:
            messagebox.showerror("Image Error", f"Could not load image: {e}")

    def get_form_data(self):
        return {key: var.get().strip() for key, var in self.vars.items()}

    def add_profile(self):
        data = self.get_form_data()
        student_no = data["Student Number"]

        if not student_no or not data["First Name"]:
            messagebox.showwarning("Input Error", "First Name and Student Number are required!")
            return

        if student_no in self.profiles:
            messagebox.showerror("Error", "A profile with this Student Number already exists!")
            return

        # Save profile
        data["Image Path"] = self.current_image_path
        self.profiles[student_no] = data
        
        self.update_listbox()
        self.clear_form()
        messagebox.showinfo("Success", "Profile added successfully!")

    def view_profile(self, event):
        selection = self.profile_listbox.curselection()
        if not selection:
            return
        
        # Get student number from the selected listbox item
        selected_text = self.profile_listbox.get(selection[0])
        student_no = selected_text.split(" - ")[0]
        
        profile = self.profiles.get(student_no)
        if profile:
            self.clear_form() # Clear first to avoid residual data
            
            # Populate text fields
            for key in self.vars:
                self.vars[key].set(profile[key])
            
            # Populate image
            self.current_image_path = profile.get("Image Path")
            if self.current_image_path and os.path.exists(self.current_image_path):
                self.display_image(self.current_image_path)
            else:
                self.img_label.config(image='', text="No Image")

    def edit_profile(self):
        data = self.get_form_data()
        student_no = data["Student Number"]

        if not student_no:
            messagebox.showwarning("Input Error", "Student Number is required to edit a profile.")
            return

        if student_no not in self.profiles:
            messagebox.showerror("Error", "Profile not found. Student Number cannot be changed during an edit.")
            return

        data["Image Path"] = self.current_image_path
        self.profiles[student_no] = data
        self.update_listbox()
        messagebox.showinfo("Success", "Profile updated successfully!")

    def delete_profile(self):
        student_no = self.vars["Student Number"].get().strip()
        if not student_no:
            messagebox.showwarning("Selection Error", "Please select a profile to delete (or enter the Student Number).")
            return
            
        if student_no in self.profiles:
            confirm = messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete profile {student_no}?")
            if confirm:
                del self.profiles[student_no]
                self.update_listbox()
                self.clear_form()
                messagebox.showinfo("Success", "Profile deleted.")
        else:
            messagebox.showerror("Error", "Profile not found.")

    def clear_form(self):
        for var in self.vars.values():
            var.set("")
        self.current_image_path = None
        self.img_label.config(image='', text="No Image")
        self.profile_listbox.selection_clear(0, tk.END)

    def update_listbox(self):
        self.profile_listbox.delete(0, tk.END)
        for student_no, data in self.profiles.items():
            display_text = f"{student_no} - {data['First Name']} {data['Last Name']}"
            self.profile_listbox.insert(tk.END, display_text)

if __name__ == "__main__":
    root = tk.Tk()
    app = ProfileManagerApp(root)
    root.mainloop()