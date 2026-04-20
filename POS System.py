import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import datetime
import cv2
import time
from pyzbar import pyzbar

# --- DATABASE SETUP ---
class POSDatabase:
    def __init__(self, db_name="pos_system.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Inventory Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barcode TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL
            )
        """)
        
        # Sales History Table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_date TEXT NOT NULL,
                items_summary TEXT NOT NULL,
                total_amount REAL NOT NULL
            )
        """)
        
        # Reset ID sequence to 1 if table is completely empty
        self.cursor.execute("SELECT COUNT(*) FROM products")
        if self.cursor.fetchone()[0] == 0:
            try:
                self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
            except sqlite3.OperationalError:
                pass 
                
        self.conn.commit()

    # --- INVENTORY CRUD OPERATIONS ---
    def get_inventory(self):
        self.cursor.execute("SELECT id, barcode, name, price, stock FROM products")
        return self.cursor.fetchall()

    def get_product_by_barcode(self, barcode):
        self.cursor.execute("SELECT id, barcode, name, price, stock FROM products WHERE barcode = ?", (barcode,))
        return self.cursor.fetchone()

    def add_product(self, barcode, name, price, stock):
        try:
            self.cursor.execute("INSERT INTO products (barcode, name, price, stock) VALUES (?, ?, ?, ?)", (barcode, name, price, stock))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def update_product_info(self, item_id, barcode, name, price, stock):
        try:
            self.cursor.execute("UPDATE products SET barcode = ?, name = ?, price = ?, stock = ? WHERE id = ?", (barcode, name, price, stock, item_id))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_product(self, item_id):
        self.cursor.execute("DELETE FROM products WHERE id = ?", (item_id,))
        
        # Smart Reset: If last item is deleted, reset the ID sequence back to 1
        self.cursor.execute("SELECT COUNT(*) FROM products")
        if self.cursor.fetchone()[0] == 0:
            try:
                self.cursor.execute("DELETE FROM sqlite_sequence WHERE name='products'")
            except sqlite3.OperationalError:
                pass
                
        self.conn.commit()

    # --- SALES OPERATIONS ---
    def update_stock(self, item_id, quantity_sold):
        self.cursor.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (quantity_sold, item_id))
        self.conn.commit()

    def record_sale(self, items_summary, total_amount):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute("INSERT INTO sales_history (sale_date, items_summary, total_amount) VALUES (?, ?, ?)", 
                            (now, items_summary, total_amount))
        self.conn.commit()

    def get_sales_history(self):
        self.cursor.execute("SELECT sale_date, items_summary, total_amount FROM sales_history ORDER BY id DESC")
        return self.cursor.fetchall()


