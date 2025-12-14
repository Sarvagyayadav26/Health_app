package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val prefs = getSharedPreferences("app", MODE_PRIVATE)
        val email = prefs.getString("email", null)

        if (email != null) {
            // User already logged in → go to home
            startActivity(Intent(this, HomeActivity::class.java))
        } else {
            // User not logged in → go to login screen
            startActivity(Intent(this, LoginActivity::class.java))
        }

        finish()
    }
}
