# Product Requirements Document (PRD): Sahab IPTV

## 1. Product Overview
**Product Name:** Sahab IPTV
**Description:** A modern, feature-rich, and highly responsive Crossplatform IPTV player tailored for the Xtream Codes API. It allows seamless consumption of Live TV, Movies (VOD), and TV Series. Sahab IPTV is fully cross-platform and uniquely distinguishes itself by providing an ultra-premium UX (similar to modern streaming giants) enriched with third-party metadata and on-the-fly translations.
**Target Platforms:** Windows, macOS, Linux (Desktop), Android (TV, Boxes)

## 2. Product Vision & Goals
* **Best-in-Class UX:** Implement an immersive, sleek, and intuitive user interface inspired by world-class streaming platforms (e.g., Netflix, Apple TV, Plex). This includes fluid animations, hero banners, frosted glass overlays, and impeccable spatial navigation tailored for TV screens as well as desktops.
* **Information Richness:** Ensure every movie or series feels like a premium VOD platform by enriching sparse Xtream Codes data with detailed TMDB metadata (posters, backdrops, cast, ratings, trailers).
* **Accessibility:** Break language barriers with automatic language detection and translation of plot summaries via LibreTranslate.
* **Performance:** Deliver lightning-fast navigation, rapid video playback, and zero UI stuttering through smart caching, asynchronous data fetching, and an extremely optimal rendering engine.

## 3. Target Audience
* IPTV subscribers looking for an organized, responsive player.
* International users needing localized metadata and plot translations.
* Power users who want features like favorites, offline downloads, and seamless navigation with remote controls.
* Android TV / Set-top box owners who need an app strictly optimized for D-Pad navigation.

---

## 4. Feature Requirements

### 4.1 Authentication & Profile Management
* **Credentials:** Accept Server URL, Username, and Password based on Xtream API standards. Multiple profiles/servers support.
* **User Settings:** Persist configurations such as default language, volume, subtitle appearance, hardware acceleration toggles, and caching limits securely on the local device.

### 4.2 Content Libraries & Navigation
The UI will feature a main sidebar (collapsible) or top-rail navigation, with distinct feature tabs:
* **Live TV:** Directory of live channel categories with immediate playback capabilities, complete EPG (Electronic Program Guide) timeline views, and localized channel icons. 
* **Movies (VOD):** Netflix-style grid view and horizontal scrolling carousels (e.g., "Recently Added", "Trending"). Features Hero banners at the top of the screen showcasing a featured movie.
* **Series:** Similar to Movies, but with a highly intuitive season and episode selector. Tracks user's watch progress (e.g., "Resume watching S02E04").

### 4.3 Media Playback Engine
* **Integration:** Native embedding of high-performance media players that best fit the seamless watching experience on all target platforms (e.g., standardizing on a cross-platform engine like `libmpv` wrapped in the application layer).
* **Controls:** TV-optimized On-Screen Display (OSD), Play/Pause, Seek, Volume/Brightness swipe controls (for touch/mouse) or D-Pad steps.
* **Format Support:** Must seamlessly handle HLS, TS, M3U8 streams, and various VOD codecs without external dependencies.
* **VOD Downloading & Recording:** Capability to queue and download VOD movies or episodes for offline viewing.

### 4.4 Metadata Enrichment (TMDB API)
* Retrieve extensive metrics: Backdrop backgrounds, high-res posters, cast/crew, genres, and TMDB voting scores.
* **Data Consistency:** Use strict Data Models to parse API data robustly, mitigating Missing-Key errors from sparse databases and gracefully degrading when TMDB lacks info.

### 4.5 Localization & Translation
* **Auto-Translation:** English plots fetched from TMDB/Xtream must be dynamically translated based on detected series language flags via LibreTranslate.
* **Multi-Language Support (i18n):** Complete RTL (Right-to-Left) support for Arabic, combined with dynamic LTR for English/French based on the user's system or app preference.

### 4.6 Offline & Caching Architecture
* **Aggressive Structured Caching:** Utilize a high-performance local database to index channels, EPG data, and history to eliminate redundant network overhead and ensure instant app startup.
* **Image Caching & Preloading:** Load and store image files asynchronously. Low-resolution placeholders should load instantly, fading smoothly into high-res images.

