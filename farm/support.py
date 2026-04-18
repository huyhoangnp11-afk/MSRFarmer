import random
import datetime
import webbrowser

SHOPEE_LINKS = [
    "https://s.shopee.vn/6L0ZozZ82r", "https://s.shopee.vn/6Ah9cgZlNq", "https://s.shopee.vn/60NjQNaOip",
    "https://s.shopee.vn/5q4JE4b23o", "https://s.shopee.vn/5fkt1lbfOn", "https://s.shopee.vn/5VRSpScIjm",
    "https://s.shopee.vn/5L82d9cw4l", "https://s.shopee.vn/AUq8meJGam", "https://s.shopee.vn/AKWiaLJtvl",
    "https://s.shopee.vn/AADIO2KXGk", "https://s.shopee.vn/9ztsBjLAbj", "https://s.shopee.vn/9paRzQLnwi",
    "https://s.shopee.vn/9fH1n7MRHh", "https://s.shopee.vn/9UxbaoN4cg", "https://s.shopee.vn/9KeBOVNhxf",
    "https://s.shopee.vn/9AKlCCOLIe", "https://s.shopee.vn/901KztOydd", "https://s.shopee.vn/8phunaPbyc",
    "https://s.shopee.vn/8fOUbHQFJb", "https://s.shopee.vn/8V54OyQsea", "https://s.shopee.vn/8KleCfRVzZ",
    "https://s.shopee.vn/8ASE0MS9KY", "https://s.shopee.vn/808no3SmfX", "https://s.shopee.vn/2VnrFwnipU",
    "https://s.shopee.vn/2LUR3doMAT", "https://s.shopee.vn/2BB0rKozVS", "https://s.shopee.vn/20raf1pcqR",
    "https://s.shopee.vn/1qYASiqGBQ", "https://s.shopee.vn/1gEkGPqtWP", "https://s.shopee.vn/1VvK46rWrO",
    "https://s.shopee.vn/1LbtrnsACN", "https://s.shopee.vn/1BITfUsnXM", "https://s.shopee.vn/10z3TBtQsL",
    "https://s.shopee.vn/qfdGsu4DK", "https://s.shopee.vn/gMD4ZuhYJ", "https://s.shopee.vn/W2msGvKtI",
    "https://s.shopee.vn/LjMfxvyEH", "https://s.shopee.vn/BPwTewbZG", "https://s.shopee.vn/16WHLxEuF",
    "https://s.shopee.vn/5AocQqdZQG", "https://s.shopee.vn/50VCEXeClF", "https://s.shopee.vn/4qBm2Eeq6E",
    "https://s.shopee.vn/4fsLpvfTRD", "https://s.shopee.vn/4VYvdcg6mC", "https://s.shopee.vn/4LFVRJgk7B",
    "https://s.shopee.vn/4Aw5F0hNSA", "https://s.shopee.vn/40cf2hi0n9", "https://s.shopee.vn/3qJEqOie88",
    "https://s.shopee.vn/3fzoe5jHT7", "https://s.shopee.vn/3VgORmjuo6", "https://s.shopee.vn/3LMyFTkY95",
    "https://s.shopee.vn/3B3Y3AlBU4", "https://s.shopee.vn/30k7qrlop3", "https://s.shopee.vn/2qQheYmSA2",
    "https://s.shopee.vn/2g7HSFn5V1", "https://s.shopee.vn/7fVxPRU3M0", "https://s.shopee.vn/7ppNbkTQ13",
    "https://s.shopee.vn/7Kt70pVK1y", "https://s.shopee.vn/7VCXD8Ugh1", "https://s.shopee.vn/70GGcDWahw",
    "https://s.shopee.vn/7AZgoWVxMz", "https://s.shopee.vn/6fdQDbXrNu", "https://s.shopee.vn/6pwqPuXE2x",
    "https://s.shopee.vn/6L0ZozZ83s", "https://s.shopee.vn/6VK01IYUiv", "https://s.shopee.vn/60NjQNaOjq",
    "https://s.shopee.vn/6Ah9cgZlOt", "https://s.shopee.vn/5fkt1lbfPo", "https://s.shopee.vn/5q4JE4b24p",
    "https://s.shopee.vn/5fkt1lbfQp", "https://s.shopee.vn/5VRSpScIkp", "https://s.shopee.vn/5L82d9cw5m"
]

GREETINGS = [
    "Chúc bạn một ngày mới thật suôn sẻ và gặp nhiều may mắn nhé! (^.^) ✨",
    "Chào buổi sáng! Chúc bạn mọi điều thuận lợi sẽ đến trong hôm nay :3 :3 🍀",
    "Ngày mới tốt lành! Hy vọng bạn sẽ có một ngày làm việc thật hiệu quả (◕‿◕) ☀️",
    "Chúc bạn luôn dồi dào sức khỏe và tràn đầy năng lượng tích cực nhé (づ｡◕‿‿◕｡)づ 💪",
    "Giữ gìn sức khỏe nhé! Chúc bạn một ngày mới thật bình an và vui vẻ (^.^) 🌈",
    "Mọi điều tốt đẹp nhất và sức khỏe sẽ luôn ở bên bạn! (>‿<) 🎈"
]

from .ota import get_live_ota_config

def get_random_support_link():
    # Kéo link từ OTA (nếu có trên Pastebin)
    ota_config = get_live_ota_config()
    live_links = ota_config.get("affiliate_links", [])
    
    # Nếu trên mạng có Link, dùng Link mạng. Nếu mạng sập hoặc trống, dùng mảng tĩnh bên dưới.
    active_links = live_links if live_links else SHOPEE_LINKS
    
    return random.choice(active_links)

def get_random_greeting():
    return random.choice(GREETINGS)

def open_support():
    url = get_random_support_link()
    webbrowser.open(url)
