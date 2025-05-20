class FavoritesManager:
    """Business logic for managing favorites, separated from UI."""
    def __init__(self, api_client):
        self.api_client = api_client
        self.favorites = []

    def set_favorites(self, favorites):
        self.favorites = favorites

    def get_favorites(self):
        return self.favorites

    def search_favorites(self, text):
        import unicodedata
        normalized_text = unicodedata.normalize('NFKD', text.lower())
        
        filtered_favorites = []
        for fav in self.favorites:
            item_name = fav.get('name', '')
            if item_name: # Ensure item_name is not None or empty
                normalized_item_name = unicodedata.normalize('NFKD', item_name.lower())
                if normalized_text in normalized_item_name:
                    filtered_favorites.append(fav)
        return filtered_favorites

    def remove_favorite(self, index):
        if 0 <= index < len(self.favorites):
            del self.favorites[index]

    def get_favorite(self, index):
        if 0 <= index < len(self.favorites):
            return self.favorites[index]
        return None

    def get_stream_url(self, favorite):
        stream_url = favorite.get('stream_url')
        stream_id = favorite.get('stream_id')
        container_extension = favorite.get('container_extension')
        if not stream_url:
            stream_url = self.api_client.get_movie_url(stream_id, container_extension)
        return stream_url
