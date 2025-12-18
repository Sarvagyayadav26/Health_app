package com.sarvagya.mentalhealthchat.ui

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.sarvagya.mentalhealthchat.R
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

/**
 * Test version of subscription without Google Play
 * Use this to test the flow with your backend first
 */
class SubscriptionTestActivity : AppCompatActivity() {

    private lateinit var buy10Btn: Button
    private lateinit var buy5Btn: Button
    private lateinit var proPackText: TextView
    private lateinit var statusText: TextView

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_subscription)

        buy10Btn = findViewById(R.id.buy10Btn)
        buy5Btn = findViewById(R.id.buy5Btn)
        proPackText = findViewById(R.id.proPackText)
        statusText = findViewById(R.id.statusText)

        val backBtn = findViewById<Button>(R.id.backBtn)
        backBtn.setOnClickListener { finish() }

        // Display test pricing
        proPackText.text = "10 Chats - $2.99"

        // Check for remaining chats from Intent
        val remaining = intent.getIntExtra("CHATS", -1)
        if (remaining >= 0) {
            statusText.text = "You have $remaining chats remaining"
        } else {
            statusText.text = "Please select a plan to continue"
        }

        // Buy 10 chats
        buy10Btn.setOnClickListener {
            performTestPurchase("mental_health_10_chats")
        }
        
        // Buy 5 chats
        buy5Btn.setOnClickListener {
            performTestPurchase("mental_health_5_chats")
        }
    }

    private fun performTestPurchase(productId: String) {
        val email = getSharedPreferences("app", MODE_PRIVATE).getString("email", null)
        
        if (email == null) {
            Toast.makeText(this, "No user email found", Toast.LENGTH_SHORT).show()
            return
        }

        // Call your backend to add chats (test mode)
        val api = RetrofitClient.instance
        val req = PurchaseRequest(
            email = email,
            purchase_token = "test_token_${System.currentTimeMillis()}",
            product_id = productId
        )

        api.verifyPurchase(req).enqueue(object : Callback<PurchaseResponse> {
            override fun onResponse(
                call: Call<PurchaseResponse>,
                response: Response<PurchaseResponse>
            ) {
                if (response.isSuccessful && response.body()?.success == true) {
                    val res = response.body()!!
                    Toast.makeText(
                        this@SubscriptionTestActivity,
                        "Success! Added ${res.chats_added} chats",
                        Toast.LENGTH_LONG
                    ).show()
                    
                    // Save updated chats to SharedPreferences
                    val newChats = res.remaining_chats ?: 0
                    getSharedPreferences("app", MODE_PRIVATE)
                        .edit()
                        .putInt("chats", newChats)
                        .putBoolean("has_subscription", true)
                        .apply()
                    
                    finish() // Go back to chat
                } else {
                    Toast.makeText(
                        this@SubscriptionTestActivity,
                        "Purchase failed: ${response.body()?.message ?: "Unknown error"}",
                        Toast.LENGTH_SHORT
                    ).show()
                }
            }

            override fun onFailure(call: Call<PurchaseResponse>, t: Throwable) {
                Toast.makeText(
                    this@SubscriptionTestActivity,
                    "Error: ${t.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        })
    }
}

data class PurchaseRequest(
    val email: String,
    val purchase_token: String,
    val product_id: String
)

data class PurchaseResponse(
    val success: Boolean,
    val chats_added: Int?,
    val remaining_chats: Int?,
    val message: String?
)
