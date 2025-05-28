#!/usr/bin/env python3
"""
Test script to demonstrate the translation functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.utils.translator import get_translation_manager

def test_translation():
    """Test the translation functionality."""
    print("Testing LibreTranslate Translation Functionality")
    print("=" * 50)
    
    # Get translation manager
    translation_manager = get_translation_manager()
    
    # Test if service is available
    print("\n1. Checking if LibreTranslate service is available...")
    is_available = translation_manager.translator.is_service_available()
    print(f"   Service available: {is_available}")
    
    if not is_available:
        print("   Note: LibreTranslate service is not available. This could be due to:")
        print("   - No internet connection")
        print("   - LibreTranslate public instance is down")
        print("   - Firewall blocking the request")
        print("\n   You can set up a local LibreTranslate instance for better reliability.")
        return
    
    # Test English to Arabic translation
    print("\n2. Testing English to Arabic translation...")
    english_plot = "A young detective investigates a series of mysterious crimes in the city. As he delves deeper into the case, he discovers a conspiracy that threatens everything he holds dear."
    
    print(f"   Original (English): {english_plot[:100]}...")
    
    arabic_translation = translation_manager.translate_plot(
        english_plot, 
        target_language='ar', 
        source_language='en'
    )
    
    if arabic_translation and arabic_translation != english_plot:
        print(f"   Translated (Arabic): {arabic_translation[:100]}...")
        print("   ✓ Translation successful!")
    else:
        print("   ✗ Translation failed or returned same text")
    
    # Test English to French translation
    print("\n3. Testing English to French translation...")
    french_translation = translation_manager.translate_plot(
        english_plot, 
        target_language='fr', 
        source_language='en'
    )
    
    if french_translation and french_translation != english_plot:
        print(f"   Translated (French): {french_translation[:100]}...")
        print("   ✓ Translation successful!")
    else:
        print("   ✗ Translation failed or returned same text")
    
    # Test caching
    print("\n4. Testing translation caching...")
    print("   Translating same text again (should use cache)...")
    
    cached_translation = translation_manager.translate_plot(
        english_plot, 
        target_language='ar', 
        source_language='en'
    )
    
    if cached_translation == arabic_translation:
        print("   ✓ Caching working correctly!")
    else:
        print("   ✗ Caching may not be working")
    
    print("\n5. Integration with IPTV Application:")
    print("   - When a series/movie is detected as non-English (Arabic, French, etc.)")
    print("   - And TMDB returns an English plot description")
    print("   - The application will automatically translate it to the detected language")
    print("   - Translations are cached to improve performance")
    print("   - If translation fails, the original English text is used")
    
    print("\n" + "=" * 50)
    print("Translation functionality test completed!")

if __name__ == "__main__":
    test_translation()