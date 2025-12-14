package com.sarvagya.mentalhealthchat.ui

data class RegisterRequest(
    val email: String,
    val age: Int,
    val sex: String,
    val password: String
)
