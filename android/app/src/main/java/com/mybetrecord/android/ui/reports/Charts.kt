package com.mybetrecord.android.ui.reports

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.dp

private val ProfitGreen = Color(0xFF157A52)
private val LossRed = Color(0xFFBD3A2B)

/** Cumulative P/L line chart — the mobile rendering of the web app's equity curve. */
@Composable
fun EquityCurveChart(values: List<Double>, modifier: Modifier = Modifier) {
    val lineColor = MaterialTheme.colorScheme.primary
    val axisColor = MaterialTheme.colorScheme.outlineVariant
    Canvas(modifier = modifier.fillMaxWidth().height(180.dp)) {
        if (values.size < 2) return@Canvas
        val min = minOf(values.min(), 0.0)
        val max = maxOf(values.max(), 0.0)
        val range = (max - min).takeIf { it > 0 } ?: 1.0
        fun x(i: Int) = size.width * i / (values.size - 1).toFloat()
        fun y(v: Double) = size.height * (1 - ((v - min) / range)).toFloat()

        // Zero baseline.
        val zeroY = y(0.0)
        drawLine(axisColor, Offset(0f, zeroY), Offset(size.width, zeroY), strokeWidth = 1.dp.toPx())

        val path = Path()
        values.forEachIndexed { i, v ->
            if (i == 0) path.moveTo(x(i), y(v)) else path.lineTo(x(i), y(v))
        }
        drawPath(path, lineColor, style = Stroke(width = 2.dp.toPx()))
    }
}

/** Monthly P/L bar chart: green above the baseline, red below, like the web charts page. */
@Composable
fun MonthlyBarChart(values: List<Double>, modifier: Modifier = Modifier) {
    val axisColor = MaterialTheme.colorScheme.outlineVariant
    Canvas(modifier = modifier.fillMaxWidth().height(180.dp)) {
        if (values.isEmpty()) return@Canvas
        val min = minOf(values.min(), 0.0)
        val max = maxOf(values.max(), 0.0)
        val range = (max - min).takeIf { it > 0 } ?: 1.0
        fun y(v: Double) = size.height * (1 - ((v - min) / range)).toFloat()

        val zeroY = y(0.0)
        drawLine(axisColor, Offset(0f, zeroY), Offset(size.width, zeroY), strokeWidth = 1.dp.toPx())

        val slot = size.width / values.size
        val barWidth = (slot * 0.7f).coerceAtLeast(1f)
        values.forEachIndexed { i, v ->
            val left = slot * i + (slot - barWidth) / 2
            val top = minOf(y(v), zeroY)
            val bottom = maxOf(y(v), zeroY)
            drawRect(
                color = if (v >= 0) ProfitGreen else LossRed,
                topLeft = Offset(left, top),
                size = androidx.compose.ui.geometry.Size(barWidth, (bottom - top).coerceAtLeast(1f)),
            )
        }
    }
}
