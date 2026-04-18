"""Dump full DOM structure of rewards page to find correct selectors"""
import os, sys, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from farm.driver import setup_driver

local_app = os.environ.get('LOCALAPPDATA', '')
profile_path = os.path.join(local_app, 'Microsoft', 'Edge', 'User Data', 'Profile 1')

driver = setup_driver(profile_path, is_mobile=False, headless=False)
if not driver:
    print("FAILED to create driver")
    sys.exit(1)

driver.get("https://rewards.bing.com/")
time.sleep(10)

# Dump all clickable-looking elements with their tag, class, text
js = """
const all = document.querySelectorAll('*');
const results = [];
all.forEach(el => {
    const rect = el.getBoundingClientRect();
    if (rect.width > 50 && rect.height > 30 && rect.top > 0 && rect.top < 3000) {
        let text = (el.innerText || '').replace(/\\n/g, ' | ').trim().substring(0, 120);
        let tag = el.tagName.toLowerCase();
        let cls = (el.className || '').toString().substring(0, 80);
        let href = el.getAttribute('href') || '';
        let role = el.getAttribute('role') || '';
        let dataAttrs = [];
        for(let attr of el.attributes) {
            if(attr.name.startsWith('data-')) dataAttrs.push(attr.name + '=' + attr.value.substring(0,30));
        }
        // Only keep interesting elements (not pure divs/spans with no interaction)
        if (text.length > 5 && (
            tag === 'a' || tag === 'button' || role === 'button' || 
            tag.includes('-') || cls.includes('card') || cls.includes('Card') ||
            cls.includes('task') || cls.includes('Task') || cls.includes('promo') ||
            cls.includes('daily') || cls.includes('Daily') || cls.includes('activity') ||
            cls.includes('earn') || cls.includes('reward') || cls.includes('streak') ||
            href || dataAttrs.length > 0
        )) {
            results.push({
                tag: tag,
                cls: cls.substring(0, 60),
                text: text.substring(0, 100),
                href: href.substring(0, 60),
                role: role,
                data: dataAttrs.join('; ').substring(0, 100),
                top: Math.round(rect.top),
                w: Math.round(rect.width),
                h: Math.round(rect.height)
            });
        }
    }
});
return JSON.stringify(results);
"""

data = json.loads(driver.execute_script(js))
print(f"Found {len(data)} interesting elements:\n")

for i, el in enumerate(data):
    print(f"[{i}] <{el['tag']}> cls=\"{el['cls']}\"")
    print(f"     text: {el['text']}")
    if el['href']: print(f"     href: {el['href']}")
    if el['data']: print(f"     data: {el['data']}")
    if el['role']: print(f"     role: {el['role']}")
    print(f"     pos: top={el['top']} size={el['w']}x{el['h']}")
    print()

# Also dump all custom elements (web components)
js2 = """
const customs = new Set();
document.querySelectorAll('*').forEach(el => {
    if(el.tagName.includes('-')) customs.add(el.tagName.toLowerCase());
});
return JSON.stringify([...customs]);
"""
customs = json.loads(driver.execute_script(js2))
print(f"\nCustom web components found: {customs}")

# Dump outer HTML of the main content area
js3 = """
let main = document.querySelector('main') || document.querySelector('[role="main"]') || document.querySelector('.content') || document.body;
return main.outerHTML.substring(0, 8000);
"""
html_snippet = driver.execute_script(js3)

with open('logs/dom_dump.html', 'w', encoding='utf-8') as f:
    f.write(html_snippet)
print(f"\nMain HTML dumped to logs/dom_dump.html ({len(html_snippet)} chars)")

driver.quit()
print("\nDone!")
