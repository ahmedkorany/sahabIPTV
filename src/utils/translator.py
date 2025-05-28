import requests
import json
from typing import Optional, Dict

class LibreTranslateClient:
    """Client for LibreTranslate API to translate text between languages."""
    
    def __init__(self, base_url: str = "https://libretranslate.com", api_key: Optional[str] = None):
        """
        Initialize LibreTranslate client.
        
        Args:
            base_url: LibreTranslate server URL (default: public instance)
            api_key: API key if required by the server
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session = requests.Session()
        
        # Language code mapping for common languages
        self.language_mapping = {
            'ar': 'ar',  # Arabic
            'fr': 'fr',  # French
            'es': 'es',  # Spanish
            'de': 'de',  # German
            'it': 'it',  # Italian
            'tr': 'tr',  # Turkish
            'en': 'en',  # English
            'pt': 'pt',  # Portuguese
            'ru': 'ru',  # Russian
            'ja': 'ja',  # Japanese
            'ko': 'ko',  # Korean
            'zh': 'zh',  # Chinese
        }
    
    def get_supported_languages(self) -> Optional[Dict]:
        """Get list of supported languages from LibreTranslate."""
        try:
            url = f"{self.base_url}/languages"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[LibreTranslate] Error getting supported languages: {e}")
            return None
    
    def translate_text(self, text: str, source_lang: str = 'en', target_lang: str = 'ar') -> Optional[str]:
        """
        Translate text from source language to target language.
        
        Args:
            text: Text to translate
            source_lang: Source language code (default: 'en')
            target_lang: Target language code (default: 'ar')
            
        Returns:
            Translated text or None if translation fails
        """
        if not text or not text.strip():
            return None
            
        # Don't translate if source and target are the same
        if source_lang == target_lang:
            return text
            
        # Map language codes if needed
        source_lang = self.language_mapping.get(source_lang, source_lang)
        target_lang = self.language_mapping.get(target_lang, target_lang)
        
        try:
            url = f"{self.base_url}/translate"
            
            data = {
                'q': text,
                'source': source_lang,
                'target': target_lang,
                'format': 'text'
            }
            
            # Add API key if provided
            if self.api_key:
                data['api_key'] = self.api_key
            
            headers = {
                'Content-Type': 'application/json'
            }
            
            response = self.session.post(
                url, 
                json=data, 
                headers=headers, 
                timeout=30
            )
            
            response.raise_for_status()
            result = response.json()
            
            translated_text = result.get('translatedText')
            if translated_text:
                print(f"[LibreTranslate] Successfully translated text from {source_lang} to {target_lang}")
                return translated_text
            else:
                print(f"[LibreTranslate] No translated text in response: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"[LibreTranslate] Network error during translation: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[LibreTranslate] JSON decode error: {e}")
            return None
        except Exception as e:
            print(f"[LibreTranslate] Unexpected error during translation: {e}")
            return None
    
    def is_service_available(self) -> bool:
        """Check if LibreTranslate service is available."""
        try:
            url = f"{self.base_url}/languages"
            response = self.session.get(url, timeout=5)
            return response.status_code == 200
        except Exception:
            return False


class TranslationManager:
    """Manager for handling plot translations with caching."""
    
    def __init__(self, libre_translate_url: str = "https://libretranslate.com", api_key: Optional[str] = None):
        """
        Initialize translation manager.
        
        Args:
            libre_translate_url: LibreTranslate server URL
            api_key: API key if required
        """
        self.translator = LibreTranslateClient(libre_translate_url, api_key)
        self.translation_cache = {}  # Simple in-memory cache
        
    def get_cache_key(self, text: str, source_lang: str, target_lang: str) -> str:
        """Generate cache key for translation."""
        # Use first 50 characters of text + language codes for cache key
        text_snippet = text[:50].replace(' ', '_').replace('\n', '_')
        return f"{source_lang}_{target_lang}_{hash(text_snippet)}"
    
    def translate_plot(self, plot_text: str, target_language: str, source_language: str = 'en') -> Optional[str]:
        """
        Translate plot text with caching.
        
        Args:
            plot_text: Plot text to translate
            target_language: Target language code
            source_language: Source language code (default: 'en')
            
        Returns:
            Translated plot text or original text if translation fails
        """
        if not plot_text or not plot_text.strip():
            return plot_text
            
        # Don't translate if target is English or same as source
        if target_language == 'en' or target_language == source_language:
            return plot_text
            
        # Check cache first
        cache_key = self.get_cache_key(plot_text, source_language, target_language)
        if cache_key in self.translation_cache:
            print(f"[TranslationManager] Using cached translation for {source_language} -> {target_language}")
            return self.translation_cache[cache_key]
        
        # Skip translation if no API key is available for LibreTranslate
        if not self.translator.api_key:
            print(f"[TranslationManager] No API key available for LibreTranslate. Translation skipped.")
            print(f"[TranslationManager] To enable translation, get a free API key from https://portal.libretranslate.com")
            return plot_text
        
        # Check if service is available
        if not self.translator.is_service_available():
            print(f"[TranslationManager] LibreTranslate service not available, returning original text")
            return plot_text
        
        # Attempt translation
        translated_text = self.translator.translate_text(
            plot_text, 
            source_language, 
            target_language
        )
        
        if translated_text:
            # Cache the translation
            self.translation_cache[cache_key] = translated_text
            print(f"[TranslationManager] Successfully translated and cached plot text")
            return translated_text
        else:
            print(f"[TranslationManager] Translation failed, returning original text")
            return plot_text


# Global translation manager instance
_translation_manager = None

def get_translation_manager() -> TranslationManager:
    """Get global translation manager instance."""
    global _translation_manager
    if _translation_manager is None:
        _translation_manager = TranslationManager()
    return _translation_manager