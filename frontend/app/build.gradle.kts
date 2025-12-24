plugins {
    id("com.android.application")
    kotlin("android")
}

android {
    namespace = "com.sarvagya.mentalhealthchat"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.sarvagya.mentalhealthchat"
        minSdk = 24
        targetSdk = 35
        versionCode = 35
        versionName = "sarvagya_1.4"
    }

    signingConfigs {
        create("release") {
            storeFile = rootProject.file("keystore/Keystore")
            storePassword = "Qwerty@123"
            keyAlias = "key0"
            keyPassword = "Qwerty@123"
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        buildConfig = true
    }
}

dependencies {
    implementation(libs.androidx.core.ktx.v1120)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)

    implementation("com.squareup.retrofit2:retrofit:2.9.0")
    implementation("com.squareup.retrofit2:converter-gson:2.9.0")

    implementation("com.squareup.okhttp3:okhttp:4.10.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.10.0")

    // Google Play Billing Library
    implementation("com.android.billingclient:billing-ktx:6.1.0")
}
