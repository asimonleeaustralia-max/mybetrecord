package com.mybetrecord.android.ui.reports

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectHorizontalDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.mybetrecord.android.i18n.tr
import kotlin.math.roundToInt

private val ProfitGreen = Color(0xFF157A52)
private val LossRed = Color(0xFFBD3A2B)
private val BrassLine = Color(0xFFA9791F)

private val CHART_HEIGHT = 200.dp

/**
 * Cumulative P/L line chart — the mobile rendering of the web app's equity curve.
 *
 * Touching the plot scrubs a crosshair along the series and reports the point
 * under the finger, which is how the web chart's hover tooltip reads.
 */
@Composable
fun EquityCurveChart(
    labels: List<String>,
    values: List<Double>,
    formatValue: (Double) -> String,
    modifier: Modifier = Modifier,
) {
    var selected by remember(values) { mutableStateOf<Int?>(null) }
    val axisColor = MaterialTheme.colorScheme.outlineVariant
    val markerColor = MaterialTheme.colorScheme.primary

    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        ChartReadout(
            label = selected?.let { labels.getOrNull(it) },
            value = selected?.let { values.getOrNull(it)?.let(formatValue) },
            placeholder = tr("android.chartHint"),
        )

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(CHART_HEIGHT)
                // Horizontal-only, so a vertical swipe still scrolls the page.
                .pointerInput(values) {
                    if (values.size < 2) return@pointerInput
                    fun pick(x: Float) {
                        val step = size.width / (values.size - 1).toFloat()
                        selected = (x / step).roundToInt().coerceIn(0, values.size - 1)
                    }
                    detectHorizontalDragGestures(
                        onDragStart = { pick(it.x) },
                        onDragEnd = { selected = null },
                        onDragCancel = { selected = null },
                    ) { change, _ -> pick(change.position.x) }
                }
                .pointerInput(values) {
                    if (values.size < 2) return@pointerInput
                    detectTapGestures { offset ->
                        val step = size.width / (values.size - 1).toFloat()
                        val index = (offset.x / step).roundToInt().coerceIn(0, values.size - 1)
                        selected = if (selected == index) null else index
                    }
                },
        ) {
            if (values.size < 2) return@Canvas
            val min = minOf(values.min(), 0.0)
            val max = maxOf(values.max(), 0.0)
            val range = (max - min).takeIf { it > 0 } ?: 1.0
            fun x(i: Int) = size.width * i / (values.size - 1).toFloat()
            fun y(v: Double) = size.height * (1 - ((v - min) / range)).toFloat()

            // Zero baseline.
            val zeroY = y(0.0)
            drawLine(axisColor, Offset(0f, zeroY), Offset(size.width, zeroY), strokeWidth = 1.dp.toPx())

            val line = Path().apply {
                values.forEachIndexed { i, v ->
                    if (i == 0) moveTo(x(i), y(v)) else lineTo(x(i), y(v))
                }
            }
            // Fill under the curve, matching the web chart's tinted area.
            val fill = Path().apply {
                addPath(line)
                lineTo(x(values.lastIndex), zeroY)
                lineTo(x(0), zeroY)
                close()
            }
            drawPath(
                fill,
                Brush.verticalGradient(listOf(BrassLine.copy(alpha = 0.18f), Color.Transparent)),
            )
            drawPath(line, BrassLine, style = Stroke(width = 2.dp.toPx()))

            selected?.let { i ->
                val px = x(i)
                val py = y(values[i])
                drawLine(
                    color = markerColor.copy(alpha = 0.6f),
                    start = Offset(px, 0f),
                    end = Offset(px, size.height),
                    strokeWidth = 1.dp.toPx(),
                    pathEffect = PathEffect.dashPathEffect(floatArrayOf(6f, 6f)),
                )
                drawCircle(markerColor, radius = 4.dp.toPx(), center = Offset(px, py))
            }
        }
    }
}

/** Monthly P/L bar chart: green above the baseline, red below, like the web charts page. */
@Composable
fun MonthlyBarChart(
    labels: List<String>,
    values: List<Double>,
    formatValue: (Double) -> String,
    modifier: Modifier = Modifier,
) {
    var selected by remember(values) { mutableStateOf<Int?>(null) }
    val axisColor = MaterialTheme.colorScheme.outlineVariant
    val outlineColor = MaterialTheme.colorScheme.onSurface

    Column(modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        ChartReadout(
            label = selected?.let { labels.getOrNull(it) },
            value = selected?.let { values.getOrNull(it)?.let(formatValue) },
            placeholder = tr("android.barChartHint"),
        )

        Canvas(
            modifier = Modifier
                .fillMaxWidth()
                .height(CHART_HEIGHT)
                .pointerInput(values) {
                    if (values.isEmpty()) return@pointerInput
                    detectTapGestures { offset ->
                        val slot = size.width / values.size
                        val index = (offset.x / slot).toInt().coerceIn(0, values.lastIndex)
                        selected = if (selected == index) null else index
                    }
                },
        ) {
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
                val barSize = Size(barWidth, (bottom - top).coerceAtLeast(1f))
                val isSelected = selected == i
                drawRect(
                    color = if (v >= 0) ProfitGreen else LossRed,
                    topLeft = Offset(left, top),
                    size = barSize,
                    alpha = if (selected == null || isSelected) 1f else 0.35f,
                )
                if (isSelected) {
                    drawRect(
                        color = outlineColor,
                        topLeft = Offset(left, top),
                        size = barSize,
                        style = Stroke(width = 1.5.dp.toPx()),
                    )
                }
            }
        }

        // Range labels, so an unselected chart still says which months it spans.
        if (labels.isNotEmpty()) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(labels.first(), style = MaterialTheme.typography.labelSmall)
                if (labels.size > 1) {
                    Text(labels.last(), style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
}

/** Shared header line: the selected point's label/value, or the touch hint. */
@Composable
private fun ChartReadout(label: String?, value: String?, placeholder: String) {
    if (label == null || value == null) {
        Text(
            placeholder,
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.fillMaxWidth(),
            textAlign = TextAlign.Center,
        )
        return
    }
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.CenterHorizontally),
    ) {
        Text(label, style = MaterialTheme.typography.labelLarge)
        Text(
            value,
            style = MaterialTheme.typography.labelLarge,
            fontFamily = FontFamily.Monospace,
        )
    }
}
