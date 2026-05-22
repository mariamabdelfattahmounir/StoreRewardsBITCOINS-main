import tkinter as tk
from tkinter import messagebox, ttk
from transaction_sender import *

root = tk.Tk()
root.title("🎁 Store Rewards System")
root.geometry("750x550")
root.configure(bg="#1e1e2f")

# ================= HEADER =================
tk.Label(root, text="🎁 Store Rewards System",
         font=("Arial", 20, "bold"),
         bg="#1e1e2f", fg="white").pack(pady=10)

# ================= USER INFO =================
info_frame = tk.Frame(root, bg="#2c2c3e", padx=10, pady=10)
info_frame.pack(fill="x", padx=20)

tk.Label(info_frame, text=f"Address:",
         bg="#2c2c3e", fg="gray").pack(anchor="w")

tk.Label(info_frame, text=SENDER,
         bg="#2c2c3e", fg="#00ffcc").pack(anchor="w")

mode = "👑 Admin" if is_admin else "👤 User"
tk.Label(info_frame, text=f"Mode: {mode}",
         bg="#2c2c3e", fg="white").pack(anchor="w")

# ================= NOTEBOOK =================
notebook = ttk.Notebook(root)
notebook.pack(expand=True, fill="both", pady=10)
status_label = tk.Label(root,
                        text="",
                        bg="#1e1e2f",
                        fg="lightgreen",
                        font=("Arial", 12))
status_label.pack(pady=5)

# ================= DASHBOARD =================
dashboard = tk.Frame(notebook, bg="#1e1e2f")
notebook.add(dashboard, text="Dashboard")

balance_label = tk.Label(dashboard,
                         text="RPC Balance: ---",
                         font=("Arial", 16),
                         bg="#1e1e2f", fg="white")
balance_label.pack(pady=20)

def gui_check_balance():
    bal = contract.functions.getCoinBalance(SENDER).call()
    bal = w3.from_wei(bal, "ether")
    balance_label.config(text=f"RPC Balance: {bal}")

tk.Button(dashboard, text="Check Balance",
          command=gui_check_balance,
          bg="#00adb5", width=20).pack()

# ================= USER TAB =================
user_tab = tk.Frame(notebook, bg="#1e1e2f")
notebook.add(user_tab, text="User Actions")


# VIEW ITEMS
def gui_view_items():
    win = tk.Toplevel(root)
    win.title("Reward Items")
    win.geometry("400x300")

    tree = ttk.Treeview(win, columns=("Name", "Cost", "Qty"), show="headings")

    tree.heading("Name", text="Name")
    tree.heading("Cost", text="Cost")
    tree.heading("Qty", text="Quantity")

    tree.pack(fill="both", expand=True)

    total = contract.functions.getTotalRewardItems().call()

    for i in range(1, total + 1):
        item = contract.functions.getRewardItem(i).call()
        tree.insert("", "end", values=(
            item[1],
            w3.from_wei(item[2], "ether"),
            item[3]
        ))
# PURCHASE
def gui_purchase():
    win = tk.Toplevel(root)
    win.title("Purchase Item")

    tree = ttk.Treeview(win, columns=("ID","Name","Cost"), show="headings")

    tree.heading("ID", text="ID")
    tree.heading("Name", text="Name")
    tree.heading("Cost", text="Cost")

    tree.pack(fill="both", expand=True)

    total = contract.functions.getTotalRewardItems().call()

    for i in range(1, total + 1):
        item = contract.functions.getRewardItem(i).call()
        tree.insert("", "end", values=(
            item[0],
            item[1],
            w3.from_wei(item[2], "ether")
        ))

    def buy():
        selected = tree.selection()
        if not selected:
           status_label.config(text="❌ Select item first", fg="red")
           return

        try:
            item_id = tree.item(selected[0])["values"][0]

        
            tx_hash = send_tx(contract.functions.purchaseRewardItem(item_id), "Purchase")
 
        
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        
            if receipt.status == 1:
               status_label.config(text="✔ Purchased successfully", fg="lightgreen")
               gui_check_balance()
            else:
               status_label.config(text="❌ Purchase failed (Insufficient coins?)", fg="red")

        except Exception as e:
           status_label.config(text=f"❌ {str(e)}", fg="red")

    tk.Button(win, text="Buy Selected", command=buy).pack(pady=10)

