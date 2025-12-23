package com.sarvagya.mentalhealthchat.ui

import android.util.Log
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object RetrofitClient {
//s
//     private const val BASE_URL = "http://10.0.2.2:8001/"
//private const val BASE_URL = "http://192.168.1.3:8001/"
    private const val BASE_URL = "http://192.168.1.103:8001/"


    //    private const val BASE_URL = "https://mental-health-llm.onrender.com/"
//    private const val BASE_URL = "https://health-app-mjt7.onrender.com"
    private const val TAG = "RetrofitClient"

    // Resolve BuildConfig.DEBUG at runtime via reflection to avoid unresolved
    // reference compilation errors in some build setups. Falls back to true.
    private val isDebug: Boolean by lazy {
        try {
            val cls = Class.forName("com.sarvagya.mentalhealthchat.BuildConfig")
            val f = cls.getField("DEBUG")
            f.getBoolean(null)
        } catch (t: Throwable) {
            true
        }
    }

    // 🔥 Logging interceptor: use BASIC to reduce body dumps in production/dev
    private val logging = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BASIC
    }

    // 🔥 OkHttpClient with logging enabled
    private val client = OkHttpClient.Builder()
        .addInterceptor(logging)
        .connectTimeout(
            if (isDebug) 5 else 10,
            TimeUnit.SECONDS
        )
        .readTimeout(
            if (isDebug) 20 else 30,
            TimeUnit.SECONDS
        )
        .writeTimeout(
            if (isDebug) 10 else 15,
            TimeUnit.SECONDS
        )
        .callTimeout(
            if (isDebug) 25 else 40,
            TimeUnit.SECONDS
        )
        .retryOnConnectionFailure(!isDebug)
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
