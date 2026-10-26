import csv
import math
import os
import random
from datetime import datetime, timedelta, date, time

SEED = 2026
DAYS_OF_HISTORY = 180
NUM_CUSTOMERS = 1500
NUM_RESTAURANTS = 120
NUM_PARTNERS = 150
NUM_ORDERS = 15000

LOCALITIES = [
    ("Andheri West", 19.1364, 72.8296),
    ("Andheri East", 19.1136, 72.8697),
    ("Bandra West", 19.0596, 72.8295),
    ("Khar", 19.0710, 72.8360),
    ("Santacruz", 19.0810, 72.8410),
    ("Vile Parle", 19.0990, 72.8490),
    ("Juhu", 19.1075, 72.8263),
    ("Goregaon", 19.1663, 72.8526),
    ("Malad West", 19.1872, 72.8484),
    ("Borivali", 19.2307, 72.8567),
    ("Powai", 19.1176, 72.9060),
    ("Kanjurmarg", 19.1290, 72.9330),
    ("Vikhroli", 19.1110, 72.9280),
    ("Bhandup", 19.1440, 72.9370),
    ("Mulund", 19.1726, 72.9425),
    ("Ghatkopar", 19.0860, 72.9081),
    ("Kurla", 19.0726, 72.8845),
    ("Chembur", 19.0522, 72.9005),
    ("Sion", 19.0390, 72.8619),
    ("Matunga", 19.0270, 72.8570),
    ("Dadar", 19.0178, 72.8478),
    ("Worli", 19.0176, 72.8150),
    ("Lower Parel", 18.9950, 72.8300),
    ("Fort", 18.9338, 72.8356),
    ("Colaba", 18.9067, 72.8147),
]

STREETS = ["SV Road", "LBS Marg", "Link Road", "Hill Road", "Station Road", "MG Road", "Linking Road",
           "Carter Road", "JP Road", "Tilak Road", "Gandhi Nagar", "Nehru Road", "Ambedkar Chowk",
           "Shivaji Path", "Hiranandani Gardens", "Main Market", "College Lane", "Mahakali Caves Road"]

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Arjun", "Reyansh", "Sai", "Krishna", "Ishaan", "Rohan", "Kabir",
               "Ananya", "Diya", "Aadhya", "Saanvi", "Pari", "Myra", "Sara", "Ira", "Kiara", "Riya",
               "Rahul", "Neha", "Pooja", "Amit", "Sneha", "Vikram", "Priya", "Karan", "Meera", "Yash",
               "Tanvi", "Siddharth", "Nikita", "Omkar", "Shruti", "Harsh", "Zara", "Ayaan", "Fatima", "Imran",
               "Sana", "Farhan", "Aisha", "Dev", "Nisha", "Tejas", "Gauri", "Pranav", "Ritika", "Manish"]

LAST_NAMES = ["Sharma", "Patil", "Shetty", "Iyer", "Nair", "Desai", "Mehta", "Shah", "Kulkarni", "Joshi",
              "Gupta", "Khan", "Shaikh", "Fernandes", "D'Souza", "Rao", "Reddy", "Pillai", "Jain", "Bhatt",
              "More", "Pawar", "Naik", "Kapoor", "Malhotra", "Chopra", "Banerjee", "Das", "Menon", "Gaikwad"]

