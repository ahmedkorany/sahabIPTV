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
        text = text.lower()
        return [fav for fav in self.favorites if text in fav.get('name', '').lower()]

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
