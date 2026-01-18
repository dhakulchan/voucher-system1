//
//  NFCService.swift
//  PassportScanner
//
//  Service for reading e-Passport NFC chips
//

import Foundation
import CoreNFC
// import NFCPassportReader  // Add this package via Swift Package Manager

class NFCService: NSObject, ObservableObject {
    @Published var isReading = false
    @Published var statusMessage = ""
    @Published var passportData: PassportData?
    @Published var error: Error?
    
    private var nfcSession: NFCTagReaderSession?
    
    // MARK: - Start NFC Reading
    func startReading(completion: @escaping (Result<PassportData, Error>) -> Void) {
        guard NFCTagReaderSession.readingAvailable else {
            let error = NSError(
                domain: "NFCService",
                code: 1,
                userInfo: [NSLocalizedDescriptionKey: "NFC is not available on this device"]
            )
            completion(.failure(error))
            return
        }
        
        isReading = true
        statusMessage = "Ready to scan passport..."
        
        nfcSession = NFCTagReaderSession(
            pollingOption: [.iso14443],
            delegate: self,
            queue: nil
        )
        
        nfcSession?.alertMessage = "Hold your iPhone near the passport"
        nfcSession?.begin()
    }
    
    // MARK: - Cancel Reading
    func cancelReading() {
        nfcSession?.invalidate()
        isReading = false
    }
    
    // MARK: - Process Passport Data
    private func processPassportData(_ nfcPassport: NFCPassportModel) -> PassportData {
        // Convert NFC passport model to our PassportData model
        return PassportData(from: nfcPassport)
    }
}

// MARK: - NFCTagReaderSessionDelegate
extension NFCService: NFCTagReaderSessionDelegate {
    func tagReaderSessionDidBecomeActive(_ session: NFCTagReaderSession) {
        statusMessage = "NFC session active. Hold passport to back of iPhone..."
    }
    
    func tagReaderSession(_ session: NFCTagReaderSession, didInvalidateWithError error: Error) {
        isReading = false
        
        if let nfcError = error as? NFCReaderError {
            switch nfcError.code {
            case .readerSessionInvalidationErrorUserCanceled:
                statusMessage = "Scan cancelled"
            case .readerSessionInvalidationErrorSessionTimeout:
                statusMessage = "Scan timeout"
            default:
                self.error = error
                statusMessage = "Error: \(error.localizedDescription)"
            }
        }
    }
    
    func tagReaderSession(_ session: NFCTagReaderSession, didDetect tags: [NFCTag]) {
        guard let tag = tags.first else {
            session.invalidate(errorMessage: "No tags detected")
            return
        }
        
        session.connect(to: tag) { [weak self] error in
            if let error = error {
                session.invalidate(errorMessage: "Connection error: \(error.localizedDescription)")
                return
            }
            
            self?.statusMessage = "Connected to passport. Reading data..."
            
            // Here you would use NFCPassportReader library to read the chip
            // This is a simplified example - full implementation requires:
            // 1. Reading MRZ data (passport number, DOB, expiry)
            // 2. Computing BAC keys
            // 3. Reading DG1 (MRZ), DG2 (Photo), etc.
            
            /*
            Example with NFCPassportReader library:
            
            let passportReader = PassportReader()
            passportReader.readPassport(
                mrzKey: mrzKey,
                tags: tags,
                completed: { passport, error in
                    if let passport = passport {
                        let data = self?.processPassportData(passport)
                        self?.passportData = data
                        session.alertMessage = "Passport read successfully!"
                        session.invalidate()
                    } else {
                        session.invalidate(errorMessage: error?.localizedDescription ?? "Read failed")
                    }
                }
            )
            */
            
            // For now, create mock data
            DispatchQueue.main.asyncAfter(deadline: .now() + 2) {
                let mockNFCPassport = NFCPassportModel(
                    lastName: "SMITH",
                    firstName: "JOHN MICHAEL",
                    documentNumber: "AA1234567",
                    nationality: "USA",
                    dateOfBirth: "900115",
                    dateOfExpiry: "301231",
                    gender: "M",
                    issuingAuthority: "USA",
                    personalNumber: nil,
                    mrzLine1: "P<USASMITH<<JOHN<MICHAEL<<<<<<<<<<<<<<<<<<<<",
                    mrzLine2: "AA12345671USA9001155M3012319<<<<<<<<<<<<<<02"
                )
                
                let data = self?.processPassportData(mockNFCPassport)
                self?.passportData = data
                self?.statusMessage = "Read complete!"
                
                session.alertMessage = "✅ Passport read successfully!"
                session.invalidate()
            }
        }
    }
}
