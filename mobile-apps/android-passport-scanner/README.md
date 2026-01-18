# Passport Scanner - Android App

Kotlin application for reading e-Passport NFC chips.

## Requirements

- Android Studio Hedgehog (2023.1.1) or later
- Android SDK 26+ (Android 8.0+)
- Kotlin 1.9+
- Device with NFC capability

## Setup

### 1. Open Project
```bash
cd mobile-apps/android-passport-scanner
# Open in Android Studio
```

### 2. Add Dependencies

Edit `app/build.gradle.kts`:
```kotlin
dependencies {
    // NFC Passport Reading
    implementation("org.jmrtd:jmrtd:0.7.34")
    implementation("com.madgag.spongycastle:prov:1.58.0.0")
    
    // QR Code Scanning
    implementation("com.google.mlkit:barcode-scanning:17.2.0")
    implementation("androidx.camera:camera-camera2:1.3.0")
    implementation("androidx.camera:camera-lifecycle:1.3.0")
    implementation("androidx.camera:camera-view:1.3.0")
    
    // Networking
    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.11.0")
    
    // Coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    
    // ViewModel
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.6.2")
    implementation("androidx.activity:activity-ktx:1.8.0")
}
```

### 3. Configure AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.NFC" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.INTERNET" />

<uses-feature
    android:name="android.hardware.nfc"
    android:required="true" />
<uses-feature
    android:name="android.hardware.camera"
    android:required="true" />

<application>
    <activity
        android:name=".ui.MainActivity"
        android:exported="true">
        <intent-filter>
            <action android:name="android.intent.action.MAIN" />
            <category android:name="android.intent.category.LAUNCHER" />
        </intent-filter>
        
        <!-- Deep link for QR code -->
        <intent-filter android:autoVerify="true">
            <action android:name="android.intent.action.VIEW" />
            <category android:name="android.intent.category.DEFAULT" />
            <category android:name="android.intent.category.BROWSABLE" />
            <data
                android:scheme="passportscanner"
                android:host="scan" />
        </intent-filter>
    </activity>
</application>
```

### 4. Update API Endpoint

Edit `services/ApiService.kt`:
```kotlin
private const val BASE_URL = "https://yourdomain.com/"  // Change this
```

### 5. Build & Run

1. Connect Android device with NFC
2. Enable USB debugging
3. Click Run in Android Studio
4. Grant Camera and NFC permissions

## Architecture

- **MVVM Pattern**: Clean architecture
- **Kotlin Coroutines**: Async operations
- **Retrofit**: REST API communication
- **CameraX**: QR code scanning
- **JMRTD**: NFC passport reading

## Key Files

- `MainActivity.kt` - Main activity
- `NFCReader.kt` - NFC passport reading
- `QRScanner.kt` - QR code scanning
- `ApiService.kt` - Backend communication
- `PassportData.kt` - Data model

## Testing

Requires physical device with NFC capability. Emulator does not support NFC.

## Troubleshooting

### NFC not working
- Check device supports NFC
- Enable NFC in device settings
- Verify permissions in manifest
- Check Android version (8.0+)

### Camera not working
- Grant camera permission
- Check camera availability
- Verify CameraX setup

### API errors
- Verify BASE_URL is correct
- Check network connection
- Review backend logs
