package com.sarvagya.mentalhealthchat.ui

data class LoginResponse(
    val success: String?,
    val error: String?,
    val chats: Int? // Chats from database
)
