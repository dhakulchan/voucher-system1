//
//  ContentView.swift
//  PassportScanner
//
//  Main view with QR scanner and NFC reader
//

import SwiftUI
import AVFoundation

struct ContentView: View {
    @StateObject private var viewModel = PassportScanViewModel()
    
    var body: some View {
        NavigationView {
            VStack(spacing: 20) {
                // Header
                VStack {
                    Image(systemName: "person.text.rectangle")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)
                    
                    Text("Passport Scanner")
                        .font(.title)
                        .fontWeight(.bold)
                    
                    Text("Scan QR code to start")
                        .font(.subheadline)
                        .foregroundColor(.gray)
                }
                .padding(.top, 40)
                
                // Status Display
                if !viewModel.statusMessage.isEmpty {
                    StatusCardView(
                        icon: viewModel.statusIcon,
                        message: viewModel.statusMessage,
                        color: viewModel.statusColor
                    )
                    .padding(.horizontal)
                }
                
                Spacer()
                
                // Action Buttons
                VStack(spacing: 15) {
                    if viewModel.sessionToken == nil {
                        // Scan QR Code Button
                        Button(action: {
                            viewModel.showQRScanner = true
                        }) {
                            Label("Scan QR Code", systemImage: "qrcode.viewfinder")
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.blue)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                        }
                    } else if !viewModel.isScanning {
                        // Read Passport Button
                        Button(action: {
                            viewModel.startNFCReading()
                        }) {
                            Label("Read Passport NFC", systemImage: "wave.3.right")
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.green)
                                .foregroundColor(.white)
                                .cornerRadius(12)
                        }
                    }
                    
                    // Cancel/Reset Button
                    if viewModel.sessionToken != nil {
                        Button(action: {
                            viewModel.reset()
                        }) {
                            Text("Cancel")
                                .frame(maxWidth: .infinity)
                                .padding()
                                .background(Color.gray.opacity(0.2))
                                .foregroundColor(.red)
                                .cornerRadius(12)
                        }
                    }
                }
                .padding(.horizontal, 30)
                .padding(.bottom, 40)
            }
            .navigationBarHidden(true)
            .sheet(isPresented: $viewModel.showQRScanner) {
                QRScannerView(sessionToken: $viewModel.sessionToken)
            }
            .alert("Success", isPresented: $viewModel.showSuccessAlert) {
                Button("OK") {
                    viewModel.reset()
                }
            } message: {
                Text("Passport data has been sent to the server successfully!")
            }
            .alert("Error", isPresented: $viewModel.showErrorAlert) {
                Button("OK") {}
            } message: {
                Text(viewModel.errorMessage)
            }
        }
    }
}

// MARK: - Status Card View
struct StatusCardView: View {
    let icon: String
    let message: String
    let color: Color
    
    var body: some View {
        HStack {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(color)
            
            Text(message)
                .font(.body)
                .foregroundColor(.primary)
            
            Spacer()
        }
        .padding()
        .background(color.opacity(0.1))
        .cornerRadius(10)
    }
}

// MARK: - Preview
struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
