import csv
import re

csv_file = r'C:\Users\HUYHOANG\Downloads\Lấy link sản phẩm hàng loạt20260417183240-1a251be83e6e4e689283b77297ce5e7a.csv'
links = []
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        link = row.get('Link ưu đãi', '').strip()
        if link and link.startswith('http'):
            links.append(f'            "{link}",')

# Build the block
links_block = "\n".join(links)
links_block = links_block.rstrip(',') # remove last comma

target_file = r'd:\sao lưu E\MSrequat\launcher_gui.py'
with open(target_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace block
original = """        shopee_links = [
            "https://shopee.vn/universal-link/...",  # Link 1
            "https://shopee.vn/universal-link/...",  # Link 2
            "https://shopee.vn/universal-link/..."   # Link 3
        ]"""

new_content = f"""        shopee_links = [
{links_block}
        ]"""

content = content.replace(original, new_content)

with open(target_file, 'w', encoding='utf-8') as f:
    f.write(content)

print("SUCCESSFULLY INJECTED", len(links), "LINKS!")
