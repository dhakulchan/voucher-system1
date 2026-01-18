# Passport Scanner - iOS App

Swift + SwiftUI application for reading e-Passport NFC chips.

## Requirements

- Xcode 15.0+
- iOS 13.0+
- iPhone 7 or later (NFC capability)
- Apple Developer Account (for NFC entitlements)

## Setup

### 1. Open Project
```bash
cd mobile-apps/ios-passport-scanner
open PassportScanner.xcodeproj
```

### 2. Install Dependencies

Add to `Package.swift`:
```swift
dependencies: [
    .package(url: "https://github.com/AndyQ/NFCPassportReader.git", from: "2.3.0"),
    .package(url: "https://github.com/WeTransfer/WeScan.git", from: "1.8.0")
]
```

### 3. Configure Capabilities

1. Select target → Signing & Capabilities
2. Add "Near Field Communication Tag Reading"
3. Add entitlement: `com.apple.developer.nfc.readersession.iso7816.select-identifiers`

### 4. Update Info.plist

```xml
<key>NFCReaderUsageDescription</key>
<string>We need NFC to read your passport chip</string>

<key>com.apple.developer.nfc.readersession.iso7816.select-identifiers</key>
<array>
    <string>A0000002471001</string>
</array>

<key>NSCameraUsageDescription</key>
<string>We need camera access to scan QR codes</string>
```

### 5. Update API Endpoint

Edit `Services/APIService.swift`:
```swift
static let baseURL = "https://yourdomain.com"  // Change this
```

### 6. Build & Run

1. Select your iPhone device
2. Press Cmd+R to build and run
3. Grant NFC and Camera permissions

## Architecture

- **MVVM Pattern**: Clean separation of concerns
- **SwiftUI**: Modern declarative UI
- **Combine**: Reactive programming
- **NFCPassportReader**: NFC chip reading library

## Key Files

- `PassportScannerApp.swift` - App entry point
- `ContentView.swift` - Main view
- `NFCService.swift` - NFC passport reading
- `APIService.swift` - Backend communication
- `PassportData.swift` - Data model

## Testing

Requires physical device with NFC capability. Simulator does not support NFC.

## Troubleshooting

### NFC not working
- Check device supports NFC (iPhone 7+)
- Verify NFC entitlements in Xcode
- Ensure Info.plist has correct keys
- Check iOS version (13.0+)

### API errors
- Verify baseURL is correct
- Check network connection
- Review backend logs
