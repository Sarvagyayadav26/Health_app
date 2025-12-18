package com.sarvagya.mentalhealthchat.ui

import android.content.Intent
import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.billingclient.api.*
import com.sarvagya.mentalhealthchat.R

class SubscriptionActivity : AppCompatActivity() {

    private lateinit var billingClient: BillingClient
    private lateinit var buy5Btn: Button
    private lateinit var buy10Btn: Button
    private lateinit var starterPackText: TextView
    private lateinit var proPackText: TextView
    private lateinit var statusText: TextView

    // Define your product IDs (you'll create these in Google Play Console)
    private val PRODUCT_ID_5_CHATS = "mental_health_5_chats_v1"
    private val PRODUCT_ID_10_CHATS = "mental_health_10_chats_v1"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_subscription)

        buy5Btn = findViewById(R.id.buy5Btn)
        buy10Btn = findViewById(R.id.buy10Btn)
        starterPackText = findViewById(R.id.starterPackText)
        proPackText = findViewById(R.id.proPackText)
        statusText = findViewById(R.id.statusText)

        // Show remaining chats if passed via Intent, otherwise fall back to cached value
        val remainingFromIntent = intent.getIntExtra("CHATS", Int.MIN_VALUE)
        if (remainingFromIntent != Int.MIN_VALUE) {
            if (remainingFromIntent > 0) {
                statusText.text = "You have $remainingFromIntent chats remaining"
            } else if (remainingFromIntent == 0) {
                statusText.text = "You've reached your free chat limit"
            } else {
                statusText.text = "Start a conversation or upgrade your plan"
            }
        } else {
            // try cached value
            val cached = getSharedPreferences("app", MODE_PRIVATE).getInt("chats", -1)
            if (cached >= 0) {
                statusText.text = if (cached > 0) "You have $cached chats remaining" else "You've reached your free chat limit"
            }
        }

        val backBtn = findViewById<Button>(R.id.backBtn)
        backBtn.setOnClickListener { finish() }

        setupBillingClient()

        // Ensure UI reflects latest cached value when first created
        refreshStatus()
    }

    override fun onResume() {
        super.onResume()
        // Refresh status when returning to this activity
        refreshStatus()
    }

    override fun onNewIntent(intent: Intent?) {
        super.onNewIntent(intent)
        intent?.let { setIntent(it) }
        refreshStatus()
    }

    private fun refreshStatus() {
        val prefs = getSharedPreferences("app", MODE_PRIVATE)
        val cached = prefs.getInt("chats", Int.MIN_VALUE)
        val remainingFromIntent = intent?.getIntExtra("CHATS", Int.MIN_VALUE) ?: Int.MIN_VALUE

        val valueToShow = if (cached != Int.MIN_VALUE) cached else remainingFromIntent

        statusText.text = when {
            valueToShow == Int.MIN_VALUE -> "Start a conversation or upgrade your plan"
            valueToShow > 0 -> "You have $valueToShow chats remaining"
            else -> "You've reached your free chat limit"
        }
    }

    private fun setupBillingClient() {
        billingClient = BillingClient.newBuilder(this)
            .setListener { billingResult, purchases ->
                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
                    handlePurchases(purchases)
                }
            }
            .enablePendingPurchases()
            .build()

        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(billingResult: BillingResult) {
                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                    queryProducts()
                }
            }

            override fun onBillingServiceDisconnected() {
                // Retry connection
                Toast.makeText(this@SubscriptionActivity, "Connection lost. Please retry.", Toast.LENGTH_SHORT).show()
            }
        })
    }

    private fun queryProducts() {
        val productList = listOf(
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(PRODUCT_ID_5_CHATS)
                .setProductType(BillingClient.ProductType.INAPP)
                .build(),
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(PRODUCT_ID_10_CHATS)
                .setProductType(BillingClient.ProductType.INAPP)
                .build()
        )

        val params = QueryProductDetailsParams.newBuilder()
            .setProductList(productList)
            .build()

        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK && productDetailsList.isNotEmpty()) {
                displayProducts(productDetailsList)
            }
        }
    }

    private fun displayProducts(products: List<ProductDetails>) {
        // Find both products by ID
        val fiveChats = products.find { it.productId == PRODUCT_ID_5_CHATS }
        val tenChats = products.find { it.productId == PRODUCT_ID_10_CHATS }

        // Update UI for 5 chats pack
        if (fiveChats != null) {
            val price = fiveChats.oneTimePurchaseOfferDetails?.formattedPrice ?: "Check price"
            starterPackText.text = "5 Chats - $price"
            buy5Btn.setOnClickListener {
                launchPurchaseFlow(fiveChats)
            }
        }

        // Update UI for 10 chats pack
        if (tenChats != null) {
            val price = tenChats.oneTimePurchaseOfferDetails?.formattedPrice ?: "Check price"
            proPackText.text = "10 Chats - $price"
            buy10Btn.setOnClickListener {
                launchPurchaseFlow(tenChats)
            }
        }
    }

    private fun launchPurchaseFlow(productDetails: ProductDetails) {
        val productDetailsParamsList = listOf(
            BillingFlowParams.ProductDetailsParams.newBuilder()
                .setProductDetails(productDetails)
                .build()
        )

        val billingFlowParams = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(productDetailsParamsList)
            .build()

        billingClient.launchBillingFlow(this, billingFlowParams)
    }

    private fun handlePurchases(purchases: List<Purchase>) {
        for (purchase in purchases) {
            if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                if (!purchase.isAcknowledged) {
                    acknowledgePurchase(purchase)
                }
                
                // Send purchase token to your backend for verification
                verifyPurchaseOnBackend(purchase.purchaseToken, purchase.products[0])
            }
        }
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        val acknowledgePurchaseParams = AcknowledgePurchaseParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()

        billingClient.acknowledgePurchase(acknowledgePurchaseParams) { billingResult ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                Toast.makeText(this, "Purchase successful!", Toast.LENGTH_SHORT).show()
                // Refresh product info to ensure UI is up-to-date
                queryProducts()
                refreshStatus()
            }
        }
    }

    private fun verifyPurchaseOnBackend(purchaseToken: String, productId: String) {
        // TODO: Send to your backend API to verify and add chats
        val email = getSharedPreferences("app", MODE_PRIVATE).getString("email", null)
        
        // Example API call structure:
        // POST /purchase/verify
        // Body: { "email": "user@example.com", "purchase_token": "...", "product_id": "..." }
        
        // For now, just save locally (not secure, use backend verification in production)
        getSharedPreferences("app", MODE_PRIVATE)
            .edit()
            .putBoolean("has_subscription", true)
            .apply()
    }

    override fun onDestroy() {
        super.onDestroy()
        billingClient.endConnection()
    }
}
