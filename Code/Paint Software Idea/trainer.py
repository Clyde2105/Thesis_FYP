import tkinter as tk
from tkinter import messagebox
import json
import os

# CONFIG
GRID_SIZE = 20
DATA_FILE = "brain.json"

class TrainerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Trainer V3: Aspect Ratio Fixed")
        self.root.geometry("600x650")
        
        self.dataset = {}
        self.last_label_saved = None 
        self.load_existing_data()
        
        # --- UI ---
        tk.Label(root, text="Draw -> Type Name -> Save", font=("Arial", 14, "bold")).pack(pady=10)
        
        self.canvas = tk.Canvas(root, bg="white", width=400, height=400, bd=2, relief="sunken")
        self.canvas.pack()
        
        controls = tk.Frame(root)
        controls.pack(pady=10)
        
        tk.Label(controls, text="Label:").pack(side="left")
        self.entry_label = tk.Entry(controls, font=("Arial", 12), width=10)
        self.entry_label.pack(side="left", padx=5)
        
        tk.Button(controls, text="💾 Save", bg="#ccffcc", command=self.save_sample).pack(side="left", padx=5)
        self.btn_undo = tk.Button(controls, text="↩️ Undo Last", bg="#ffcccc", command=self.undo_last)
        self.btn_undo.pack(side="left", padx=5)
        
        tk.Button(root, text="Clear Canvas Only", command=self.clear_canvas).pack(pady=5)
        
        self.lbl_status = tk.Label(root, text=f"Total Samples: {self.count_samples()}", fg="blue")
        self.lbl_status.pack(side="bottom", pady=10)

        # Drawing
        self.current_stroke = []
        self.all_strokes = []
        self.canvas.bind("<Button-1>", self.start_draw)
        self.canvas.bind("<B1-Motion>", self.draw)
        self.canvas.bind("<ButtonRelease-1>", self.end_draw)

    def save_sample(self):
        label = self.entry_label.get().strip().upper()
        if not label or not self.all_strokes: return

        # Rasterize & Save
        points = [p for s in self.all_strokes for p in s]
        grid = self.rasterize(points)
        
        if label not in self.dataset: self.dataset[label] = []
        self.dataset[label].append(grid)
        self.write_to_file()
        
        self.last_label_saved = label
        self.lbl_status.config(text=f"Saved '{label}'! Total: {self.count_samples()}")
        self.clear_canvas()

    def undo_last(self):
        if not self.last_label_saved: return
        if self.last_label_saved in self.dataset:
            data_list = self.dataset[self.last_label_saved]
            if data_list:
                data_list.pop()
                self.write_to_file()
                self.lbl_status.config(text=f"Removed last '{self.last_label_saved}'.")
                self.last_label_saved = None

    def write_to_file(self):
        with open(DATA_FILE, "w") as f: json.dump(self.dataset, f)

    def load_existing_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r") as f: self.dataset = json.load(f)
            except: self.dataset = {}

    def count_samples(self): return sum(len(v) for v in self.dataset.values())

    # --- Drawing ---
    def start_draw(self, e): self.current_stroke = [(e.x, e.y)]
    def draw(self, e): 
        self.current_stroke.append((e.x, e.y))
        self.canvas.create_oval(e.x-3, e.y-3, e.x+3, e.y+3, fill="black", outline="black")
    def end_draw(self, e): 
        self.all_strokes.append(self.current_stroke); self.current_stroke = []
    def clear_canvas(self): 
        self.canvas.delete("all"); self.all_strokes = []

    # --- NEW INTELLIGENT RASTERIZER (Preserves Aspect Ratio) ---
    def rasterize(self, points):
        grid = [0] * (GRID_SIZE * GRID_SIZE)
        if not points: return grid
        
        # 1. Get Bounding Box
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        
        w = max_x - min_x
        h = max_y - min_y
        
        # 2. Determine Scale (Fit the largest dimension into the grid)
        max_dim = max(w, h)
        if max_dim == 0: max_dim = 1
        
        # Leave a 2-pixel padding on each side (16x16 usable area in 20x20 grid)
        scale = (GRID_SIZE - 4) / max_dim
        
        # 3. Center the drawing
        center_x_offset = (GRID_SIZE - (w * scale)) / 2
        center_y_offset = (GRID_SIZE - (h * scale)) / 2
        
        for x, y in points:
            # Shift to 0,0 -> Scale -> Shift to center
            gx = int(center_x_offset + (x - min_x) * scale)
            gy = int(center_y_offset + (y - min_y) * scale)
            
            # Draw point + Neighbors (Dilation)
            for neighbor in [0, -1, 1, -GRID_SIZE, GRID_SIZE]:
                idx = gy * GRID_SIZE + gx + neighbor
                if 0 <= idx < len(grid): grid[idx] = 1
                
        return grid

if __name__ == "__main__":
    root = tk.Tk()
    TrainerApp(root)
    root.mainloop()