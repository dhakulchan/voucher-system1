package com.passportscanner.models

import com.google.gson.annotations.SerializedName

/**
 * Passport data model
 */
data class PassportData(
    @SerializedName("full_name")
    val fullName: String,
    
    @SerializedName("passport_number")
    val passportNumber: String,
    
    @SerializedName("nationality")
    val nationality: String,
    
    @SerializedName("date_of_birth")
    val dateOfBirth: String,
    
    @SerializedName("expiry_date")
    val expiryDate: String,
    
    @SerializedName("sex")
    val sex: String,
    
    @SerializedName("issuing_country")
    val issuingCountry: String,
    
    @SerializedName("personal_number")
    val personalNumber: String? = null,
    
    @SerializedName("mrz_line1")
    val mrzLine1: String,
    
    @SerializedName("mrz_line2")
    val mrzLine2: String
) {
    companion object {
        /**
         * Convert MRZ date format (YYMMDD) to YYYY-MM-DD
         */
        fun formatMRZDate(mrzDate: String): String {
            if (mrzDate.length != 6) return ""
            
            val yy = mrzDate.substring(0, 2)
            val mm = mrzDate.substring(2, 4)
            val dd = mrzDate.substring(4, 6)
            
            // Determine century (assume 20xx for 00-30, 19xx for 31-99)
            val year = yy.toIntOrNull() ?: 0
            val yyyy = if (year <= 30) "20$yy" else "19$yy"
            
            return "$yyyy-$mm-$dd"
        }
    }
}

/**
 * API Request wrapper
 */
data class PassportSubmitRequest(
    val token: String,
    val data: PassportData
)

/**
 * API Response
 */
data class ApiResponse(
    val success: Boolean,
    val message: String? = null,
    val error: String? = null
)

/**
 * Session response
 */
data class SessionResponse(
    val success: Boolean,
    @SerializedName("session_token")
    val sessionToken: String? = null,
    @SerializedName("expires_in")
    val expiresIn: Int? = null,
    @SerializedName("qr_url")
    val qrUrl: String? = null,
    val error: String? = null
)
