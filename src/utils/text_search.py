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