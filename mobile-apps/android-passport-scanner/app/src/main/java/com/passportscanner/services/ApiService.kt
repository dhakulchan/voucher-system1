package com.passportscanner.services

import com.passportscanner.models.ApiResponse
import com.passportscanner.models.PassportSubmitRequest
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path
import java.util.concurrent.TimeUnit

/**
 * API Service for backend communication
 */
interface ApiService {
    
    @POST("api/passport/nfc/scanning/{token}")
    suspend fun updateScanningStatus(@Path("token") token: String): ApiResponse
    
    @POST("api/passport/nfc/submit")
    suspend fun submitPassportData(@Body request: PassportSubmitRequest): ApiResponse
    
    companion object {
        // TODO: Update this to your production domain
        private const val BASE_URL = "http://10.0.2.2:5001/"  // For Android emulator (localhost)
        // For physical device, use: "http://YOUR_COMPUTER_IP:5001/"
        // For production: "https://yourdomain.com/"
        
        fun create(): ApiService {
            val logging = HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            }
            
            val client = OkHttpClient.Builder()
                .addInterceptor(logging)
                .connectTimeout(30, TimeUnit.SECONDS)
                .readTimeout(30, TimeUnit.SECONDS)
                .writeTimeout(30, TimeUnit.SECONDS)
                .build()
            
            val retrofit = Retrofit.Builder()
                .baseUrl(BASE_URL)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
            
            return retrofit.create(ApiService::class.java)
        }
    }
}
