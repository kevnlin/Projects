import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os

class InventoryItem:
    def __init__(self, name, quantity, expiration_date, category):
        self.name = name
        self.quantity = quantity
        self.expiration_date = expiration_date
        self.category = category

class WasteBatch:
    def __init__(self, batch_date, items, total_waste, notes):
        self.batch_date = batch_date
        self.items = items  # List of WasteItem objects
        self.total_waste = total_waste
        self.notes = notes

class WasteItem:
    def __init__(self, item, quantity_wasted, date, reason, notes, batch_id=None):
        self.item = item
        self.quantity_wasted = quantity_wasted
        self.date = date
        self.reason = reason
        self.notes = notes
        self.batch_id = batch_id

class InventoryManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Restaurant Inventory Management")
        self.root.geometry("1000x600")
        
        # Data storage
        self.items = []
        self.waste_items = []
        self.waste_batches = []
        self.current_batch_items = []
        self.current_batch_total = 0
        
        # Load data
        self.load_data()
        
        # Create main frame
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create inventory tab
        self.inventory_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_frame, text="Inventory")
        
        # Create waste tracker tab
        self.waste_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.waste_frame, text="Waste Tracker")
        
        # Create left panel for item list
        self.create_item_list()
        
        # Create right panel for item details
        self.create_item_details()
        
        # Create waste tracker interface
        self.create_waste_tracker()
        
        # Bind drag and drop events
        self.setup_drag_drop()
        
        # Bind window close event
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Bring window to front
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        # Update displays after UI is created
        self.update_item_list()
        self.update_waste_list()
        self.update_batch_list()
        
    def on_closing(self):
        # Save data before closing
        self.save_data()
        self.root.destroy()
        
    def validate_date(self, date_str):
        try:
            # Try parsing with year first
            if len(date_str.split('/')) == 3:
                return datetime.strptime(date_str, "%m/%d/%Y").strftime("%m/%d/%Y")
            # Try parsing without year
            elif len(date_str.split('/')) == 2:
                return datetime.strptime(date_str, "%m/%d").strftime("%m/%d")
            else:
                return None
        except ValueError:
            return None
            
    def create_item_list(self):
        # Create list frame
        self.list_frame = ttk.LabelFrame(self.inventory_frame, text="Inventory Items")
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create treeview
        self.tree = ttk.Treeview(self.list_frame, columns=("Name", "Quantity", "Expiration", "Category"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Expiration", text="Expiration Date")
        self.tree.heading("Category", text="Category")
        
        # Configure columns
        self.tree.column("Name", width=150)
        self.tree.column("Quantity", width=100)
        self.tree.column("Expiration", width=150)
        self.tree.column("Category", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        
    def create_item_details(self):
        # Create details frame
        self.details_frame = ttk.LabelFrame(self.inventory_frame, text="Item Details")
        self.details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create form fields
        ttk.Label(self.details_frame, text="Name:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.name_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.name_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.details_frame, text="Quantity:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.quantity_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.quantity_var).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self.details_frame, text="Expiration Date:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.expiration_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.expiration_var).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(self.details_frame, text="Category:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.category_var = tk.StringVar()
        ttk.Entry(self.details_frame, textvariable=self.category_var).grid(row=3, column=1, padx=5, pady=5)
        
        # Create button frame
        button_frame = ttk.Frame(self.details_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        # Create buttons
        ttk.Button(button_frame, text="Save", command=self.save_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_item).pack(side=tk.LEFT, padx=5)
        
        # Create sort buttons frame
        sort_frame = ttk.Frame(self.details_frame)
        sort_frame.grid(row=5, column=0, columnspan=2, pady=5)
        
        ttk.Button(sort_frame, text="Sort by Name", command=lambda: self.sort_items("Name")).pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="Sort by Expiration", command=lambda: self.sort_items("Expiration")).pack(side=tk.LEFT, padx=5)
        
    def create_controls(self):
        # Create controls frame
        self.controls_frame = ttk.Frame(self.inventory_frame)
        self.controls_frame.pack(fill=tk.X, padx=10, pady=5)
        
    def setup_drag_drop(self):
        self.tree.bind("<Button-1>", self.start_drag)
        self.tree.bind("<B1-Motion>", self.on_drag)
        self.tree.bind("<ButtonRelease-1>", self.stop_drag)
        
    def start_drag(self, event):
        self.drag_data = {"x": event.x, "y": event.y}
        
    def on_drag(self, event):
        if hasattr(self, 'drag_data'):
            dx = event.x - self.drag_data["x"]
            dy = event.y - self.drag_data["y"]
            self.tree.yview_scroll(int(-1*(dy/120)), "units")
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            
    def stop_drag(self, event):
        if hasattr(self, 'drag_data'):
            del self.drag_data
            
    def add_new_item(self):
        self.name_var.set("")
        self.quantity_var.set("")
        self.expiration_var.set("")
        self.category_var.set("")
        
    def save_item(self):
        try:
            name = self.name_var.get()
            quantity = int(self.quantity_var.get())
            expiration = self.expiration_var.get()
            category = self.category_var.get()
            
            if not all([name, quantity, expiration, category]):
                messagebox.showerror("Error", "All fields are required!")
                return
                
            # Validate date format
            formatted_date = self.validate_date(expiration)
            if not formatted_date:
                messagebox.showerror("Error", "Invalid date format! Use MM/DD or MM/DD/YYYY")
                return
                
            # Create or update item
            item = InventoryItem(name, quantity, formatted_date, category)
            
            # Check if item exists
            selected = self.tree.selection()
            if selected:
                # Update existing item
                index = self.tree.index(selected[0])
                self.items[index] = item
            else:
                # Add new item
                self.items.append(item)
                
            # Sort items by expiration date for FIFO
            self.items.sort(key=lambda x: datetime.strptime(x.expiration_date, "%m/%d/%Y") if len(x.expiration_date.split('/')) == 3 else datetime.strptime(x.expiration_date, "%m/%d"))
            
            self.update_item_list()
            self.save_data()
            
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number!")
            
    def delete_item(self):
        selected = self.tree.selection()
        if selected:
            index = self.tree.index(selected[0])
            del self.items[index]
            self.update_item_list()
            self.save_data()
            
    def on_item_select(self, event):
        selected = self.tree.selection()
        if selected:
            index = self.tree.index(selected[0])
            item = self.items[index]
            self.name_var.set(item.name)
            self.quantity_var.set(str(item.quantity))
            self.expiration_var.set(item.expiration_date)
            self.category_var.set(item.category)
            
    def update_item_list(self):
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Add items
        for item in self.items:
            # Calculate days until expiration
            expiration_date = datetime.strptime(item.expiration_date, "%m/%d/%Y") if len(item.expiration_date.split('/')) == 3 else datetime.strptime(item.expiration_date, "%m/%d")
            days_until_expiration = (expiration_date - datetime.now()).days
            
            # Determine tag based on expiration status
            if expiration_date < datetime.now():
                tag = 'expired'
            elif days_until_expiration <= 7:
                tag = 'expiring_soon'
            else:
                tag = ''
                
            self.tree.insert("", tk.END, values=(
                item.name,
                item.quantity,
                item.expiration_date,
                item.category
            ), tags=(tag,))
        
        # Configure tag styles
        self.tree.tag_configure('expired', background='red')
        self.tree.tag_configure('expiring_soon', background='yellow')
        
        # Auto-save after updating list
        self.save_data()
        
    def sort_items(self, column):
        if column == "Name":
            self.items.sort(key=lambda x: x.name)
        elif column == "Expiration":
            self.items.sort(key=lambda x: x.expiration_date)
        self.update_item_list()
        
    def create_waste_tracker(self):
        # Create notebook for waste tracking
        waste_notebook = ttk.Notebook(self.waste_frame)
        waste_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create individual waste entry tab
        individual_frame = ttk.Frame(waste_notebook)
        waste_notebook.add(individual_frame, text="Individual Entries")
        
        # Create batch waste entry tab
        batch_frame = ttk.Frame(waste_notebook)
        waste_notebook.add(batch_frame, text="Batch Entries")
        
        # Create individual waste interface
        self.create_individual_waste_interface(individual_frame)
        
        # Create batch waste interface
        self.create_batch_waste_interface(batch_frame)
        
    def create_individual_waste_interface(self, parent):
        # Create waste list frame
        self.waste_list_frame = ttk.LabelFrame(parent, text="Waste Items")
        self.waste_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create waste treeview
        self.waste_tree = ttk.Treeview(self.waste_list_frame, columns=("Item", "Quantity Wasted", "Date", "Reason", "Notes", "Batch"), show="headings")
        self.waste_tree.heading("Item", text="Item")
        self.waste_tree.heading("Quantity Wasted", text="Quantity Wasted")
        self.waste_tree.heading("Date", text="Date")
        self.waste_tree.heading("Reason", text="Reason")
        self.waste_tree.heading("Notes", text="Notes")
        self.waste_tree.heading("Batch", text="Batch")
        
        # Configure columns
        self.waste_tree.column("Item", width=150)
        self.waste_tree.column("Quantity Wasted", width=100)
        self.waste_tree.column("Date", width=100)
        self.waste_tree.column("Reason", width=100)
        self.waste_tree.column("Notes", width=200)
        self.waste_tree.column("Batch", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.waste_list_frame, orient=tk.VERTICAL, command=self.waste_tree.yview)
        self.waste_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.waste_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create waste details frame
        self.waste_details_frame = ttk.LabelFrame(parent, text="Waste Details")
        self.waste_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create form fields
        ttk.Label(self.waste_details_frame, text="Item:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.waste_item_var = tk.StringVar()
        ttk.Entry(self.waste_details_frame, textvariable=self.waste_item_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.waste_details_frame, text="Quantity Wasted:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.waste_quantity_var = tk.StringVar()
        ttk.Entry(self.waste_details_frame, textvariable=self.waste_quantity_var).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(self.waste_details_frame, text="Date:").grid(row=2, column=0, padx=5, pady=5, sticky=tk.W)
        self.waste_date_var = tk.StringVar()
        ttk.Entry(self.waste_details_frame, textvariable=self.waste_date_var).grid(row=2, column=1, padx=5, pady=5)
        
        ttk.Label(self.waste_details_frame, text="Reason:").grid(row=3, column=0, padx=5, pady=5, sticky=tk.W)
        self.waste_reason_var = tk.StringVar()
        reason_combo = ttk.Combobox(self.waste_details_frame, textvariable=self.waste_reason_var, values=["Expired", "Damaged", "Overstocked"])
        reason_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Label(self.waste_details_frame, text="Notes:").grid(row=4, column=0, padx=5, pady=5, sticky=tk.W)
        self.waste_notes_var = tk.StringVar()
        ttk.Entry(self.waste_details_frame, textvariable=self.waste_notes_var).grid(row=4, column=1, padx=5, pady=5)
        
        # Create buttons
        ttk.Button(self.waste_details_frame, text="Add Waste", command=self.add_waste).grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(self.waste_details_frame, text="Delete Waste", command=self.delete_waste).grid(row=6, column=0, columnspan=2, pady=5)
        
        # Bind selection event
        self.waste_tree.bind("<<TreeviewSelect>>", self.on_waste_select)
        
    def create_batch_waste_interface(self, parent):
        # Create batch list frame
        self.batch_list_frame = ttk.LabelFrame(parent, text="Waste Batches")
        self.batch_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create batch treeview
        self.batch_tree = ttk.Treeview(self.batch_list_frame, columns=("Date", "Total Waste", "Items", "Notes"), show="headings")
        self.batch_tree.heading("Date", text="Date")
        self.batch_tree.heading("Total Waste", text="Total Waste")
        self.batch_tree.heading("Items", text="Items")
        self.batch_tree.heading("Notes", text="Notes")
        
        # Configure columns
        self.batch_tree.column("Date", width=100)
        self.batch_tree.column("Total Waste", width=100)
        self.batch_tree.column("Items", width=200)
        self.batch_tree.column("Notes", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.batch_list_frame, orient=tk.VERTICAL, command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.batch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create batch details frame
        self.batch_details_frame = ttk.LabelFrame(parent, text="Batch Details")
        self.batch_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        # Create form fields
        ttk.Label(self.batch_details_frame, text="Batch Date:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_date_var = tk.StringVar()
        ttk.Entry(self.batch_details_frame, textvariable=self.batch_date_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.batch_details_frame, text="Notes:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_notes_var = tk.StringVar()
        ttk.Entry(self.batch_details_frame, textvariable=self.batch_notes_var).grid(row=1, column=1, padx=5, pady=5)
        
        # Create current batch items frame
        self.current_batch_frame = ttk.LabelFrame(self.batch_details_frame, text="Current Batch Items")
        self.current_batch_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        # Create current batch treeview
        self.current_batch_tree = ttk.Treeview(self.current_batch_frame, columns=("Item", "Quantity", "Reason"), show="headings", height=5)
        self.current_batch_tree.heading("Item", text="Item")
        self.current_batch_tree.heading("Quantity", text="Quantity")
        self.current_batch_tree.heading("Reason", text="Reason")
        
        # Configure columns
        self.current_batch_tree.column("Item", width=150)
        self.current_batch_tree.column("Quantity", width=100)
        self.current_batch_tree.column("Reason", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.current_batch_frame, orient=tk.VERTICAL, command=self.current_batch_tree.yview)
        self.current_batch_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.current_batch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create buttons
        ttk.Button(self.batch_details_frame, text="Add to Batch", command=self.add_to_batch).grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(self.batch_details_frame, text="Save Batch", command=self.save_batch).grid(row=4, column=0, columnspan=2, pady=5)
        ttk.Button(self.batch_details_frame, text="Delete Batch", command=self.delete_batch).grid(row=5, column=0, columnspan=2, pady=5)
        
        # Bind selection event
        self.batch_tree.bind("<<TreeviewSelect>>", self.on_batch_select)
        
    def add_to_batch(self):
        try:
            item = self.waste_item_var.get()
            quantity = int(self.waste_quantity_var.get())
            reason = self.waste_reason_var.get()
            
            if not all([item, quantity, reason]):
                messagebox.showerror("Error", "Item, quantity, and reason are required!")
                return
                
            # Add to current batch
            self.current_batch_items.append(WasteItem(item, quantity, self.batch_date_var.get(), reason, self.waste_notes_var.get()))
            self.current_batch_total += quantity
            
            # Update current batch display
            self.current_batch_tree.insert("", tk.END, values=(item, quantity, reason))
            
            # Clear the form
            self.waste_item_var.set("")
            self.waste_quantity_var.set("")
            self.waste_reason_var.set("")
            self.waste_notes_var.set("")
            
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number!")
            
    def save_batch(self):
        if not self.current_batch_items:
            messagebox.showerror("Error", "No items in the current batch!")
            return
            
        # Validate date
        formatted_date = self.validate_date(self.batch_date_var.get())
        if not formatted_date:
            messagebox.showerror("Error", "Invalid date format! Use MM/DD or MM/DD/YYYY")
            return
            
        # Create batch
        batch = WasteBatch(
            formatted_date,
            self.current_batch_items,
            self.current_batch_total,
            self.batch_notes_var.get()
        )
        
        # Add to waste items with batch ID
        batch_id = len(self.waste_batches)
        for item in self.current_batch_items:
            item.batch_id = batch_id
            self.waste_items.append(item)
            
        # Add to batches
        self.waste_batches.append(batch)
        
        # Update displays
        self.update_batch_list()
        self.update_waste_list()
        self.save_data()
        
        # Clear current batch
        self.current_batch_items = []
        self.current_batch_total = 0
        self.current_batch_tree.delete(*self.current_batch_tree.get_children())
        self.batch_date_var.set("")
        self.batch_notes_var.set("")
        
    def delete_batch(self):
        selected = self.batch_tree.selection()
        if selected:
            index = self.batch_tree.index(selected[0])
            batch = self.waste_batches[index]
            
            # Remove associated waste items
            self.waste_items = [item for item in self.waste_items if item.batch_id != index]
            
            # Remove batch
            del self.waste_batches[index]
            
            # Update batch IDs
            for item in self.waste_items:
                if item.batch_id > index:
                    item.batch_id -= 1
                    
            self.update_batch_list()
            self.update_waste_list()
            self.save_data()
            
    def on_batch_select(self, event):
        selected = self.batch_tree.selection()
        if selected:
            index = self.batch_tree.index(selected[0])
            batch = self.waste_batches[index]
            self.batch_date_var.set(batch.batch_date)
            self.batch_notes_var.set(batch.notes)
            
    def update_batch_list(self):
        # Clear tree
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
            
        # Add batches
        for batch in self.waste_batches:
            items_text = ", ".join([f"{item.item} ({item.quantity_wasted})" for item in batch.items])
            self.batch_tree.insert("", tk.END, values=(
                batch.batch_date,
                batch.total_waste,
                items_text,
                batch.notes
            ))
            
    def add_waste(self):
        try:
            item = self.waste_item_var.get()
            quantity_wasted = int(self.waste_quantity_var.get())
            date = self.waste_date_var.get()
            reason = self.waste_reason_var.get()
            notes = self.waste_notes_var.get()
            
            if not all([item, quantity_wasted, date, reason]):
                messagebox.showerror("Error", "All fields are required!")
                return
                
            # Validate date format
            formatted_date = self.validate_date(date)
            if not formatted_date:
                messagebox.showerror("Error", "Invalid date format! Use MM/DD or MM/DD/YYYY")
                return
                
            # Create waste item
            waste_item = WasteItem(item, quantity_wasted, formatted_date, reason, notes)
            self.waste_items.append(waste_item)
            
            self.update_waste_list()
            self.save_data()
            
        except ValueError:
            messagebox.showerror("Error", "Quantity must be a number!")
            
    def delete_waste(self):
        selected = self.waste_tree.selection()
        if selected:
            index = self.waste_tree.index(selected[0])
            del self.waste_items[index]
            self.update_waste_list()
            self.save_data()
            
    def on_waste_select(self, event):
        selected = self.waste_tree.selection()
        if selected:
            index = self.waste_tree.index(selected[0])
            item = self.waste_items[index]
            self.waste_item_var.set(item.item)
            self.waste_quantity_var.set(str(item.quantity_wasted))
            self.waste_date_var.set(item.date)
            self.waste_reason_var.set(item.reason)
            self.waste_notes_var.set(item.notes)
            
    def update_waste_list(self):
        # Clear tree
        for item in self.waste_tree.get_children():
            self.waste_tree.delete(item)
            
        # Add items
        for item in self.waste_items:
            self.waste_tree.insert("", tk.END, values=(
                item.item,
                item.quantity_wasted,
                item.date,
                item.reason,
                item.notes
            ))
            
    def save_data(self):
        try:
            data = {
                "inventory": [vars(item) for item in self.items],
                "waste": [vars(item) for item in self.waste_items],
                "waste_batches": [{
                    "batch_date": batch.batch_date,
                    "items": [vars(item) for item in batch.items],
                    "total_waste": batch.total_waste,
                    "notes": batch.notes
                } for batch in self.waste_batches]
            }
            with open("inventory_data.json", "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Save Error", f"Error saving data: {str(e)}")
            
    def load_data(self):
        if os.path.exists("inventory_data.json"):
            try:
                with open("inventory_data.json", "r") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        self.items = [InventoryItem(**item) for item in data.get("inventory", [])]
                        self.waste_items = [WasteItem(**item) for item in data.get("waste", [])]
                        self.waste_batches = []
                        for batch_data in data.get("waste_batches", []):
                            items = [WasteItem(**item) for item in batch_data.get("items", [])]
                            batch = WasteBatch(
                                batch_data.get("batch_date", ""),
                                items,
                                batch_data.get("total_waste", 0),
                                batch_data.get("notes", "")
                            )
                            self.waste_batches.append(batch)
                    else:
                        self.items = []
                        self.waste_items = []
                        self.waste_batches = []
            except (json.JSONDecodeError, TypeError) as e:
                messagebox.showerror("Load Error", f"Error loading data: {str(e)}")
                self.items = []
                self.waste_items = []
                self.waste_batches = []
        else:
            self.items = []
            self.waste_items = []
            self.waste_batches = []
            
if __name__ == "__main__":
    root = tk.Tk()
    app = InventoryManager(root)
    root.mainloop()
