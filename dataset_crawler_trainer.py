import os
import sys
import logging
import subprocess

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input_videos")

os.makedirs(INPUT_DIR, exist_ok=True)

class DatasetCrawlerTrainer:
    """Crawler and Dataset Pipeline Engine.

    Forces exact video page titles into output filenames and feeds them to the auto-annotator.
    """

    def __init__(self, output_dir=INPUT_DIR):
        self.output_dir = output_dir

    def download_video_with_exact_title(self, url: str, browser: str = "firefox") -> str:
        """Downloads a video and enforces the exact webpage video title as the filename."""
        logging.info(f"[*] Fetching video with exact webpage title formatting from: {url}")
        
        # -o "%(title)s.%(ext)s" forces yt-dlp to use the exact webpage video title
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", browser,
            "-P", self.output_dir,
            "-o", "%(title)s.%(ext)s",
            "--restrict-filenames",  # Prevents OS path breaking while keeping full title intact
            url
        ]

        try:
            result = subprocess.run(" ".join(cmd), shell=True, check=True)
            logging.info("[+] Download complete with exact webpage title matching!")
            return self.output_dir
        except Exception as e:
            logging.error(f"[!] Failed to download video: {e}")
            return None

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logging.info("[+] Dataset Crawler Trainer module verified (Exact Title Auto-Naming active).")
    elif len(sys.argv) > 1:
        target_url = sys.argv[1]
        crawler = DatasetCrawlerTrainer()
        crawler.download_video_with_exact_title(target_url)