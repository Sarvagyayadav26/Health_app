package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LoginActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_login)

        val emailEt = findViewById<EditText>(R.id.emailEt)
        val passwordEt = findViewById<EditText>(R.id.passwordEt)
        val loginBtn = findViewById<Button>(R.id.loginBtn)
        val registerText = findViewById<TextView>(R.id.registerText)

        // ⬅️ Go to Register screen
        registerText.setOnClickListener {
            startActivity(Intent(this, RegisterActivity::class.java))
            finish()
        }

        // ⬅️ Login button click
        loginBtn.setOnClickListener {

            val email = emailEt.text.toString().trim()
            val password = passwordEt.text.toString().trim()

            if (email.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please enter email & password", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val req = LoginRequest(email, password)

            RetrofitClient.instance.login(req)
                .enqueue(object : Callback<LoginResponse> {

                    override fun onResponse(
                        call: Call<LoginResponse>,
                        response: Response<LoginResponse>
                    ) {
                        val res = response.body()

                        if (response.isSuccessful && res?.success != null) {

                            val prefs = getSharedPreferences("app", MODE_PRIVATE)
                            val editor = prefs.edit()
                            
                            editor.putString("email", email)
                            
                            // Save chats from backend
                            val purchasedChats = res.chats ?: 0
                            editor.putInt("chats", purchasedChats)
                            
                            editor.apply()

                            startActivity(Intent(this@LoginActivity, HomeActivity::class.java))
                            finish()

                        } else {
                            // Show EXACT backend error ("User does not exist", "Incorrect password", etc.)
                            val errorMsg =
                                res?.error
                                    ?: response.errorBody()?.string()
                                    ?: "Login failed"

                            Toast.makeText(this@LoginActivity, errorMsg, Toast.LENGTH_SHORT).show()
                        }
                    }

                    override fun onFailure(call: Call<LoginResponse>, t: Throwable) {
                        Toast.makeText(
                            this@LoginActivity,
                            "Error: ${t.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                })
        }
    }
}
