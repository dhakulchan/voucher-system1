//
//  QRScannerView.swift
//  PassportScanner
//
//  QR Code scanner view
//

import SwiftUI
import AVFoundation

struct QRScannerView: View {
    @Binding var sessionToken: String?
    @Environment(\.dismiss) var dismiss
    @StateObject private var scanner = QRCodeScanner()
    
    var body: some View {
        ZStack {
            // Camera preview
            QRCodeScannerViewRepresentable(scanner: scanner)
                .edgesIgnoringSafeArea(.all)
            
            // Overlay
            VStack {
                // Top bar
                HStack {
                    Spacer()
                    Button(action: {
                        dismiss()
                    }) {
                        Image(systemName: "xmark")
                            .font(.title2)
                            .foregroundColor(.white)
                            .padding()
                            .background(Color.black.opacity(0.6))
                            .clipShape(Circle())
                    }
                    .padding()
                }
                
                Spacer()
                
                // Instructions
                VStack(spacing: 10) {
                    Text("Scan QR Code")
                        .font(.title2)
                        .fontWeight(.bold)
                    
                    Text("Position the QR code within the frame")
                        .font(.subheadline)
                }
                .foregroundColor(.white)
                .padding()
                .background(Color.black.opacity(0.6))
                .cornerRadius(12)
                .padding(.bottom, 50)
            }
            
            // Scanning frame
            Rectangle()
                .stroke(Color.green, lineWidth: 3)
                .frame(width: 250, height: 250)
        }
        .onReceive(scanner.$scannedCode) { code in
            if let code = code {
                extractToken(from: code)
            }
        }
    }
    
    private func extractToken(from url: String) {
        // Extract token from URL: .../mobile/nfc-scan?token=xxx
        if let urlComponents = URLComponents(string: url),
           let token = urlComponents.queryItems?.first(where: { $0.name == "token" })?.value {
            sessionToken = token
            dismiss()
        }
    }
}

// MARK: - QR Code Scanner
class QRCodeScanner: NSObject, ObservableObject, AVCaptureMetadataOutputObjectsDelegate {
    @Published var scannedCode: String?
    
    var captureSession: AVCaptureSession?
    var previewLayer: AVCaptureVideoPreviewLayer?
    
    func setupCamera(in view: UIView) {
        let session = AVCaptureSession()
        
        guard let videoCaptureDevice = AVCaptureDevice.default(for: .video),
              let videoInput = try? AVCaptureDeviceInput(device: videoCaptureDevice),
              session.canAddInput(videoInput) else { return }
        
        session.addInput(videoInput)
        
        let metadataOutput = AVCaptureMetadataOutput()
        
        guard session.canAddOutput(metadataOutput) else { return }
        
        session.addOutput(metadataOutput)
        metadataOutput.setMetadataObjectsDelegate(self, queue: DispatchQueue.main)
        metadataOutput.metadataObjectTypes = [.qr]
        
        let previewLayer = AVCaptureVideoPreviewLayer(session: session)
        previewLayer.frame = view.layer.bounds
        previewLayer.videoGravity = .resizeAspectFill
        view.layer.addSublayer(previewLayer)
        
        self.captureSession = session
        self.previewLayer = previewLayer
        
        DispatchQueue.global(qos: .userInitiated).async {
            session.startRunning()
        }
    }
    
    func metadataOutput(_ output: AVCaptureMetadataOutput, didOutput metadataObjects: [AVMetadataObject], from connection: AVCaptureConnection) {
        if let metadataObject = metadataObjects.first,
           let readableObject = metadataObject as? AVMetadataMachineReadableCodeObject,
           let stringValue = readableObject.stringValue {
            scannedCode = stringValue
            captureSession?.stopRunning()
        }
    }
}

// MARK: - UIViewRepresentable
struct QRCodeScannerViewRepresentable: UIViewRepresentable {
    let scanner: QRCodeScanner
    
    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        scanner.setupCamera(in: view)
        return view
    }
    
    func updateUIView(_ uiView: UIView, context: Context) {}
}