CUISINES = {
    "North Indian": {
        "words": (["Punjab", "Dilli", "Amritsari", "Lahori", "Pind", "Dhaba"], ["Tadka", "Darbar", "Rasoi", "Junction", "Zaika", "Kitchen"]),
        "cost": (400, 900),
        "prep": (15, 25),
        "menu": [("Paneer Butter Masala", "Main Course", 260, True), ("Dal Makhani", "Main Course", 220, True),
                 ("Butter Chicken", "Main Course", 340, False), ("Chole Bhature", "Main Course", 180, True),
                 ("Butter Naan", "Breads", 50, True), ("Tandoori Roti", "Breads", 30, True),
                 ("Chicken Tikka", "Starters", 300, False), ("Paneer Tikka", "Starters", 260, True),
                 ("Jeera Rice", "Rice", 160, True), ("Gulab Jamun", "Desserts", 90, True),
                 ("Sweet Lassi", "Beverages", 90, True)],
    },
    "South Indian": {
        "words": (["Udupi", "Madras", "Mysore", "Malgudi", "Anand", "Sagar"], ["Bhavan", "Cafe", "Tiffins", "Vihar", "Mess", "Corner"]),
        "cost": (200, 450),
        "prep": (8, 15),
        "menu": [("Masala Dosa", "Dosa", 120, True), ("Mysore Masala Dosa", "Dosa", 140, True),
                 ("Idli Sambar", "Breakfast", 80, True), ("Medu Vada", "Breakfast", 80, True),
                 ("Rava Uttapam", "Dosa", 130, True), ("Pongal", "Breakfast", 110, True),
                 ("Lemon Rice", "Rice", 120, True), ("Filter Coffee", "Beverages", 50, True),
                 ("Curd Rice", "Rice", 110, True)],
    },
    "Chinese": {
        "words": (["Golden", "Red", "Dragon", "Lucky", "Jade", "Mainland"], ["Wok", "Bowl", "Lantern", "Express", "House", "Garden"]),
        "cost": (350, 800),
        "prep": (12, 20),
        "menu": [("Veg Hakka Noodles", "Noodles", 200, True), ("Chicken Hakka Noodles", "Noodles", 240, False),
                 ("Veg Manchurian", "Starters", 210, True), ("Chilli Chicken", "Starters", 270, False),
                 ("Schezwan Fried Rice", "Rice", 220, True), ("Chicken Fried Rice", "Rice", 250, False),
                 ("Hot and Sour Soup", "Soups", 150, True), ("Spring Rolls", "Starters", 180, True),
                 ("Dim Sum Basket", "Starters", 280, False)],
    },
    "Italian": {
        "words": (["Bella", "La", "Via", "Little", "Casa", "Trattoria"], ["Italia", "Roma", "Napoli", "Forno", "Piazza", "Cucina"]),
        "cost": (700, 1600),
        "prep": (15, 25),
        "menu": [("Margherita Pizza", "Pizza", 350, True), ("Farmhouse Pizza", "Pizza", 420, True),
                 ("Pepperoni Pizza", "Pizza", 480, False), ("Penne Arrabbiata", "Pasta", 360, True),
                 ("Spaghetti Aglio Olio", "Pasta", 340, True), ("Chicken Alfredo", "Pasta", 430, False),
                 ("Garlic Bread", "Sides", 160, True), ("Tiramisu", "Desserts", 260, True),
                 ("Bruschetta", "Starters", 220, True)],
    },
    "Biryani": {
        "words": (["Hyderabadi", "Lucknowi", "Nawabi", "Shahi", "Biryani", "Kolkata"], ["Handi", "Pot", "House", "Darbar", "Mahal", "Express"]),
        "cost": (400, 900),
        "prep": (12, 22),
        "menu": [("Chicken Dum Biryani", "Biryani", 300, False), ("Mutton Biryani", "Biryani", 380, False),
                 ("Veg Biryani", "Biryani", 230, True), ("Egg Biryani", "Biryani", 240, False),
                 ("Paneer Biryani", "Biryani", 270, True), ("Mirchi Ka Salan", "Sides", 90, True),
                 ("Raita", "Sides", 60, True), ("Chicken 65", "Starters", 260, False),
                 ("Double Ka Meetha", "Desserts", 120, True)],
    },
    "Street Food": {
        "words": (["Bombay", "Mumbai", "Juhu", "Chowpatty", "Tapri", "Khau"], ["Chaat", "Gully", "Corner", "Junction", "Wala", "Adda"]),
        "cost": (150, 350),
        "prep": (5, 12),
        "menu": [("Vada Pav", "Snacks", 30, True), ("Pav Bhaji", "Main Course", 140, True),
                 ("Pani Puri", "Chaat", 60, True), ("Sev Puri", "Chaat", 70, True),
                 ("Bombay Sandwich", "Snacks", 90, True), ("Misal Pav", "Main Course", 110, True),
                 ("Dabeli", "Snacks", 40, True), ("Ragda Pattice", "Chaat", 90, True),
                 ("Cutting Chai", "Beverages", 20, True)],
    },
    "Cafe": {
        "words": (["Brew", "Bean", "Daily", "Third", "Morning", "Urban"], ["Lab", "Story", "Grind", "Wave", "Table", "Room"]),
        "cost": (500, 1100),
        "prep": (8, 15),
        "menu": [("Cappuccino", "Coffee", 180, True), ("Cold Brew", "Coffee", 220, True),
                 ("Cafe Latte", "Coffee", 190, True), ("Club Sandwich", "Sandwiches", 260, False),
                 ("Avocado Toast", "Breakfast", 320, True), ("Chicken Croissant", "Bakery", 240, False),
                 ("Blueberry Muffin", "Bakery", 150, True), ("Belgian Waffle", "Desserts", 230, True),
                 ("Iced Tea", "Beverages", 160, True)],
    },
    "Desserts": {
        "words": (["Sugar", "Sweet", "Choco", "Frozen", "Cake", "Creamy"], ["Rush", "Tooth", "Cloud", "Studio", "Box", "Bliss"]),
        "cost": (300, 700),
        "prep": (5, 10),
        "menu": [("Chocolate Truffle Cake", "Cakes", 450, True), ("Red Velvet Pastry", "Pastries", 140, True),
                 ("Brownie with Ice Cream", "Desserts", 190, True), ("Blueberry Cheesecake", "Pastries", 220, True),
                 ("Kulfi Falooda", "Desserts", 160, True), ("Mango Mastani", "Shakes", 180, True),
                 ("Belgian Chocolate Shake", "Shakes", 210, True), ("Rasmalai", "Indian Sweets", 120, True)],
    },
    "Coastal": {
        "words": (["Konkan", "Malvani", "Goan", "Mangalorean", "Coastal", "Sea"], ["Katta", "Kinara", "Shack", "Spice", "Tide", "Bay"]),
        "cost": (600, 1400),
        "prep": (15, 25),
        "menu": [("Surmai Fry", "Seafood", 420, False), ("Prawns Koliwada", "Seafood", 380, False),
                 ("Bombil Fry", "Seafood", 300, False), ("Fish Curry Rice", "Main Course", 340, False),
                 ("Chicken Sukka", "Main Course", 320, False), ("Neer Dosa", "Breads", 80, True),
                 ("Solkadhi", "Beverages", 70, True), ("Kombdi Vade", "Main Course", 330, False)],
    },
    "Burgers": {
        "words": (["Burger", "Big", "Smash", "Grill", "Patty", "Bun"], ["Barn", "Bros", "Shack", "Point", "Factory", "Joint"]),
        "cost": (300, 700),
        "prep": (8, 15),
        "menu": [("Classic Veg Burger", "Burgers", 150, True), ("Crispy Chicken Burger", "Burgers", 200, False),
                 ("Double Smash Burger", "Burgers", 290, False), ("Paneer Tikka Burger", "Burgers", 180, True),
                 ("Peri Peri Fries", "Sides", 120, True), ("Loaded Nachos", "Sides", 190, True),
                 ("Chicken Wings", "Sides", 250, False), ("Oreo Shake", "Shakes", 170, True)],
    },
    "Healthy": {
        "words": (["Green", "Fit", "Lean", "Fresh", "Pure", "Good"], ["Bowl", "Leaf", "Fuel", "Kitchen", "Box", "Harvest"]),
        "cost": (500, 1000),
        "prep": (8, 15),
        "menu": [("Quinoa Salad Bowl", "Salads", 320, True), ("Grilled Chicken Bowl", "Bowls", 360, False),
                 ("Paneer Protein Bowl", "Bowls", 330, True), ("Greek Salad", "Salads", 290, True),
                 ("Acai Smoothie Bowl", "Breakfast", 380, True), ("Detox Juice", "Beverages", 180, True),
                 ("Millet Khichdi", "Main Course", 240, True), ("Hummus Platter", "Starters", 270, True)],
    },
    "Mughlai": {
        "words": (["Noor", "Bade", "Mughal", "Zaffran", "Shalimar", "Persian"], ["Mahal", "Miyan", "Durbar", "Kebabs", "Nihari", "Darbar"]),
        "cost": (500, 1100),
        "prep": (15, 25),
        "menu": [("Chicken Seekh Kebab", "Kebabs", 300, False), ("Mutton Galouti Kebab", "Kebabs", 380, False),
                 ("Nalli Nihari", "Main Course", 420, False), ("Chicken Korma", "Main Course", 330, False),
                 ("Rumali Roti", "Breads", 40, True), ("Shahi Paneer", "Main Course", 280, True),
                 ("Phirni", "Desserts", 110, True), ("Haleem", "Main Course", 340, False)],
    },
}

