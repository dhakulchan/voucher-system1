package com.passportscanner.services

import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.util.Log
import com.passportscanner.models.PassportData
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import net.sf.scuba.smartcards.CardService
import org.jmrtd.BACKey
import org.jmrtd.PassportService
import org.jmrtd.lds.icao.DG1File
import org.jmrtd.lds.icao.MRZInfo
import java.io.InputStream

/**
 * NFC Passport Reader
 * Reads e-Passport chip data using JMRTD library
 */
class NFCReader {
    
    companion object {
        private const val TAG = "NFCReader"
    }
    
    /**
     * Read passport data from NFC tag
     * 
     * @param tag NFC tag from intent
     * @param documentNumber Passport number from MRZ
     * @param dateOfBirth DOB in YYMMDD format
     * @param dateOfExpiry Expiry in YYMMDD format
     * @return PassportData or null if read fails
     */
    suspend fun readPassport(
        tag: Tag,
        documentNumber: String,
        dateOfBirth: String,
        dateOfExpiry: String
    ): PassportData? = withContext(Dispatchers.IO) {
        try {
            Log.d(TAG, "Starting passport read...")
            
            // Get IsoDep tag
            val isoDep = IsoDep.get(tag) ?: run {
                Log.e(TAG, "IsoDep not available")
                return@withContext null
            }
            
            // Connect to tag
            isoDep.connect()
            Log.d(TAG, "Connected to NFC tag")
            
            // Create BAC key from MRZ data
            val bacKey = BACKey(documentNumber, dateOfBirth, dateOfExpiry)
            
            // Create card service
            val cardService = CardService.getInstance(isoDep)
            cardService.open()
            
            // Create passport service
            val passportService = PassportService(
                cardService,
                PassportService.NORMAL_MAX_TRANCEIVE_LENGTH,
                PassportService.DEFAULT_MAX_BLOCKSIZE,
                false,
                false
            )
            
            passportService.open()
            
            // Perform BAC (Basic Access Control)
            Log.d(TAG, "Performing BAC...")
            passportService.sendSelectApplet(false)
            passportService.doBAC(bacKey)
            
            Log.d(TAG, "BAC successful, reading DG1...")
            
            // Read DG1 (MRZ data)
            val dg1InputStream: InputStream = passportService.getInputStream(
                PassportService.EF_DG1,
                PassportService.DEFAULT_MAX_BLOCKSIZE
            )
            
            val dg1File = DG1File(dg1InputStream)
            val mrzInfo: MRZInfo = dg1File.mrzInfo
            
            Log.d(TAG, "Successfully read passport data")
            
            // Convert to PassportData
            val passportData = PassportData(
                fullName = "${mrzInfo.primaryIdentifier}, ${mrzInfo.secondaryIdentifier}",
                passportNumber = mrzInfo.documentNumber,
                nationality = mrzInfo.nationality,
                dateOfBirth = PassportData.formatMRZDate(mrzInfo.dateOfBirth),
                expiryDate = PassportData.formatMRZDate(mrzInfo.dateOfExpiry),
                sex = mrzInfo.gender.toString(),
                issuingCountry = mrzInfo.issuingState,
                personalNumber = mrzInfo.personalNumber,
                mrzLine1 = mrzInfo.toString().lines().getOrNull(0) ?: "",
                mrzLine2 = mrzInfo.toString().lines().getOrNull(1) ?: ""
            )
            
            // Close connections
            passportService.close()
            cardService.close()
            isoDep.close()
            
            return@withContext passportData
            
        } catch (e: Exception) {
            Log.e(TAG, "Error reading passport", e)
            return@withContext null
        }
    }
    
    /**
     * Simplified mock read for testing without actual passport
     */
    suspend fun mockReadPassport(): PassportData = withContext(Dispatchers.IO) {
        // Simulate reading delay
        kotlinx.coroutines.delay(2000)
        
        PassportData(
            fullName = "SMITH, JOHN MICHAEL",
            passportNumber = "AA1234567",
            nationality = "USA",
            dateOfBirth = "1990-01-15",
            expiryDate = "2030-12-31",
            sex = "M",
            issuingCountry = "USA",
            personalNumber = null,
            mrzLine1 = "P<USASMITH<<JOHN<MICHAEL<<<<<<<<<<<<<<<<<<<<",
            mrzLine2 = "AA12345671USA9001155M3012319<<<<<<<<<<<<<<02"
        )
    }
}
