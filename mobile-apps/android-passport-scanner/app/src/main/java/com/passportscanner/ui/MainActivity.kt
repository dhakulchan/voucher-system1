package com.passportscanner.ui

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import android.util.Log
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.passportscanner.databinding.ActivityMainBinding
import com.passportscanner.models.PassportData
import com.passportscanner.services.ApiService
import com.passportscanner.services.NFCReader
import kotlinx.coroutines.launch

/**
 * Main Activity
 * Handles QR scanning and NFC passport reading
 */
class MainActivity : AppCompatActivity() {
    
    private lateinit var binding: ActivityMainBinding
    private var nfcAdapter: NfcAdapter? = null
    private val nfcReader = NFCReader()
    private val apiService = ApiService.create()
    
    private var sessionToken: String? = null
    private var isScanning = false
    
    // Camera permission launcher
    private val cameraPermissionLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { isGranted ->
        if (isGranted) {
            startQRScanner()
        } else {
            Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
        }
    }
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        
        setupNFC()
        setupUI()
        handleIntent(intent)
    }
    
    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        handleIntent(intent)
    }
    
    override fun onResume() {
        super.onResume()
        enableNFCForegroundDispatch()
    }
    
    override fun onPause() {
        super.onPause()
        disableNFCForegroundDispatch()
    }
    
    private fun setupNFC() {
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)
        
        if (nfcAdapter == null) {
            showError("This device doesn't support NFC")
            binding.btnReadPassport.isEnabled = false
        } else if (nfcAdapter?.isEnabled == false) {
            showError("Please enable NFC in settings")
        }
    }
    
    private fun setupUI() {
        binding.btnScanQr.setOnClickListener {
            checkCameraPermissionAndScan()
        }
        
        binding.btnReadPassport.setOnClickListener {
            if (sessionToken != null) {
                startNFCReading()
            } else {
                showError("Please scan QR code first")
            }
        }
        
        binding.btnCancel.setOnClickListener {
            reset()
        }
        
        updateUI()
    }
    
    private fun handleIntent(intent: Intent?) {
        when (intent?.action) {
            NfcAdapter.ACTION_TAG_DISCOVERED,
            NfcAdapter.ACTION_TECH_DISCOVERED -> {
                handleNFCTag(intent)
            }
            Intent.ACTION_VIEW -> {
                // Handle deep link from QR code
                val token = intent.data?.getQueryParameter("token")
                if (token != null) {
                    sessionToken = token
                    updateUI()
                    updateStatus("✅ QR Code scanned! Ready to read passport.", StatusType.SUCCESS)
                }
            }
        }
    }
    
    private fun checkCameraPermissionAndScan() {
        when {
            ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.CAMERA
            ) == PackageManager.PERMISSION_GRANTED -> {
                startQRScanner()
            }
            else -> {
                cameraPermissionLauncher.launch(Manifest.permission.CAMERA)
            }
        }
    }
    
    private fun startQRScanner() {
        // TODO: Implement QR scanner using CameraX + MLKit
        // For now, show input dialog
        val builder = AlertDialog.Builder(this)
        val input = android.widget.EditText(this)
        input.hint = "Enter token from QR code"
        
        builder.setTitle("QR Code Scanner")
            .setMessage("In production, this will scan QR code automatically")
            .setView(input)
            .setPositiveButton("OK") { _, _ ->
                val token = input.text.toString().trim()
                if (token.isNotEmpty()) {
                    sessionToken = token
                    updateUI()
                    updateStatus("✅ Session token received", StatusType.SUCCESS)
                }
            }
            .setNegativeButton("Cancel", null)
            .show()
    }
    
    private fun startNFCReading() {
        if (isScanning) return
        
        isScanning = true
        updateUI()
        updateStatus("📱 Hold passport to back of phone...", StatusType.INFO)
        
        // Notify server
        lifecycleScope.launch {
            try {
                sessionToken?.let { token ->
                    apiService.updateScanningStatus(token)
                }
            } catch (e: Exception) {
                Log.e(TAG, "Failed to update scanning status", e)
            }
        }
    }
    
    private fun handleNFCTag(intent: Intent) {
        if (!isScanning) {
            updateStatus("⚠️ Please tap 'Read Passport' first", StatusType.WARNING)
            return
        }
        
        val tag: Tag? = intent.getParcelableExtra(NfcAdapter.EXTRA_TAG)
        if (tag == null) {
            showError("Failed to get NFC tag")
            return
        }
        
        updateStatus("🔄 Reading passport chip...", StatusType.INFO)
        
        lifecycleScope.launch {
            try {
                // For testing, use mock data
                // In production, you need to get MRZ data first, then call:
                // val passportData = nfcReader.readPassport(tag, docNumber, dob, expiry)
                
                val passportData = nfcReader.mockReadPassport()
                
                updateStatus("📤 Sending data to server...", StatusType.INFO)
                
                // Submit to server
                sessionToken?.let { token ->
                    val request = com.passportscanner.models.PassportSubmitRequest(
                        token = token,
                        data = passportData
                    )
                    
                    val response = apiService.submitPassportData(request)
                    
                    if (response.success) {
                        updateStatus("✅ Success! Data sent to server.", StatusType.SUCCESS)
                        showSuccessDialog()
                    } else {
                        showError(response.error ?: "Unknown error")
                    }
                }
                
                isScanning = false
                updateUI()
                
            } catch (e: Exception) {
                Log.e(TAG, "Error processing passport", e)
                showError("Failed to read passport: ${e.message}")
                isScanning = false
                updateUI()
            }
        }
    }
    
    private fun showSuccessDialog() {
        AlertDialog.Builder(this)
            .setTitle("Success")
            .setMessage("Passport data has been sent to the server successfully!")
            .setPositiveButton("OK") { _, _ ->
                reset()
            }
            .show()
    }
    
    private fun updateUI() {
        binding.apply {
            btnScanQr.visibility = if (sessionToken == null) View.VISIBLE else View.GONE
            btnReadPassport.visibility = if (sessionToken != null && !isScanning) View.VISIBLE else View.GONE
            btnCancel.visibility = if (sessionToken != null) View.VISIBLE else View.GONE
            progressBar.visibility = if (isScanning) View.VISIBLE else View.GONE
        }
    }
    
    private fun updateStatus(message: String, type: StatusType) {
        binding.tvStatus.text = message
        binding.tvStatus.visibility = View.VISIBLE
        
        val color = when (type) {
            StatusType.INFO -> android.graphics.Color.parseColor("#2196F3")
            StatusType.SUCCESS -> android.graphics.Color.parseColor("#4CAF50")
            StatusType.WARNING -> android.graphics.Color.parseColor("#FF9800")
            StatusType.ERROR -> android.graphics.Color.parseColor("#F44336")
        }
        binding.tvStatus.setTextColor(color)
    }
    
    private fun showError(message: String) {
        updateStatus("❌ $message", StatusType.ERROR)
        Toast.makeText(this, message, Toast.LENGTH_LONG).show()
    }
    
    private fun reset() {
        sessionToken = null
        isScanning = false
        binding.tvStatus.visibility = View.GONE
        updateUI()
    }
    
    private fun enableNFCForegroundDispatch() {
        nfcAdapter?.enableForegroundDispatch(
            this,
            android.app.PendingIntent.getActivity(
                this,
                0,
                Intent(this, javaClass).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
                android.app.PendingIntent.FLAG_MUTABLE
            ),
            null,
            null
        )
    }
    
    private fun disableNFCForegroundDispatch() {
        nfcAdapter?.disableForegroundDispatch(this)
    }
    
    enum class StatusType {
        INFO, SUCCESS, WARNING, ERROR
    }
    
    companion object {
        private const val TAG = "MainActivity"
    }
}