CUISINE_WEIGHTS = {"North Indian": 16, "South Indian": 10, "Chinese": 12, "Italian": 8, "Biryani": 13,
                   "Street Food": 10, "Cafe": 7, "Desserts": 7, "Coastal": 5, "Burgers": 6, "Healthy": 3, "Mughlai": 5}

GOOD_COMMENTS = ["Loved it, will order again", "Food arrived hot and fresh", "Great taste and quantity",
                 "Delivery partner was very polite", "Best in the area", "Perfectly packed", "Value for money",
                 "Super quick delivery", "Authentic flavours", "Exactly like eating at the restaurant"]
OKAY_COMMENTS = ["Decent food", "Taste was okay", "A bit late but fine", "Quantity could be better",
                 "Average experience", "Good but slightly expensive"]
BAD_COMMENTS = ["Food was cold", "Very late delivery", "Wrong item delivered", "Too oily",
                "Packaging was leaking", "Not worth the price"]

HOUR_WEIGHTS = [1, 1, 0.5, 0.2, 0.1, 0.1, 0.3, 1, 3, 4, 3, 5, 10, 12, 9, 4, 3, 4, 6, 10, 14, 13, 9, 4]


def haversine(lat1, lon1, lat2, lon2):
    r = 6371
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def random_point_near(lat, lon, spread):
    new_lat = lat + random.uniform(-spread, spread)
    new_lon = lon + random.uniform(-spread, spread)
    return round(new_lat, 6), round(new_lon, 6)


