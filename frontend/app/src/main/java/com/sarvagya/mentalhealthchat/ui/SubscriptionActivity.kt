//sss
package com.sarvagya.mentalhealthchat.ui

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.android.billingclient.api.*
import com.sarvagya.mentalhealthchat.R
import com.sarvagya.mentalhealthchat.ui.RetrofitClient
import com.sarvagya.mentalhealthchat.ui.PurchaseRequest
import com.sarvagya.mentalhealthchat.ui.PurchaseResponse
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class SubscriptionActivity : AppCompatActivity() {

    private lateinit var billingClient: BillingClient
    private lateinit var buy5Btn: Button
    private lateinit var buy10Btn: Button
    private lateinit var starterPackText: TextView
    private lateinit var proPackText: TextView
    private lateinit var statusText: TextView

    // Use a map to safely store and retrieve product details
    private val productDetailsMap = mutableMapOf<String, ProductDetails>()

    companion object {
        const val PRODUCT_ID_5 = "mental_health_5_chats_v1"
        const val PRODUCT_ID_10 = "mental_health_10_chats_v1"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_subscription)

        buy5Btn = findViewById(R.id.buy5Btn)
        buy10Btn = findViewById(R.id.buy10Btn)
        starterPackText = findViewById(R.id.starterPackText)
        proPackText = findViewById(R.id.proPackText)
        statusText = findViewById(R.id.statusText)

        disableButtons()
        findViewById<Button>(R.id.backBtn).setOnClickListener { finish() }

        setupBilling()
        refreshStatus() // Initial status refresh
    }

    // ---------- Billing setup ----------
    private fun setupBilling() {
        billingClient = BillingClient.newBuilder(this)
            .enablePendingPurchases()
            .setListener { result, purchases ->
                // If purchase succeeded, handle purchases. Otherwise restore buttons so user can retry.
                if (result.responseCode == BillingClient.BillingResponseCode.OK && purchases != null) {
                    handlePurchases(purchases)
                } else {
                    // Re-enable buttons on UI thread for canceled/failed flows
                    runOnUiThread {
                        enableButtonsAfterFailure()
                    }
                }
            }
            .build()

        billingClient.startConnection(object : BillingClientStateListener {
            override fun onBillingSetupFinished(result: BillingResult) {
                Log.d("BILLING", "setup=${result.responseCode}")
                if (result.responseCode == BillingClient.BillingResponseCode.OK) {
                    queryProducts()
                    // Process any already-owned INAPP purchases so they get verified & consumed
                    billingClient.queryPurchasesAsync(
                        QueryPurchasesParams.newBuilder().setProductType(BillingClient.ProductType.INAPP).build()
                    ) { qResult, purchases ->
                        if (qResult.responseCode == BillingClient.BillingResponseCode.OK) {
                            if (!purchases.isNullOrEmpty()) {
                                Log.d("BILLING", "Found owned purchases: ${purchases.map { it.products }}")
                                handlePurchases(purchases)
                            } else {
                                Log.d("BILLING", "No owned purchases found on startup")
                            }
                        } else {
                            Log.e("BILLING", "queryPurchasesAsync failed: ${qResult.debugMessage}")
                        }
                    }
                }
            }

            override fun onBillingServiceDisconnected() {
                Log.d("BILLING", "service disconnected, retrying...")
                // Implement a retry mechanism if needed
            }
        })
    }

    // ---------- Query products ----------
    private fun queryProducts() {
        val productList = listOf(
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(PRODUCT_ID_5)
                .setProductType(BillingClient.ProductType.INAPP)
                .build(),
            QueryProductDetailsParams.Product.newBuilder()
                .setProductId(PRODUCT_ID_10)
                .setProductType(BillingClient.ProductType.INAPP)
                .build()
        )
        val params = QueryProductDetailsParams.newBuilder().setProductList(productList).build()

        // **FIXED**: Correctly call queryProductDetailsAsync with a listener
        billingClient.queryProductDetailsAsync(params) { billingResult, productDetailsList ->
            if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                // **FIXED**: Ensure UI updates happen on the main thread
                runOnUiThread {
                    displayProducts(productDetailsList)
                }
            } else {
                Log.e("BILLING", "Query failed: ${billingResult.debugMessage}")
            }
        }
    }


    private fun displayProducts(products: List<ProductDetails>) {
        if (products.isEmpty()) {
            Log.w("BILLING", "No products found to display.")
            return
        }

        products.forEach { product ->
            productDetailsMap[product.productId] = product // Store for later
            when (product.productId) {
                PRODUCT_ID_5 -> {
                    val price = product.oneTimePurchaseOfferDetails?.formattedPrice
                    starterPackText.text = if (price != null) "5 Chats - $price" else "5 Chats"
                    enableButton(buy5Btn) { launchPurchase(product) }
                }

                PRODUCT_ID_10 -> {
                    val price = product.oneTimePurchaseOfferDetails?.formattedPrice
                    proPackText.text = if (price != null) "10 Chats - $price" else "10 Chats"
                    enableButton(buy10Btn) { launchPurchase(product) }
                }
            }
        }
    }

    private fun enableButton(btn: Button, action: () -> Unit) {
        btn.isEnabled = true
        btn.alpha = 1f
        btn.setOnClickListener { action() }
    }

    // ---------- Purchase ----------
    private fun launchPurchase(product: ProductDetails) {
        disableButtons() // Prevent multiple clicks

        val params = BillingFlowParams.newBuilder()
            .setProductDetailsParamsList(
                listOf(
                    BillingFlowParams.ProductDetailsParams.newBuilder().setProductDetails(product).build()
                )
            )
            .build()
        billingClient.launchBillingFlow(this, params)
    }

    // ---------- Handle purchase (MAJOR FIX) ----------
    private fun handlePurchases(purchases: List<Purchase>) {
        purchases.forEach { purchase ->
            if (purchase.purchaseState == Purchase.PurchaseState.PURCHASED) {
                // Skip if we've already processed this purchase token (prevents duplicate grants)
                if (isTokenProcessed(purchase.purchaseToken)) {
                    Log.d("BILLING", "Skipping already-processed purchase: ${purchase.purchaseToken}")
                    return@forEach
                }

                val chatsToAdd = when {
                    purchase.products.contains(PRODUCT_ID_5) -> 5
                    purchase.products.contains(PRODUCT_ID_10) -> 10
                    else -> 0
                }
                if (chatsToAdd > 0) {
                    grantChatsOnBackend(purchase, chatsToAdd)
                }
            }
        }
    }

    // **NEW**: Function to call your backend before acknowledging
    private fun grantChatsOnBackend(purchase: Purchase, chatsToAdd: Int) {
        val email = getSharedPreferences("app", MODE_PRIVATE).getString("email", null)
        if (email == null) {
            Toast.makeText(this, "Error: User not logged in.", Toast.LENGTH_LONG).show()
            return
        }

        // Determine product_id from the purchase.products list (supports multi-product purchases)
        val productId = when {
            purchase.products.contains(PRODUCT_ID_5) -> PRODUCT_ID_5
            purchase.products.contains(PRODUCT_ID_10) -> PRODUCT_ID_10
            else -> null
        }

        // Build a PurchaseRequest and call `/purchase/verify` on the backend.
        val req = PurchaseRequest(
            email = email,
            purchase_token = purchase.purchaseToken,
            product_id = productId ?: ""
        )

        RetrofitClient.instance.verifyPurchase(req).enqueue(object : Callback<PurchaseResponse> {
            override fun onResponse(call: Call<PurchaseResponse>, response: Response<PurchaseResponse>) {
                Log.d("BILLING", "verifyPurchase response code=${response.code()} body=${response.body()}")
                if (response.isSuccessful && response.body()?.success == true) {
                    // Mark token as processed (prevents duplicate backend grants)
                    markTokenProcessed(purchase.purchaseToken)

                    // Update stored chat count if backend provided it
                    val newTotal = response.body()?.remaining_chats
                    if (newTotal != null) {
                        getSharedPreferences("app", MODE_PRIVATE).edit().putInt("chats", newTotal).apply()
                    }
                    runOnUiThread {
                    refreshStatus()
                    }
                    // Consume the purchase (consumable flow)
                    consumePurchase(purchase)
                } else {
                    Log.e("BILLING", "Backend failed to verify purchase. code=${response.code()} message=${response.message()}")
                    Toast.makeText(this@SubscriptionActivity, "Server error. Please try again.", Toast.LENGTH_LONG).show()
                    enableButtonsAfterFailure()
                }
            }

            override fun onFailure(call: Call<PurchaseResponse>, t: Throwable) {
                Log.e("BILLING", "Network error while verifying purchase: ${t.localizedMessage}", t)
                Toast.makeText(this@SubscriptionActivity, "Network error. Please try again.", Toast.LENGTH_LONG).show()
                enableButtonsAfterFailure()
            }
        })
    }

    // ---------- Processed token helpers (persistent) ----------
    private fun isTokenProcessed(token: String): Boolean {
        val set = getSharedPreferences("app", MODE_PRIVATE).getStringSet("processed_purchases", emptySet())
        return set?.contains(token) == true
    }

    private fun markTokenProcessed(token: String) {
        val prefs = getSharedPreferences("app", MODE_PRIVATE)
        val existing = prefs.getStringSet("processed_purchases", null)?.toMutableSet() ?: mutableSetOf()
        existing.add(token)
        prefs.edit().putStringSet("processed_purchases", existing).apply()
    }

    // **NEW**: Consume purchase (for consumable SKUs) after backend success
    private fun consumePurchase(purchase: Purchase) {
        val params = ConsumeParams.newBuilder()
            .setPurchaseToken(purchase.purchaseToken)
            .build()

        billingClient.consumeAsync(params) { billingResult, _ ->
            runOnUiThread {
                if (billingResult.responseCode == BillingClient.BillingResponseCode.OK) {
                    Toast.makeText(
                        this@SubscriptionActivity,
                        "Purchase successful!",
                        Toast.LENGTH_SHORT
                    ).show()

                    refreshStatus()
                    enableButtonsAfterFailure()
                } else {
                    Log.e("BILLING", "Failed to consume purchase: ${billingResult.debugMessage}")
                    enableButtonsAfterFailure()
                }
            }
        }
    }



    // ---------- Helpers ----------
    private fun disableButtons() {
        buy5Btn.isEnabled = false
        buy10Btn.isEnabled = false
        buy5Btn.alpha = 0.5f
        buy10Btn.alpha = 0.5f
    }

    // **NEW**: Re-enable buttons if purchase flow fails
    private fun enableButtonsAfterFailure() {
        if(productDetailsMap.containsKey(PRODUCT_ID_5)) enableButton(buy5Btn) { launchPurchase(productDetailsMap[PRODUCT_ID_5]!!) }
        if(productDetailsMap.containsKey(PRODUCT_ID_10)) enableButton(buy10Btn) { launchPurchase(productDetailsMap[PRODUCT_ID_10]!!) }
    }

    private fun refreshStatus() {
        val email = getSharedPreferences("app", MODE_PRIVATE).getString("email", null)
        if (email == null) {
            statusText.text = "You're not logged in"
            return
        }

        // Fetch authoritative remaining chats from backend
        val req = UserChatsRequest(email = email)
        RetrofitClient.instance.getUserChats(req).enqueue(object : Callback<ChatsResponse> {
            override fun onResponse(call: Call<ChatsResponse>, response: Response<ChatsResponse>) {
                if (response.isSuccessful) {
                    val chats = response.body()?.chats ?: 0
                    // Persist authoritative value locally
                    getSharedPreferences("app", MODE_PRIVATE).edit().putInt("chats", chats).apply()
                    runOnUiThread {
                        statusText.text = if (chats > 0) "You have $chats chats remaining" else "You've reached your free chat limit"
                    }
                } else {
                    Log.e("SUBS", "getUserChats failed: ${response.code()} ${response.message()}")
                }
            }

            override fun onFailure(call: Call<ChatsResponse>, t: Throwable) {
                Log.e("SUBS", "Network error while fetching chats: ${t.localizedMessage}")
            }
        })
    }

    override fun onResume() {
        super.onResume()
        refreshStatus()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::billingClient.isInitialized) {
            billingClient.endConnection()
        }
    }
}
