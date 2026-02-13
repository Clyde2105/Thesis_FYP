import tkinter as tk
from tkinter import ttk, messagebox
import json
import os

# CONFIG
GRID_SIZE = 20
DATA_FILE = "brain.json"

class RobotPaintApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Robot Paint: Final Version")
        self.root.geometry("1100x750")

        self.mode = "engineer" 
        self.valid_size = True 
        self.current_w = 100
        self.current_h = 100
        self.all_strokes = [] 
        self.current_stroke = [] 
        
        # LOAD DATASET
        self.training_data = {}
        self.load_dataset()

        # --- UI LAYOUT ---
        self.top_bar = tk.Frame(root, bg="#333", height=50)
        self.top_bar.pack(fill="x", side="top")
        
        self.lbl_mode = tk.Label(self.top_bar, text="CURRENT MODE: ENGINEER", fg="white", bg="#333", font=("Arial", 14, "bold"))
        self.lbl_mode.pack(side="left", padx=20)

        # BUTTON START STATE
        self.btn_switch = tk.Button(self.top_bar, text="🔄 Switch to Artist Mode", bg="#ffcc00", command=self.toggle_mode)
        self.btn_switch.pack(side="right", padx=20, pady=10)

        self.main_split = tk.PanedWindow(root, orient="horizontal", sashwidth=5)
        self.main_split.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(self.main_split, bg="white")
        self.main_split.add(self.canvas, width=750)

        self.right_panel = tk.Frame(self.main_split, bg="#f0f0f0")
        self.main_split.add(self.right_panel, width=350)

        self.frame_engineer = tk.Frame(self.right_panel, bg="#f0f0f0")
        self.create_engineer_ui()

        self.frame_artist = tk.Frame(self.right_panel, bg="#f0f0f0")
        self.create_artist_ui()

        self.btn_clear = tk.Button(self.right_panel, text="🗑️ Clear Canvas", command=self.clear_canvas, bg="#ffcccc", height=3)
        self.btn_clear.pack(side="bottom", fill="x", padx=10, pady=20)

        self.frame_engineer.pack(fill="both", expand=True)
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def load_dataset(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f:
                    self.training_data = json.load(f)
                print(f"Brain loaded: {len(self.training_data)} categories.")
            except:
                self.training_data = {}
        else:
            messagebox.showerror("Error", "brain.json not found! Run the Trainer first.")

    def create_engineer_ui(self):
        lbl = tk.Label(self.frame_engineer, text="Engineer Mode", font=("Arial", 12, "bold"))
        lbl.pack(pady=10)
        
        # --- SIZE INPUTS ---
        frame_size = tk.Frame(self.frame_engineer)
        frame_size.pack(pady=5)
        tk.Label(frame_size, text="W:").pack(side="left")
        self.entry_w = tk.Entry(frame_size, width=5); self.entry_w.pack(side="left")
        self.entry_w.insert(0, "100")
        tk.Label(frame_size, text="H:").pack(side="left")
        self.entry_h = tk.Entry(frame_size, width=5); self.entry_h.pack(side="left")
        self.entry_h.insert(0, "100")
        
        tk.Button(frame_size, text="Set", command=self.validate_measurements).pack(side="left", padx=5)

        # --- TABS ---
        nb = ttk.Notebook(self.frame_engineer)
        nb.pack(fill="both", expand=True, padx=5, pady=10)
        
        tab_shape = tk.Frame(nb); nb.add(tab_shape, text="Shapes")
        tab_num = tk.Frame(nb); nb.add(tab_num, text="Numbers") 
        tab_let = tk.Frame(nb); nb.add(tab_let, text="Letters") 

        # 1. SHAPES (Stacked)
        for s in ["Quadrilateral", "Circle", "Triangle"]:
            tk.Button(tab_shape, text=s, command=lambda x=s: self.spawn_item(x, "shape")).pack(fill="x", pady=2)
        
        # 2. NUMBERS (Grid Layout)
        # Using a grid so they don't run off the screen
        for i in range(10):
            b = tk.Button(tab_num, text=str(i), width=5, command=lambda x=str(i): self.spawn_item(x, "text"))
            b.grid(row=i//4, column=i%4, padx=2, pady=2) # 4 columns
            
        # 3. LETTERS (Grid Layout - Full Alphabet)
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for i, l in enumerate(alphabet):
            b = tk.Button(tab_let, text=l, width=5, command=lambda x=l: self.spawn_item(x, "text"))
            b.grid(row=i//4, column=i%4, padx=2, pady=2) # 4 columns

    def create_artist_ui(self):
        tk.Label(self.frame_artist, text="✏️ Artist Canvas", font=("Arial", 12, "bold")).pack(pady=10)
        self.btn_recognize = tk.Button(self.frame_artist, text="✨ Recognize", bg="#66ccff", font=("Arial", 14), height=2, command=self.perform_recognition)
        self.btn_recognize.pack(fill="x", padx=20, pady=20)
        
        self.lbl_result = tk.Label(self.frame_artist, text="...", font=("Arial", 18, "bold"), fg="blue")
        self.lbl_result.pack(pady=20)

    # --- VALIDATION ---
    def validate_measurements(self):
        w_str = self.entry_w.get().strip()
        h_str = self.entry_h.get().strip()

        if not w_str or not h_str:
            messagebox.showwarning("Error", "Dimensions cannot be empty.")
            self.valid_size = False
            return

        try:
            w = int(w_str)
            h = int(h_str)
        except ValueError:
            messagebox.showwarning("Error", "Please enter valid whole numbers.")
            self.valid_size = False
            return

        if w < 0 or h < 0:
            messagebox.showwarning("Error", "Dimensions cannot be negative.")
            self.valid_size = False
            return
        
        if w > 400 or h > 400:
            messagebox.showwarning("Error", "Max dimension is 400.")
            self.valid_size = False
            return

        self.current_w = w
        self.current_h = h
        self.valid_size = True
        messagebox.showinfo("Success", f"Size set to {w}x{h}")

    # --- SPAWN ITEMS ---
    def spawn_item(self, item, type_):
        if not self.valid_size:
            messagebox.showwarning("Blocked", "Please set a valid size (0-400) first.")
            return

        self.canvas.delete("all")
        cx, cy = 375, 375 
        
        if type_ == "shape":
            if item == "Quadrilateral":
                self.canvas.create_rectangle(cx-self.current_w/2, cy-self.current_h/2, cx+self.current_w/2, cy+self.current_h/2, width=5)
            elif item == "Circle":
                self.canvas.create_oval(cx-self.current_w/2, cy-self.current_h/2, cx+self.current_w/2, cy+self.current_h/2, width=5)
            elif item == "Triangle":
                self.canvas.create_polygon(cx, cy-self.current_h/2, cx-self.current_w/2, cy+self.current_h/2, cx+self.current_w/2, cy+self.current_h/2, width=5, fill="", outline="black")
        else:
            font_size = int(self.current_h * 0.8) 
            self.canvas.create_text(cx, cy, text=item, font=("Arial", font_size))

    # --- RECOGNITION LOGIC ---
    def perform_recognition(self):
        if not self.all_strokes: return
        
        all_points_flat = [p for stroke in self.all_strokes for p in stroke]
        if not all_points_flat: return

        input_grid = self.rasterize(all_points_flat)
        
        best_label = "?"
        best_score = -1
        
        for label, samples in self.training_data.items():
            for sample in samples:
                score = self.compare(input_grid, sample)
                if score > best_score:
                    best_score = score
                    best_label = label
        
        self.display_result(self.all_strokes, all_points_flat, best_label)

    def display_result(self, stroke_list, flat_points, label):
        self.canvas.delete("all")
        
        # Original
        self.canvas.create_text(60, 20, text="Original:", font=("Arial", 10, "bold"))
        xs = [p[0] for p in flat_points]
        ys = [p[1] for p in flat_points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        scale_view = 0.2 
        offset_x, offset_y = 20, 40
        
        for stroke in stroke_list:
            scaled_stroke = []
            for x, y in stroke:
                sx = (x - min_x) * scale_view + offset_x
                sy = (y - min_y) * scale_view + offset_y
                scaled_stroke.append(sx)
                scaled_stroke.append(sy)
            if len(scaled_stroke) >= 4:
                self.canvas.create_line(scaled_stroke, fill="gray", width=2)

        # Matched
        cx, cy = 375, 375
        w, h = 200, 200 
        
        if label.upper() == "QUADRILATERAL":
            self.canvas.create_rectangle(cx-w/2, cy-h/2, cx+w/2, cy+h/2, width=8, outline="black")
        elif label.upper() == "CIRCLE":
            self.canvas.create_oval(cx-w/2, cy-h/2, cx+w/2, cy+h/2, width=8, outline="black")
        elif label.upper() == "TRIANGLE":
            self.canvas.create_polygon(cx, cy-h/2, cx-w/2, cy+h/2, cx+w/2, cy+h/2, width=8, outline="black", fill="")
        elif label.upper() == "LINE":
            self.canvas.create_line(cx-w/2, cy, cx+w/2, cy, width=8, fill="black")
        else:
            self.canvas.create_text(cx, cy, text=label, font=("Arial", 200, "bold"), fill="black")

        self.lbl_result.config(text=f"Detected: {label}")
        self.all_strokes = [] 

    def rasterize(self, points):
        grid = [0] * (GRID_SIZE * GRID_SIZE)
        if not points: return grid
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        w, h = max(1, max_x - min_x), max(1, max_y - min_y)
        
        # Aspect Ratio logic
        max_dim = max(w, h)
        scale = (GRID_SIZE - 4) / max_dim
        center_x_offset = (GRID_SIZE - (w * scale)) / 2
        center_y_offset = (GRID_SIZE - (h * scale)) / 2
        
        for x, y in points:
            gx = int(center_x_offset + (x - min_x) * scale)
            gy = int(center_y_offset + (y - min_y) * scale)
            for neighbor in [0, -1, 1, -GRID_SIZE, GRID_SIZE]:
                idx = gy * GRID_SIZE + gx + neighbor
                if 0 <= idx < len(grid): grid[idx] = 1
        return grid

    def compare(self, grid1, grid2):
        matches = 0
        total = 0
        for i in range(len(grid1)):
            if grid1[i] == 1 or grid2[i] == 1:
                total += 1
                if grid1[i] == 1 and grid2[i] == 1:
                    matches += 1
        return matches / total if total > 0 else 0

    # --- UI LOGIC ---
    def toggle_mode(self):
        self.canvas.delete("all")
        if self.mode == "engineer":
            self.mode = "artist"
            self.frame_engineer.pack_forget()
            self.frame_artist.pack(fill="both")
            self.lbl_mode.config(text="CURRENT MODE: ARTIST")
            self.btn_switch.config(text="🔄 Switch to Engineer Mode")
        else:
            self.mode = "engineer"
            self.frame_artist.pack_forget()
            self.frame_engineer.pack(fill="both")
            self.lbl_mode.config(text="CURRENT MODE: ENGINEER")
            self.btn_switch.config(text="🔄 Switch to Artist Mode")

    def clear_canvas(self):
        self.canvas.delete("all")
        self.all_strokes = []

    def on_mouse_down(self, e):
        if self.mode == "artist": self.current_stroke = [(e.x, e.y)]
    def on_mouse_drag(self, e):
        if self.mode == "artist":
            self.current_stroke.append((e.x, e.y))
            if len(self.current_stroke) > 1:
                self.canvas.create_line(self.current_stroke[-2], self.current_stroke[-1], width=5, capstyle=tk.ROUND)
    def on_mouse_up(self, e):
        if self.mode == "artist": 
            self.all_strokes.append(self.current_stroke)
            self.current_stroke = []

if __name__ == "__main__":
    root = tk.Tk()
    RobotPaintApp(root)
    root.mainloop()