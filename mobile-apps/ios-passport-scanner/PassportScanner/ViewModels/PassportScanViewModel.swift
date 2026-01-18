//
//  PassportScanViewModel.swift
//  PassportScanner
//
//  ViewModel for handling passport scanning workflow
//

import SwiftUI
import Combine

class PassportScanViewModel: ObservableObject {
    @Published var sessionToken: String?
    @Published var isScanning = false
    @Published var showQRScanner = false
    @Published var showSuccessAlert = false
    @Published var showErrorAlert = false
    @Published var statusMessage = ""
    @Published var errorMessage = ""
    
    private let nfcService = NFCService()
    private let apiService = APIService.shared
    private var cancellables = Set<AnyCancellable>()
    
    var statusIcon: String {
        if isScanning {
            return "antenna.radiowaves.left.and.right"
        } else if sessionToken != nil {
            return "checkmark.circle.fill"
        } else {
            return "qrcode"
        }
    }
    
    var statusColor: Color {
        if isScanning {
            return .blue
        } else if sessionToken != nil {
            return .green
        } else {
            return .gray
        }
    }
    
    func startNFCReading() {
        guard let token = sessionToken else { return }
        
        isScanning = true
        statusMessage = "Preparing NFC reader..."
        
        // Notify server that scanning started
        apiService.updateScanningStatus(token: token)
            .sink(
                receiveCompletion: { completion in
                    if case .failure(let error) = completion {
                        print("Failed to update scanning status: \(error)")
                    }
                },
                receiveValue: { response in
                    print("Scanning status updated: \(response.success)")
                }
            )
            .store(in: &cancellables)
        
        // Start NFC reading
        statusMessage = "Hold passport to back of iPhone..."
        nfcService.startReading { [weak self] result in
            guard let self = self else { return }
            
            self.isScanning = false
            
            switch result {
            case .success(let passportData):
                self.statusMessage = "Passport read successfully! Sending data..."
                self.submitPassportData(passportData)
                
            case .failure(let error):
                self.errorMessage = error.localizedDescription
                self.showErrorAlert = true
                self.statusMessage = ""
            }
        }
        
        // Monitor NFC service status
        nfcService.$statusMessage
            .assign(to: &$statusMessage)
        
        nfcService.$passportData
            .compactMap { $0 }
            .sink { [weak self] passportData in
                self?.submitPassportData(passportData)
            }
            .store(in: &cancellables)
    }
    
    private func submitPassportData(_ data: PassportData) {
        guard let token = sessionToken else { return }
        
        apiService.submitPassportData(token: token, data: data)
            .sink(
                receiveCompletion: { [weak self] completion in
                    if case .failure(let error) = completion {
                        self?.errorMessage = "Failed to send data: \(error.localizedDescription)"
                        self?.showErrorAlert = true
                        self?.statusMessage = ""
                    }
                },
                receiveValue: { [weak self] response in
                    if response.success {
                        self?.statusMessage = "✅ Data sent successfully!"
                        self?.showSuccessAlert = true
                    } else {
                        self?.errorMessage = response.error ?? "Unknown error"
                        self?.showErrorAlert = true
                        self?.statusMessage = ""
                    }
                }
            )
            .store(in: &cancellables)
    }
    
    func reset() {
        sessionToken = nil
        isScanning = false
        statusMessage = ""
        errorMessage = ""
        showSuccessAlert = false
        showErrorAlert = false
    }
}
