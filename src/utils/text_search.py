import unicodedata
import re

class TextSearch:
    @staticmethod
    def normalize_text(text):
        """Normalize text by removing diacritics, converting to lowercase, and applying Arabic-specific normalizations."""
        if not text:
            return ""
        
        text = str(text) # Ensure text is a string
        
        # General Unicode normalization for diacritics (covers many languages including Arabic tashkeel)
        # NFD: Canonical Decomposition. Converts characters to their base form + combining diacritical marks.
        # e.g., 'é' becomes 'e' + '´'. Then we remove Mn (Nonspacing_Mark).
        text = ''.join(c for c in unicodedata.normalize('NFD', text)
                       if unicodedata.category(c) != 'Mn')
        
        text = text.lower() # Convert to lowercase after NFD to handle cases like Turkish 'İ' -> 'i'

        # Arabic-specific normalizations (applied after general normalization and lowercasing)
        # Normalize Alef variants (Alef with Hamza Above, Hamza Below, Alef Madda) to basic Alef
        text = re.sub(r'[أإآ]', 'ا', text)
        # Normalize Teh Marbuta to Heh
        text = re.sub(r'ة', 'ه', text)
        # Normalize Alef Maqsurah to Yeh
        text = re.sub(r'ى', 'ي', text)
        
        # Optional: Remove common prefixes like "ال" if followed by an Arabic letter.
        # This might be too aggressive for a general normalization function, consider if this should be here
        # or applied selectively. For now, keeping it as per original movies_tab logic.
        text = re.sub(r'\bال(?=[؀-ۿ])', '', text)
        
        # Remove leading/trailing whitespace and collapse multiple spaces to a single space
        text = text.strip()
        text = re.sub(r'\s+', ' ', text)
        
        return text

    @staticmethod
    def search(items, search_term, key_func):
        """Search items based on a search term and a key function."""
        if not search_term:
            return items
        
        normalized_search_term = TextSearch.normalize_text(search_term)
        
        results = []
        for item in items:
            value_to_search = key_func(item)
            if value_to_search:
                normalized_value = TextSearch.normalize_text(value_to_search)
                if normalized_search_term in normalized_value:
                    results.append(item)
        return results

def search_all_data(api_client, query):
    """
    Searches across live channels, movies, and series for the given query.
    Returns a list of combined, structured results.
    """
    if not api_client or not query:
        return []

    normalized_query = TextSearch.normalize_text(query)
    if not normalized_query: # Or if len(normalized_query) < MIN_SEARCH_LEN
        return []

    all_results = []

    # --- Search Live Channels ---
    # Assuming api_client.get_live_streams_for_search() or similar exists
    # and returns a list of dicts with 'name', 'stream_id', 'stream_icon', 'category_name', etc.
    # For now, let's assume a generic get_live_streams() that might need category iteration.
    # This part needs to align with how live channels are fetched for searching.
    # A more optimized API endpoint for searching live channels would be ideal.
    # If we need to fetch all live streams first:
    live_streams_data = []
    success_cat_live, live_categories = api_client.get_live_categories()
    if success_cat_live:
        for cat in live_categories:
            category_id = cat.get('category_id')
            if category_id:
                success_streams, streams = api_client.get_live_streams(category_id)
                if success_streams:
                    live_streams_data.extend(streams)
    
    for item in live_streams_data:
        name = item.get('name', '')
        normalized_name = TextSearch.normalize_text(name)
        if normalized_query in normalized_name:
            result_item = {
                'stream_type': 'live',
                'name': name,
                'stream_id': item.get('stream_id'),
                'cover': item.get('stream_icon'),
                'rating': item.get('rating', 0), # Live channels might not have ratings
                # Add any other relevant fields for display or action
                'category_name': item.get('category_name', 'Live')
            }
            all_results.append(result_item)

    # --- Search Movies ---
    # Assuming api_client.get_movies_for_search() or similar exists.
    # Or iterate through movie categories and then movies.
    movies_data = []
    success_cat_movies, movie_categories = api_client.get_vod_categories() # Changed to get_vod_categories
    if success_cat_movies:
        for cat in movie_categories:
            category_id = cat.get('category_id')
            if category_id:
                # Using get_vod_streams which is often used for movies
                success_movies, movies = api_client.get_vod_streams(category_id)
                if success_movies:
                    movies_data.extend(movies) 
    
    for item in movies_data:
        name = item.get('name', '')
        normalized_name = TextSearch.normalize_text(name)
        if normalized_query in normalized_name:
            result_item = {
                'stream_type': 'movie',
                'name': name,
                'stream_id': item.get('stream_id'), # Use stream_id consistently
                'cover': item.get('stream_icon') or item.get('movie_image'),
                'rating': item.get('rating', 0),
                'year': item.get('year'),
                'plot': item.get('plot'),
                # Add other relevant fields
            }
            all_results.append(result_item)

    # --- Search Series ---
    # Assuming api_client.get_series_for_search() or similar exists.
    series_data = []
    success_cat_series, series_categories = api_client.get_series_categories()
    if success_cat_series:
        for cat in series_categories:
            category_id = cat.get('category_id')
            if category_id:
                success_series, series_list = api_client.get_series(category_id)
                if success_series:
                    series_data.extend(series_list)

    for item in series_data:
        name = item.get('name', '')
        normalized_name = TextSearch.normalize_text(name)
        if normalized_query in normalized_name:
            result_item = {
                'stream_type': 'series',
                'name': name,
                'series_id': item.get('series_id'),
                'cover': item.get('cover'),
                'rating': item.get('rating', 0),
                'plot': item.get('plot'),
                'year': item.get('year'),
                # Add other relevant fields
            }
            all_results.append(result_item)
            
    # Remove duplicates if any (e.g., if an item appears in multiple categories)
    # This basic de-duplication assumes unique IDs per type.
    # A more robust de-duplication might be needed if IDs are not globally unique across types.
    unique_results = []
    seen_ids = set()
    for item in all_results:
        item_id = None
        if item['stream_type'] == 'live':
            item_id = item.get('stream_id')
        elif item['stream_type'] == 'movie':
            item_id = item.get('stream_id') # Use stream_id here as well for consistency during de-duplication
        elif item['stream_type'] == 'series':
            item_id = item.get('series_id')
        
        if item_id:
            unique_key = (item['stream_type'], item_id)
            if unique_key not in seen_ids:
                unique_results.append(item)
                seen_ids.add(unique_key)
        else: # If no ID, just add it (less ideal)
            unique_results.append(item)


    return unique_results
