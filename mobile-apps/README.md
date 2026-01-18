# Passport Scanner Mobile Apps

Mobile applications for reading e-Passport NFC chips and submitting data to the booking system.

## Directory Structure

```
mobile-apps/
├── ios-passport-scanner/          # iOS App (Swift + SwiftUI)
│   └── PassportScanner/
│       ├── Models/                # Data models
│       ├── Views/                 # SwiftUI views
│       ├── ViewModels/            # Business logic
│       └── Services/              # NFC & API services
│
└── android-passport-scanner/      # Android App (Kotlin)
    └── app/src/main/
        ├── java/com/passportscanner/
        │   ├── models/            # Data models
        │   ├── ui/                # Activities & Fragments
        │   └── services/          # NFC & API services
        └── res/                   # Resources & layouts
```

## Features

- 📱 QR Code scanning to get session token
- 🔐 NFC passport chip reading (ICAO 9303 standard)
- ✅ Data validation and parsing
- 🌐 API integration with backend
- 🎨 Modern UI/UX

## Requirements

### iOS
- Xcode 15+
- iOS 13.0+
- Swift 5.9+
- Device with NFC capability

### Android
- Android Studio Hedgehog+
- Android 8.0+ (API 26+)
- Kotlin 1.9+
- Device with NFC capability

## Getting Started

See individual README files in each app directory for setup instructions.
