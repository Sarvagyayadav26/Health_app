package com.sarvagya.mentalhealthchat.ui

import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {

     private const val BASE_URL = "http://10.0.2.2:8000/"
//    private const val BASE_URL = "https://mental-health-llm.onrender.com/"

    // 🔥 Logging interceptor to see ALL network requests in Logcat
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    // 🔥 OkHttpClient with logging enabled
    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        .build()

    // 🔥 Retrofit instance
    val instance: ApiService by lazy {
        println("🔥 DEBUG: RetrofitClient INSTANCE CREATED")
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)  // attach OkHttp client with logging
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
//sarvagya
