/**
 * OOP Purity Analyzer — Plotly chart rendering utilities.
 * 
 * Renders Plotly charts from JSON data passed by the Flask backend.
 * All charts use the plotly_dark template with a consistent dark theme.
 */

/**
 * Render a Plotly chart in the specified container div.
 * 
 * @param {string} divId - The ID of the target div element.
 * @param {Object|string} chartData - Plotly figure JSON (parsed or string).
 */
function renderChart(divId, chartData) {
    var container = document.getElementById(divId);
    if (!container) {
        console.warn('Chart container not found:', divId);
        return;
    }

    var figure;
    if (typeof chartData === 'string') {
        try {
            figure = JSON.parse(chartData);
        } catch (e) {
            console.error('Failed to parse chart JSON for', divId, e);
            container.innerHTML = '<p style="color:#888;text-align:center;padding:2rem;">Failed to load chart</p>';
            return;
        }
    } else {
        figure = chartData;
    }

    var data = figure.data || [];
    var layout = figure.layout || {};

    // Ensure responsive sizing
    layout.autosize = true;
    layout.paper_bgcolor = layout.paper_bgcolor || '#1a1a2e';
    layout.plot_bgcolor = layout.plot_bgcolor || '#1a1a2e';
    layout.font = layout.font || {};
    layout.font.family = layout.font.family || 'Inter, sans-serif';

    var config = {
        responsive: true,
        displayModeBar: true,
        displaylogo: false,
        modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d'],
        toImageButtonOptions: {
            format: 'png',
            filename: 'oop_purity_chart_' + divId,
            height: 600,
            width: 1000,
            scale: 2
        }
    };

    try {
        Plotly.react(divId, data, layout, config);
    } catch (e) {
        console.error('Plotly render error for', divId, e);
        container.innerHTML = '<p style="color:#888;text-align:center;padding:2rem;">Chart rendering failed</p>';
    }
}
