#!/usr/bin/env python3

import sys
sys.path.append('.')

from src.api.tmdb import TMDBClient

print("Testing TMDB client...")
try:
    client = TMDBClient()
    print("TMDB client created successfully")
    
    # Test with Game of Thrones TMDB ID
    tmdb_id = "1399"
    print(f"Testing get_series_credits with ID: {tmdb_id}")
    
    credits = client.get_series_credits(tmdb_id)
    print(f"Credits result type: {type(credits)}")
    
    if credits:
        print(f"Credits keys: {list(credits.keys())}")
        if 'cast' in credits:
            print(f"Cast count: {len(credits['cast'])}")
            if credits['cast']:
                print(f"First cast member: {credits['cast'][0]}")
        else:
            print("No 'cast' key found in credits")
    else:
        print("No credits returned")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()