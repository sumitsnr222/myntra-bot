import shutil, os

src = r"C:\Users\DELL\.gemini\antigravity-ide\scratch\myntra-bot"
dst = r"C:\Users\DELL\.gemini\antigravity-ide\scratch\myntra-bot-v2"

# Create zip excluding data dir, __pycache__, test files
shutil.make_archive(dst, 'zip', root_dir=os.path.dirname(src), base_dir=os.path.basename(src))
print(f"ZIP created: {dst}.zip")
print(f"Size: {os.path.getsize(dst + '.zip') / 1024:.1f} KB")
