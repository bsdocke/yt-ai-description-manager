import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox
import sys
import os
import json
import threading
import config
import video_processor
import youtube_uploader

class TextRedirector(object):
    """Redirects stdout/stderr to a Tkinter Text widget."""
    def __init__(self, widget, tag="stdout"):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        # Use after() to ensure thread safety when updating UI from another thread
        self.widget.after(0, self._write, str)

    def _write(self, str):
        self.widget.configure(state="normal")
        self.widget.insert("end", str, (self.tag,))
        self.widget.see("end")
        self.widget.configure(state="disabled")

    def flush(self):
        pass

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.geometry("400x250")
        self.transient(parent)
        self.grab_set()
        
        self.parent = parent
        self.original_api_key = config.GOOGLE_AI_API_KEY
        self.original_max_errors = str(config.MAX_CONSECUTIVE_ERRORS)
        self.original_max_retries = str(config.MAX_RETRIES)

        self.api_key_var = tk.StringVar(value=config.GOOGLE_AI_API_KEY)
        self.max_errors_var = tk.StringVar(value=str(config.MAX_CONSECUTIVE_ERRORS))
        self.max_retries_var = tk.StringVar(value=str(config.MAX_RETRIES))

        # UI Layout
        frame = tk.Frame(self, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Google AI API Key:").pack(anchor="w")
        tk.Entry(frame, textvariable=self.api_key_var, width=50).pack(fill=tk.X, pady=(0, 10))

        tk.Label(frame, text="Max Consecutive Errors:").pack(anchor="w")
        tk.Entry(frame, textvariable=self.max_errors_var, width=10).pack(anchor="w", pady=(0, 20))

        tk.Label(frame, text="Max Upload Retries:").pack(anchor="w")
        tk.Entry(frame, textvariable=self.max_retries_var, width=10).pack(anchor="w", pady=(0, 20))

        btn_frame = tk.Frame(frame)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.save_btn = tk.Button(btn_frame, text="Save", command=self.save, state=tk.DISABLED)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

        tk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT)

        # Trace changes
        self.api_key_var.trace_add("write", self.on_change)
        self.max_errors_var.trace_add("write", self.on_change)
        self.max_retries_var.trace_add("write", self.on_change)

    def on_change(self, *args):
        if (self.api_key_var.get() != self.original_api_key or 
            self.max_errors_var.get() != self.original_max_errors or
            self.max_retries_var.get() != self.original_max_retries):
            self.save_btn.config(state=tk.NORMAL)
        else:
            self.save_btn.config(state=tk.DISABLED)

    def save(self):
        new_key = self.api_key_var.get().strip()
        try:
            new_max_errors = int(self.max_errors_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Max Consecutive Errors must be a number.")
            return

        try:
            new_max_retries = int(self.max_retries_var.get().strip())
        except ValueError:
            messagebox.showerror("Error", "Max Retries must be a number.")
            return

        # Update globals
        config.GOOGLE_AI_API_KEY = new_key
        config.MAX_CONSECUTIVE_ERRORS = new_max_errors
        config.MAX_RETRIES = new_max_retries

        # Persist to file
        data = {}
        if os.path.exists(config.CONFIG_FILE):
            try:
                with open(config.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data["google_ai_api_key"] = config.GOOGLE_AI_API_KEY
        data["max_consecutive_errors"] = config.MAX_CONSECUTIVE_ERRORS
        data["max_upload_retries"] = config.MAX_RETRIES

        try:
            with open(config.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
            return

        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("YouTube Description Generator")
        self.geometry("700x500")

        self.directory_var = tk.StringVar()
        self.load_config()

        # Toolbar
        toolbar = tk.Frame(self, bd=1, relief=tk.RAISED)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        
        tk.Button(toolbar, text="Settings", command=self.open_settings).pack(side=tk.LEFT, padx=2, pady=2)

        # Main Frame
        main_frame = tk.Frame(self, padx=10, pady=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Directory Selection
        dir_frame = tk.Frame(main_frame)
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(dir_frame, text="Source Directory:").pack(side=tk.LEFT)
        
        self.dir_entry = tk.Entry(dir_frame, textvariable=self.directory_var)
        self.dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)

        tk.Button(dir_frame, text="Browse...", command=self.browse_directory).pack(side=tk.LEFT)

        # Generate Button
        self.generate_btn = tk.Button(main_frame, text="Generate Description", command=self.start_processing, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.generate_btn.pack(pady=(0, 10), fill=tk.X)

        # YT Upload Button
        self.yt_upload_btn = tk.Button(main_frame, text="Upload to Youtube", command=self.start_yt_upload, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
        self.yt_upload_btn.pack(pady=(0, 10), fill=tk.X)

        # Log Area
        tk.Label(main_frame, text="Logs:").pack(anchor="w")
        self.log_area = scrolledtext.ScrolledText(main_frame, state='disabled', height=15)
        self.log_area.pack(fill=tk.BOTH, expand=True)

        # Redirect stdout/stderr
        sys.stdout = TextRedirector(self.log_area, "stdout")
        sys.stderr = TextRedirector(self.log_area, "stderr")

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.directory_var.get())
        if directory:
            self.directory_var.set(directory)

    def open_settings(self):
        SettingsDialog(self)

    def load_config(self):
        if os.path.exists(config.CONFIG_FILE):
            try:
                with open(config.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    self.directory_var.set(data.get("last_directory", ""))
                    
                    config.GOOGLE_AI_API_KEY = data.get("google_ai_api_key", "")
                    config.MAX_CONSECUTIVE_ERRORS = int(data.get("max_consecutive_errors", 3))
                    config.MAX_RETRIES = int(data.get("max_upload_retries", 10))
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        data = {}
        if os.path.exists(config.CONFIG_FILE):
            try:
                with open(config.CONFIG_FILE, 'r') as f:
                    data = json.load(f)
            except Exception:
                pass
        
        data["last_directory"] = self.directory_var.get()
        
        try:
            with open(config.CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    def start_processing(self):
        if not config.GOOGLE_AI_API_KEY:
            messagebox.showwarning("Missing API Key", "Please configure the Google AI API Key in Settings before uploading.")
            return

        directory = self.directory_var.get()
        if not directory or not os.path.isdir(directory):
            messagebox.showerror("Error", "Please select a valid directory.")
            return

        self.save_config()
        self.generate_btn.config(state=tk.DISABLED, text="Processing...")
        self.yt_upload_btn.config(state=tk.DISABLED, text="Processing...")

        # Run in a separate thread to keep UI responsive
        threading.Thread(target=video_processor.process_videos, args=(directory, self.on_process_complete), daemon=True).start()

    def on_process_complete(self):
        # This needs to be scheduled on the main thread
        self.after(0, self._reset_button)

    def on_upload_complete(self):
        self.after(0, self._reset_button)

    def _reset_button(self):
        self.generate_btn.config(state=tk.NORMAL, text="Generate Description")
        self.yt_upload_btn.config(state=tk.NORMAL, text="Upload to YouTube")
        messagebox.showinfo("Complete", "Action finished.")

    def start_yt_upload(self):
        self.generate_btn.config(state=tk.DISABLED, text="Uploading...")
        self.yt_upload_btn.config(state=tk.DISABLED, text="Uploading...")
        threading.Thread(target=youtube_uploader.start_yt_upload, args=(self.directory_var.get(), self.on_upload_complete), daemon=True).start()
