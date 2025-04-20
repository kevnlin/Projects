import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import csv
import os
import hashlib
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv, set_key
import logging
from typing import List, Dict, Optional

# Set up logging
logging.basicConfig(
    filename='inventory_system.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class SecureStorage:
    def __init__(self):
        self.key_file = '.encryption_key'
        self.encryption_key = self._get_or_create_key()
        self.cipher_suite = Fernet(self.encryption_key)
        
    def _get_or_create_key(self) -> bytes:
        if os.path.exists(self.key_file):
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            os.chmod(self.key_file, 0o600) 
            return key
            
    def encrypt_data(self, data: str) -> str:
        return self.cipher_suite.encrypt(data.encode()).decode()
        
    def decrypt_data(self, encrypted_data: str) -> str:
        return self.cipher_suite.decrypt(encrypted_data.encode()).decode()
        
    def save_secure_csv(self, filename: str, data: List[Dict], fieldnames: List[str]):
        try:
            temp_file = f"{filename}.tmp"
            with open(temp_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for row in data:
                    encrypted_row = {k: self.encrypt_data(str(v)) for k, v in row.items()}
                    writer.writerow(encrypted_row)
                    
            # Atomic file replacement
            if os.path.exists(filename):
                os.remove(filename)
            os.rename(temp_file, filename)
            os.chmod(filename, 0o600)  
            
            logging.info(f"Successfully saved secure data to {filename}")
        except Exception as e:
            logging.error(f"Error saving secure data: {str(e)}")
            raise
            
    def load_secure_csv(self, filename: str, fieldnames: List[str]) -> List[Dict]:
        if not os.path.exists(filename):
            return []
            
        try:
            with open(filename, 'r', newline='') as f:
                reader = csv.DictReader(f)
                decrypted_data = []
                for row in reader:
                    decrypted_row = {k: self.decrypt_data(v) for k, v in row.items()}
                    decrypted_data.append(decrypted_row)
                return decrypted_data
        except Exception as e:
            logging.error(f"Error loading secure data: {str(e)}")
            return []

class SecureLogin:
    def __init__(self):
        self.reload_pin_hash()
        self.max_attempts = 3
        self.attempts = 0
        self.lockout_time = 300
        self.last_failed_attempt = 0
        
    def reload_pin_hash(self):
        load_dotenv()
        self.stored_pin_hash = os.getenv("PIN_HASH", "")
        
    def verify_pin(self, pin: str) -> bool:
        current_time = datetime.now().timestamp()
        
        if self.attempts >= self.max_attempts:
            if current_time - self.last_failed_attempt < self.lockout_time:
                remaining_time = int(self.lockout_time - (current_time - self.last_failed_attempt))
                messagebox.showerror("Account Locked", 
                    f"Too many failed attempts. Please try again in {remaining_time} seconds.")
                return False
            else:
                self.attempts = 0
                
        if not self.stored_pin_hash:
            return True
            
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        if pin_hash == self.stored_pin_hash:
            self.attempts = 0
            logging.info("Successful login")
            return True
        else:
            self.attempts += 1
            self.last_failed_attempt = current_time
            logging.warning(f"Failed login attempt {self.attempts}")
            if self.attempts >= self.max_attempts:
                messagebox.showerror("Account Locked", 
                    f"Too many failed attempts. Account locked for {self.lockout_time//60} minutes.")
            else:
                messagebox.showerror("Error", f"Invalid PIN! {self.max_attempts - self.attempts} attempts remaining.")
            return False
            
    def set_new_pin(self, pin: str) -> bool:
        if len(pin) < 4:
            messagebox.showerror("Error", "PIN must be at least 4 characters long!")
            return False
            
        pin_hash = hashlib.sha256(pin.encode()).hexdigest()
        set_key(".env", "PIN_HASH", pin_hash)
        self.reload_pin_hash()
        logging.info("PIN successfully updated")
        return True

class InventoryItem:
    def __init__(self, name: str, quantity: int, expiration_date: str, category: str):
        self.name = name
        self.quantity = quantity
        self.expiration_date = expiration_date
        self.category = category

    @classmethod
    def from_csv_row(cls, row: Dict) -> 'InventoryItem':
        return cls(row['name'], int(row['quantity']), row['expiration_date'], row['category'])

    def to_csv_row(self) -> Dict:
        return {
            'name': self.name,
            'quantity': str(self.quantity),
            'expiration_date': self.expiration_date,
            'category': self.category
        }

class WasteBatch:
    def __init__(self, batch_date, items, total_waste, notes):
        self.batch_date = batch_date
        self.items = items
        self.total_waste = total_waste
        self.notes = notes

    @classmethod
    def from_csv_row(cls, row, items):
        return cls(row['batch_date'], items, int(row['total_waste']), row['notes'])

    def to_csv_row(self):
        return {
            'batch_date': self.batch_date,
            'total_waste': str(self.total_waste),
            'notes': self.notes
        }

class WasteItem:
    def __init__(self, item, quantity_wasted, date, reason, notes, batch_id=None):
        self.item = item
        self.quantity_wasted = quantity_wasted
        self.date = date
        self.reason = reason
        self.notes = notes
        self.batch_id = batch_id

    @classmethod
    def from_csv_row(cls, row):
        batch_id = int(row['batch_id']) if row['batch_id'] else None
        return cls(
            row['item'],
            int(row['quantity_wasted']),
            row['date'],
            row['reason'],
            row['notes'],
            batch_id
        )

    def to_csv_row(self):
        return {
            'item': self.item,
            'quantity_wasted': str(self.quantity_wasted),
            'date': self.date,
            'reason': self.reason,
            'notes': self.notes,
            'batch_id': str(self.batch_id) if self.batch_id is not None else ''
        }

class InventoryManager:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Restaurant Inventory Management")
        self.root.geometry("1000x600")
        
        self.storage = SecureStorage()
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
        self.tree.bind("<Button-3>", self.unselect_item)  
        self.tree.bind("<Escape>", self.unselect_item)  
        
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
                messagebox.showerror("All fields are required")
                return
                
            formatted_date = self.validate_date(expiration)
            if not formatted_date:
                messagebox.showerror("Invalid date format, Use MM/DD or MM/DD/YYYY")
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
            messagebox.showerror("Quantity must be a number")
            
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
        self.waste_tree.bind("<Button-3>", self.unselect_waste)  
        self.waste_tree.bind("<Escape>", self.unselect_waste)    
        
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
                messagebox.showerror("Item, quantity, and reason are required!")
                return
                
            self.current_batch_items.append(WasteItem(item, quantity, self.batch_date_var.get(), reason, self.waste_notes_var.get()))
            self.current_batch_total += quantity
            
            self.current_batch_tree.insert("", tk.END, values=(item, quantity, reason))
            
            self.waste_item_var.set("")
            self.waste_quantity_var.set("")
            self.waste_reason_var.set("")
            self.waste_notes_var.set("")
            
        except ValueError:
            messagebox.showerror("Quantity must be a number")
            
    def save_batch(self):
        if not self.current_batch_items:
            messagebox.showerror("No items in the current batch")
            return
            
        formatted_date = self.validate_date(self.batch_date_var.get())
        if not formatted_date:
            messagebox.showerror("Invalid date format, Use MM/DD or MM/DD/YYYY")
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
        if not selected:
            messagebox.showwarning("Warning", "Please select a batch to delete")
            return
            
        try:
            index = self.batch_tree.index(selected[0])
            if index < 0 or index >= len(self.waste_batches):
                raise IndexError("Invalid batch index")
                
            self.waste_items = [item for item in self.waste_items if item.batch_id != index]
           
            del self.waste_batches[index]
            
            for item in self.waste_items:
                if item.batch_id > index:
                    item.batch_id -= 1
            
            
            if self.current_batch_items and self.batch_date_var.get() == self.waste_batches[index].batch_date:
                self.current_batch_items = []
                self.current_batch_total = 0
                self.current_batch_tree.delete(*self.current_batch_tree.get_children())
                self.batch_date_var.set("")
                self.batch_notes_var.set("")
            
            
            self.update_batch_list()
            self.update_waste_list()
            self.save_data()
            
            logging.info(f"Successfully deleted batch {index}")
            messagebox.showinfo("Success", "Batch deleted successfully")
            
        except Exception as e:
            logging.error(f"Error deleting batch: {str(e)}")
            messagebox.showerror("Error", f"Failed to delete batch: {str(e)}")
        
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
                messagebox.showerror("All fields are required")
                return
                
            formatted_date = self.validate_date(date)
            if not formatted_date:
                messagebox.showerror("Invalid date format, Use MM/DD or MM/DD/YYYY")
                return
                
            waste_item = WasteItem(item, quantity_wasted, formatted_date, reason, notes)
            self.waste_items.append(waste_item)
            
            self.update_waste_list()
            self.save_data()
            
        except ValueError:
            messagebox.showerror("Quantity must be a number")
            
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
            self.storage.save_secure_csv(
                'inventory.csv',
                [item.to_csv_row() for item in self.items],
                ['name', 'quantity', 'expiration_date', 'category']
            )

            self.storage.save_secure_csv(
                'waste.csv',
                [item.to_csv_row() for item in self.waste_items],
                ['item', 'quantity_wasted', 'date', 'reason', 'notes', 'batch_id']
            )

            self.storage.save_secure_csv(
                'waste_batches.csv',
                [batch.to_csv_row() for batch in self.waste_batches],
                ['batch_date', 'total_waste', 'notes']
            )

            logging.info("Data saved successfully")
        except Exception as e:
            logging.error(f"Error saving data: {str(e)}")
            messagebox.showerror("Save Error", f"Error saving data: {str(e)}")
            
    def load_data(self):
        try:
           
            inventory_data = self.storage.load_secure_csv('inventory.csv', 
                ['name', 'quantity', 'expiration_date', 'category'])
            self.items = [InventoryItem.from_csv_row(row) for row in inventory_data]

            
            waste_data = self.storage.load_secure_csv('waste.csv',
                ['item', 'quantity_wasted', 'date', 'reason', 'notes', 'batch_id'])
            self.waste_items = [WasteItem.from_csv_row(row) for row in waste_data]

            
            batch_data = self.storage.load_secure_csv('waste_batches.csv',
                ['batch_date', 'total_waste', 'notes'])
            for row in batch_data:
                batch_id = int(row['batch_date'].split('_')[1]) if '_' in row['batch_date'] else None
                batch_items = [item for item in self.waste_items if item.batch_id == batch_id]
                batch = WasteBatch.from_csv_row(row, batch_items)
                self.waste_batches.append(batch)

            logging.info("Data loaded successfully")
        except Exception as e:
            logging.error(f"Error loading data: {str(e)}")
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

class LoginWindow:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Secure Login")
        self.root.geometry("300x200")
        self.root.resizable(False, False)
        
        self.secure_login = SecureLogin()
        
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Enter PIN:").pack(pady=10)
        
        self.pin_var = tk.StringVar()
        self.pin_entry = ttk.Entry(main_frame, textvariable=self.pin_var, show="*")
        self.pin_entry.pack(pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="Login", command=self.verify_login).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Reset PIN", command=self.show_reset_dialog).pack(side=tk.LEFT, padx=5)
        
        self.pin_entry.bind("<Return>", lambda e: self.verify_login())
        
    def verify_login(self):
        pin = self.pin_var.get()
        if self.secure_login.verify_pin(pin):
            self.root.destroy()
            main_root = tk.Tk()
            app = InventoryManager(main_root)
            main_root.mainloop()
            
    def show_reset_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Reset PIN")
        dialog.geometry("300x250")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        
        if not os.getenv("PIN_HASH"):
            ttk.Label(frame, text="Set Initial PIN:").pack(pady=5)
            new_pin_var = tk.StringVar()
            new_pin_entry = ttk.Entry(frame, textvariable=new_pin_var, show="*")
            new_pin_entry.pack(pady=5)
            
            ttk.Label(frame, text="Confirm PIN:").pack(pady=5)
            confirm_pin_var = tk.StringVar()
            confirm_pin_entry = ttk.Entry(frame, textvariable=confirm_pin_var, show="*")
            confirm_pin_entry.pack(pady=5)
            
            def set_initial_pin():
                new_pin = new_pin_var.get()
                confirm_pin = confirm_pin_var.get()
                
                if not new_pin or not confirm_pin:
                    messagebox.showerror("Error", "Please enter and confirm your PIN")
                    return
                    
                if new_pin != confirm_pin:
                    messagebox.showerror("Error", "PINs do not match")
                    return
                    
                if self.secure_login.set_new_pin(new_pin):
                    messagebox.showinfo("Success", "PIN has been set successfully!")
                    dialog.destroy()
                    
            ttk.Button(frame, text="Set PIN", command=set_initial_pin).pack(pady=10)
            
        else:
            ttk.Label(frame, text="Enter Current PIN:").pack(pady=5)
            current_pin_var = tk.StringVar()
            current_pin_entry = ttk.Entry(frame, textvariable=current_pin_var, show="*")
            current_pin_entry.pack(pady=5)
            
            ttk.Label(frame, text="Enter New PIN:").pack(pady=5)
            new_pin_var = tk.StringVar()
            new_pin_entry = ttk.Entry(frame, textvariable=new_pin_var, show="*")
            new_pin_entry.pack(pady=5)
            
            ttk.Label(frame, text="Confirm New PIN:").pack(pady=5)
            confirm_pin_var = tk.StringVar()
            confirm_pin_entry = ttk.Entry(frame, textvariable=confirm_pin_var, show="*")
            confirm_pin_entry.pack(pady=5)
            
            def reset_pin():
                current_pin = current_pin_var.get()
                new_pin = new_pin_var.get()
                confirm_pin = confirm_pin_var.get()
                
                if not all([current_pin, new_pin, confirm_pin]):
                    messagebox.showerror("Error", "Please fill in all fields")
                    return
                    
                if not self.secure_login.verify_pin(current_pin):
                    messagebox.showerror("Error", "Current PIN is incorrect")
                    return
                    
                if new_pin != confirm_pin:
                    messagebox.showerror("Error", "New PINs do not match")
                    return
                    
                if self.secure_login.set_new_pin(new_pin):
                    messagebox.showinfo("Success", "PIN has been reset successfully!")
                    dialog.destroy()
                    
            ttk.Button(frame, text="Reset PIN", command=reset_pin).pack(pady=10)
            
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f'{width}x{height}+{x}+{y}')

if __name__ == "__main__":
    root = tk.Tk()
    login_window = LoginWindow(root)
    root.mainloop()
