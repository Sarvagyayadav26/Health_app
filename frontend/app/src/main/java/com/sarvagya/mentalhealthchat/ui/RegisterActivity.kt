package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import org.json.JSONObject
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class RegisterActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_register)

        val emailEt = findViewById<EditText>(R.id.emailEt)
        val ageEt = findViewById<EditText>(R.id.ageEt)
        val sexEt = findViewById<EditText>(R.id.sexEt)
        val passwordEt = findViewById<EditText>(R.id.passwordEt)
        val registerBtn = findViewById<Button>(R.id.registerBtn)
        val loginText = findViewById<TextView>(R.id.loginText)

        loginText.setOnClickListener {
            startActivity(Intent(this, LoginActivity::class.java))
            finish()
        }

        registerBtn.setOnClickListener {

            val email = emailEt.text.toString().trim()
            val ageText = ageEt.text.toString().trim()
            val sex = sexEt.text.toString().trim()
            val password = passwordEt.text.toString().trim()

            if (email.isEmpty() || ageText.isEmpty() || sex.isEmpty() || password.isEmpty()) {
                Toast.makeText(this, "Please fill all fields", Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            val age = ageText.toInt()

            val req = RegisterRequest(
                email = email,
                age = age,
                sex = sex,
                password = password
            )

            val api = RetrofitClient.instance

            api.register(req).enqueue(object : Callback<BasicResponse> {

                override fun onResponse(
                    call: Call<BasicResponse>,
                    response: Response<BasicResponse>
                ) {

                    val res = response.body()

                    if (response.isSuccessful && res?.success != null) {

                        Toast.makeText(
                            this@RegisterActivity,
                            res.success,
                            Toast.LENGTH_SHORT
                        ).show()

                        // Generate username from email
                        val generatedName = email.substringBefore("@").replaceFirstChar { it.uppercase() }

                        // Save email AND name locally for personalization
                        getSharedPreferences("app", MODE_PRIVATE)
                            .edit()
                            .putString("email", email)
                            .putString("username", generatedName)
                            .apply()

                        startActivity(Intent(this@RegisterActivity, HomeActivity::class.java))
                        finish()

                    } else {

                        // 🔥 Parse backend error message
                        val errorJson = response.errorBody()?.string()
                        val message = try {
                            JSONObject(errorJson).getString("error")
                        } catch (e: Exception) {
                            "Registration failed"
                        }

                        Toast.makeText(
                            this@RegisterActivity,
                            message,
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }

                override fun onFailure(call: Call<BasicResponse>, t: Throwable) {
                    Toast.makeText(
                        this@RegisterActivity,
                        "Error: ${t.message}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            })
        }
    }
}
