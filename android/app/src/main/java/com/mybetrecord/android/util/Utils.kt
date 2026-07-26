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

fun formatMoney(amount: Double, currency: String?): String {
    val ccy = currency?.uppercase()?.takeIf { it.isNotBlank() } ?: ""
    return "%s%.2f".format(if (ccy.isNotEmpty()) "$ccy " else "", amount)
}

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

/** Opens the system share sheet for a file in this app's cache, via FileProvider. */
fun Context.shareFile(file: java.io.File, mimeType: String) {
    val uri = androidx.core.content.FileProvider.getUriForFile(
        this,
        "$packageName.fileprovider",
        file,
    )
    val intent = Intent(Intent.ACTION_SEND).apply {
        type = mimeType
        putExtra(Intent.EXTRA_STREAM, uri)
        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    }
    startActivity(Intent.createChooser(intent, null))
}
