package com.sarvagya.mentalhealthchat.ui

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.billingclient.api.*
import com.sarvagya.mentalhealthchat.R

class SubscriptionActivity : AppCompatActivity() {

    private lateinit var billingClient: BillingClient
    private lateinit var subscribeBtn: Button
    private lateinit var priceText: TextView

    // Define your product IDs (you'll create these in Google Play Console)
    private val PRODUCT_ID_5_CHATS = "mental_health_5_chats_v1"
    private val PRODUCT_ID_10_CHATS = "mental_health_10_chats_v1"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_subscription)

        subscribeBtn = findViewById(R.id.subscribeBtn)
        priceText = findViewById(R.id.priceText)

        val backBtn = findViewById<Button>(R.id.backBtn)
        backBtn.setOnClickListener { finish() }

        setupBillingClient()
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
        // Display first product (5 chats) as example
        val product = products.firstOrNull()
        if (product != null) {
            val price = product.oneTimePurchaseOfferDetails?.formattedPrice ?: "Check price"
            priceText.text = "5 Chats - $price"
            
            subscribeBtn.setOnClickListener {
                launchPurchaseFlow(product)
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
                finish() // Go back to chat
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
