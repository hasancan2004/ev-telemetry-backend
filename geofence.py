import math

# Konya Merkez Koordinatları (Komuta Merkezi)
CENTER_LAT = 37.8715
CENTER_LNG = 32.4850
MAX_RADIUS_KM = 20.0 # 20 kilometrelik güvenlik çemberi

def calculate_distance(lat1, lon1, lat2, lon2):
    """Haversine formülü ile iki koordinat arasındaki kuş uçuşu mesafeyi hesaplar."""
    R = 6371.0 # Dünyanın yarıçapı (km)
    
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    distance = R * c
    return distance

def check_geofence_breach(current_lat: float, current_lng: float) -> bool:
    """Araç 20 km'lik çemberin dışına çıktıysa True, güvenliyse False döner."""
    distance = calculate_distance(CENTER_LAT, CENTER_LNG, current_lat, current_lng)
    return distance > MAX_RADIUS_KM