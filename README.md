# Music Library & Game Sync Manager

A lightweight Python application to manage a local music library, download songs from YouTube, and synchronize the library with game folders.

## Features

1.  **Search & Browse:**
    *   A search bar to query YouTube for songs.
    *   A list to display search results with Title, Channel, and Thumbnail.

2.  **Smart Download:**
    *   Download selected videos as high-quality MP3 files (320kbps).
    *   Automatically embed the video thumbnail as album art.
    *   Write metadata (Title, Artist) to the MP3 file.
    *   Option to download as a `.webm` video for local playback.

3.  **Library & Multi-Sync:**
    *   Set a "Master Music Library" folder to store all downloaded music.
    *   Add multiple target game folders (e.g., for GTA V, Cyberpunk 2077).
    *   A "Sync" button to create symbolic links from the master library to the target folders, ensuring games can access the music without duplicating files.
    *   The application will handle administrative privileges required for creating symlinks on Windows.

## Tech Stack

*   **GUI:** Python's built-in `tkinter` library with a modern dark theme.
*   **Downloading:** `yt-dlp` for handling YouTube searches and downloads.
*   **Metadata:** `mutagen` for embedding cover art and tags into MP3 files.
*   **Image Processing:** `Pillow` to handle thumbnail data.

## Development Plan

1.  **Setup & UI Scaffolding:**
    *   Create the main application window with a dark theme.
    *   Build the main layout: search bar, results frame, download options, and sync section.

2.  **YouTube Search Integration:**
    *   Implement the function to call `yt-dlp` with a search query.
    *   Parse the results and display them in the UI, including fetching and showing thumbnails.

3.  **MP3 & WebM Download Logic:**
    *   Create a download manager to handle `yt-dlp` download processes in a separate thread to keep the UI responsive.
    *   Implement the `ffmpeg` conversion process to create 320kbps MP3s.
    *   Use `mutagen` to write the ID3 tags (title, artist, album art) after conversion.
    *   Implement the `.webm` download option.

4.  **Library and Sync Management:**
    *   Implement the UI for setting the master library and adding/removing target sync folders.
    *   Implement the symbolic link creation logic.
    *   Add a check for administrator privileges on Windows and guide the user if needed.

5.  **Final Touches & Packaging:**
    *   Refine the UI/UX.
    *   Add comprehensive error handling (e.g., for network issues, file system errors).
    *   (Optional) Package the application into a standalone executable using PyInstaller.
