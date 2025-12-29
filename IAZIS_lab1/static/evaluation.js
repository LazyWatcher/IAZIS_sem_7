document.addEventListener('DOMContentLoaded', function() {
    const runEvaluationBtn = document.getElementById('runEvaluation');
    const showMetricsInfoBtn = document.getElementById('showMetricsInfo');
    const loadingElement = document.getElementById('loading');
    const resultsElement = document.getElementById('results');
    const errorMessageElement = document.getElementById('errorMessage');
    const metricsModal = document.getElementById('metricsModal');
    const closeModal = document.querySelector('.close');

    runEvaluationBtn.addEventListener('click', runEvaluation);
    showMetricsInfoBtn.addEventListener('click', showMetricsInfo);
    closeModal.addEventListener('click', () => metricsModal.classList.add('hidden'));

    // Закрытие модального окна при клике вне его
    window.addEventListener('click', (event) => {
        if (event.target === metricsModal) {
            metricsModal.classList.add('hidden');
        }
    });

    async function runEvaluation() {
        showLoading();
        hideResults();
        hideError();

        try {
            // Получаем оператор (по умолчанию AND)
            const operator = 'AND'; // Можно добавить выбор оператора на странице

            const response = await fetch('/api/evaluate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    qrels_file: 'data/qrels.txt',
                    operator: operator
                })
            });

            const data = await response.json();

            if (data.success) {
                displayResults(data.metrics, data.plots, data.operator);
            } else {
                showError(data.error);
            }
        } catch (error) {
            showError('Ошибка при выполнении оценки: ' + error.message);
        } finally {
            hideLoading();
        }
    }

    async function showMetricsInfo() {
        try {
            const response = await fetch('/api/metrics/details');
            const metricsInfo = await response.json();
            displayMetricsInfo(metricsInfo);
        } catch (error) {
            showError('Ошибка при загрузке информации о метриках');
        }
    }

    function displayResults(metrics, plots, operator) {
        displayMacroMetrics(metrics.macro, operator);
        displayPlots(plots, operator);
        displayDetailedMetrics(metrics.per_query, operator);
        showResults();
    }

    function displayMacroMetrics(macroMetrics, operator) {
        const container = document.getElementById('macroMetrics');
        container.innerHTML = '';

        const metrics = [
            { key: 'precision', name: 'Precision', description: 'Точность' },
            { key: 'recall', name: 'Recall', description: 'Полнота' },
            { key: 'f_measure', name: 'F-measure', description: 'F-мера' },
            { key: 'accuracy', name: 'Accuracy', description: 'Аккуратность' }
        ];

        metrics.forEach(metric => {
            const value = macroMetrics[metric.key];
            const valueClass = getValueClass(value);

            const metricCard = document.createElement('div');
            metricCard.className = 'metric-card';
            metricCard.innerHTML = `
                <div class="metric-name">${metric.description}</div>
                <div class="metric-value ${valueClass}">${value.toFixed(3)}</div>
                <div class="metric-desc">${metric.name}</div>
                <div class="operator-info">Оператор: ${operator}</div>
            `;
            container.appendChild(metricCard);
        });
    }

    function displayPlots(plots, operator) {
        const container = document.getElementById('plotsContainer');
        container.innerHTML = '';

        if (plots.precision_recall) {
            const plotDiv = document.createElement('div');
            plotDiv.className = 'plot-container';
            plotDiv.innerHTML = `
                <h4>Precision-Recall по запросам (Оператор: ${operator})</h4>
                <img src="data:image/png;base64,${plots.precision_recall}" alt="Precision-Recall Plot">
                <p class="plot-description">График показывает баланс между точностью и полнотой для каждого запроса</p>
            `;
            container.appendChild(plotDiv);
        }

        if (plots.metrics_comparison) {
            const plotDiv = document.createElement('div');
            plotDiv.className = 'plot-container';
            plotDiv.innerHTML = `
                <h4>Сравнение метрик качества (Оператор: ${operator})</h4>
                <img src="data:image/png;base64,${plots.metrics_comparison}" alt="Metrics Comparison Plot">
                <p class="plot-description">Сравнение макроусредненных метрик для оценки общей эффективности системы</p>
            `;
            container.appendChild(plotDiv);
        }
    }

    function displayDetailedMetrics(perQueryMetrics, operator) {
        const container = document.getElementById('detailedMetrics');

        if (Object.keys(perQueryMetrics).length === 0) {
            container.innerHTML = '<p>Нет данных для отображения</p>';
            return;
        }

        let tableHTML = `
            <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>Запрос</th>
                        <th>Precision</th>
                        <th>Recall</th>
                        <th>F-measure</th>
                        <th>Accuracy</th>
                        <th>TP/FP/FN</th>
                        <th>Статус</th>
                    </tr>
                </thead>
                <tbody>
        `;

        Object.entries(perQueryMetrics).forEach(([query, metrics]) => {
            const stats = `${metrics.true_positive}/${metrics.false_positive}/${metrics.false_negative}`;
            const statusClass = getStatusClass(metrics.f_measure);
            const statusText = getStatusText(metrics.f_measure);

            tableHTML += `
                <tr>
                    <td title="${query}">${truncateText(query, 30)}</td>
                    <td class="${getValueClass(metrics.precision)}">${metrics.precision.toFixed(3)}</td>
                    <td class="${getValueClass(metrics.recall)}">${metrics.recall.toFixed(3)}</td>
                    <td class="${getValueClass(metrics.f_measure)}">${metrics.f_measure.toFixed(3)}</td>
                    <td class="${getValueClass(metrics.accuracy)}">${metrics.accuracy.toFixed(3)}</td>
                    <td>${stats}</td>
                    <td class="status-cell ${statusClass}">${statusText}</td>
                </tr>
            `;
        });

        tableHTML += '</tbody></table></div>';
        container.innerHTML = tableHTML;
    }

    function displayMetricsInfo(metricsInfo) {
        const container = document.getElementById('metricsInfo');
        container.innerHTML = '';

        Object.entries(metricsInfo).forEach(([key, info]) => {
            const metricDiv = document.createElement('div');
            metricDiv.className = 'metric-info';
            metricDiv.innerHTML = `
                <h4>${info.name}</h4>
                <p>${info.description}</p>
                <div class="metric-formula">${info.formula}</div>
            `;
            container.appendChild(metricDiv);
        });

        metricsModal.classList.remove('hidden');
    }

    function getValueClass(value) {
        if (value >= 0.7) return 'high';
        if (value >= 0.4) return 'medium';
        return 'low';
    }

    function getStatusClass(value) {
        if (value >= 0.8) return 'status-excellent';
        if (value >= 0.6) return 'status-good';
        if (value >= 0.4) return 'status-fair';
        return 'status-poor';
    }

    function getStatusText(value) {
        if (value >= 0.8) return 'Отлично';
        if (value >= 0.6) return 'Хорошо';
        if (value >= 0.4) return 'Удовлетворительно';
        return 'Плохо';
    }

    function truncateText(text, maxLength) {
        return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
    }

    function showLoading() {
        loadingElement.classList.remove('hidden');
    }

    function hideLoading() {
        loadingElement.classList.add('hidden');
    }

    function showResults() {
        resultsElement.classList.remove('hidden');
    }

    function hideResults() {
        resultsElement.classList.add('hidden');
    }

    function showError(message) {
        errorMessageElement.textContent = message;
        errorMessageElement.classList.remove('hidden');
    }

    function hideError() {
        errorMessageElement.classList.add('hidden');
    }
});