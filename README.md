# Music Library & Game Sync Manager

A lightweight Python application to manage a local music library, download songs from YouTube, and synchronize the library with game folders (one copy - access from multiple directories).

## Features

1.  **Search & Browse:**
    *   A search bar to query YouTube for songs.
    *   A list to display search results with Title, Channel, and Thumbnail.
    *   Support URL direct install.

2.  **Smart Download:**
    *   Download selected videos as high-quality MP3 files (320kbps).
    *   Automatically embed the video thumbnail as album art.
    *   Write metadata (Title, Artist) to the MP3 file.
    *   Option to download as a `.webm` video for local playback.

3.  **Library & Multi-Sync:**
    *   Set a "Music Library" folder to store all downloaded music.
    *   Set a "Video Library" folder to store all downloaded webm.
    *   Add multiple target game folders (e.g., for GTA V, Cyberpunk 2077).
    *   A "Sync" button to create symbolic links from the master library to the target folders, ensuring games can access the music without duplicating files.
    *   The application will handle administrative privileges required for creating symlinks on Windows.

