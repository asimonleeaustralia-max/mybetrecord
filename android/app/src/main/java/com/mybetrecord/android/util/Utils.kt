package com.mybetrecord.android.util

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.content.Intent
import android.net.Uri
import android.view.WindowManager
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.platform.LocalContext
import retrofit2.HttpException
import java.io.IOException

fun Context.findActivity(): Activity? {
    var ctx = this
    while (ctx is ContextWrapper) {
        if (ctx is Activity) return ctx
        ctx = ctx.baseContext
    }
    return null
}

fun Context.openUrl(url: String) {
    startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
}

fun Throwable.toUserMessage(): String = when (this) {
    is HttpException -> {
        val body = response()?.errorBody()?.string().orEmpty()
        when {
            body.contains("detail") -> body.take(200)
            code() == 401 -> "Session expired. Please sign in again."
            code() == 403 -> "You do not have permission for this action."
            code() == 422 -> "Please check the form and try again."
            else -> "Request failed (${code()})"
        }
    }
    is IOException -> "Network error. Check your connection."
    else -> message ?: "Something went wrong"
}

/** Optionally prevent screenshots/recents previews on auth screens. */
@Composable
fun SecureWindowEffect(enabled: Boolean = true) {
    val context = LocalContext.current
    DisposableEffect(enabled) {
        val window = context.findActivity()?.window
        if (enabled) {
            window?.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE,
            )
        }
        onDispose {
            window?.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
        }
    }
}

/** [signed] prefixes gains with "+", matching the web app's money(v, true). */
fun formatMoney(amount: Double, currency: String?, signed: Boolean = false): String {
    val ccy = currency?.uppercase()?.takeIf { it.isNotBlank() } ?: ""
    val sign = if (signed && amount > 0) "+" else ""
    return "%s%s%.2f".format(if (ccy.isNotEmpty()) "$ccy " else "", sign, amount)
}

fun formatPct(value: Double?): String = if (value == null) "—" else "%.2f%%".format(value)

/** Web origin for public links (share pages, profiles). Same host as the API. */
fun webOrigin(): String = com.mybetrecord.android.BuildConfig.API_BASE_URL.trimEnd('/')

fun shareLinkUrl(token: String): String = "${webOrigin()}/share/$token"

fun publicProfileUrl(token: String): String = "${webOrigin()}/u/$token"

/** Opens the system share sheet with a plain-text payload (e.g. a public link). */
fun Context.shareText(text: String) {
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = "text/plain"
        putExtra(Intent.EXTRA_TEXT, text)
    }
    startActivity(Intent.createChooser(intent, null))
}
