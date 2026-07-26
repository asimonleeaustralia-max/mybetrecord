package com.mybetrecord.android.data.repository

import android.content.Context
import com.mybetrecord.android.data.remote.EquityPointDto
import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.remote.ReportsApi
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.io.File
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReportsRepository @Inject constructor(
    private val api: ReportsApi,
    @ApplicationContext private val context: Context,
) {
    suspend fun summary(): ReportSummaryDto = api.summary(usePrimaryCurrency = true)

    suspend fun equityCurve(): List<EquityPointDto> = api.equityCurve()

    /**
     * Downloads /reports/export.{kind} into the app cache and returns the file,
     * ready to hand to a share intent via FileProvider.
     */
    suspend fun downloadExport(kind: String): File = withContext(Dispatchers.IO) {
        require(kind in setOf("csv", "json", "xlsx")) { "Unsupported export kind: $kind" }
        val dir = File(context.cacheDir, "exports").apply { mkdirs() }
        val file = File(dir, "mybetrecord.$kind")
        api.export(kind).use { body ->
            body.byteStream().use { input ->
                file.outputStream().use { output -> input.copyTo(output) }
            }
        }
        file
    }
}
