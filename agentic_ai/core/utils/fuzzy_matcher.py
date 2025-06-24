"""
Fuzzy string matching utility for flexible city name recognition.
"""
try:
    from fuzzywuzzy import process, fuzz
    FUZZY_AVAILABLE = True
except ImportError:
    print("Warning: fuzzywuzzy not installed. Fallback to basic matching for city names.")
    FUZZY_AVAILABLE = False

class CityMatcher:
    """
    A utility class for matching city names using fuzzy string matching.
    Supports common alternative names for Indian cities.
    """
    
    def __init__(self, available_cities=None):
        """
        Initialize the CityMatcher with a list of available cities.
        
        Args:
            available_cities: List of official city names
        """
        self.available_cities = available_cities or []
        
        # Common alternative names/spellings for cities
        self.city_aliases = {
            'Mumbai': ['Bombay', 'Bambai'],
            'Delhi': ['New Delhi', 'Dilli', 'NCR'],
            'Bangalore': ['Bengaluru', 'Bengalooru', 'Bengluru', 'Silicon City', 'Garden City'],
            'Chennai': ['Madras', 'Chenai'],
            'Kolkata': ['Calcutta', 'Kolikata'],
            'Hyderabad': ['Cyberabad', 'Hiderabad', 'Bhagyanagar'],
            'Pune': ['Poona', 'Puna'],
            'Ahmedabad': ['Amdavad', 'Ahmdabad'],
            'Jaipur': ['Pink City', 'Jaypur'],
            'Surat': ['Suryapur', 'Soorat'],
        }

    def get_closest_match(self, input_city, threshold=70):
        """
        Find the closest matching city from the available cities list.
        
        Args:
            input_city: User input for city name
            threshold: Minimum similarity score (0-100) to accept a match
            
        Returns:
            tuple: (matched_city, score) or (None, 0) if no match found
        """
        if not input_city:
            return None, 0
        
        input_city = input_city.strip().lower()
        
        # First check for exact matches (case-insensitive)
        for city in self.available_cities:
            if city.lower() == input_city:
                return city, 100
        
        # Then check aliases
        for official_name, aliases in self.city_aliases.items():
            if official_name in self.available_cities:  # Make sure the official name is in our allowed list
                for alias in aliases:
                    if alias.lower() == input_city:
                        return official_name, 100
        
        # If no exact match, use fuzzy matching if available
        if FUZZY_AVAILABLE:
            # Create a combined list of official names and aliases
            all_names = []
            for city in self.available_cities:
                all_names.append(city)
                if city in self.city_aliases:
                    all_names.extend(self.city_aliases[city])
            
            # Find the best match
            best_match, score = process.extractOne(input_city, all_names, scorer=fuzz.token_sort_ratio)
            
            if score >= threshold:
                # If the best match is an alias, return its official name
                for official_name, aliases in self.city_aliases.items():
                    if best_match in aliases and official_name in self.available_cities:
                        return official_name, score
                
                # If it's an official name, return it directly
                if best_match in self.available_cities:
                    return best_match, score
                
                # As a fallback, find the closest official city
                for official_name in self.available_cities:
                    if official_name.lower() == best_match.lower():
                        return official_name, score
            
            return None, score
        
        # Fallback to basic matching if fuzzywuzzy is not available
        for city in self.available_cities:
            if city.lower().replace(" ", "") == input_city.replace(" ", ""):
                return city, 90
                
        return None, 0
