//sss
package com.sarvagya.mentalhealthchat.ui

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.POST

data class BasicResponse(
    val success: String?,
    val error: String?
)

data class UserChatsRequest(
    val email: String
)

data class ChatsResponse(
    val chats: Int?,
    val error: String?
)

data class ChatHistoryListResponse(
    val chats: List<ChatSession>
)

data class ChatSession(
    val id: Int,
    val title: String,
    val preview: String,
    val message_count: Int
)

data class ChatMessage(
    val role: String,
    val content: String,
    val timestamp: String
)

data class ChatHistoryMessagesResponse(
    val messages: List<ChatMessage>,
    val count: Int
)

data class ChatHistoryMessagesRequest(
    val email: String,
    val limit: Int,
    val session_id: String
)

// (No grant endpoint) Use `purchase/verify` for purchase verification and granting.

interface ApiService {

    @POST("auth/register")
    fun register(@Body req: RegisterRequest): Call<BasicResponse>

    @POST("auth/login")
    fun login(@Body req: LoginRequest): Call<LoginResponse>

    @POST("chat")
    fun chat(@Body request: ChatRequest): Call<ChatResponse>

    @POST("purchase/verify")
    fun verifyPurchase(@Body request: PurchaseRequest): Call<PurchaseResponse>

    @POST("user/chats")
    fun getUserChats(@Body request: UserChatsRequest): Call<ChatsResponse>

    @POST("/chat/history/list")
    fun getChatHistoryList(@Body request: UserChatsRequest): Call<ChatHistoryListResponse>

    @POST("/chat/history/get")
    fun getChatHistoryMessages(@Body request: ChatHistoryMessagesRequest): Call<ChatHistoryMessagesResponse>

    @POST("user/history/hide")
    fun hideHistory(@Body request: UserChatsRequest): Call<BasicResponse>

    // Removed `/purchase/grant` — client should call `purchase/verify` instead.

}