### 4.7 Monetization Strategy (Foundation for Future)
The app architecture must be designed to eventually support native business models once critical mass is achieved:
* **Free Version:** Integrations for Ad-SDKs (e.g., Google IMA SDK) to handle pre-roll, mid-roll, and overlay in-video ads for viewers in the free tier without completely breaking the UX immersion.
* **Pro Subscription Tier:** System capable of validating RevenueCat/In-App-Purchase receipts to unlock Premium logic. Premium features will include: No Ads, advanced VOD downloading limits, PIP (Picture in Picture), and Multi-Account switching capabilities.

### 4.8 Analytics & User Behavior Tracking
* **Data Telemetry:** Integrate an analytics suite (e.g., Firebase Analytics, PostHog, or Mixpanel) to intelligently track app usage while respecting user privacy.
* **Key Metrics:** Monitor feature usage drops, error crash rates (Sentry/Crashlytics), video playback buffers, and most-navigated tabs. This telemetry dictates exactly which UX elements to improve over time.

---

## 5. Non-Functional Requirements (NFR)

### 5.1 UI/UX Standards (The Benchmark)
* **TV & Desktop Unified Navigation:** The UI must natively support Focus Management. Every element must be reachable and clearly highlighted via a Keyboard or Android TV Remote Control (D-Pad), while simultaneously feeling natural for a Desktop Mouse/Touchpad pointer.
* **Micro-interactions:** Use Hero transitions between grid items and their detail pages. Add subtle scaling/glow effects on button/card focus.
* **Aspect Ratios & Grids:** Responsive layouts that automatically adapt from wide desktop monitors down to standard Android TV 16:9 displays, utilizing masonry or virtualized grids.

### 5.2 Software Architecture (Best Practices)
Use **Clean Architecture** combined with a robust, predictable State Management system to guarantee scalability and maintainability:
* **Presentation Layer:** Views (Screens/Widgets), ViewModels (State Holders / Controllers). This layer strictly handles UI and user input.
* **Domain Layer:** Business Rules, Entities (Movies, LiveChannels), and abstract Repository interfaces. Independent of any framework.
* **Data Layer:** API Data Sources (Xtream, TMDB, Ads), Local Storage Data Sources (SQLite DBs), and implementation of Repositories.
* **Dependency Injection:** Centralized registry for all services and repositories.

### 5.3 Reliability & Resilience
* **Error Handling:** Centralized error handling. Never crash on missing remote data; implement graceful UI fallbacks.
* **Performance:** Ensure 60fps/120fps UI rendering across all platforms.

### 5.4 Security & App Protection
If the app serves as a gateway to premium content or a paid model, protection is exceptionally crucial:
* **Code Obfuscation:** The build process must aggressively obfuscate source code (e.g., Dart `--obfuscate`) and strip debug symbols to thwart reverse engineering.
* **Environment Integrity:** Implement RASP (Runtime Application Self-Protection) such as FreeRASP. Include Root/Jailbreak detection on mobile/TV OS to prevent modded setups from bypassing premium checks.
* **Network & API Security:** Enforce strict SSL Certificate Pinning. Mitigate MITM (Man-in-the-Middle) proxy interception to secure Xtream credentials and internal App Revenue endpoints.

---

## 6. Recommended Technology Stack (From Scratch)
To achieve the "Best in the World" standard, supporting Android TV & Desktop with incredible UI performance out-of-the-box:

* **Core Framework:** **Flutter (Dart)** - Native compilation for Desktop/Android, exceptional tooling for complex animations, and perfect for creating Netflix-like interfaces.
* **Video Playback Engine:** `media_kit` (A highly optimized Flutter wrapper around the robust `libmpv` engine).
* **Architecture / State Management:** **Clean Architecture** paired with `flutter_bloc` or `Riverpod`.
* **Dependency Injection:** `get_it` and `injectable`.
* **Local Storage / Caching:** `Isar Database` or `sqflite`.
* **Networking, Ads, & Telemetry:** `dio` for HTTP, `google_mobile_ads` for potential monetization, `firebase_analytics` / `firebase_crashlytics` for monitoring.

## 7. Future Expansions
1. **Cloud Account Sync:** Seamless account synchronization powered by a cloud backend (e.g., Firebase Auth/Firestore or Supabase). This will allow users to log in and sync their favorites, UI settings, watch history, and multiple Xtream accounts across Desktop and Android TV simultaneously.
2. Advanced AI content recommendations based on watch history.
3. Custom M3U playlist file ingestion handling. 
4. Parent-controlled PIN lock for categorized profiles.

---
*Created per high software production standards to guide the foundational rebuild of Sahab IPTV.*
