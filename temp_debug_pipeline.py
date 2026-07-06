import os
import sys
import shutil
import gdown

sys.path.append("src")
import downloader
import audio_processor
import config

temp_dir = "temp_debug_pipeline"
shutil.rmtree(temp_dir, ignore_errors=True)
os.makedirs(temp_dir, exist_ok=True)

url = "https://drive.google.com/drive/folders/1sG_6HQtBIqPwz6Hl2Hyn4fTeXy_UU4BY"
download_zip = os.path.join(temp_dir, "download.zip")
extracted_dir = os.path.join(temp_dir, "extracted")

print("Downloading folder...")
gdown.download_folder(url, output=download_zip, quiet=False)

print("\nFiles in download_zip directory:")
if os.path.isdir(download_zip):
    for f in os.listdir(download_zip):
        print(" -", f)

print("\nUnzipping...")
audio_processor.unzip_pack(download_zip, extracted_dir)

print("\nFiles in extracted_dir:")
for r, d, files in os.walk(extracted_dir):
    for f in files:
        print(" -", os.path.relpath(os.path.join(r, f), extracted_dir))

print("\nProcessing and renaming...")
cats, all_files = audio_processor.process_and_rename_kit(
    extracted_dir, rebranded_name="TestLink", genre="Trap", ai_naming=False
)

print("\nRenamed files:")
for f in all_files:
    print(" -", f)

# Cleanup
shutil.rmtree(temp_dir, ignore_errors=True)
