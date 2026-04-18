"""
farm/config.py - Constants, vocabulary, and device profiles
"""
import os
import threading

# =================CONFIGURATION=================
PC_SEARCH_COUNT = 55      # Đảm bảo đủ quét 150 điểm (50 searches @ 3pts)
MOBILE_SEARCH_COUNT = 40  # Đảm bảo quét đủ 100 điểm mobile
MAX_WORKERS = 1  # Sequential mode to avoid port/resource conflicts
DRIVER_RETRY_ATTEMPTS = 3
DRIVER_RETRY_DELAY = 2

PROFILE_DIRECTORY = "Default"
LOG_DIR = os.path.join(os.getcwd(), "logs")
SCREENSHOT_DIR = os.path.join(LOG_DIR, "screenshots")

query_gen_lock = threading.Lock()

# =================MASSIVE VOCABULARY=================
VOCAB = {
    "cities_vn": [
        "Hanoi", "Ho Chi Minh City", "Da Nang", "Hai Phong", "Can Tho", "Nha Trang", "Da Lat", "Hue", 
        "Vung Tau", "Quy Nhon", "Phu Quoc", "Sapa", "Ha Long", "Buon Ma Thuot", "Vinh", "Thanh Hoa"
    ],
    "cities_global": [
        "New York", "London", "Paris", "Tokyo", "Seoul", "Beijing", "Shanghai", "Singapore", "Bangkok", 
        "Dubai", "Los Angeles", "San Francisco", "Berlin", "Rome", "Madrid", "Toronto", "Sydney", "Melbourne"
    ],
    "famous_people": [
        "Elon Musk", "Bill Gates", "Jeff Bezos", "Mark Zuckerberg", "Tim Cook", "Satya Nadella", "Sundar Pichai",
        "Taylor Swift", "Justin Bieber", "BTS", "Blackpink", "Son Tung MTP", "Tran Thanh", "Ly Hai",
        "Messi", "Ronaldo", "Mbappe", "Haaland", "LeBron James", "Stephen Curry", "Novak Djokovic",
        "Albert Einstein", "Isaac Newton", "Nikola Tesla", "Stephen Hawking", "Marie Curie", "Leonardo da Vinci"
    ],
    "tech_products": [
        "iPhone 15 Pro Max", "Samsung Galaxy S24 Ultra", "MacBook Air M3", "iPad Pro", "AirPods Pro",
        "Sony WH-1000XM5", "Nintendo Switch 2", "PlayStation 5 Pro", "Xbox Series X", "RTX 5090",
        "Dell XPS 13", "ThinkPad X1 Carbon", "Logitech MX Master 3S", "Keychron Q1", "Kindle Paperwhite"
    ],
    "coding_stack": [
        "Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "Go", "Rust", "Swift", "Kotlin",
        "React", "Vue", "Angular", "Next.js", "Node.js", "Django", "Flask", "Spring Boot",
        "Docker", "Kubernetes", "AWS", "Azure", "Google Cloud", "TensorFlow", "PyTorch", "Selenium"
    ],
    "movies_types": [
        "Action movies", "Comedy movies", "Horror movies", "Sci-fi movies", "Romance movies", "Anime",
        "Documentaries", "Korean dramas", "Marvel movies", "DC movies", "Oscar winners"
    ],
    "games": [
        "League of Legends", "Dota 2", "Valorant", "CS2", "Minecraft", "Roblox", "GTA VI", 
        "Elden Ring", "Cyberpunk 2077", "Genshin Impact", "Honkai Star Rail", "Palworld", "PUBG Mobile"
    ],
    "food_vn": [
        "Pho bo", "Banh mi", "Bun cha", "Bun bo Hue", "Com tam", "Banh xeo", "Goi cuon", "Ca phe trung",
        "Nem nuong", "Mi quang", "Cao lau", "Cha ca La Vong", "Banh cuon", "Xoi xeo"
    ],
    "food_global": [
        "Pizza", "Burger", "Sushi", "Ramen", "Pasta", "Steak", "Tacos", "Dim sum", "Kimchi", "Curry",
        "Fish and Chips", "Croissant", "Tiramisu", "Bubble tea"
    ],
    "animals": [
        "Capybara", "Golden Retriever", "Corgi", "British Shorthair", "Red Panda", "Penguin", "Lion", 
        "Tiger", "Elephant", "Whale", "Dolphin", "Eagle", "Owl", "Sloth", "Otter", "Hamster"
    ],
    "nature": [
        "Mount Everest", "Amazon Rainforest", "Sahara Desert", "Grand Canyon", "Great Barrier Reef", 
        "Northern Lights", "Niagara Falls", "Ha Long Bay", "Son Doong Cave", "Phu Quoc beaches"
    ],
    "finance": [
        "Bitcoin price", "Ethereum price", "Stock market today", "Gold price", "USD to VND", "EUR to USD",
        "Inflation rate", "GDP growth", "Interest rates", "Real estate market", "Passive income ideas",
        "How to invest in stocks", "Best credit cards 2026", "Crypto news today", "Federal Reserve interest rate"
    ],
    "health": [
        "benefits of yoga", "meditation techniques", "keto diet", "intermittent fasting", "best exercises for abs",
        "how to sleep better", "vitamin D sources", "drink water reminder", "mental health tips", "stress relief",
        "home workout routine", "calories in an apple", "high protein breakfast", "how to cure a cold",
        "signs of dehydration", "benefits of green tea", "low carb snacks"
    ],
    "cars": [
        "Tesla Model 3", "Toyota Camry", "Ford Mustang", "Porsche 911", "Honda Civic", "BMW M3", 
        "Audi R8", "Mercedes S-Class", "VinFast VF8", "Hyundai Tucson", "Kia Sorento", "Mazda CX-5"
    ],
    "hobbies": [
        "photography basics", "how to play guitar", "gardening tips", "watercolor painting", "knitting patterns",
        "woodworking projects", "home brewing beer", "baking sourdough bread", "calligraphy for beginners",
        "digital art tutorial", "origami step by step", "film photography"
    ],
    "books": [
        "Atomic Habits", "Harry Potter", "Lord of the Rings", "1984 George Orwell", "The Great Gatsby",
        "Rich Dad Poor Dad", "Thinking Fast and Slow", "Sapiens", "Dune", "To Kill a Mockingbird",
        "best self help books", "top sci-fi novels 2025"
    ],
    "questions_prefix": [
        "How to", "What is", "Why does", "When is", "Best way to", "History of", "Meaning of", "Benefits of",
        "Top 10", "Review of", "Price of", "Difference between", "Guide to", "Where to buy", "Is it safe to",
        "How much does", "Who invented", "Symptoms of", "Examples of"
    ],
    "modifiers": [
        "2025", "2026", "news", "wiki", "images", "wallpaper", "reddit", "youtube", "tutorial", "for beginners",
        "near me", "recipes", "deals", "specs", "rumors", "vs", "review", "history", "guide", "explained",
        "pdf", "download", "alternatives", "examples", "price", "meaning"
    ]
}

# ============== MOBILE DEVICE PROFILES ==============
MOBILE_DEVICES = {
    'pixel_7': {
        'width': 412, 'height': 915, 'deviceScaleFactor': 2.625, 'mobile': True,
        'screenWidth': 1080, 'screenHeight': 2400,
        'ua': 'Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{VERSION} Mobile Safari/537.36 EdgA/{VERSION}'
    },
    'iphone_14': {
        'width': 390, 'height': 844, 'deviceScaleFactor': 3, 'mobile': True,
        'screenWidth': 1170, 'screenHeight': 2532,
        'ua': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 EdgiOS/{VERSION} Mobile/15E148 Safari/604.1'
    },
    'samsung_s23': {
        'width': 360, 'height': 780, 'deviceScaleFactor': 3, 'mobile': True,
        'screenWidth': 1080, 'screenHeight': 2340,
        'ua': 'Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{VERSION} Mobile Safari/537.36 EdgA/{VERSION}'
    }
}
