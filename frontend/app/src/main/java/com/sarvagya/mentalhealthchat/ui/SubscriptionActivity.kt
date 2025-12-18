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
    private lateinit var buy5Btn: Button
    private lateinit var buy10Btn: Button
    private lateinit var starterPackText: TextView
    private lateinit var proPackText: TextView
    private lateinit var statusText: TextView

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

        // ✅ Disable ONCE here
        buy5Btn.isEnabled = false
        buy10Btn.isEnabled = false

        buy5Btn.setOnClickListener {
            Toast.makeText(this, "Loading products…", Toast.LENGTH_SHORT).show()
        }
        buy10Btn.setOnClickListener {
            Toast.makeText(this, "Loading products…", Toast.LENGTH_SHORT).show()
        }

        findViewById<Button>(R.id.backBtn).setOnClickListener { finish() }

        setupBillingClient()
        refreshStatus()
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

            override fun onBillingServiceDisconnected() {}
        })
    }

    private fun queryProducts() {
        val products = listOf(
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
            .setProductList(products)
            .build()

        billingClient.queryProductDetailsAsync(params) { _, productDetailsList ->
            if (productDetailsList.isNotEmpty()) {
                displayProducts(productDetailsList)
            }
        }
    }

    private fun displayProducts(products: List<ProductDetails>) {

        val fiveChats = products.find { it.productId == PRODUCT_ID_5_CHATS }
        val tenChats = products.find { it.productId == PRODUCT_ID_10_CHATS }

        // ✅ 5 chats
        fiveChats?.oneTimePurchaseOfferDetails?.formattedPrice?.let { price ->
            starterPackText.text = "5 Chats - $price"
            buy5Btn.isEnabled = true
            buy5Btn.setOnClickListener { launchPurchaseFlow(fiveChats) }
        }

        // ✅ 10 chats (FIXED TextView)
        tenChats?.oneTimePurchaseOfferDetails?.formattedPrice?.let { price ->
            proPackText.text = "10 Chats - $price"
            buy10Btn.isEnabled = true
            buy10Btn.setOnClickListener { launchPurchaseFlow(tenChats) }
        }
    }

    private fun launchPurchaseFlow(productDetails: ProductDetails) {
        buy5Btn.isEnabled = false
        buy10Btn.isEnabled = false

        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(
                    BillingFlowParams.ProductDetailsParams
                        .newBuilder()
                        .setProductDetails(productDetails)
                        .build()
                )
            )
            .build()

        billingClient.launchBillingFlow(this, params)
    }

    private fun handlePurchases(purchases: List<Purchase>) {
        purchases.forEach { purchase ->
            if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED && !purchase.isAcknowledged) {
                acknowledgePurchase(purchase)
            }
        }
    }

    private fun acknowledgePurchase(purchase: Purchase) {
        billingClient.acknowledgePurchase(
            AcknowledgePurchaseParams.newBuilder()
                .setPurchaseToken(purchase.purchaseToken)
                .build()
        ) {
            Toast.makeText(this, "Purchase successful!", Toast.LENGTH_SHORT).show()
            refreshStatus()
        }
    }

    private fun refreshStatus() {
        val chats = getSharedPreferences("app", MODE_PRIVATE).getInt("chats", -1)
        statusText.text =
            if (chats > 0) "You have $chats chats remaining"
            else "You've reached your free chat limit"
    }

    override fun onDestroy() {
        super.onDestroy()
        billingClient.endConnection()
    }
}
