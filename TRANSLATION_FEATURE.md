# Translation Feature for IPTV Application

This document describes the automatic plot translation feature that has been added to the IPTV application.

## Overview

The application now automatically translates English plot descriptions from TMDB into the detected language of the series or movie. This provides a better user experience for non-English content.

## How It Works

### Language Detection

The application detects the content language using two methods:

1. **Keyword Detection**: Looks for language indicators in the series/movie name:
   - Arabic: `arabic`, `عربي`, `عرب`
   - French: `french`, `français`, `francais`
   - Spanish: `spanish`, `español`, `espanol`
   - German: `german`, `deutsch`
   - Italian: `italian`, `italiano`
   - Turkish: `turkish`, `türkçe`, `turkce`

2. **Language Field**: Checks for a `language` field in the series/movie metadata

### Translation Process

1. When TMDB returns an English plot description
2. And a non-English language is detected
3. The application attempts to translate the plot using LibreTranslate
4. If translation succeeds, the translated text is displayed
5. If translation fails, the original English text is used
6. All translations are cached for better performance

## Translation Service

### LibreTranslate

The application uses LibreTranslate, a free and open-source translation service:

- **Free**: No API key required for the public instance
- **Open Source**: Can be self-hosted for better reliability
- **Privacy-focused**: No data logging or tracking
- **Multiple Languages**: Supports many language pairs

### Supported Languages

- Arabic (ar)
- French (fr)
- Spanish (es)
- German (de)
- Italian (it)
- Turkish (tr)
- Portuguese (pt)
- Russian (ru)
- Japanese (ja)
- Korean (ko)
- Chinese (zh)

## Configuration

### API Key Requirement (Updated)
**Important**: As of late 2024, the public LibreTranslate instance requires an API key for translation requests.

#### Getting a Free API Key
1. Visit [LibreTranslate Portal](https://portal.libretranslate.com)
2. Sign up for a free account
3. Get your API key from the dashboard
4. The free tier typically includes a generous number of translation requests

#### Setting Up the API Key
To enable translation functionality, you need to provide the API key to the `TranslationManager`:

```python
# In your code, update the TranslationManager initialization:
translation_manager = TranslationManager(
    libre_translate_url="https://libretranslate.com",
    api_key="your-api-key-here"
)
```

### Self-Hosting LibreTranslate (Alternative)
For complete control and privacy, you can host your own LibreTranslate instance:

1. Follow the [LibreTranslate installation guide](https://github.com/LibreTranslate/LibreTranslate)
2. Update the `libre_translate_url` parameter in the `TranslationManager` initialization
3. Self-hosted instances may not require an API key depending on your configuration

1. **Docker Installation**:
   ```bash
   docker run -ti --rm -p 5000:5000 libretranslate/libretranslate
   ```

2. **Update Translation Manager**:
   ```python
   # In src/utils/translator.py, modify the default URL:
   _translation_manager = TranslationManager("http://localhost:5000")
   ```

### API Key (Optional)

If your LibreTranslate instance requires an API key:

1. Add to your `.env` file:
   ```
   LIBRETRANSLATE_API_KEY=your_api_key_here
   ```

2. Update the translation manager initialization:
   ```python
   import os
   api_key = os.getenv("LIBRETRANSLATE_API_KEY")
   _translation_manager = TranslationManager(api_key=api_key)
   ```

## Files Modified

### New Files
- `src/utils/translator.py`: Translation utility module
- `test_translation.py`: Test script for translation functionality

### Modified Files
- `src/ui/widgets/series_details_widget.py`: Added translation for series plots
- `src/ui/widgets/movie_details_widget.py`: Added translation for movie plots

## Testing

Run the test script to verify translation functionality:

```bash
python3 test_translation.py
```

This will:
- Check if LibreTranslate service is available
- Test English to Arabic translation
- Test English to French translation
- Verify caching functionality

## Troubleshooting

### Translation Not Working

1. **Check Internet Connection**: LibreTranslate requires internet access
2. **Service Availability**: The public instance may be temporarily down
3. **Language Detection**: Ensure the content language is properly detected
4. **Logs**: Check console output for translation error messages

### Performance Considerations

1. **Caching**: Translations are cached to avoid repeated API calls
2. **Fallback**: Original English text is used if translation fails
3. **Timeout**: Translation requests have a 30-second timeout

### Alternative Translation Services

If LibreTranslate is not suitable, the translation module can be extended to support:

- Google Translate API (requires API key)
- Microsoft Translator API (requires API key)
- DeepL API (requires API key)
- Amazon Translate (requires AWS credentials)

## Benefits

1. **Better User Experience**: Users see plot descriptions in their preferred language
2. **Automatic**: No manual intervention required
3. **Fallback**: Always shows content even if translation fails
4. **Performance**: Caching prevents repeated translation requests
5. **Privacy**: Can be self-hosted for complete data control
6. **Free**: No cost when using public LibreTranslate instance

## Future Enhancements

1. **Language Preference**: Allow users to set preferred language
2. **Translation Quality**: Add support for multiple translation services
3. **Offline Translation**: Integrate offline translation models
4. **UI Indicators**: Show when content is translated vs. original
5. **Manual Override**: Allow users to request translation manually