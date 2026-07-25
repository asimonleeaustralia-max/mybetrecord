package com.mybetrecord.android.data.repository

import com.mybetrecord.android.data.remote.ReportSummaryDto
import com.mybetrecord.android.data.remote.ReportsApi
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class ReportsRepository @Inject constructor(
    private val api: ReportsApi,
) {
    suspend fun summary(): ReportSummaryDto = api.summary(usePrimaryCurrency = true)
}
