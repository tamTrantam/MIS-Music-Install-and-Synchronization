import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import threading
import subprocess
from turtle import title
import urllib.request
import unicodedata
from urllib.parse import parse_qs, urlparse
from PIL import Image, ImageTk
import io
import functools
from yt_dlp import YoutubeDL
from mutagen.mp3 import MP3
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3
from mutagen.id3._frames import APIC

def get_bundle_path(relative_path):
    """Safely finds the path to bundled files (yt-dlp, ffmpeg) inside the EXE."""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

def log_to_terminal(func):
    """Decorator to log function calls and errors to the terminal."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"\n--- Calling function: {func.__name__} ---")
        try:
            result = func(*args, **kwargs)
            print(f"--- Function {func.__name__} executed successfully ---\n")
            return result
        except Exception as e:
            error_msg = str(e)
            func_name = func.__name__
            print(f"!!! An error occurred in {func_name}: {error_msg} !!!\n")
            if isinstance(args[0], App):
                args[0].after(0, lambda msg=error_msg, fn=func_name: messagebox.showerror("Error", f"An error occurred in {fn}:\n{msg}"))
    return wrapper


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.option_add("*Font", "SegoeUI 10")
        self.title("Music Library & Game Sync Manager")
        self.geometry("900x700")
        self.thumbnail_cache = {}
        self.current_results = []

        # --- Main Layout ---
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Styling ---
        self.style = ttk.Style(self)
        self.style.theme_use('clam')

        # --- Search Section ---
        search_frame = ttk.LabelFrame(self.main_frame, text="Search")
        search_frame.pack(fill=tk.X, pady=5)

        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=60)
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        search_entry.bind('<Return>', lambda e: self.start_search())
        search_button = ttk.Button(search_frame, text="Search", command=self.start_search)
        search_button.pack(side=tk.RIGHT, padx=5)

        # --- Results Section ---
        results_frame = ttk.LabelFrame(self.main_frame, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, columns=("Title", "Channel"), show="headings", height=8)
        self.results_tree.heading("Title", text="Title")
        self.results_tree.heading("Channel", text="Channel")
        self.results_tree.column("Title", width=550)
        self.results_tree.column("Channel", width=250)
        self.results_tree.pack(fill=tk.BOTH, expand=True)
        self.results_tree.bind('<<TreeviewSelect>>', self.on_result_select)

        self.thumbnail_photo = None
        self.thumbnail_label = tk.Label(results_frame, text="Select a result to preview its thumbnail", bg="#3e3e3e", fg="white", padx=10, pady=8)
        self.thumbnail_label.pack(fill=tk.X, padx=5, pady=(0, 5))

        # --- Download Section ---
        download_frame = ttk.LabelFrame(self.main_frame, text="Download Options")
        download_frame.pack(fill=tk.X, pady=5)

        self.download_mp3_button = ttk.Button(download_frame, text="Download as MP3 (320kbps)", command=self.download_mp3)
        self.download_mp3_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.download_webm_button = ttk.Button(download_frame, text="Download as WebM", command=self.download_webm)
        self.download_webm_button.pack(side=tk.LEFT, padx=5, pady=5)

        # --- Progress Bar & Status ---
        progress_frame = ttk.Frame(self.main_frame)
        progress_frame.pack(fill=tk.X, pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", width=30)
        self.status_label.pack(side=tk.RIGHT, padx=5)

        # --- Sync Section ---
        sync_frame = ttk.LabelFrame(self.main_frame, text="Library & Sync")
        sync_frame.pack(fill=tk.X, pady=5)

        # Master Library
        master_lib_frame = ttk.Frame(sync_frame)
        master_lib_frame.pack(fill=tk.X, padx=5, pady=5)
        master_lib_label = ttk.Label(master_lib_frame, text="Master Library:")
        master_lib_label.pack(side=tk.LEFT)
        self.master_lib_path = tk.StringVar(value="Not Set")
        master_lib_entry = ttk.Entry(master_lib_frame, textvariable=self.master_lib_path, state="readonly")
        master_lib_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        master_lib_button = ttk.Button(master_lib_frame, text="Set...", command=self.set_master_library)
        master_lib_button.pack(side=tk.RIGHT)

        webm_lib_frame = ttk.Frame(sync_frame)
        webm_lib_frame.pack(fill=tk.X, padx=5, pady=5)
        webm_lib_label = ttk.Label(webm_lib_frame, text="WebM Folder:")
        webm_lib_label.pack(side=tk.LEFT)
        self.webm_lib_path = tk.StringVar(value="Not Set")
        webm_lib_entry = ttk.Entry(webm_lib_frame, textvariable=self.webm_lib_path, state="readonly")
        webm_lib_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        webm_lib_button = ttk.Button(webm_lib_frame, text="Set...", command=self.set_webm_library)
        webm_lib_button.pack(side=tk.RIGHT)

        playlist_button = ttk.Button(sync_frame, text="Import JSON Playlist", command=self.load_json_playlist)
        playlist_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Target Folders
        target_folders_frame = ttk.Frame(sync_frame)
        target_folders_frame.pack(fill=tk.X, padx=5, pady=5)
        target_folders_label = ttk.Label(target_folders_frame, text="Game Folders to Sync:")
        target_folders_label.pack(anchor=tk.W)
        
        self.target_listbox = tk.Listbox(target_folders_frame, height=3, background="#3e3e3e", foreground="white", borderwidth=0, highlightthickness=0)
        self.target_listbox.pack(fill=tk.X, expand=True, pady=2)

        target_buttons_frame = ttk.Frame(target_folders_frame)
        target_buttons_frame.pack(fill=tk.X)
        add_target_button = ttk.Button(target_buttons_frame, text="Add Folder", command=self.add_target_folder)
        add_target_button.pack(side=tk.LEFT)
        remove_target_button = ttk.Button(target_buttons_frame, text="Remove Selected", command=self.remove_target_folder)
        remove_target_button.pack(side=tk.LEFT, padx=5)

        # Sync Button
        sync_button = ttk.Button(sync_frame, text="Sync Library to Game Folders", command=self.sync_library)
        sync_button.pack(in_=target_buttons_frame, side=tk.RIGHT)

        # --- Apply Theme & Load Config ---
        self.configure_dark_theme()
        self.load_config()

    def configure_dark_theme(self):
        bg_color = '#23262b'
        fg_color = '#f2f4f8'
        field_bg = '#31353c'
        button_bg = '#5b6470'
        active_button_bg = '#7a8696'

        self.style.configure('.', background=bg_color, foreground=fg_color)
        self.style.configure('TButton', background=button_bg, foreground=fg_color, borderwidth=0, padding=6, relief='flat')
        self.style.map('TButton', background=[('active', active_button_bg)])
        self.style.configure('TEntry', fieldbackground=field_bg, foreground=fg_color, borderwidth=1, relief='flat')
        self.style.configure('TLabel', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelFrame', background=bg_color, foreground=fg_color)
        self.style.configure('TLabelFrame.Label', background=bg_color, foreground=fg_color)
        self.style.configure('Treeview', 
                             background=field_bg, 
                             fieldbackground=field_bg, 
                             foreground=fg_color)
        self.style.configure('Treeview.Heading', background=button_bg, foreground=fg_color, font=('Calibri', 10, 'bold'))
        self.style.map('Treeview.Heading', background=[('active', active_button_bg)])
        self.style.configure('green.Horizontal.TProgressbar', troughcolor=field_bg, background='green', borderwidth=0)
        self.progress_bar.configure(style='green.Horizontal.TProgressbar')
        self.configure(background=bg_color)

    @log_to_terminal
    def start_search(self):
        query = self.search_var.get()
        if not query:
            messagebox.showwarning("Empty Search", "Please enter a search term.")
            return
        
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)
        self.current_results = []
            
        self.update_status("Searching...")
        
        print(f"Starting search for: '{query}'")
        threading.Thread(target=self.perform_search, args=(query,), daemon=True).start()

    @log_to_terminal
    def perform_search(self, query):
        try:
            print(f"Performing YouTube search for: {query}")
            results = self.search_youtube(query, max_results=15)
            
            print(f"Found {len(results)} results")
            self.current_results = [self.normalize_search_result(item) for item in results]
            
            for item in self.current_results:
                self.after(0, self.add_search_result, item)
            
            self.after(0, lambda: self.update_status("Search complete"))
        except Exception as e:
            print(f"Error during YouTube search: {e}")
            self.after(0, lambda: self.update_status("Search failed"))
            raise

    def search_youtube(self, query, max_results=15):
        if self.is_youtube_url(query):
            return [self.fetch_video_info(query)]

        candidates = [query]
        normalized = self.normalize_vietnamese_query(query)
        if normalized and normalized not in candidates:
            candidates.append(normalized)

        for candidate in candidates:
            results = self.search_youtube_raw(candidate, max_results=max_results)
            if results:
                return results

        return []

    def search_youtube_raw(self, query, max_results=15):
        ydl_opts: dict[str, object] = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
            'extract_flat': True,
        }
        with YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            data = ydl.extract_info(f'ytsearch{max_results}:{query}', download=False)
        return list(data.get('entries') or [])[:max_results]

    def fetch_video_info(self, video_url):
        ydl_opts: dict[str, object] = {
            'quiet': True,
            'skip_download': True,
            'noplaylist': True,
        }
        with YoutubeDL(ydl_opts) as ydl:  # type: ignore[arg-type]
            return ydl.extract_info(video_url, download=False)

    def normalize_vietnamese_query(self, query):
        normalized = unicodedata.normalize('NFKD', query)
        stripped = ''.join(char for char in normalized if not unicodedata.combining(char))
        stripped = stripped.replace('đ', 'd').replace('Đ', 'D')
        return ' '.join(stripped.split())

    def is_youtube_url(self, query):
        parsed = urlparse(query.strip())
        host = parsed.netloc.lower()
        if parsed.scheme not in ('http', 'https'):
            return False
        return 'youtube.com' in host or 'youtu.be' in host

    def normalize_search_result(self, item):
        if isinstance(item, dict):
            video_id = item.get('id', '') or ''
            url = item.get('url', '') or item.get('webpage_url', '') or (f"https://www.youtube.com/watch?v={video_id}" if video_id else '')
            channel = item.get('channel') or item.get('uploader') or item.get('uploader_id') or 'No Channel'
            title = item.get('title', 'No Title')
            thumbnail_url = self.extract_thumbnail_url(item)
        else:
            video_id = getattr(item, 'video_id', '') or getattr(item, 'id', '') or ''
            url = getattr(item, 'watch_url', '') or getattr(item, 'webpage_url', '') or (f"https://www.youtube.com/watch?v={video_id}" if video_id else '')
            channel = getattr(item, 'author', None) or getattr(item, 'channel', None) or getattr(item, 'uploader', None) or 'No Channel'
            title = getattr(item, 'title', 'No Title')
            thumbnail_url = None
        return {
            'id': video_id,
            'url': url,
            'title': title,
            'channel': channel or 'No Channel',
            'thumbnail_url': thumbnail_url,
        }

    def extract_thumbnail_url(self, item):
        thumbnail = item.get('thumbnail')
        if isinstance(thumbnail, str) and thumbnail:
            return thumbnail

        thumbnails = item.get('thumbnails') or []
        if thumbnails:
            for candidate in reversed(thumbnails):
                url = candidate.get('url') if isinstance(candidate, dict) else None
                if url:
                    return url

        video_id = item.get('id', '') or ''
        if video_id:
            return f'https://i.ytimg.com/vi/{video_id}/hqdefault.jpg'

        return None

    def add_search_result(self, item):
        title = item.get('title', 'No Title')
        channel = item.get('channel', 'No Channel')
        self.results_tree.insert('', tk.END, values=(title, channel))

    def on_result_select(self, event=None):
        selected = self.results_tree.selection()
        if not selected:
            return

        index = self.results_tree.index(selected[0])
        if index >= len(self.current_results):
            return

        self.update_thumbnail_preview(self.current_results[index])

    def update_thumbnail_preview(self, item):
        thumbnail_bytes = None
        thumbnail_url = item.get('thumbnail_url') if isinstance(item, dict) else None

        if thumbnail_url:
            try:
                request = urllib.request.Request(thumbnail_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(request, timeout=10) as response:
                    thumbnail_bytes = response.read()
            except Exception:
                thumbnail_bytes = None

        if not thumbnail_bytes:
            video_id = item.get('id', '') if isinstance(item, dict) else ''
            thumbnail_bytes = self.fetch_thumbnail_bytes(video_id)

        if not thumbnail_bytes:
            self.thumbnail_label.configure(image='', text='Thumbnail unavailable')
            self.thumbnail_photo = None
            return

        try:
            image = Image.open(io.BytesIO(thumbnail_bytes))
            image.thumbnail((240, 135))
            self.thumbnail_photo = ImageTk.PhotoImage(image)
            self.thumbnail_label.configure(image=self.thumbnail_photo, text='')
        except Exception:
            self.thumbnail_label.configure(image='', text='Thumbnail unavailable')
            self.thumbnail_photo = None

    def update_status(self, message):
        self.status_label.config(text=message)
        print(f"Status: {message}")

    @log_to_terminal
    def download_mp3(self):
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a video to download.")
            return
        
        index = int(selected[0].split('I')[-1]) - 1
        video_info = self.current_results[index]
        video_id = video_info.get('id')
        title = video_info.get('title', 'Unknown')
        
        if not self.master_lib_path.get() or self.master_lib_path.get() == "Not Set":
            messagebox.showwarning("No Library Set", "Please set a Master Music Library folder first.")
            return
        
        print(f"Starting MP3 download for: {title} (ID: {video_id})")
        self.update_status(f"Downloading: {title}")
        
        video_url = video_info.get('url') or f"https://www.youtube.com/watch?v={video_id}"
        threading.Thread(target=self.perform_download_mp3, args=(video_url, title, video_info), daemon=True).start()

    @log_to_terminal
    def perform_download_mp3(self, video_url, title, video_info):
        try:
            output_dir = os.path.abspath(self.master_lib_path.get())
            # Sanitize title to create a valid filename
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-')]).rstrip()
            output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")

            ytdlp_exe = get_bundle_path("yt-dlp.exe")
            ffmpeg_dir = get_bundle_path(".") # The directory containing ffmpeg.exe

            cmd = [
                ytdlp_exe,
                '--progress', # Request progress output
                '--ffmpeg-location', ffmpeg_dir,
                '-x', '--audio-format', 'mp3',
                '--audio-quality', '320K',
                '--add-metadata',
                '--print', 'after_move:filepath',
                '-o', output_template,
                video_url
            ]

            channel = video_info.get('channel', 'Unknown Artist')
            
            print(f"Downloading video: {video_url}")
            print(f"Output directory: {output_dir}")
            
            print(f"Running command: {' '.join(cmd)}")
            # Use CREATE_NO_WINDOW to prevent the console from popping up in the compiled app
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            assert process.stdout is not None
            assert process.stderr is not None

            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100

            # Read stdout line by line to parse progress
            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if '[download]' in line and '%' in line:
                    try:
                        # Extract percentage more carefully
                        import re
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            percent = float(match.group(1))
                            self.after(0, self.update_progress, percent)
                    except (ValueError, AttributeError):
                        # Ignore lines that can't be parsed
                        pass
                elif line and not line.startswith('after_move'):
                    print(f"yt-dlp: {line}")

            process.wait()
            stderr_output = process.stderr.read()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr=stderr_output)

            downloaded_path = output_template.replace('%(ext)s', 'mp3')

            if downloaded_path and os.path.exists(downloaded_path):
                self.write_mp3_metadata(downloaded_path, title, channel, video_url, video_info.get('id', ''))
            else:
                print("Could not determine the downloaded file path.")

            print(f"Download completed for: {title}")
            self.after(0, lambda: self.update_status("Download complete"))
            self.after(0, self.update_progress, 100) # Ensure it finishes at 100%
    
    # TRIGGER AUTO SYNC HERE
            threading.Thread(target=self.perform_sync, daemon=True).start() 
    
            self.after(0, lambda: messagebox.showinfo("Success", f"Downloaded and Synced: {title}"))
        except Exception as e:
            print(f"Error during MP3 download: {e}")
            if isinstance(e, subprocess.CalledProcessError) and e.stderr:
                print(f"STDERR: {e.stderr}")
            self.after(0, lambda: self.update_status(f"Error: {e}"))
            self.after(0, lambda: messagebox.showerror("Download Failed", f"Failed to download '{title}'.\n\nError: {e}"))
            self.after(0, self.update_progress, 0) # Reset on failure

    def update_progress(self, value):
        self.progress_bar['value'] = value

    def write_mp3_metadata(self, mp3_path, title, artist, source_url, video_id):
        try:
            try:
                audio = EasyID3(mp3_path)
            except Exception:
                audio = EasyID3()

            audio['title'] = [title]
            audio['artist'] = [artist or 'Unknown Artist']
            audio['album'] = ['YouTube Downloads']
            audio['albumartist'] = [artist or 'Unknown Artist']
            audio['website'] = [source_url]
            audio.save(mp3_path)

            thumbnail_data = self.fetch_thumbnail_bytes(video_id)
            if thumbnail_data:
                self.embed_thumbnail(mp3_path, thumbnail_data)

            print(f"Metadata written to: {mp3_path}")
        except Exception as e:
            print(f"Error writing MP3 metadata: {e}")

    def fetch_thumbnail_bytes(self, video_id):
        if not video_id:
            return None

        thumbnail_urls = [
            f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
            f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        ]

        headers = {"User-Agent": "Mozilla/5.0"}
        for url in thumbnail_urls:
            try:
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=10) as response:
                    data = response.read()
                if data:
                    return data
            except Exception:
                continue
        return None

    def embed_thumbnail(self, mp3_path, thumbnail_data):
        try:
            try:
                tags = ID3(mp3_path)
            except Exception:
                tags = ID3()

            tags.delall('APIC')
            tags.add(APIC(
                encoding=3,
                mime='image/jpeg',
                type=3,
                desc='Cover',
                data=thumbnail_data,
            ))
            tags.save(mp3_path)
            print(f"Cover art embedded in: {mp3_path}")
        except Exception as e:
            print(f"Error embedding cover art: {e}")

    @log_to_terminal
    def download_webm(self):
        selected = self.results_tree.selection()
        if not selected:
            messagebox.showwarning("No Selection", "Please select a video to download.")
            return
        
        index = int(selected[0].split('I')[-1]) - 1
        video_info = self.current_results[index]
        video_id = video_info.get('id')
        title = video_info.get('title', 'Unknown')
        
        if not self.master_lib_path.get() or self.master_lib_path.get() == "Not Set":
            messagebox.showwarning("No Library Set", "Please set a Master Music Library folder first.")
            return

        if not self.webm_lib_path.get() or self.webm_lib_path.get() == "Not Set":
            messagebox.showwarning("No WebM Folder Set", "Please set a WebM output folder first.")
            return
        
        print(f"Starting WebM download for: {title} (ID: {video_id})")
        self.update_status(f"Downloading: {title}")
        
        video_url = video_info.get('url') or f"https://www.youtube.com/watch?v={video_id}"
        threading.Thread(target=self.perform_download_webm, args=(video_url, title), daemon=True).start()

    @log_to_terminal
    def perform_download_webm(self, video_url, title):
        try:
            output_dir = os.path.abspath(self.webm_lib_path.get())
            safe_title = "".join([c for c in title if c.isalpha() or c.isdigit() or c in (' ', '-')]).rstrip()
            output_template = os.path.join(output_dir, f"{safe_title}.%(ext)s")
            
            ytdlp_exe = get_bundle_path("yt-dlp.exe")

            print(f"Downloading video: {video_url}")
            print(f"Output directory: {output_dir}")
            
            cmd = [
                ytdlp_exe,
                '--progress', # Request progress output
                '-f', 'bv*+ba/b',
                '--recode-video', 'webm',
                '-o', output_template,
                video_url
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            assert process.stdout is not None
            assert process.stderr is not None

            self.progress_bar['value'] = 0
            self.progress_bar['maximum'] = 100

            for line in iter(process.stdout.readline, ''):
                line = line.strip()
                if '[download]' in line and '%' in line:
                    try:
                        # Extract percentage more carefully
                        import re
                        match = re.search(r'(\d+\.\d+)%', line)
                        if match:
                            percent = float(match.group(1))
                            self.after(0, self.update_progress, percent)
                    except (ValueError, AttributeError):
                        pass
                elif line:
                    print(f"yt-dlp: {line}")
            
            process.wait()
            stderr_output = process.stderr.read()

            if process.returncode != 0:
                raise subprocess.CalledProcessError(process.returncode, cmd, stderr=stderr_output)

            print(f"Download completed for: {title}")
            self.after(0, lambda: self.update_status("Download complete"))
            self.after(0, self.update_progress, 100)
            downloaded_path = output_template.replace('%(ext)s', 'webm')
            if not os.path.exists(downloaded_path):
                downloaded_path = ""
            self.after(0, lambda: messagebox.showinfo("Success", f"Downloaded: {title}"))
        except Exception as e:
            print(f"Error during WebM download: {e}")
            if isinstance(e, subprocess.CalledProcessError) and e.stderr:
                print(f"STDERR: {e.stderr}")
            self.after(0, lambda: self.update_status(f"Error: {e}"))
            self.after(0, lambda: messagebox.showerror("Download Failed", f"Failed to download '{title}'.\n\nError: {e}"))
            self.after(0, self.update_progress, 0)

    @log_to_terminal
    def set_master_library(self):
        folder = filedialog.askdirectory(title="Select Master Music Library Folder")
        if folder:
            self.master_lib_path.set(folder)
            print(f"Master library set to: {folder}")
            self.save_config()

    @log_to_terminal
    def set_webm_library(self):
        folder = filedialog.askdirectory(title="Select WebM Output Folder")
        if folder:
            self.webm_lib_path.set(folder)
            print(f"WebM folder set to: {folder}")
            self.save_config()

    @log_to_terminal
    def add_target_folder(self):
        folder = filedialog.askdirectory(title="Select Game Folder")
        if folder:
            self.target_listbox.insert(tk.END, folder)
            print(f"Added target folder: {folder}")
            self.save_config()

    @log_to_terminal
    def remove_target_folder(self):
        selected = self.target_listbox.curselection()
        if selected:
            self.target_listbox.delete(selected)
            print(f"Removed target folder at index: {selected[0]}")
            self.save_config()

    @log_to_terminal
    def sync_library(self):
        master = self.master_lib_path.get()
        if master == "Not Set":
            messagebox.showwarning("No Library", "Please set the Master Music Library first.")
            return
        
        if not self.target_listbox.size():
            messagebox.showinfo("No Sync Targets", "No game folders selected. The installer will continue using the Master Library only.")
            return
        
        print("Starting library sync...")
        self.update_status("Syncing...")
        threading.Thread(target=self.perform_sync, daemon=True).start()

    @log_to_terminal
    def perform_sync(self):
        try:
            master = self.master_lib_path.get()
            targets = self.target_listbox.get(0, tk.END)
            
            if not targets:
                self.after(0, lambda: self.update_status("No sync targets selected"))
                return

            # Counter Logic
            master_mp3s = {f for f in os.listdir(master) if f.lower().endswith('.mp3')}
            total_songs_in_lib = len(master_mp3s)
            links_created = 0
            links_cleaned = 0
            folders_count = len(targets)

            for target in targets:
                if not os.path.exists(target):
                    continue

                # 1. Cleanup Dead Links
                for game_file in os.listdir(target):
                    game_file_path = os.path.join(target, game_file)
                    if os.path.islink(game_file_path) and game_file not in master_mp3s:
                        os.remove(game_file_path)
                        links_cleaned += 1

                # 2. Link New Files
                for mp3 in master_mp3s:
                    src = os.path.join(master, mp3)
                    dst = os.path.join(target, mp3)
                    if not os.path.exists(dst):
                        try:
                            # Catch stale files that aren't symlinks
                            if os.path.lexists(dst): os.remove(dst)
                            os.symlink(src, dst)
                            links_created += 1
                        except Exception as e:
                            print(f"Link Error: {e}")

            # New Stats Message
            stats_msg = (
                f"✅ Sync Successful!\n\n"
                f"🎵 Master Library: {total_songs_in_lib} songs\n"
                f"📂 Game Folders: {folders_count} processed\n"
                f"🔗 New Links Created: {links_created}\n"
                f"🗑️ Dead Links Cleaned: {links_cleaned}\n\n"
                f"Total active links across all games: {total_songs_in_lib * folders_count}"
            )
            
            self.after(0, lambda: messagebox.showinfo("Sync Report", stats_msg))
            self.after(0, lambda: self.update_status("Sync Complete"))
                
        except Exception as e:
            print(f"Critical Sync Error: {e}")
            raise

    @log_to_terminal
    def load_json_playlist(self):
        file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if not file_path:
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                entries = data.get('entries', [])
                
            if not entries:
                messagebox.showwarning("Empty Playlist", "No entries found in JSON.")
                return

            # Run in thread to keep UI responsive
            threading.Thread(target=self.process_json_playlist, args=(entries,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("JSON Error", f"Failed to read playlist: {e}")

    def process_json_playlist(self, entries):
        total = len(entries)
        self.after(0, lambda: self.progress_bar.configure(maximum=total, value=0))

        for i, query in enumerate(entries):
            self.after(0, lambda q=query, count=i+1: self.update_status(f"Processing ({count}/{total}): {q}"))
            
            try:
                # 1. Search for the best match
                results = self.search_youtube(query, max_results=1)
                if not results:
                    print(f"No results for {query}, skipping.")
                    continue
                
                best_match = results[0]
                video_info = self.normalize_search_result(best_match)
                
                # 2. Perform the download (Synchronously within this thread)
                # We use a modified version of your download logic that doesn't spawn a NEW thread
                self.run_download_logic(video_info)
                
                # 3. Update Progress
                self.after(0, lambda v=i+1: self.progress_bar.configure(value=v))
                
            except Exception as e:
                print(f"Error processing '{query}': {e}")
                # We continue to the next item instead of crashing the whole playlist

        self.after(0, lambda: self.update_status("Playlist Install Complete"))
        # Trigger final sync
        self.perform_sync()

    def run_download_logic(self, video_info):
        video_url = video_info.get('url')
        title = video_info.get('title')
        output_dir = self.master_lib_path.get()
        output_template = f'"{os.path.join(output_dir, "%(title)s.%(ext)s")}"'
        
        # USE get_bundle_path to find the bundled yt-dlp.exe
        ytdlp_path = get_bundle_path("yt-dlp.exe")
        ffmpeg_path = get_bundle_path(".") # Folder containing ffmpeg.exe

        cmd = [
            ytdlp_path, 
            '--ffmpeg-location', ffmpeg_path,
            '-x', '--audio-format', 'mp3', '--audio-quality', '320K',
            '--add-metadata', '--print', 'after_move:filepath',
            '-o', output_template, video_url
        ]
        
        # Use shell=True for better EXE compatibility on Windows
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, shell=True)
    def load_config(self):
        config_file = "app_config.json"
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    if config.get('master_library'):
                        self.master_lib_path.set(config['master_library'])
                    if config.get('webm_library'):
                        self.webm_lib_path.set(config['webm_library'])
                    if config.get('target_folders'):
                        for folder in config['target_folders']:
                            self.target_listbox.insert(tk.END, folder)
                print("Configuration loaded from file")
            except Exception as e:
                print(f"Error loading configuration: {e}")

    def save_config(self):
        config = {
            'master_library': self.master_lib_path.get() if self.master_lib_path.get() != "Not Set" else "",
            'webm_library': self.webm_lib_path.get() if self.webm_lib_path.get() != "Not Set" else "",
            'target_folders': list(self.target_listbox.get(0, tk.END))
        }
        try:
            with open('app_config.json', 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print("Configuration saved to file")
        except Exception as e:
            print(f"Error saving configuration: {e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