# TRANSFER
def gui_transfer():
    win = tk.Toplevel(root)
    win.title("Transfer Coins")

    tk.Label(win, text="Select User").pack()

    selected_user = tk.StringVar()
    accounts = w3.eth.accounts
    user_list = []

    for acc in accounts:
        try:
            name = contract.functions.getUserName(acc).call()
            if name != "":
                user_list.append(f"{name} - {acc}")
        except:
            pass

    dropdown = ttk.Combobox(win, textvariable=selected_user, width=50)
    dropdown['values'] = user_list
    dropdown.pack(pady=5)

    tk.Label(win, text="Amount").pack()
    val = tk.Entry(win)
    val.pack()

    def send():
        try:
            selected = selected_user.get()

            if not selected:
                status_label.config(text="❌ Select a user first", fg="red")
                return

            address = selected.split(" - ")[1]
            amount = w3.to_wei(float(val.get()), "ether")

            tx_hash = send_tx(contract.functions.transferCoins(address, amount), "Transfer")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                status_label.config(text="✔ Transferred successfully", fg="lightgreen")
                gui_check_balance()
            else:
                status_label.config(text="❌ Transfer failed", fg="red")

            win.destroy()

        except Exception as e:
            status_label.config(text=f"❌ {str(e)}", fg="red")

    tk.Button(win, text="✅ Send",
              command=send,
              bg="#00adb5").pack(pady=10)

# ACTIVITY
def gui_activity():
    win = tk.Toplevel(root)
    win.title("Activity History")
    win.geometry("500x400")

    text = tk.Text(win)
    text.pack(fill="both", expand=True)

    for b in range(w3.eth.block_number + 1):
        block = w3.eth.get_block(b, full_transactions=True)

        for tx in block.transactions:
            if tx.to and tx.to.lower() == CONTRACT_ADDRESS.lower():
                text.insert("end", f"Block {b} - {tx['from']}\n")

actions_frame = tk.Frame(user_tab, bg="#1e1e2f")
actions_frame.pack(pady=20)

tk.Button(actions_frame, text="📦 View Items",
          command=gui_view_items,
          width=25).grid(row=0, column=0, padx=10, pady=5)

tk.Button(actions_frame, text="🛒 Purchase",
          command=gui_purchase,
          width=25).grid(row=1, column=0, padx=10, pady=5)

tk.Button(actions_frame, text="🔄 Transfer",
          command=gui_transfer,
          width=25).grid(row=2, column=0, padx=10, pady=5)

tk.Button(actions_frame, text="📊 Activity",
          command=gui_activity,
          width=25).grid(row=3, column=0, padx=10, pady=5)

def gui_status():
    try:
        contract_address = contract.address
        your_address = SENDER
        block = w3.eth.block_number

        total_items = contract.functions.getTotalRewardItems().call()

        balance = contract.functions.getCoinBalance(SENDER).call()
        balance = w3.from_wei(balance, "ether")

        
        try:
            admin = contract.functions.owner().call()
        except:
            admin = your_address

        status_label.config(
            text=f"""
CONTRACT STATUS
────────────────────────────
Address     : {contract_address}
Admin       : {admin}
Block       : {block}
Total Items : {total_items}
Your Balance: {balance:.2f} RPC
""",
            fg="lightgreen",
            justify="left"
        )

    except Exception as e:
        status_label.config(text=f"❌ {str(e)}", fg="red")
tk.Button(actions_frame, text="📡 Contract Status",
  command=gui_status,
  width=25).grid(row=4, column=0, padx=10, pady=5)

