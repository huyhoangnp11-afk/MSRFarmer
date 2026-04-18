"""
farm/query.py - Query generation for search farming
"""
import random
import logging
import threading
import json
from datetime import datetime
from .config import VOCAB, query_gen_lock


class QueryGenerator:
    """Thread-safe query generator với global lock protection + Bing Suggest"""
    def __init__(self):
        self.history = set()
        self.chain_queue = []
        self._suggest_cache = []
        self._suggest_seeds = [
            "how to", "best", "why", "what is", "top 10",
            "latest", "new", "price of", "review", "where to"
        ]
    
    def reset_history(self):
        """Reset used query history - call between profiles to avoid pool exhaustion."""
        self.history.clear()
        self.chain_queue.clear()
        self._suggest_cache.clear()
        logging.info("[QUERY] History reset. Pool sẵ được tái sử dụng.")

    def generate(self):
        """Thread-safe generate với global lock"""
        with query_gen_lock:
            return self._generate_unsafe()
    
    def _generate_unsafe(self):
        """Internal generate (không thread-safe, gọi qua generate())"""
        if self.chain_queue:
            q = self.chain_queue.pop(0)
            if q not in self.history:
                self.history.add(q)
                return q
            
        # 45% chance: use Bing Suggest trending query (most natural)
        if random.random() < 0.45:
            q = self._get_suggest_query()
            if q and q not in self.history:
                self.history.add(q)
                return q

        if random.random() < 0.4:
            self._create_chain_queries()
            if self.chain_queue:
                return self._generate_unsafe()

        for _ in range(50): 
            q = self._create_random_query()
            if q not in self.history:
                self.history.add(q)
                return q
                
        # If all 50 tries are in history, just append a random natural modifier instead of a number
        base = self._create_random_query()
        return f"{base} {random.choice(['review', 'tips', 'guide', 'explained', 'examples'])}"

    def _get_suggest_query(self):
        """Fetch query from Bing Suggest API (cached)."""
        if not self._suggest_cache:
            self._fetch_bing_suggestions()
        if self._suggest_cache:
            return self._suggest_cache.pop(0)
        return None

    def _fetch_bing_suggestions(self):
        """Fetch trending suggestions from Bing autocomplete API."""
        try:
            import urllib.request
            import urllib.parse
            seed = random.choice(self._suggest_seeds)
            topic = random.choice(
                VOCAB.get("tech_products", []) + VOCAB.get("famous_people", []) + 
                VOCAB.get("cities_global", []) + VOCAB.get("animals", [])
            )
            query = f"{seed} {topic}"
            url = f"https://api.bing.com/osjson.aspx?query={urllib.parse.quote(query)}"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp = urllib.request.urlopen(req, timeout=3)
            data = json.loads(resp.read().decode('utf-8'))
            
            if len(data) >= 2 and isinstance(data[1], list):
                suggestions = [s for s in data[1] if len(s) > 5 and s != query]
                random.shuffle(suggestions)
                self._suggest_cache.extend(suggestions[:8])
                logging.info(f"   [SUGGEST] Fetched {len(suggestions[:8])} trending queries from Bing")
        except Exception as e:
            logging.debug(f"Bing Suggest unavailable: {e}")

    def _create_chain_queries(self):
        chain_len = random.randint(3, 7)
        topic = random.choice(["travel", "tech", "celeb", "game", "cooking", "books", "cars", "hobbies"])
        
        if topic == "travel":
            city = random.choice(VOCAB["cities_vn"] + VOCAB["cities_global"])
            img_syn = random.choice(["images of", "pictures of", "beautiful photos of", "scenery in"])
            tour_syn = random.choice(["tourist attractions in", "places to visit in", "things to do in", "must see in"])
            hotel_syn = random.choice(["cheap hotels in", "best places to stay in", "luxury resorts in"])
            pool = [
                f"{img_syn} {city}", f"weather in {city} today",
                f"{tour_syn} {city}", f"{hotel_syn} {city}", 
                f"flights to {city}", f"{city} nightlife", f"{city} street food",
                f"best time to visit {city}", f"travel guide for {city}", f"cost of living in {city}"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Du lịch: {city} ({chain_len} queries)")

        elif topic == "tech":
            product = random.choice(VOCAB["tech_products"])
            buy_syn = random.choice(["price of", "cost of", "where to buy", "best deals for"])
            rev_syn = random.choice(["review", "unboxing", "hands on", "first impressions"])
            pool = [
                f"{product} official release date", f"{product} full specifications",
                f"{product} vs {random.choice(VOCAB['tech_products'])}", f"{product} {rev_syn} video", 
                f"{buy_syn} {product} in Vietnam", f"{product} pros and cons",
                f"is {product} worth buying", f"{product} user manual pdf", f"{product} hidden features"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Công nghệ: {product} ({chain_len} queries)")
            
        elif topic == "celeb":
            person = random.choice(VOCAB["famous_people"])
            news_syn = random.choice(["latest news", "recent updates", "scandals", "interviews"])
            wealth_syn = random.choice(["net worth", "salary", "how rich is", "total assets of"])
            pool = [
                f"who is {person}", f"{person} {news_syn}", 
                f"{person} {wealth_syn} {datetime.now().year}",
                f"{person} family and children", f"{person} instagram official",
                f"{person} age and birthday", f"{person} quotes about success",
                f"{person} awards and achievements", f"books recommended by {person}"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Sao: {person} ({chain_len} queries)")

        elif topic == "game":
            game = random.choice(VOCAB["games"])
            sys_syn = random.choice(["system requirements", "pc specs for", "can my pc run"])
            tips_syn = random.choice(["beginner guide", "tips and tricks", "how to play", "starter guide"])
            pool = [
                f"{game} download pc", f"{game} {sys_syn}", 
                f"{game} {tips_syn}", f"{game} top tier characters", 
                f"{game} latest patch notes", f"{game} tier list",
                f"{game} best settings", f"{game} speedrun world record", f"{game} easter eggs"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Game: {game} ({chain_len} queries)")
            
        elif topic == "cooking":
            dish = random.choice(VOCAB["food_vn"] + VOCAB["food_global"])
            cook_syn = random.choice(["how to cook", "how to make", "step by step recipe for"])
            pool = [
                f"{cook_syn} {dish} at home", f"best {dish} recipe simple",
                f"{dish} calories", f"history of {dish}", f"ingredients for {dish}",
                f"{dish} variations", f"easy {dish} for beginners",
                f"{dish} restaurant near me", f"is {dish} healthy", f"vegan alternative for {dish}"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Nấu ăn: {dish} ({chain_len} queries)")

        elif topic == "books":
            book = random.choice(VOCAB["books"])
            summ_syn = random.choice(["summary", "plot explained", "chapter 1 summary"])
            pool = [
                f"{book} {summ_syn}", f"{book} main characters",
                f"{book} author biography", f"books similar to {book}",
                f"{book} pdf download", f"{book} quotes",
                f"{book} review {datetime.now().year}", f"is {book} worth reading"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Sách: {book} ({chain_len} queries)")

        elif topic == "cars":
            car = random.choice(VOCAB["cars"])
            price_syn = random.choice(["price of", "msrp of", "how much is", "leasing cost of"])
            pool = [
                f"{car} review", f"{car} interior features",
                f"{car} vs {random.choice(VOCAB['cars'])}", f"{price_syn} {car}",
                f"{car} top speed", f"{car} fuel economy mpg",
                f"common problems with {car}", f"{car} modified custom"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Xe: {car} ({chain_len} queries)")

        elif topic == "hobbies":
            hobby = random.choice(VOCAB["hobbies"])
            pool = [
                f"{hobby}", f"how to start {hobby}",
                f"{hobby} tools needed", f"{hobby} course online",
                f"benefits of {hobby}", f"is {hobby} expensive",
                f"{hobby} community forums", f"{hobby} beginner mistakes"
            ]
            random.shuffle(pool)
            self.chain_queue.extend(pool[:chain_len])
            logging.info(f"   [SMART CHAIN] Sở thích: {hobby} ({chain_len} queries)")

    def _create_random_query(self):
        strategy = random.choices(
            ["travel", "tech", "coding", "food", "celeb", "finance", "question", "compare", "local",
             "health", "science", "movies", "sports", "education", "books", "cars", "hobbies", "crossover"],
            weights=[8, 8, 8, 8, 8, 6, 8, 6, 4, 6, 6, 4, 4, 4, 4, 4, 4, 4]
        )[0]

        if strategy == "travel":
            city = random.choice(VOCAB["cities_vn"] + VOCAB["cities_global"])
            action = random.choice(["hotels in", "flights to", "weather in", "tourist attractions around", "map of", "food in", "history of"])
            return f"{action} {city}"
        elif strategy == "tech":
            product = random.choice(VOCAB["tech_products"])
            suffix = random.choice(VOCAB["modifiers"])
            return f"{product} {suffix}"
        elif strategy == "coding":
            stack = random.choice(VOCAB["coding_stack"])
            suffix = random.choice(["tutorial", "interview questions", "documentation", "error handling", "course", "best practices", "jobs remote"])
            return f"{stack} {suffix}"
        elif strategy == "food":
            dish = random.choice(VOCAB["food_vn"] + VOCAB["food_global"])
            suffix = random.choice(["recipe", "calories", "near me", "history", "ingredients", "best restaurant", "how to cook"])
            return f"{dish} {suffix}"
        elif strategy == "celeb":
            person = random.choice(VOCAB["famous_people"])
            suffix = random.choice(["net worth", "news", "family", "height", "quotes", "biography", "latest song", "movies", "house"])
            return f"{person} {suffix}"
        elif strategy == "finance":
            return random.choice(VOCAB["finance"])
        elif strategy == "question":
            prefix = random.choice(VOCAB["questions_prefix"])
            topic = random.choice(VOCAB["animals"] + VOCAB["nature"] + VOCAB.get("cars", []) + ["AI", "Blockchain", "Climate change", "Space exploration"])
            if prefix == "Difference between":
                return f"{prefix} {topic} and {random.choice(VOCAB['animals'])}"
            return f"{prefix} {topic}"
        elif strategy == "compare":
            cat = random.choice(["tech_products", "games", "cars", "cities_global"])
            item1 = random.choice(VOCAB[cat])
            item2 = random.choice(VOCAB[cat])
            while item1 == item2:
                item2 = random.choice(VOCAB[cat])
            return f"{item1} vs {item2}"
        elif strategy == "local":
            service = random.choice(["Coffee shop", "Gym", "Cinema", "Pharmacy", "ATM", "Gas station", "Supermarket", "Library", "Park"])
            return f"{service} near me"
        elif strategy == "health":
            return random.choice(VOCAB["health"])
        elif strategy == "science":
            topic = random.choice(["James Webb telescope", "Mars exploration", "quantum computing",
                "climate change solutions", "renewable energy", "DNA editing CRISPR",
                "black holes explained", "ocean exploration", "electric vehicles",
                "artificial intelligence future", "5G technology", "nuclear fusion"])
            return f"{topic} latest news" if random.random() < 0.3 else topic
        elif strategy == "movies":
            topic = random.choice(["best movies", "Netflix top shows", "Marvel upcoming movies",
                "anime recommendations", "Oscar winners", "horror movies",
                "comedy movies", "Korean drama", "Disney Plus new releases",
                "action movies", "documentary recommendations", "movie trailers"])
            year = datetime.now().year
            return f"{topic} {year}"
        elif strategy == "sports":
            topic = random.choice(["Premier League standings", "NBA scores today", "UFC results",
                "Champions League", "Formula 1 race", "tennis rankings",
                "World Cup", "Olympic games", "boxing results",
                "golf tournament", "swimming records", "esports tournament"])
            return topic
        elif strategy == "education":
            topic = random.choice(["learn Python programming", "free online courses", "study tips",
                "best universities", "scholarship applications", "language learning apps",
                "math practice online", "science experiments for kids", "history facts",
                "coding bootcamp", "online degree programs", "exam preparation"])
            return topic
        elif strategy == "books":
            book = random.choice(VOCAB["books"])
            suffix = random.choice(["summary", "audiobook free", "pdf download", "author", "quotes", "review"])
            return f"{book} {suffix}"
        elif strategy == "cars":
            car = random.choice(VOCAB["cars"])
            suffix = random.choice(["price", "review", "interior", "specs", "top speed", "fuel economy"])
            return f"{car} {suffix}"
        elif strategy == "hobbies":
            hobby = random.choice(VOCAB["hobbies"])
            return f"{hobby} for beginners" if random.random() < 0.5 else hobby
        elif strategy == "crossover":
            person = random.choice(VOCAB["famous_people"])
            product = random.choice(VOCAB["tech_products"] + VOCAB["cars"])
            return f"Does {person} use {product}"

        return f"Microsoft Rewards tips {datetime.now().year}"


query_gen = QueryGenerator()
