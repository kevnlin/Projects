import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json
import os
import hashlib

class InventoryItem:
    def __init__(self, name, quantity, expiration_date, category):
        self.name = name
        self.quantity = quantity
        self.expiration_date = expiration_date
        self.category = category

class WasteBatch:
    def __init__(self, batch_date, items, total_waste, notes):
        self.batch_date = batch_date
        self.items = items
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
        
        self.items = []
        self.waste_items = []
        self.waste_batches = []
        self.current_batch_items = []
        self.current_batch_total = 0
        
        self.load_data()
        
        self.main_frame = ttk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        self.inventory_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.inventory_frame, text="Inventory")
        
        self.waste_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.waste_frame, text="Waste Tracker")
        
        self.create_item_list()
        self.create_item_details()
        self.create_waste_tracker()
        self.setup_drag_drop()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        self.update_item_list()
        self.update_waste_list()
        self.update_batch_list()
        
    def validate_date(self, date_str):
        try:
            if len(date_str.split('/')) == 3:
                return datetime.strptime(date_str, "%m/%d/%Y").strftime("%m/%d/%Y")
            elif len(date_str.split('/')) == 2:
                return datetime.strptime(date_str, "%m/%d").strftime("%m/%d")
            else:
                return None
        except ValueError:
            return None
            
    def on_closing(self):
        self.save_data()
        self.root.destroy()
        
    def create_item_list(self):
        self.list_frame = ttk.LabelFrame(self.inventory_frame, text="Inventory Items")
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.tree = ttk.Treeview(self.list_frame, columns=("Name", "Quantity", "Expiration", "Category"), show="headings")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Quantity", text="Quantity")
        self.tree.heading("Expiration", text="Expiration Date")
        self.tree.heading("Category", text="Category")
        
        self.tree.column("Name", width=150)
        self.tree.column("Quantity", width=100)
        self.tree.column("Expiration", width=150)
        self.tree.column("Category", width=100)
        
        scrollbar = ttk.Scrollbar(self.list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.tree.bind("<<TreeviewSelect>>", self.on_item_select)
        self.tree.bind("<Button-3>", self.unselect_item)  # Right-click to unselect
        self.tree.bind("<Escape>", self.unselect_item)   # Escape key to unselect
        
    def create_item_details(self):
        self.details_frame = ttk.LabelFrame(self.inventory_frame, text="Item Details")
        self.details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
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
        
        button_frame = ttk.Frame(self.details_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Save", command=self.save_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Delete", command=self.delete_item).pack(side=tk.LEFT, padx=5)
        
        sort_frame = ttk.Frame(self.details_frame)
        sort_frame.grid(row=5, column=0, columnspan=2, pady=5)
        
        ttk.Button(sort_frame, text="Sort by Name", command=lambda: self.sort_items("Name")).pack(side=tk.LEFT, padx=5)
        ttk.Button(sort_frame, text="Sort by Expiration", command=lambda: self.sort_items("Expiration")).pack(side=tk.LEFT, padx=5)
        
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
            
    def save_item(self):
        try:
            name = self.name_var.get()
            quantity = int(self.quantity_var.get())
            expiration = self.expiration_var.get()
            category = self.category_var.get()
            
            if not all([name, quantity, expiration, category]):
                messagebox.showerror("Error", "All fields are required!")
                return
                
            formatted_date = self.validate_date(expiration)
            if not formatted_date:
                messagebox.showerror("Error", "Invalid date format! Use MM/DD or MM/DD/YYYY")
                return
                
            item = InventoryItem(name, quantity, formatted_date, category)
            
            selected = self.tree.selection()
            if selected:
                index = self.tree.index(selected[0])
                self.items[index] = item
            else:
                self.items.append(item)
                
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
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        for item in self.items:
            expiration_date = datetime.strptime(item.expiration_date, "%m/%d/%Y") if len(item.expiration_date.split('/')) == 3 else datetime.strptime(item.expiration_date, "%m/%d")
            days_until_expiration = (expiration_date - datetime.now()).days
            
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
        
        self.tree.tag_configure('expired', background='red')
        self.tree.tag_configure('expiring_soon', background='yellow')
        
    def sort_items(self, column):
        if column == "Name":
            self.items.sort(key=lambda x: x.name)
        elif column == "Expiration":
            self.items.sort(key=lambda x: datetime.strptime(x.expiration_date, "%m/%d/%Y") if len(x.expiration_date.split('/')) == 3 else datetime.strptime(x.expiration_date, "%m/%d"))
        self.update_item_list()
        
    def create_waste_tracker(self):
        
        waste_notebook = ttk.Notebook(self.waste_frame)
        waste_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
       
        individual_frame = ttk.Frame(waste_notebook)
        waste_notebook.add(individual_frame, text="Individual Entries")
        
        batch_frame = ttk.Frame(waste_notebook)
        waste_notebook.add(batch_frame, text="Batch Entries")
        
        self.create_individual_waste_interface(individual_frame)
        
        self.create_batch_waste_interface(batch_frame)
        
    def create_individual_waste_interface(self, parent):
        self.waste_list_frame = ttk.LabelFrame(parent, text="Waste Items")
        self.waste_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.waste_tree = ttk.Treeview(self.waste_list_frame, columns=("Item", "Quantity Wasted", "Date", "Reason", "Notes", "Batch"), show="headings")
        self.waste_tree.heading("Item", text="Item")
        self.waste_tree.heading("Quantity Wasted", text="Quantity Wasted")
        self.waste_tree.heading("Date", text="Date")
        self.waste_tree.heading("Reason", text="Reason")
        self.waste_tree.heading("Notes", text="Notes")
        self.waste_tree.heading("Batch", text="Batch")
        
        self.waste_tree.column("Item", width=150)
        self.waste_tree.column("Quantity Wasted", width=100)
        self.waste_tree.column("Date", width=100)
        self.waste_tree.column("Reason", width=100)
        self.waste_tree.column("Notes", width=200)
        self.waste_tree.column("Batch", width=100)
        
        scrollbar = ttk.Scrollbar(self.waste_list_frame, orient=tk.VERTICAL, command=self.waste_tree.yview)
        self.waste_tree.configure(yscrollcommand=scrollbar.set)
        
        self.waste_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.waste_tree.bind("<<TreeviewSelect>>", self.on_waste_select)
        self.waste_tree.bind("<Button-3>", self.unselect_waste)  # Right-click to unselect
        self.waste_tree.bind("<Escape>", self.unselect_waste)    # Escape key to unselect
        
        self.waste_details_frame = ttk.LabelFrame(parent, text="Waste Details")
        self.waste_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
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
        
        ttk.Button(self.waste_details_frame, text="Add Waste", command=self.add_waste).grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(self.waste_details_frame, text="Delete Waste", command=self.delete_waste).grid(row=6, column=0, columnspan=2, pady=5)
        
    def create_batch_waste_interface(self, parent):
        self.batch_list_frame = ttk.LabelFrame(parent, text="Waste Batches")
        self.batch_list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.batch_tree = ttk.Treeview(self.batch_list_frame, columns=("Date", "Total Waste", "Items", "Notes"), show="headings")
        self.batch_tree.heading("Date", text="Date")
        self.batch_tree.heading("Total Waste", text="Total Waste")
        self.batch_tree.heading("Items", text="Items")
        self.batch_tree.heading("Notes", text="Notes")
        
        self.batch_tree.column("Date", width=100)
        self.batch_tree.column("Total Waste", width=100)
        self.batch_tree.column("Items", width=200)
        self.batch_tree.column("Notes", width=200)
        
        scrollbar = ttk.Scrollbar(self.batch_list_frame, orient=tk.VERTICAL, command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=scrollbar.set)
        
        self.batch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.batch_tree.bind("<<TreeviewSelect>>", self.on_batch_select)
        self.batch_tree.bind("<Button-3>", self.unselect_batch)
        self.batch_tree.bind("<Escape>", self.unselect_batch)
        
        self.batch_details_frame = ttk.LabelFrame(parent, text="Batch Details")
        self.batch_details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        ttk.Label(self.batch_details_frame, text="Batch Date:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_date_var = tk.StringVar()
        ttk.Entry(self.batch_details_frame, textvariable=self.batch_date_var).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(self.batch_details_frame, text="Notes:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.batch_notes_var = tk.StringVar()
        ttk.Entry(self.batch_details_frame, textvariable=self.batch_notes_var).grid(row=1, column=1, padx=5, pady=5)
        
        self.current_batch_frame = ttk.LabelFrame(self.batch_details_frame, text="Current Batch Items")
        self.current_batch_frame.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky=tk.W+tk.E)
        
        self.current_batch_tree = ttk.Treeview(self.current_batch_frame, columns=("Item", "Quantity", "Reason"), show="headings", height=5)
        self.current_batch_tree.heading("Item", text="Item")
        self.current_batch_tree.heading("Quantity", text="Quantity")
        self.current_batch_tree.heading("Reason", text="Reason")
        
        self.current_batch_tree.column("Item", width=150)
        self.current_batch_tree.column("Quantity", width=100)
        self.current_batch_tree.column("Reason", width=100)
        
        scrollbar = ttk.Scrollbar(self.current_batch_frame, orient=tk.VERTICAL, command=self.current_batch_tree.yview)
        self.current_batch_tree.configure(yscrollcommand=scrollbar.set)
        
        self.current_batch_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        ttk.Button(self.batch_details_frame, text="Add to Batch", command=self.add_to_batch).grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(self.batch_details_frame, text="Save Batch", command=self.save_batch).grid(row=4, column=0, columnspan=2, pady=5)
        ttk.Button(self.batch_details_frame, text="Delete Batch", command=self.delete_batch).grid(row=5, column=0, columnspan=2, pady=5)
        
    def add_to_batch(self):
        try:
            item = self.waste_item_var.get()
            quantity = int(self.waste_quantity_var.get())
            reason = self.waste_reason_var.get()
            
            if not all([item, quantity, reason]):
                messagebox.showerror("Error", "Item, quantity, and reason are required!")
                return
                
            self.current_batch_items.append(WasteItem(item, quantity, self.batch_date_var.get(), reason, self.waste_notes_var.get()))
            self.current_batch_total += quantity
            
            self.current_batch_tree.insert("", tk.END, values=(item, quantity, reason))
            
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
            
        formatted_date = self.validate_date(self.batch_date_var.get())
        if not formatted_date:
            messagebox.showerror("Error", "Invalid date format! Use MM/DD or MM/DD/YYYY")
            return
            
        batch = WasteBatch(
            formatted_date,
            self.current_batch_items,
            self.current_batch_total,
            self.batch_notes_var.get()
        )
        
        batch_id = len(self.waste_batches)
        for item in self.current_batch_items:
            item.batch_id = batch_id
            self.waste_items.append(item)
            
        self.waste_batches.append(batch)
        self.update_batch_list()
        self.update_waste_list()
        self.save_data()
        
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
            
            # Remove all waste items associated with this batch
            self.waste_items = [item for item in self.waste_items if item.batch_id != index]
            
            # Remove the batch
            del self.waste_batches[index]
            
            # Update batch IDs for remaining items
            for item in self.waste_items:
                if item.batch_id > index:
                    item.batch_id -= 1
            
            # Clear the current batch if it's the one being deleted
            if self.current_batch_items and self.batch_date_var.get() == batch.batch_date:
                self.current_batch_items = []
                self.current_batch_total = 0
                self.current_batch_tree.delete(*self.current_batch_tree.get_children())
                self.batch_date_var.set("")
                self.batch_notes_var.set("")
            
            self.update_batch_list()
            self.update_waste_list()
            self.save_data()
            messagebox.showinfo("Success", "Batch deleted successfully!")
        
    def on_batch_select(self, event):
        selected = self.batch_tree.selection()
        if selected:
            index = self.batch_tree.index(selected[0])
            batch = self.waste_batches[index]
            self.batch_date_var.set(batch.batch_date)
            self.batch_notes_var.set(batch.notes)
            
    def update_batch_list(self):
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)
            
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
        for item in self.waste_tree.get_children():
            self.waste_tree.delete(item)
            
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
            
    def unselect_item(self, event=None):
        self.tree.selection_remove(self.tree.selection())
        self.name_var.set("")
        self.quantity_var.set("")
        self.expiration_var.set("")
        self.category_var.set("")
        
    def unselect_waste(self, event=None):
        self.waste_tree.selection_remove(self.waste_tree.selection())
        self.waste_item_var.set("")
        self.waste_quantity_var.set("")
        self.waste_date_var.set("")
        self.waste_reason_var.set("")
        self.waste_notes_var.set("")
        
    def unselect_batch(self, event=None):
        self.batch_tree.selection_remove(self.batch_tree.selection())
        self.batch_date_var.set("")
        self.batch_notes_var.set("")

class SecurityManager:
    def __init__(self):
        self.pin_file = "security_data.json"
        self.load_pin()
        
    def load_pin(self):
        if os.path.exists(self.pin_file):
            try:
                with open(self.pin_file, "r") as f:
                    data = json.load(f)
                    self.stored_pin_hash = data.get("pin_hash", "")
            except:
                self.stored_pin_hash = ""
        else:
            self.stored_pin_hash = ""
            
    def save_pin(self, pin):
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        with open(self.pin_file, "w") as f:
            json.dump({"pin_hash": pin_hash}, f)
        self.stored_pin_hash = pin_hash
        
    def verify_pin(self, pin):
        if not self.stored_pin_hash:
            return True
        return hashlib.sha256(pin.encode()).hexdigest() == self.stored_pin_hash

class LoginWindow:
    def __init__(self, root, security_manager):
        self.root = root
        self.security_manager = security_manager
        self.root.title("Login")
        self.root.geometry("300x200")
        self.root.resizable(False, False)
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Enter PIN:").pack(pady=10)
        
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(main_frame, textvariable=self.pin_var, show="*")
        self.pin_entry.pack(pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Login", command=self.verify_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Set New PIN", command=self.set_new_pin).pack(side=tk.LEFT, padx=5)
        
        self.pin_entry.bind("<Return>", lambda e: self.verify_login())
        
    def verify_login(self):
        pin = self.pin_var.get()
        if self.security_manager.verify_pin(pin):
            self.root.destroy()
            main_root = tk.Tk()
            app = InventoryManager(main_root)
            main_root.mainloop()
        else:
            messagebox.showerror("Error", "Invalid PIN!")
            
    def set_new_pin(self):
        pin = self.pin_var.get()
        if pin:
            self.security_manager.save_pin(pin)
            messagebox.showinfo("Success", "PIN has been set successfully!")
        else:
            messagebox.showerror("Error", "Please enter a PIN!")

if __name__ == "__main__":
    root = tk.Tk()
    security_manager = SecurityManager()
    login_window = LoginWindow(root, security_manager)
    root.mainloop()
