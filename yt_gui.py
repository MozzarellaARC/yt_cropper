# ========== GUI ========== 
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class YouTubeCropperGUI:
    def __init__(self, backend):
        self.backend = backend
        self.setup_gui()
        
    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("YouTube Multi Trim + Cropper")
        self.root.configure(bg="#f0f0f0")

        style = ttk.Style()
        style.configure("TLabel", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10))
        style.configure("TEntry", padding=5)

        self.frame = ttk.Frame(self.root, padding=10)
        self.frame.grid(row=0, column=0, sticky="nsew")

        self.frame.grid_columnconfigure(0, weight=0)
        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_columnconfigure(2, weight=0)

        # Entry widgets
        self.url_entry = ttk.Entry(self.frame)
        self.start_entry = ttk.Entry(self.frame)
        self.end_entry = ttk.Entry(self.frame)
        self.output_dir_entry = ttk.Entry(self.frame)
        self.base_name_entry = ttk.Entry(self.frame)

        # Variables
        self.resolution_var = tk.StringVar(value="")
        self.trim_var = tk.BooleanVar(value=True)
        self.crop_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="")

        # Global lists for backend
        self.segment_list = []  # global list of trim segments

        self.create_widgets()

    def add_labeled_row(self, row, label, entry, pad_top=3):
        pady = (pad_top, 0)
        ttk.Label(self.frame, text=label).grid(row=row, column=0, sticky="e", padx=(0, 5), pady=pady)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 5), pady=pady, columnspan=2)

    def create_widgets(self):
        self.add_labeled_row(0, "YouTube URL:", self.url_entry)
        self.add_labeled_row(1, "Output Directory:", self.output_dir_entry)
        self.add_labeled_row(2, "Base File Name:", self.base_name_entry)
        self.add_labeled_row(3, "Start Time (HH:MM:SS):", self.start_entry, pad_top=25)
        self.add_labeled_row(4, "End Time (HH:MM:SS):", self.end_entry)

        ttk.Button(self.frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=3, sticky="w", padx=5)

        ttk.Button(self.frame, text="+ Add Segment", command=self.add_segment).grid(row=5, column=1, sticky="w", padx=5, pady=3)
        ttk.Button(self.frame, text="- Remove Segment", command=self.remove_segment).grid(row=5, column=2, sticky="w", padx=5, pady=3)

        ttk.Label(self.frame, text="Trim Segments:").grid(row=6, column=0, sticky="ne", padx=(0, 5), pady=3)
        self.segments_box = tk.Listbox(self.frame, height=4, width=40)
        self.segments_box.grid(row=6, column=1, columnspan=2, sticky="ew", pady=3)

        ttk.Label(self.frame, text="Resolution:").grid(row=7, column=0, sticky="e", padx=(0, 5), pady=3)
        self.resolution_menu = ttk.OptionMenu(self.frame, self.resolution_var, "")
        self.resolution_menu.grid(row=7, column=1, sticky="w", padx=(0, 5), pady=3)
        ttk.Button(self.frame, text="Fetch Resolutions", command=self.fetch_resolutions).grid(row=7, column=2, sticky="w", pady=3)

        checkbox_frame = ttk.Frame(self.frame)
        checkbox_frame.grid(row=8, column=0, columnspan=3, sticky="w", pady=5)
        ttk.Checkbutton(checkbox_frame, text="Trim video (multiple segments)", variable=self.trim_var).grid(row=0, column=0, sticky="w", padx=5)
        ttk.Checkbutton(checkbox_frame, text="Crop to 9:16 vertical (auto-safe)", variable=self.crop_var).grid(row=0, column=1, sticky="w", padx=5)

        ttk.Button(self.frame, text="Download & Process", command=self.run_process).grid(row=9, column=0, columnspan=3, pady=10)
        self.status_label = ttk.Label(self.frame, textvariable=self.status_var, foreground="green")
        self.status_label.grid(row=10, column=0, columnspan=3, pady=(0, 5))

    def browse_output_dir(self):
        d = filedialog.askdirectory()
        if d:
            self.output_dir_entry.delete(0, tk.END)
            self.output_dir_entry.insert(0, d)

    def add_segment(self):
        start = self.start_entry.get().strip()
        end = self.end_entry.get().strip()
        if start and end:
            self.segment_list.append((start, end))
            self.segments_box.insert(tk.END, f"{start} - {end}")
            self.start_entry.delete(0, tk.END)
            self.end_entry.delete(0, tk.END)

    def remove_segment(self):
        selected = self.segments_box.curselection()
        if selected:
            idx = selected[0]
            self.segment_list.pop(idx)
            self.segments_box.delete(idx)

    def fetch_resolutions(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Missing Info", "Please enter a YouTube URL.")
            return

        try:
            self.status_var.set("Fetching formats...")
            self.root.update()

            format_map = self.backend.fetch_resolutions(url)

            if not format_map:
                raise Exception("No video-only formats found.")

            menu = self.resolution_menu["menu"]
            menu.delete(0, "end")
            for res in sorted(format_map.keys(), key=lambda r: int(r.replace('p', ''))):
                menu.add_command(label=res, command=lambda r=res: self.resolution_var.set(r))

            self.backend.format_id_map = format_map

            self.resolution_var.set(max(format_map.keys(), key=lambda r: int(r.replace('p', ''))))
            self.status_var.set("Resolution list updated.")

        except Exception as e:
            self.status_var.set("Error")
            messagebox.showerror("Error", f"Could not fetch formats:\n{e}")

    def run_process(self):
        url = self.url_entry.get().strip()
        resolution = self.resolution_var.get()
        do_trim = self.trim_var.get()
        do_crop = self.crop_var.get()
        output_dir = self.output_dir_entry.get().strip()
        base_name = self.base_name_entry.get().strip()

        if not url:
            messagebox.showerror("Missing Info", "Please enter a YouTube URL.")
            return
        if not output_dir:
            messagebox.showerror("Missing Info", "Please enter an output directory.")
            return
        if not base_name:
            messagebox.showerror("Missing Info", "Please enter a base name.")
            return
        if do_trim and not self.segment_list:
            messagebox.showerror("Missing Segments", "Please add at least one trim segment.")
            return
        if resolution not in self.backend.format_id_map:
            messagebox.showerror("Missing Format", "Please fetch available resolutions first.")
            return

        try:
            self.status_var.set("Preparing...")
            self.root.update()

            def status_callback(message):
                self.status_var.set(message)
                self.root.update()

            final_output = self.backend.run_process(
                url, resolution, do_trim, do_crop, output_dir, 
                base_name, self.segment_list, status_callback
            )

            self.status_var.set("All segments saved and combined!")
            messagebox.showinfo("Success", f"Final video saved to:\n{final_output}")

        except Exception as e:
            self.status_var.set("Error")
            messagebox.showerror("Error", str(e))

    def run(self):
        self.root.mainloop()