# --- GUI APPLICATION ---
class POSApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Full Screen POS System")
        
        self.is_fullscreen = True
        self.root.attributes('-fullscreen', True)
        self.root.bind("<Escape>", self.toggle_fullscreen)
        
        self.db = POSDatabase()
        self.cart = {} 
        
        self.build_ui()
        self.refresh_inventory_table()

    def toggle_fullscreen(self, event=None):
        self.is_fullscreen = not self.is_fullscreen
        self.root.attributes('-fullscreen', self.is_fullscreen)

    def close_app(self):
        if messagebox.askyesno("Exit", "Are you sure you want to close the POS system?"):
            self.root.destroy()

    def build_ui(self):
        header = tk.Label(self.root, text="MODERN POS TERMINAL", font=("Arial", 24, "bold"), bg="#333", fg="white", pady=15)
        header.pack(fill="x")

        main_frame = tk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        main_frame.columnconfigure(0, weight=6) 
        main_frame.columnconfigure(1, weight=4) 
        main_frame.rowconfigure(0, weight=1)    

        # --- LEFT PANEL: Inventory ---
        left_frame = tk.LabelFrame(main_frame, text="Inventory Database", font=("Arial", 14, "bold"), padx=10, pady=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=(0, 10))

        columns = ("ID", "Barcode", "Name", "Price", "Stock")
        self.tree = ttk.Treeview(left_frame, columns=columns, show="headings", height=15)
        self.tree.heading("ID", text="ID")
        self.tree.heading("Barcode", text="Barcode")
        self.tree.heading("Name", text="Product Name")
        self.tree.heading("Price", text="Price ($)")
        self.tree.heading("Stock", text="In Stock")
        
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Barcode", width=120)
        self.tree.column("Name", width=200)
        self.tree.column("Price", width=80, anchor="e")
        self.tree.column("Stock", width=80, anchor="center")
        
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True, pady=10)

        # Action Buttons
        btn_action_frame = tk.Frame(left_frame)
        btn_action_frame.pack(fill="x", pady=5)
        
        tk.Button(btn_action_frame, text="Add Selected to Cart", command=self.add_selected_to_cart, bg="#4CAF50", fg="white", font=("Arial", 14, "bold"), pady=10).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_action_frame, text="📷 Scan Barcode", command=self.open_scanner, bg="#00BCD4", fg="white", font=("Arial", 14, "bold"), pady=10).pack(side="left", expand=True, fill="x", padx=5)

        # --- RIGHT PANEL: Shopping Cart ---
        right_frame = tk.LabelFrame(main_frame, text="Current Order", font=("Arial", 14, "bold"), padx=10, pady=10)
        right_frame.grid(row=0, column=1, sticky="nsew", pady=(0, 10))

        self.cart_listbox = tk.Listbox(right_frame, font=("Courier", 14))
        self.cart_listbox.pack(fill="both", expand=True, pady=10)

        self.lbl_total = tk.Label(right_frame, text="Total: $0.00", font=("Arial", 26, "bold"), fg="#d32f2f")
        self.lbl_total.pack(anchor="e", pady=15)

        btn_frame = tk.Frame(right_frame)
        btn_frame.pack(fill="x", pady=10)
        
        tk.Button(btn_frame, text="Clear Cart", command=self.clear_cart, bg="#FF9800", fg="white", font=("Arial", 14, "bold"), pady=10).pack(side="left", expand=True, fill="x", padx=5)
        tk.Button(btn_frame, text="Checkout", command=self.checkout, bg="#2196F3", fg="white", font=("Arial", 14, "bold"), pady=10).pack(side="left", expand=True, fill="x", padx=5)

        # --- BOTTOM PANEL: Controls ---
        bottom_frame = tk.Frame(main_frame)
        bottom_frame.grid(row=1, column=0, columnspan=2, sticky="ew")
        
        tk.Button(bottom_frame, text="Exit POS", command=self.close_app, bg="#555", fg="white", font=("Arial", 12, "bold")).pack(side="right", padx=(10, 0), fill="y")
        tk.Button(bottom_frame, text="Purchase History", command=self.view_history, bg="#673AB7", fg="white", font=("Arial", 12, "bold")).pack(side="right", padx=10, fill="y")
        tk.Button(bottom_frame, text="Manage Inventory", command=self.open_admin_panel, bg="#009688", fg="white", font=("Arial", 12, "bold")).pack(side="right", padx=10, fill="y")
        
        tk.Label(bottom_frame, text="Press ESC to toggle full screen", font=("Arial", 10, "italic"), fg="#555").pack(side="left")

    # --- FAST CONTINUOUS BARCODE SCANNER INTEGRATION ---
    def open_scanner(self):
        messagebox.showinfo("Scanner", "Camera active.\nHold a barcode to the camera to add it to the cart.\n\nPress 'q' to close the scanner.")
        cap = cv2.VideoCapture(0)
        
        # SPEED OPTIMIZATION 1: Lower resolution for faster processing
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        last_scanned = None
        last_scan_time = 0
        frame_counter = 0

        while True:
            success, frame = cap.read()
            if not success:
                messagebox.showerror("Camera Error", "Failed to grab frame.")
                break

            frame_counter += 1
            
            # SPEED OPTIMIZATION 2: Skip frames to double the FPS
            if frame_counter % 2 == 0:
                # SPEED OPTIMIZATION 3: Convert to grayscale
                gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                decoded_objects = pyzbar.decode(gray_frame)

                for obj in decoded_objects:
                    barcode = obj.data.decode('utf-8')
                    (x, y, w, h) = obj.rect
                    
                    # Draw targeting box
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                    # 2-second timeout to prevent scanning the same barcode rapidly
                    current_time = time.time()
                    if barcode != last_scanned or (current_time - last_scan_time) > 2.0:
                        last_scanned = barcode
                        last_scan_time = current_time
                        self.handle_scanned_barcode(barcode)
                    
                    cv2.putText(frame, "SCANNED!", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Draw instructions
            cv2.putText(frame, "Active: Press 'q' to quit", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow("Scanner (Press 'q' to quit)", frame)

            # Important: Keep the Tkinter GUI updating so the cart shows new items live!
            self.root.update()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def handle_scanned_barcode(self, barcode):
        product = self.db.get_product_by_barcode(barcode)
        if product:
            item_id, barcode_val, name, price, stock = product
            self.process_cart_addition(item_id, name, price, stock)
        else:
            messagebox.showerror("Not Found", f"Scanned barcode '{barcode}' not found in inventory!")

    # --- CORE POS LOGIC ---
    def refresh_inventory_table(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        for item in self.db.get_inventory():
            formatted_item = (item[0], item[1], item[2], f"{item[3]:.2f}", item[4])
            self.tree.insert("", tk.END, values=formatted_item)

    def add_selected_to_cart(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select an item from the inventory.")
            return

        item_values = self.tree.item(selected[0], "values")
        item_id = int(item_values[0])
        name = item_values[2]
        price = float(item_values[3])
        stock = int(item_values[4])

        self.process_cart_addition(item_id, name, price, stock)

    def process_cart_addition(self, item_id, name, price, stock):
        current_cart_qty = self.cart.get(item_id, {}).get("qty", 0)
        
        if stock > current_cart_qty:
            if item_id in self.cart:
                self.cart[item_id]["qty"] += 1
            else:
                self.cart[item_id] = {"name": name, "price": price, "qty": 1}
            self.update_cart_display()
        else:
            messagebox.showerror("Out of Stock", f"Not enough {name} in stock!")

    def update_cart_display(self):
        self.cart_listbox.delete(0, tk.END)
        total = 0.0

        for item_id, info in self.cart.items():
            line_total = info["price"] * info["qty"]
            total += line_total
            self.cart_listbox.insert(tk.END, f"{info['name'][:20]:<20} x{info['qty']:<3} ${line_total:>7.2f}")

        self.lbl_total.config(text=f"Total: ${total:.2f}")

    def clear_cart(self):
        self.cart.clear()
        self.update_cart_display()

    def checkout(self):
        if not self.cart:
            messagebox.showinfo("Empty", "Your cart is empty.")
            return

        total_amount = 0.0
        summary_list = []

        for item_id, info in self.cart.items():
            total_amount += info["price"] * info["qty"]
            summary_list.append(f"{info['qty']}x {info['name']}")
            self.db.update_stock(item_id, info["qty"])

        items_summary = ", ".join(summary_list)
        self.db.record_sale(items_summary, total_amount)

        messagebox.showinfo("Checkout Success", f"Transaction complete!\nTotal Paid: ${total_amount:.2f}")
        
        self.clear_cart()
        self.refresh_inventory_table()

    # --- HISTORY PANEL ---
    def view_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title("Purchase History")
        history_window.geometry("800x400")
        history_window.grab_set() 

        columns = ("Date", "Items", "Total")
        hist_tree = ttk.Treeview(history_window, columns=columns, show="headings")
        hist_tree.heading("Date", text="Date & Time")
        hist_tree.heading("Items", text="Purchased Items")
        hist_tree.heading("Total", text="Total Paid ($)")
        
        hist_tree.column("Date", width=150, anchor="center")
        hist_tree.column("Items", width=500)
        hist_tree.column("Total", width=100, anchor="e")
        
        hist_tree.pack(fill="both", expand=True, padx=10, pady=10)

        for record in self.db.get_sales_history():
            formatted_record = (record[0], record[1], f"${record[2]:.2f}")
            hist_tree.insert("", tk.END, values=formatted_record)

    # --- CRUD ADMIN PANEL ---
    def open_admin_panel(self):
        if self.cart:
            messagebox.showwarning("Warning", "Please clear your cart or finish checkout before managing inventory.")
            return

        self.admin_win = tk.Toplevel(self.root)
        self.admin_win.title("Manage Inventory (CRUD)")
        self.admin_win.geometry("800x550")
        self.admin_win.grab_set()

        form_frame = tk.Frame(self.admin_win, pady=15)
        form_frame.pack(fill="x", padx=20)

        tk.Label(form_frame, text="Selected ID:").grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_id = tk.Entry(form_frame, state="readonly", width=30)
        self.entry_id.grid(row=0, column=1, pady=5)

        tk.Label(form_frame, text="Barcode:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_barcode = tk.Entry(form_frame, width=30)
        self.entry_barcode.grid(row=1, column=1, pady=5)

        tk.Label(form_frame, text="Product Name:").grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.entry_name = tk.Entry(form_frame, width=30)
        self.entry_name.grid(row=2, column=1, pady=5)

        tk.Label(form_frame, text="Price ($):").grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.entry_price = tk.Entry(form_frame, width=30)
        self.entry_price.grid(row=3, column=1, pady=5)

        tk.Label(form_frame, text="Stock Quantity:").grid(row=4, column=0, sticky="e", padx=5, pady=5)
        self.entry_stock = tk.Entry(form_frame, width=30)
        self.entry_stock.grid(row=4, column=1, pady=5)

        btn_frame = tk.Frame(self.admin_win)
        btn_frame.pack(fill="x", padx=20, pady=10)

        tk.Button(btn_frame, text="Add New Item", command=self.crud_add, bg="#4CAF50", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Update Item", command=self.crud_update, bg="#2196F3", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Delete Item", command=self.crud_delete, bg="#F44336", fg="white", width=15).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Clear Form", command=self.crud_clear_form, bg="#9E9E9E", fg="white", width=15).pack(side="left", padx=5)

        tree_frame = tk.Frame(self.admin_win)
        tree_frame.pack(fill="both", expand=True, padx=20, pady=10)

        columns = ("ID", "Barcode", "Name", "Price", "Stock")
        self.admin_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.admin_tree.heading("ID", text="ID")
        self.admin_tree.heading("Barcode", text="Barcode")
        self.admin_tree.heading("Name", text="Product Name")
        self.admin_tree.heading("Price", text="Price")
        self.admin_tree.heading("Stock", text="Stock")
        self.admin_tree.pack(fill="both", expand=True)

        self.admin_tree.bind("<ButtonRelease-1>", self.crud_select_item)
        self.crud_refresh_list()

        self.admin_win.protocol("WM_DELETE_WINDOW", self.close_admin_panel)

    def close_admin_panel(self):
        self.refresh_inventory_table()
        self.admin_win.destroy()

    def crud_refresh_list(self):
        for row in self.admin_tree.get_children():
            self.admin_tree.delete(row)
        for item in self.db.get_inventory():
            self.admin_tree.insert("", tk.END, values=item)

    def crud_select_item(self, event):
        selected = self.admin_tree.selection()
        if selected:
            item = self.admin_tree.item(selected[0], "values")
            self.crud_clear_form()
            self.entry_id.config(state="normal")
            self.entry_id.insert(0, item[0])
            self.entry_id.config(state="readonly")
            self.entry_barcode.insert(0, item[1])
            self.entry_name.insert(0, item[2])
            self.entry_price.insert(0, item[3])
            self.entry_stock.insert(0, item[4])

    def crud_clear_form(self):
        self.entry_id.config(state="normal")
        self.entry_id.delete(0, tk.END)
        self.entry_id.config(state="readonly")
        self.entry_barcode.delete(0, tk.END)
        self.entry_name.delete(0, tk.END)
        self.entry_price.delete(0, tk.END)
        self.entry_stock.delete(0, tk.END)

    def crud_add(self):
        barcode = self.entry_barcode.get()
        name = self.entry_name.get()
        try:
            price = float(self.entry_price.get())
            stock = int(self.entry_stock.get())
            if name and barcode:
                success = self.db.add_product(barcode, name, price, stock)
                if success:
                    self.crud_refresh_list()
                    self.crud_clear_form()
                    messagebox.showinfo("Success", "Product added successfully!")
                else:
                    messagebox.showwarning("Error", "Barcode already exists!")
            else:
                messagebox.showwarning("Error", "Barcode and Product name cannot be empty.")
        except ValueError:
            messagebox.showwarning("Error", "Please enter valid numbers for Price and Stock.")

    def crud_update(self):
        item_id = self.entry_id.get()
        barcode = self.entry_barcode.get()
        name = self.entry_name.get()
        if not item_id:
            messagebox.showwarning("Error", "Please select an item to update.")
            return
        try:
            price = float(self.entry_price.get())
            stock = int(self.entry_stock.get())
            success = self.db.update_product_info(int(item_id), barcode, name, price, stock)
            if success:
                self.crud_refresh_list()
                self.crud_clear_form()
                messagebox.showinfo("Success", "Product updated successfully!")
            else:
                messagebox.showwarning("Error", "Barcode already assigned to another item.")
        except ValueError:
            messagebox.showwarning("Error", "Please enter valid numbers for Price and Stock.")

    def crud_delete(self):
        item_id = self.entry_id.get()
        if not item_id:
            messagebox.showwarning("Error", "Please select an item to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this product?"):
            self.db.delete_product(int(item_id))
            self.crud_refresh_list()
            self.crud_clear_form()
            messagebox.showinfo("Success", "Product deleted successfully!")

# --- MAIN EXECUTION ---
if __name__ == "__main__":
    root = tk.Tk()
    app = POSApp(root)
    root.mainloop()