//
//  APIService.swift
//  PassportScanner
//
//  Service for communicating with backend API
//

import Foundation
import Combine

class APIService {
    static let shared = APIService()
    
    // TODO: Update this to your production domain
    private let baseURL = "http://localhost:5001"  // Change for production
    
    private init() {}
    
    // MARK: - Update Scanning Status
    func updateScanningStatus(token: String) -> AnyPublisher<APIResponse, Error> {
        guard let url = URL(string: "\(baseURL)/api/passport/nfc/scanning/\(token)") else {
            return Fail(error: URLError(.badURL)).eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: APIResponse.self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
    
    // MARK: - Submit Passport Data
    func submitPassportData(token: String, data: PassportData) -> AnyPublisher<APIResponse, Error> {
        guard let url = URL(string: "\(baseURL)/api/passport/nfc/submit") else {
            return Fail(error: URLError(.badURL)).eraseToAnyPublisher()
        }
        
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let payload: [String: Any] = [
            "token": token,
            "data": [
                "full_name": data.fullName,
                "passport_number": data.passportNumber,
                "nationality": data.nationality,
                "date_of_birth": data.dateOfBirth,
                "expiry_date": data.expiryDate,
                "sex": data.sex,
                "issuing_country": data.issuingCountry,
                "personal_number": data.personalNumber ?? "",
                "mrz_line1": data.mrzLine1,
                "mrz_line2": data.mrzLine2
            ]
        ]
        
        do {
            request.httpBody = try JSONSerialization.data(withJSONObject: payload)
        } catch {
            return Fail(error: error).eraseToAnyPublisher()
        }
        
        return URLSession.shared.dataTaskPublisher(for: request)
            .map(\.data)
            .decode(type: APIResponse.self, decoder: JSONDecoder())
            .receive(on: DispatchQueue.main)
            .eraseToAnyPublisher()
    }
}