def random_phone(used):
    while True:
        number = str(random.choice([7, 8, 9])) + str(random.randint(100000000, 999999999))
        if number not in used:
            used.add(number)
            return number


def fmt(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if value is None:
        return ""
    return value


def write_csv(folder, name, header, rows):
    path = os.path.join(folder, name + ".csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for row in rows:
            clean = []
            for value in row:
                clean.append(fmt(value))
            writer.writerow(clean)
    return path


def make_customers(end_time):
    customers = []
    used_phones = set()
    used_emails = set()
    for customer_id in range(1, NUM_CUSTOMERS + 1):
        first = random.choice(FIRST_NAMES)
        last = random.choice(LAST_NAMES)
        locality, lat, lon = random.choice(LOCALITIES)
        c_lat, c_lon = random_point_near(lat, lon, 0.01)
        email_base = (first + "." + last).lower().replace("'", "")
        email = email_base + str(random.randint(1, 999)) + "@" + random.choice(["gmail.com", "yahoo.in", "outlook.com"])
        while email in used_emails:
            email = email_base + str(random.randint(1000, 9999)) + "@gmail.com"
        used_emails.add(email)
        flat = str(random.randint(1, 20)) + "0" + str(random.randint(1, 9))
        address = "Flat " + flat + ", " + random.choice(STREETS) + ", " + locality + ", Mumbai"
        joined = (end_time - timedelta(days=random.randint(DAYS_OF_HISTORY, 900))).date()
        customers.append({
            "customer_id": customer_id, "name": first + " " + last, "phone": random_phone(used_phones),
            "email": email, "address": address, "locality": locality, "latitude": c_lat,
            "longitude": c_lon, "joined_on": joined,
            "weight": random.paretovariate(1.6),
        })
    return customers


def make_restaurants():
    restaurants = []
    used_names = set()
    cuisine_names = list(CUISINE_WEIGHTS.keys())
    cuisine_weights = list(CUISINE_WEIGHTS.values())
    restaurant_id = 1
    while len(restaurants) < NUM_RESTAURANTS:
        cuisine = random.choices(cuisine_names, weights=cuisine_weights)[0]
        info = CUISINES[cuisine]
        name = random.choice(info["words"][0]) + " " + random.choice(info["words"][1])
        locality, lat, lon = random.choice(LOCALITIES)
        if (name, locality) in used_names:
            continue
        used_names.add((name, locality))
        r_lat, r_lon = random_point_near(lat, lon, 0.008)
        low, high = info["cost"]
        cost = random.randint(low // 50, high // 50) * 50
        opens = time(random.choice([7, 8, 10, 11, 12]), 0)
        closes = time(random.choice([22, 23, 23, 23]), random.choice([0, 30]))
        veg_only = cuisine in ["South Indian", "Desserts"] or random.random() < 0.08
        address = "Shop " + str(random.randint(1, 40)) + ", " + random.choice(STREETS) + ", " + locality + ", Mumbai"
        restaurants.append({
            "restaurant_id": restaurant_id, "name": name, "cuisine": cuisine, "locality": locality,
            "address": address, "latitude": r_lat, "longitude": r_lon, "rating": 0,
            "cost_for_two": cost, "opens_at": opens.strftime("%H:%M"), "closes_at": closes.strftime("%H:%M"),
            "is_veg": veg_only, "quality": random.uniform(3.5, 4.9),
            "popularity": random.uniform(0.4, 2.5),
        })
        restaurant_id += 1
    return restaurants


def make_menu(restaurants, start_time, end_time):
    items = []
    history = []
    item_id = 1001
    for restaurant in restaurants:
        dishes = CUISINES[restaurant["cuisine"]]["menu"]
        count = random.randint(len(dishes) - 3, len(dishes))
        chosen = random.sample(dishes, count)
        for dish in chosen:
            name, category, base_price, veg = dish
            if restaurant["is_veg"] and not veg:
                continue
            factor = restaurant["cost_for_two"] / ((CUISINES[restaurant["cuisine"]]["cost"][0] + CUISINES[restaurant["cuisine"]]["cost"][1]) / 2)
            price = round(base_price * random.uniform(0.85, 1.15) * (0.75 + factor * 0.25) / 5) * 5
            if price < 15:
                price = 15
            stock = random.randint(20, 150)
            item = {"item_id": item_id, "restaurant_id": restaurant["restaurant_id"], "item_name": name,
                    "category": category, "price": float(price), "stock": stock, "is_veg": veg, "prices": []}
            changes = 0
            if random.random() < 0.35:
                changes = random.choice([1, 1, 2])
            change_times = []
            for i in range(changes):
                change_times.append(start_time + timedelta(days=random.randint(15, DAYS_OF_HISTORY - 10), hours=random.randint(0, 23)))
            change_times.sort()
            old_prices = []
            current = float(price)
            for i in range(changes):
                previous = current
                current = round(current / random.uniform(1.05, 1.15) / 5) * 5
                if current >= previous:
                    current = previous - 5
                old_prices.insert(0, float(max(current, 10)))
            valid_from = start_time - timedelta(days=30)
            for i in range(changes):
                item["prices"].append((old_prices[i], valid_from, change_times[i]))
                valid_from = change_times[i]
            item["prices"].append((float(price), valid_from, None))
            for p in item["prices"]:
                history.append({"item_id": item_id, "price": p[0], "valid_from": p[1], "valid_to": p[2]})
            items.append(item)
            item_id += 1
    return items, history


def make_partners(end_time):
    partners = []
    used_phones = set()
    for partner_id in range(1, NUM_PARTNERS + 1):
        locality, lat, lon = random.choice(LOCALITIES)
        p_lat, p_lon = random_point_near(lat, lon, 0.012)
        partners.append({
            "partner_id": partner_id,
            "name": random.choice(FIRST_NAMES[:20] + FIRST_NAMES[20:30]) + " " + random.choice(LAST_NAMES),
            "phone": random_phone(used_phones),
            "vehicle": random.choices(["BIKE", "SCOOTER", "BICYCLE", "EV_BIKE"], weights=[55, 25, 5, 15])[0],
            "latitude": p_lat, "longitude": p_lon,
            "is_available": random.random() < 0.7,
            "rating": round(random.uniform(3.6, 4.9), 1),
            "joined_on": (end_time - timedelta(days=random.randint(30, 700))).date(),
        })
    return partners


def price_at(item, moment):
    for price, valid_from, valid_to in item["prices"]:
        if valid_from <= moment and (valid_to is None or moment < valid_to):
            return price
    return item["prices"][-1][0]


def random_order_time(start_time):
    day_offsets = list(range(DAYS_OF_HISTORY))
    day_weights = []
    for d in day_offsets:
        moment = start_time + timedelta(days=d)
        weight = 1 + d / DAYS_OF_HISTORY * 0.6
        if moment.weekday() >= 5:
            weight = weight * 1.35
        day_weights.append(weight)
    day = random.choices(day_offsets, weights=day_weights)[0]
    hour = random.choices(list(range(24)), weights=HOUR_WEIGHTS)[0]
    return start_time + timedelta(days=day, hours=hour, minutes=random.randint(0, 59), seconds=random.randint(0, 59))


def generate(folder):
    random.seed(SEED)
    os.makedirs(folder, exist_ok=True)

    end_time = datetime.now().replace(microsecond=0)
    start_time = (end_time - timedelta(days=DAYS_OF_HISTORY)).replace(hour=0, minute=0, second=0)

    customers = make_customers(end_time)
    restaurants = make_restaurants()
    items, price_history = make_menu(restaurants, start_time, end_time)
    partners = make_partners(end_time)

    menu_by_restaurant = {}
    for item in items:
        menu_by_restaurant.setdefault(item["restaurant_id"], []).append(item)

    nearby = {}
    for customer in customers:
        options = []
        for restaurant in restaurants:
            distance = haversine(customer["latitude"], customer["longitude"], restaurant["latitude"], restaurant["longitude"])
            options.append((distance, restaurant))
        options.sort(key=lambda pair: pair[0])
        close = []
        for distance, restaurant in options:
            if distance <= 7:
                close.append((distance, restaurant))
        if len(close) < 8:
            close = options[:8]
        nearby[customer["customer_id"]] = close

    customer_weights = []
    for customer in customers:
        customer_weights.append(customer["weight"])

    order_times = []
    for i in range(NUM_ORDERS):
        order_times.append(random_order_time(start_time))
    order_times.sort()
    live_count = 25
    for i in range(live_count):
        order_times[NUM_ORDERS - live_count + i] = end_time - timedelta(minutes=random.randint(2, 50))
    order_times.sort()

    orders = []
    order_items = []
    status_history = []
    payments = []
    deliveries = []
    reviews = []
    review_id = 1
    order_id = 100001

    for order_time in order_times:
        customer = random.choices(customers, weights=customer_weights)[0]
        if order_time.date() < customer["joined_on"]:
            customer["joined_on"] = order_time.date() - timedelta(days=random.randint(1, 20))
        choices = nearby[customer["customer_id"]]
        weights = []
        for distance, restaurant in choices:
            weights.append(restaurant["popularity"] / (1 + distance))
        distance, restaurant = random.choices(choices, weights=weights)[0]
        menu = menu_by_restaurant[restaurant["restaurant_id"]]

        basket_size = random.choices([1, 2, 3, 4, 5], weights=[30, 35, 20, 10, 5])[0]
        basket = random.sample(menu, min(basket_size, len(menu)))
        total = 0
        lines = []
        for item in basket:
            quantity = random.choices([1, 2, 3], weights=[75, 20, 5])[0]
            unit_price = price_at(item, order_time)
            total = total + quantity * unit_price
            lines.append((item["item_id"], quantity, unit_price))
        delivery_fee = 0
        if total < 199:
            delivery_fee = 30
        total = round(total + delivery_fee + total * 0.05, 2)

        method = random.choices(["UPI", "CARD", "WALLET", "CASH", "NETBANKING"], weights=[55, 15, 10, 15, 5])[0]
        minutes_ago = (end_time - order_time).total_seconds() / 60
        events = [("PLACED", order_time)]
        payment_status = "SUCCESS"
        final_status = "DELIVERED"
        is_live = minutes_ago < 60

        roll = random.random()
        if method != "CASH" and roll < 0.03:
            payment_status = "FAILED"
            final_status = "CANCELLED"
            events.append(("CANCELLED", order_time + timedelta(minutes=random.randint(1, 3))))
        elif roll < 0.05:
            final_status = "CANCELLED"
            accepted = order_time + timedelta(minutes=random.randint(1, 4))
            events.append(("ACCEPTED", accepted))
            events.append(("CANCELLED", accepted + timedelta(minutes=random.randint(2, 10))))
            if method == "CASH":
                payment_status = "FAILED"
            else:
                payment_status = "REFUNDED"
        else:
            prep_low, prep_high = CUISINES[restaurant["cuisine"]]["prep"]
            accepted = order_time + timedelta(minutes=random.randint(1, 4), seconds=random.randint(0, 59))
            preparing = accepted + timedelta(minutes=random.randint(1, 3), seconds=random.randint(0, 59))
            busy = 1.0
            if order_time.hour in [13, 20, 21]:
                busy = 1.25
            picked = preparing + timedelta(minutes=random.randint(prep_low, prep_high) * busy, seconds=random.randint(0, 59))
            road_km = round(distance * random.uniform(1.2, 1.45) + 0.3, 2)
            travel_minutes = road_km * random.uniform(2.8, 4.8) + random.randint(2, 6)
            if order_time.hour in [9, 10, 18, 19, 20]:
                travel_minutes = travel_minutes * 1.2
            delivered = picked + timedelta(minutes=travel_minutes)
            all_steps = [("ACCEPTED", accepted), ("PREPARING", preparing), ("PICKED_UP", picked), ("DELIVERED", delivered)]
            for step in all_steps:
                if step[1] <= end_time:
                    events.append(step)
            final_status = events[-1][0]
            if method == "CASH" and final_status != "DELIVERED":
                payment_status = "PENDING"

        orders.append({"order_id": order_id, "customer_id": customer["customer_id"],
                       "restaurant_id": restaurant["restaurant_id"], "order_time": order_time,
                       "status": final_status, "total_amount": total})
        for line in lines:
            order_items.append({"order_id": order_id, "item_id": line[0], "quantity": line[1], "unit_price": line[2]})
        for status, moment in events:
            status_history.append({"order_id": order_id, "status": status, "changed_at": moment})

        paid_at = order_time + timedelta(seconds=random.randint(5, 50))
        if method == "CASH" and final_status == "DELIVERED":
            paid_at = events[-1][1]
        payments.append({"order_id": order_id, "amount": total, "method": method,
                         "status": payment_status, "paid_at": paid_at})

        statuses = []
        for e in events:
            statuses.append(e[0])
        if "PREPARING" in statuses or "PICKED_UP" in statuses or "DELIVERED" in statuses:
            best_partner = None
            best_distance = None
            candidates = random.sample(partners, 25)
            for partner in candidates:
                d = haversine(partner["latitude"], partner["longitude"], restaurant["latitude"], restaurant["longitude"])
                if best_distance is None or d < best_distance:
                    best_distance = d
                    best_partner = partner
            pickup = None
            delivered_time = None
            for status, moment in events:
                if status == "PICKED_UP":
                    pickup = moment
                if status == "DELIVERED":
                    delivered_time = moment
            road_km = round(distance * random.uniform(1.2, 1.45) + 0.3, 2)
            deliveries.append({"order_id": order_id, "partner_id": best_partner["partner_id"],
                               "pickup_time": pickup, "delivered_time": delivered_time,
                               "distance_km": road_km, "route_from": (restaurant["latitude"], restaurant["longitude"]),
                               "route_to": (customer["latitude"], customer["longitude"])})
            if is_live and final_status != "DELIVERED":
                best_partner["is_available"] = False

            if final_status == "DELIVERED" and random.random() < 0.38:
                total_minutes = (delivered_time - order_time).total_seconds() / 60
                stars_value = restaurant["quality"] + random.gauss(0, 0.7)
                if total_minutes > 50:
                    stars_value = stars_value - 1
                stars = int(round(min(5, max(1, stars_value))))
                if stars >= 4:
                    comment = random.choice(GOOD_COMMENTS)
                elif stars == 3:
                    comment = random.choice(OKAY_COMMENTS)
                else:
                    comment = random.choice(BAD_COMMENTS)
                if random.random() < 0.25:
                    comment = None
                reviews.append({"review_id": review_id, "order_id": order_id, "customer_id": customer["customer_id"],
                                "restaurant_id": restaurant["restaurant_id"], "stars": stars, "comment": comment,
                                "reviewed_at": delivered_time + timedelta(minutes=random.randint(10, 600))})
                review_id += 1
        order_id += 1

    star_totals = {}
    for review in reviews:
        if review["restaurant_id"] not in star_totals:
            star_totals[review["restaurant_id"]] = [0, 0]
        star_totals[review["restaurant_id"]][0] += review["stars"]
        star_totals[review["restaurant_id"]][1] += 1
    for restaurant in restaurants:
        totals = star_totals.get(restaurant["restaurant_id"])
        if totals:
            restaurant["rating"] = round(totals[0] / totals[1], 1)
        else:
            restaurant["rating"] = round(restaurant["quality"], 1)

    write_csv(folder, "customers", ["customer_id", "name", "phone", "email", "address", "locality", "latitude", "longitude", "joined_on"],
              [[c["customer_id"], c["name"], c["phone"], c["email"], c["address"], c["locality"], c["latitude"], c["longitude"], c["joined_on"]] for c in customers])
    write_csv(folder, "restaurants", ["restaurant_id", "name", "cuisine", "locality", "address", "latitude", "longitude", "rating", "cost_for_two", "opens_at", "closes_at", "is_veg"],
              [[r["restaurant_id"], r["name"], r["cuisine"], r["locality"], r["address"], r["latitude"], r["longitude"], r["rating"], r["cost_for_two"], r["opens_at"], r["closes_at"], r["is_veg"]] for r in restaurants])
    write_csv(folder, "menu_items", ["item_id", "restaurant_id", "item_name", "category", "price", "stock", "is_veg"],
              [[m["item_id"], m["restaurant_id"], m["item_name"], m["category"], m["price"], m["stock"], m["is_veg"]] for m in items])
    write_csv(folder, "menu_price_history", ["item_id", "price", "valid_from", "valid_to"],
              [[h["item_id"], h["price"], h["valid_from"], h["valid_to"]] for h in price_history])
    write_csv(folder, "delivery_partners", ["partner_id", "name", "phone", "vehicle", "latitude", "longitude", "is_available", "rating", "joined_on"],
              [[p["partner_id"], p["name"], p["phone"], p["vehicle"], p["latitude"], p["longitude"], p["is_available"], p["rating"], p["joined_on"]] for p in partners])
    write_csv(folder, "orders", ["order_id", "customer_id", "restaurant_id", "order_time", "status", "total_amount"],
              [[o["order_id"], o["customer_id"], o["restaurant_id"], o["order_time"], o["status"], o["total_amount"]] for o in orders])
    write_csv(folder, "order_items", ["order_id", "item_id", "quantity", "unit_price"],
              [[i["order_id"], i["item_id"], i["quantity"], i["unit_price"]] for i in order_items])
    write_csv(folder, "order_status_history", ["order_id", "status", "changed_at"],
              [[h["order_id"], h["status"], h["changed_at"]] for h in status_history])
    write_csv(folder, "payments", ["order_id", "amount", "method", "status", "paid_at"],
              [[p["order_id"], p["amount"], p["method"], p["status"], p["paid_at"]] for p in payments])
    write_csv(folder, "deliveries", ["order_id", "partner_id", "pickup_time", "delivered_time", "distance_km"],
              [[d["order_id"], d["partner_id"], d["pickup_time"], d["delivered_time"], d["distance_km"]] for d in deliveries])
    write_csv(folder, "reviews", ["order_id", "customer_id", "restaurant_id", "stars", "comment", "reviewed_at"],
              [[r["order_id"], r["customer_id"], r["restaurant_id"], r["stars"], r["comment"], r["reviewed_at"]] for r in reviews])

    return {"customers": len(customers), "restaurants": len(restaurants), "menu_items": len(items),
            "menu_price_history": len(price_history), "delivery_partners": len(partners), "orders": len(orders),
            "order_items": len(order_items), "order_status_history": len(status_history),
            "payments": len(payments), "deliveries": len(deliveries), "reviews": len(reviews)}


if __name__ == "__main__":
    counts = generate(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"))
    for key in counts:
        print(key, counts[key])
