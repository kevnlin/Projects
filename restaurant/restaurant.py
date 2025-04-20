import sqlite3
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

class RestaurantInventory:
    def __init__(self):
        self.conn = sqlite3.connect('restaurant_inventory.db')
        self.create_tables()
        self.setup_gui()
        self.alert_levels = {
            "critical": 25,  # Below 25% of reorder level
            "warning": 50,   # Below 50% of reorder level
            "notice": 75     # Below 75% of reorder level
        }
        self.dragged_item = None

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inventory (
                id INTEGER PRIMARY KEY,
                item_name TEXT NOT NULL,
                quantity INTEGER,
                unit TEXT,
                category TEXT,
                reorder_level INTEGER,
                last_updated DATETIME,
                expiration_date DATE,
                stock_history TEXT
            )
        ''')
        
        # Add stock history table for tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_history (
                id INTEGER PRIMARY KEY,
                item_name TEXT NOT NULL,
                quantity INTEGER,
                change_amount INTEGER,
                timestamp DATETIME,
                action_type TEXT
            )
        ''')
        self.conn.commit()

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Restaurant Inventory Management")
        self.root.geometry("800x600")

        # Create tabs
        self.tab_control = ttk.Notebook(self.root)
        
        # Inventory tab
        inventory_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(inventory_tab, text='Inventory')
        
        # Add item frame
        add_frame = ttk.LabelFrame(inventory_tab, text="Add/Update Item", padding=10)
        add_frame.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        ttk.Label(add_frame, text="Item Name:").grid(row=0, column=0, padx=5, pady=5)
        self.item_name = ttk.Entry(add_frame)
        self.item_name.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Quantity:").grid(row=0, column=2, padx=5, pady=5)
        self.quantity = ttk.Entry(add_frame)
        self.quantity.grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(add_frame, text="Unit:").grid(row=1, column=0, padx=5, pady=5)
        self.unit = ttk.Entry(add_frame)
        self.unit.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Category:").grid(row=1, column=2, padx=5, pady=5)
        self.category = ttk.Entry(add_frame)
        self.category.grid(row=1, column=3, padx=5, pady=5)

        ttk.Label(add_frame, text="Reorder Level:").grid(row=2, column=0, padx=5, pady=5)
        self.reorder_level = ttk.Entry(add_frame)
        self.reorder_level.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(add_frame, text="Expiration Date:").grid(row=2, column=2, padx=5, pady=5)
        self.expiration_date = ttk.Entry(add_frame)
        self.expiration_date.grid(row=2, column=3, padx=5, pady=5)
        self.expiration_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

        ttk.Button(add_frame, text="Add/Update Item", command=self.add_item).grid(row=3, column=0, columnspan=4, pady=10)

        # Inventory list
        list_frame = ttk.Frame(inventory_tab)
        list_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")

        columns = ('Item Name', 'Quantity', 'Unit', 'Category', 'Reorder Level', 'Expiration Date', 'Last Updated')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Bind events for drag and drop
        self.tree.bind('<Button-1>', self.on_click)
        self.tree.bind('<B1-Motion>', self.on_drag)
        self.tree.bind('<ButtonRelease-1>', self.on_drop)
        
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        self.tree.grid(row=0, column=0, sticky="nsew")
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)

        # Buttons frame
        btn_frame = ttk.Frame(inventory_tab)
        btn_frame.grid(row=2, column=0, padx=10, pady=5)

        ttk.Button(btn_frame, text="Refresh List", command=self.refresh_list).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Check Low Stock", command=self.check_low_stock).pack(side=tk.LEFT, padx=5)

        # Add quick update buttons
        quick_update_frame = ttk.LabelFrame(inventory_tab, text="Quick Update", padding=10)
        quick_update_frame.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        ttk.Button(quick_update_frame, text="+1", command=lambda: self.quick_update(1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="+5", command=lambda: self.quick_update(5)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="+10", command=lambda: self.quick_update(10)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="-1", command=lambda: self.quick_update(-1)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="-5", command=lambda: self.quick_update(-5)).pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="-10", command=lambda: self.quick_update(-10)).pack(side=tk.LEFT, padx=5)

        # Add custom update entry
        self.quick_update_value = ttk.Entry(quick_update_frame, width=10)
        self.quick_update_value.pack(side=tk.LEFT, padx=5)
        ttk.Button(quick_update_frame, text="Update", 
                  command=self.custom_update).pack(side=tk.LEFT, padx=5)

        self.tab_control.pack(expand=1, fill="both")
        
        # Initial refresh
        self.refresh_list()
        
        # Add Analytics tab
        analytics_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(analytics_tab, text='Analytics')
        
        # Add stock level chart
        self.fig, self.ax = plt.subplots(figsize=(8, 4))
        self.canvas = FigureCanvasTkAgg(self.fig, master=analytics_tab)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add refresh button for analytics
        ttk.Button(analytics_tab, text="Refresh Analytics", 
                  command=self.update_analytics).pack(pady=5)

        self.root.mainloop()

    def on_click(self, event):
        """Handle click event for item selection"""
        item = self.tree.identify_row(event.y)
        if item:
            self.dragged_item = item
            self.item_selected(None)  # Auto-fill form with selected item

    def on_drag(self, event):
        """Handle drag event for reordering"""
        if self.dragged_item:
            item = self.tree.identify_row(event.y)
            if item and item != self.dragged_item:
                # Get the values of the dragged item
                dragged_values = self.tree.item(self.dragged_item)['values']
                # Remove the dragged item
                self.tree.delete(self.dragged_item)
                # Insert it at the new position
                self.tree.insert('', self.tree.index(item), values=dragged_values)
                self.dragged_item = item

    def on_drop(self, event):
        """Handle drop event for reordering"""
        self.dragged_item = None

    def item_selected(self, event):
        """Auto-fill form when an item is selected in the tree"""
        selected_item = self.tree.selection()
        if not selected_item:
            return
            
        # Get the values of the selected item
        item_values = self.tree.item(selected_item)['values']
        
        # Clear current entries
        self.clear_entries()
        
        # Fill the entries with selected item's values
        self.item_name.insert(0, item_values[0])  # Item Name
        self.quantity.insert(0, item_values[1])   # Quantity
        self.unit.insert(0, item_values[2])       # Unit
        self.category.insert(0, item_values[3])   # Category
        self.reorder_level.insert(0, item_values[4]) # Reorder Level
        self.expiration_date.insert(0, item_values[5]) # Expiration Date

    def add_item(self):
        try:
            item_name = self.item_name.get()
            new_quantity = int(self.quantity.get())
            expiration_date = self.expiration_date.get()
            
            # Validate expiration date format
            try:
                datetime.strptime(expiration_date, '%Y-%m-%d')
            except ValueError:
                messagebox.showerror("Error", "Invalid expiration date format. Please use YYYY-MM-DD")
                return
            
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM inventory WHERE item_name = ?', (item_name,))
            existing_item = cursor.fetchone()
            
            if existing_item:
                current_quantity = existing_item[2]
                change_amount = new_quantity - current_quantity
                
                if not messagebox.askyesno("Confirm Update", 
                    f"Update {item_name}?\n"
                    f"Current quantity: {current_quantity}\n"
                    f"Change by: {change_amount:+d}\n"
                    f"New quantity: {new_quantity}\n"
                    f"\nUnit: {self.unit.get()}\n"
                    f"Category: {self.category.get()}\n"
                    f"Reorder level: {self.reorder_level.get()}\n"
                    f"Expiration date: {expiration_date}"):
                    return

            cursor.execute('''
                INSERT OR REPLACE INTO inventory 
                (item_name, quantity, unit, category, reorder_level, expiration_date, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                item_name,
                new_quantity,
                self.unit.get(),
                self.category.get(),
                int(self.reorder_level.get()),
                expiration_date,
                datetime.now()
            ))
            self.conn.commit()
            self.refresh_list()
            messagebox.showinfo("Success", "Item added/updated successfully!")
            self.clear_entries()
        except Exception as e:
            messagebox.showerror("Error", f"Error adding item: {str(e)}")

    def refresh_list(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name, quantity, unit, category, reorder_level, 
                   expiration_date, last_updated 
            FROM inventory
            ORDER BY expiration_date ASC
        ''')
        for row in cursor.fetchall():
            self.tree.insert('', 'end', values=row)

    def delete_item(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to delete")
            return
            
        item_name = self.tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete {item_name}?"):
            cursor = self.conn.cursor()
            cursor.execute('DELETE FROM inventory WHERE item_name = ?', (item_name,))
            self.conn.commit()
            self.refresh_list()
            self.clear_entries()  # Clear the form after deletion

    def check_low_stock(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT 
                item_name, 
                quantity, 
                reorder_level,
                CAST((quantity * 100.0 / reorder_level) as INTEGER) as stock_level,
                last_updated,
                category
            FROM inventory 
            WHERE quantity <= reorder_level
            ORDER BY stock_level ASC
        ''')
        low_stock = cursor.fetchall()
        
        if low_stock:
            message = "Low Stock Report:\n\n"
            for item in low_stock:
                stock_level = item[3]
                alert_prefix = "🔴 CRITICAL: " if stock_level <= self.alert_levels["critical"] else \
                             "🟠 WARNING: " if stock_level <= self.alert_levels["warning"] else \
                             "🟡 NOTICE: "
                
                days_since_update = (datetime.now() - datetime.strptime(item[4], '%Y-%m-%d %H:%M:%S.%f')).days
                
                message += (f"{alert_prefix}{item[0]} ({item[5]})\n"
                          f"  Current: {item[1]} {item[2]}\n"
                          f"  Reorder Level: {item[2]}\n"
                          f"  Stock Level: {item[3]}%\n"
                          f"  Last Updated: {days_since_update} days ago\n\n")
            
            messagebox.warning("Stock Alert", message)
            
            # Suggest order quantities
            self.suggest_order_quantities(low_stock)
        else:
            messagebox.showinfo("Stock Status", "All items are above reorder levels")

    def suggest_order_quantities(self, low_stock):
        """Calculate and suggest order quantities"""
        suggestions = "Suggested Order Quantities:\n\n"
        
        for item in low_stock:
            name, current, reorder = item[0], item[1], item[2]
            
            # Calculate average daily usage from history
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT AVG(ABS(change_amount)) 
                FROM stock_history 
                WHERE item_name = ? 
                AND action_type = 'usage'
                AND timestamp >= ?
            ''', (name, datetime.now() - timedelta(days=30)))
            
            daily_usage = cursor.fetchone()[0] or 1  # Default to 1 if no history
            
            # Calculate suggested order amount
            suggested = max(
                reorder * 2 - current,  # Twice reorder level
                int(daily_usage * 14)   # Two weeks supply
            )
            
            suggestions += (f"{name}:\n"
                          f"  Suggested Order: {suggested} units\n"
                          f"  (Based on average daily usage: {daily_usage:.1f})\n\n")
        
        messagebox.showinfo("Order Suggestions", suggestions)

    def clear_entries(self):
        self.item_name.delete(0, tk.END)
        self.quantity.delete(0, tk.END)
        self.unit.delete(0, tk.END)
        self.category.delete(0, tk.END)
        self.reorder_level.delete(0, tk.END)
        self.expiration_date.delete(0, tk.END)
        self.expiration_date.insert(0, datetime.now().strftime('%Y-%m-%d'))

    def quick_update(self, change_amount):
        """Quickly update quantity of selected item"""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select an item to update")
            return

        item_values = self.tree.item(selected_item)['values']
        current_quantity = int(item_values[1])
        new_quantity = current_quantity + change_amount

        if new_quantity < 0:
            messagebox.showerror("Error", "Quantity cannot be negative")
            return

        if messagebox.askyesno("Confirm Update", 
            f"Update {item_values[0]}?\n"
            f"Current quantity: {current_quantity}\n"
            f"Change by: {change_amount:+d}\n"
            f"New quantity: {new_quantity}\n"
            f"\nReorder level: {item_values[4]}"):
            
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE inventory 
                SET quantity = ?, last_updated = ?
                WHERE item_name = ?
            ''', (new_quantity, datetime.now(), item_values[0]))
            
            # Record in history
            self.add_to_history(
                item_values[0], 
                new_quantity, 
                change_amount,
                'usage' if change_amount < 0 else 'restock'
            )
            
            self.conn.commit()
            self.refresh_list()
            self.update_analytics()  # Update charts
            
            # Enhanced stock level warning
            if new_quantity <= int(item_values[4]):
                stock_level = int((new_quantity * 100.0) / int(item_values[4]))
                alert_type = "CRITICAL" if stock_level <= self.alert_levels["critical"] else \
                            "WARNING" if stock_level <= self.alert_levels["warning"] else \
                            "NOTICE"
                
                messagebox.showwarning(f"{alert_type} - Low Stock Alert", 
                    f"{item_values[0]} is now at {stock_level}% of reorder level!\n"
                    f"Current quantity: {new_quantity}\n"
                    f"Reorder level: {item_values[4]}\n\n"
                    f"Suggested action: Place order soon")

    def custom_update(self):
        """Update quantity by custom amount"""
        try:
            change_amount = int(self.quick_update_value.get())
            self.quick_update(change_amount)
            self.quick_update_value.delete(0, tk.END)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number")

    def update_analytics(self):
        """Update analytics charts"""
        self.ax.clear()
        
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT item_name, quantity, reorder_level,
                   CAST((quantity * 100.0 / reorder_level) as INTEGER) as stock_level
            FROM inventory
            ORDER BY stock_level ASC
        ''')
        data = cursor.fetchall()
        
        if not data:
            return
            
        names = [row[0] for row in data]
        levels = [row[3] for row in data]
        colors = ['red' if l <= self.alert_levels["critical"] else
                 'orange' if l <= self.alert_levels["warning"] else
                 'yellow' if l <= self.alert_levels["notice"] else
                 'green' for l in levels]
        
        self.ax.bar(names, levels, color=colors)
        self.ax.set_ylabel('Stock Level (%)')
        self.ax.set_title('Current Stock Levels')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        self.canvas.draw()

    def add_to_history(self, item_name, quantity, change_amount, action_type):
        """Record stock change in history"""
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO stock_history 
            (item_name, quantity, change_amount, timestamp, action_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (item_name, quantity, change_amount, datetime.now(), action_type))
        self.conn.commit()

if __name__ == "__main__":
    app = RestaurantInventory()
