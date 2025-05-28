#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import re
from utils.translator import TranslationManager

def test_arabic_detection():
    """Test Arabic character detection and translation"""
    
    # Test Arabic series names
    test_names = [
        "فهد البطل",  # Fahd Al Batal
        "مسلسل عربي",  # Arabic Series
        "الحب لا يفهم الكلام",  # Love Doesn't Understand Words
        "English Series",  # Should not be detected as Arabic
        "Series with عربي keyword",  # Mixed with Arabic keyword
    ]
    
    # Arabic Unicode pattern (same as in the code)
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    
    print("=== Testing Arabic Character Detection ===")
    for name in test_names:
        has_arabic = bool(arabic_pattern.search(name))
        print(f"Series: '{name}' -> Arabic detected: {has_arabic}")
    
    print("\n=== Testing Translation Functionality ===")
    
    # Test translation
    translator = TranslationManager()
    
    # Test English to Arabic translation
    english_plot = "A young hero embarks on an epic adventure to save his kingdom from an ancient evil."
    
    print(f"Original English plot: {english_plot}")
    
    try:
        arabic_translation = translator.translate_plot(english_plot, target_language='ar')
        if arabic_translation:
            print(f"Arabic translation: {arabic_translation}")
        else:
            print("Translation failed or returned None")
    except Exception as e:
        print(f"Translation error: {e}")
    
    # Test caching
    print("\n=== Testing Translation Caching ===")
    try:
        cached_translation = translator.translate_plot(english_plot, target_language='ar')
        print(f"Cached translation: {cached_translation}")
        print(f"Cache size: {len(translator.translation_cache)}")
    except Exception as e:
        print(f"Cache test error: {e}")

if __name__ == "__main__":
    test_arabic_detection()