# ================= ADMIN TAB =================
if is_admin:
    admin_tab = tk.Frame(notebook, bg="#1e1e2f")
    notebook.add(admin_tab, text="Admin Panel")

    # ===== USERS DROPDOWN =====
    tk.Label(admin_tab, text="Select User",
             bg="#1e1e2f", fg="white").pack()

    accounts = w3.eth.accounts
    user_list = []

    for acc in accounts:
        try:
            name = contract.functions.getUserName(acc).call()
            if name != "":
                user_list.append(f"{name} - {acc}")
        except:
            pass

    selected_user = tk.StringVar()

    dropdown = ttk.Combobox(admin_tab,
                            textvariable=selected_user,
                            width=50)
    dropdown['values'] = user_list
    dropdown.pack(pady=5)

    # ===== AMOUNT =====
    tk.Label(admin_tab, text="Amount",
             bg="#1e1e2f", fg="white").pack()

    amount_entry = tk.Entry(admin_tab, width=40)
    amount_entry.pack(pady=5)

    # ===== FUNCTIONS =====
    def gui_mint():
        try:
            selected = selected_user.get()
            if not selected:
                status_label.config(text="❌ Select a user first", fg="red")
                return

            address = selected.split(" - ")[1]
            to = Web3.to_checksum_address(address)
            amt = w3.to_wei(float(amount_entry.get()), "ether")

            send_tx(contract.functions.mintCoins(to, amt), "Mint")
            status_label.config(text="✔ Minted successfully")

        except Exception as e:
            status_label.config(text=f"❌ {str(e)}", fg="red")

    def gui_add_item():
        win = tk.Toplevel(root)
        win.title("Add Item")

        tk.Label(win, text="Name").pack()
        name = tk.Entry(win)
        name.pack()

        tk.Label(win, text="Cost").pack()
        cost = tk.Entry(win)
        cost.pack()

        tk.Label(win, text="Quantity").pack()
        qty = tk.Entry(win)
        qty.pack()

        def add():
            try:
                send_tx(
                    contract.functions.addRewardItem(
                        name.get(),
                        w3.to_wei(float(cost.get()), "ether"),
                        int(qty.get())
                    ),
                    "Add Item"
                )
                status_label.config(text="✔ Item added")
                win.destroy()
            except Exception as e:
                status_label.config(text=f"❌ {str(e)}", fg="red")

        tk.Button(win, text="Add", command=add).pack()


    def gui_transfer_owner():
        win = tk.Toplevel(root)
        win.title("Transfer Ownership")

        tk.Label(win, text="Select New Owner").pack()

        selected_user = tk.StringVar()

        accounts = w3.eth.accounts
        user_list = []

        for acc in accounts:
            try:
                name = contract.functions.getUserName(acc).call()
                if name != "":
                    user_list.append(f"{name} - {acc}")
            except:
              pass

        dropdown = ttk.Combobox(win, textvariable=selected_user, width=50)
        dropdown['values'] = user_list
        dropdown.pack(pady=5)

        def transfer():
           try:
               selected = selected_user.get()

               if not selected:
                  status_label.config(text="❌ Select a user first", fg="red")
                  return

               address = selected.split(" - ")[1]

               tx_hash = send_tx(contract.functions.transferOwnership(address), "Transfer Ownership")
               receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

               if receipt.status == 1:
                 status_label.config(text="✔ Ownership transferred", fg="lightgreen")
               else:
                 status_label.config(text="❌ Transfer failed", fg="red")
    
                 win.destroy()

           except Exception as e:
                status_label.config(text=f"❌ {str(e)}", fg="red")
        tk.Button(win, text="✅ Confirm Transfer",
          command=transfer,
          bg="#ff9800").pack(pady=10)
    def gui_pause():
        try:
            tx_hash = send_tx(contract.functions.pause(), "Pause")
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

            if receipt.status == 1:
                status_label.config(text="⏸ Contract Paused", fg="orange")
            else:
                status_label.config(text="❌ Pause failed", fg="red")

        except Exception as e:
            status_label.config(text=f"❌ {str(e)}", fg="red")
 

    def gui_resume():
        try:
           tx_hash = send_tx(contract.functions.resume(), "Resume")
           receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

           if receipt.status == 1:
              status_label.config(text="▶ Contract Resumed", fg="lightgreen")
           else:
              status_label.config(text="❌ Resume failed", fg="red")

        except Exception as e:
            status_label.config(text=f"❌ {str(e)}", fg="red")
    # ===== BUTTONS =====
    tk.Button(admin_tab, text="💰 Mint Coins",
              command=gui_mint, width=25).pack(pady=5)

    tk.Button(admin_tab, text="➕ Add Item",
              command=gui_add_item, width=25).pack(pady=5)


    tk.Button(admin_tab, text="🔁 Transfer Ownership",
              command=gui_transfer_owner, width=25).pack(pady=5)
    tk.Button(admin_tab, text="⏸ Pause Contract",
          command=gui_pause,
          width=25).pack(pady=5)

    tk.Button(admin_tab, text="▶ Resume Contract",
          command=gui_resume,
          width=25).pack(pady=5)

root.mainloop()