package com.sarvagya.mentalhealthchat.ui

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {

//     private const val BASE_URL = "http://10.0.2.2:8001/"
//    private const val BASE_URL = "https://mental-health-llm.onrender.com/"
    private const val BASE_URL = "https://health-app-mjt7.onrender.com"
    private const val TAG = "RetrofitClient"

    // 🔥 Logging interceptor: use BASIC to reduce body dumps in production/dev
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }

    // 🔥 OkHttpClient with logging enabled
    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(30, TimeUnit.SECONDS)
        .callTimeout(40, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build()


    // 🔥 Retrofit instance
    val instance: ApiService by lazy {
        Log.d(TAG, "DEBUG: RetrofitClient INSTANCE CREATED")
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)  // attach OkHttp client with logging
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(ApiService::class.java)
    }
}
//sarvagya
