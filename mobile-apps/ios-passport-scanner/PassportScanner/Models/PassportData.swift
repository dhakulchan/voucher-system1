//
//  PassportData.swift
//  PassportScanner
//
//  Data model for passport information
//

import Foundation

struct PassportData: Codable {
    let fullName: String
    let passportNumber: String
    let nationality: String
    let dateOfBirth: String
    let expiryDate: String
    let sex: String
    let issuingCountry: String
    let personalNumber: String?
    let mrzLine1: String
    let mrzLine2: String
    
    enum CodingKeys: String, CodingKey {
        case fullName = "full_name"
        case passportNumber = "passport_number"
        case nationality
        case dateOfBirth = "date_of_birth"
        case expiryDate = "expiry_date"
        case sex
        case issuingCountry = "issuing_country"
        case personalNumber = "personal_number"
        case mrzLine1 = "mrz_line1"
        case mrzLine2 = "mrz_line2"
    }
    
    init(from nfcPassport: NFCPassportModel) {
        // Extract data from NFC passport model
        let surname = nfcPassport.lastName ?? ""
        let givenNames = nfcPassport.firstName ?? ""
        self.fullName = "\(surname), \(givenNames)"
        
        self.passportNumber = nfcPassport.documentNumber ?? ""
        self.nationality = nfcPassport.nationality ?? ""
        
        // Format dates to YYYY-MM-DD
        self.dateOfBirth = Self.formatDate(nfcPassport.dateOfBirth ?? "")
        self.expiryDate = Self.formatDate(nfcPassport.dateOfExpiry ?? "")
        
        self.sex = nfcPassport.gender ?? ""
        self.issuingCountry = nfcPassport.issuingAuthority ?? ""
        self.personalNumber = nfcPassport.personalNumber
        
        // MRZ lines
        self.mrzLine1 = nfcPassport.mrzLine1 ?? ""
        self.mrzLine2 = nfcPassport.mrzLine2 ?? ""
    }
    
    private static func formatDate(_ mrzDate: String) -> String {
        // MRZ date format: YYMMDD
        // Convert to: YYYY-MM-DD
        guard mrzDate.count == 6 else { return "" }
        
        let yy = String(mrzDate.prefix(2))
        let mm = String(mrzDate.dropFirst(2).prefix(2))
        let dd = String(mrzDate.dropFirst(4))
        
        // Determine century (assume 20xx for 00-30, 19xx for 31-99)
        let year = Int(yy) ?? 0
        let yyyy = year <= 30 ? "20\(yy)" : "19\(yy)"
        
        return "\(yyyy)-\(mm)-\(dd)"
    }
}

// NFCPassportModel placeholder - will be provided by NFCPassportReader library
struct NFCPassportModel {
    var lastName: String?
    var firstName: String?
    var documentNumber: String?
    var nationality: String?
    var dateOfBirth: String?
    var dateOfExpiry: String?
    var gender: String?
    var issuingAuthority: String?
    var personalNumber: String?
    var mrzLine1: String?
    var mrzLine2: String?
}

struct SessionResponse: Codable {
    let success: Bool
    let sessionToken: String?
    let expiresIn: Int?
    let qrUrl: String?
    let error: String?
    
    enum CodingKeys: String, CodingKey {
        case success
        case sessionToken = "session_token"
        case expiresIn = "expires_in"
        case qrUrl = "qr_url"
        case error
    }
}

struct APIResponse: Codable {
    let success: Bool
    let message: String?
    let error: String?
}
