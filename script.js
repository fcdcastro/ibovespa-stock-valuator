document.addEventListener('DOMContentLoaded', () => {
    const tableBody = document.getElementById('stock-table-body');
    const refreshBtn = document.getElementById('refresh-btn');
    const loadingOverlay = document.getElementById('loading');
    const searchInput = document.getElementById('search-input');
    
    // Stats elements
    const totalStocksEl = document.getElementById('total-stocks');
    const bestTickerEl = document.getElementById('best-ticker');
    const avgUpsideEl = document.getElementById('avg-upside');

    let stockData = [];

    const errorBanner = document.getElementById('error-banner');
    const errorMessage = document.getElementById('error-message');

    function showError(msg) {
        if (errorMessage) errorMessage.textContent = msg;
        if (errorBanner) errorBanner.classList.remove('hidden');
    }

    function hideError() {
        if (errorBanner) errorBanner.classList.add('hidden');
    }

    async function fetchData() {
        loadingOverlay.classList.remove('hidden');
        hideError();
        try {
            let rawData;
            try {
                const response = await fetch('http://localhost:5000/api/valuation');
                if (response.ok) {
                    rawData = await response.json();
                } else {
                    throw new Error('Servidor retornou erro');
                }
            } catch (e) {
                if (window.__STOCK_DATA__) {
                    rawData = window.__STOCK_DATA__;
                    showError('Servidor offline. Exibindo dados do cache local.');
                } else {
                    throw new Error('Servidor offline e nenhum cache local disponível.');
                }
            }
            
            // Suporte para o novo formato com metadados
            if (rawData.stocks) {
                stockData = rawData.stocks;
                stockData.sort((a, b) => (b.upside || 0) - (a.upside || 0));
                renderTable(stockData);
                updateStats(stockData);
                renderPredictions(stockData, rawData.model_info);
                
                if (rawData.last_update) {
                    document.getElementById('last-updated').textContent = `[Atualizado: ${rawData.last_update}]`;
                }
            } else {
                // Legado: se vier apenas o array
                stockData = rawData;
                stockData.sort((a, b) => (b.upside || 0) - (a.upside || 0));
                renderTable(stockData);
                updateStats(stockData);
            }
            
            ixUpdateAll(stockData);
            
        } catch (error) {
            console.error('Erro:', error);
            showError('Erro ao carregar dados. Verifique se o servidor está rodando (python server.py) ou se o data.json existe.');
        } finally {
            loadingOverlay.classList.add('hidden');
        }
    }

    function renderTable(data) {
        tableBody.innerHTML = '';
        data.forEach(stock => {
            const row = document.createElement('tr');
            
            const upside = stock.upside || 0;
            const upsideClass = upside > 0 ? 'upside-positive' : 'upside-negative';
            const upsideIcon = upside > 0 ? '↑' : '↓';
            
            const status = getStatusBadge(upside);

            row.innerHTML = `
                <td class="col-ticker ticker-cell">${stock.ticker || '-'}</td>
                <td class="col-price">${formatCurrency(stock.price)}</td>
                <td class="col-target">${formatCurrency(stock.target_price)}</td>
                <td class="col-graham">${formatCurrency(stock.valuation_graham)}</td>
                <td class="col-dcf">${formatCurrency(stock.valuation_dcf)}</td>
                <td class="col-upside ${upsideClass}">${upside.toFixed(2)}% ${upsideIcon}</td>
                <td class="col-pl">${formatNumber(stock.p_e)}</td>
                <td class="col-pvp">${formatNumber(stock.p_b)}</td>
                <td class="col-yield">${formatNumber(stock.dividend_yield)}%</td>
                <td class="col-status"><span class="status-badge ${status.class}">${status.label}</span></td>
            `;
            tableBody.appendChild(row);
        });
    }

    function renderPredictions(data, modelInfo) {
        const container = document.getElementById('prediction-cards-container');
        const r2El = document.getElementById('model-r2');
        const maeEl = document.getElementById('model-mae');
        
        if (!container || !modelInfo) return;

        // Atualizar métricas do cabeçalho
        r2El.textContent = `R²: ${modelInfo.r2.toFixed(4)}`;
        maeEl.textContent = `MAE: ${modelInfo.mae.toFixed(2)}%`;

        // Pegar top 5 por expected_return_3m
        const top5 = [...data]
            .filter(s => s.expected_return_3m !== undefined)
            .sort((a, b) => b.expected_return_3m - a.expected_return_3m)
            .slice(0, 5);

        container.innerHTML = '';
        top5.forEach((stock, index) => {
            const card = document.createElement('div');
            card.className = 'prediction-card';
            
            card.innerHTML = `
                <div class="rank">#${index + 1}</div>
                <div class="ticker">${stock.ticker}</div>
                <div class="prediction-label">Retorno Esperado (3m)</div>
                <div class="prediction-value">${stock.expected_return_3m.toFixed(2)}%</div>
                <div class="card-footer">
                    <span>ROE: ${stock.roe.toFixed(1)}%</span>
                    <span>P/L: ${stock.p_e.toFixed(1)}</span>
                </div>
            `;
            container.appendChild(card);
        });
    }

    function updateStats(data) {
        if (!data.length) return;

        totalStocksEl.textContent = data.length;
        const sortedByUpside = [...data].sort((a, b) => (b.upside || 0) - (a.upside || 0));
        const bestStock = sortedByUpside[0];
        if (bestStock.name) {
            bestTickerEl.innerHTML = `${bestStock.ticker} <span style="font-size: 0.75rem; color: var(--text-secondary); font-weight: normal; margin-left: 5px; text-transform: none; display: inline-block;">(${bestStock.name})</span>`;
        } else {
            bestTickerEl.textContent = bestStock.ticker;
        }
        
        const avgUpside = data.reduce((acc, curr) => acc + (curr.upside || 0), 0) / data.length;
        avgUpsideEl.textContent = `${avgUpside.toFixed(1)}%`;
    }

    function getStatusBadge(upside) {
        if (upside > 20) return { label: 'Compra Forte', class: 'status-buy' };
        if (upside > 5) return { label: 'Compra', class: 'status-buy' };
        if (upside > -5) return { label: 'Neutro', class: 'status-hold' };
        return { label: 'Venda', class: 'status-sell' };
    }

    // --- Scatter Chart (Risco x Retorno) ---
    const IBOV_TICKERS = [
        "PETR4","VALE3","ITUB4","BBDC4","BBAS3","ABEV3","B3SA3","WEGE3","SUZB3","RENT3",
        "LREN3","JBSS3","RADL3","EQTL3","ELET3","ELET6","HAPV3","PRIO3","RDOR3","RAIL3",
        "SBSP3","VIVT3","BBSE3","CPLE6","CMIG4","CCRO3","CSNA3","GGBR4","USIM5","BRFS3",
        "TOTS3","ASAI3","NTCO3","KLBN11","TIMS3","BPAC11","CSAN3","MGLU3","EGIE3","CPFE3",
        "CYRE3","MULT3","VBBR3","CRFB3","ENGI11","TAEE11","TRPL4","ALOS3","IGTI11"
    ];
    let ixChartInstance = null;
    let ixSelectedTicker = null;

    function ixClassify(tkr) {
        return IBOV_TICKERS.includes(tkr) ? 'ibov' : 'small';
    }

    function ixCalcRisk(stock) {
        var score = 0;
        if (stock.debt_equity > 3)          score += 3;
        else if (stock.debt_equity > 1.5)   score += 1.5;
        else if (stock.debt_equity > 0.5)   score += 0.5;
        if (stock.net_margin < -5)           score += 3;
        else if (stock.net_margin < 0)       score += 1.5;
        if (stock.roe < -5)                  score += 2;
        else if (stock.roe < 0)              score += 1;
        if (stock.p_e === 0 || stock.p_e === null) score += 1;
        if (stock.volume < 1000000)           score += 1;
        return score;
    }

    function ixRenderChart(data) {
        var canvas = document.getElementById('ix-scatter-chart');
        if (!canvas) return;
        var ctx;
        try { ctx = canvas.getContext('2d'); } catch(e) { return; }
        if (ixChartInstance) { ixChartInstance.destroy(); ixChartInstance = null; }

        var ibovData = [];
        var smallData = [];
        for (var i = 0; i < data.length; i++) {
            var d = data[i];
            if (d.risco === undefined || d.retorno === undefined) continue;
            var pt = { x: d.risco, y: d.retorno, ticker: d.ticker };
            if (d.category === 'ibov') ibovData.push(pt);
            else smallData.push(pt);
        }

        var sel = ixSelectedTicker;
        function styleDS(label, points, baseColor, hlColor) {
            var bg = [], border = [], radius = [], hoverR = [];
            for (var i = 0; i < points.length; i++) {
                if (sel && points[i].ticker === sel) {
                    bg.push(hlColor); border.push(hlColor); radius.push(10); hoverR.push(14);
                } else if (sel) {
                    bg.push('rgba(255,255,255,0.04)'); border.push('rgba(255,255,255,0.08)'); radius.push(3); hoverR.push(5);
                } else {
                    bg.push(baseColor); border.push(baseColor.replace('0.5','0.9')); radius.push(5); hoverR.push(8);
                }
            }
            return { label, data: points, pointBackgroundColor: bg, pointBorderColor: border, pointBorderWidth: 1, pointRadius: radius, pointHoverRadius: hoverR };
        }

        var datasets = [];
        if (ibovData.length) datasets.push(styleDS('Ibovespa', ibovData, 'rgba(0,255,65,0.5)', 'rgba(0,255,65,1)'));
        if (smallData.length) datasets.push(styleDS('Small/Mid Caps', smallData, 'rgba(255,170,0,0.5)', 'rgba(255,200,0,1)'));

        try {
            ixChartInstance = new Chart(ctx, {
                type: 'scatter',
                data: { datasets },
                options: {
                    responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
                    onClick: function(e, elements) {
                        if (elements.length > 0) {
                            var el = elements[0];
                            var ticker = this.data.datasets[el.datasetIndex].data[el.index].ticker;
                            ixSelectedTicker = (ixSelectedTicker === ticker) ? null : ticker;
                            if (stockData && stockData.length) ixUpdateAll(stockData);
                        }
                    },
                    plugins: {
                        legend: { labels: { color: '#4dff79', font: { size: 10 } } },
                        tooltip: {
                            backgroundColor: '#0d0d0d', borderColor: '#00ff41', borderWidth: 1,
                            titleColor: '#00ff41', bodyColor: '#4dff79',
                            callbacks: {
                                title: function(items) { var it = items[0]; return it.raw && it.raw.ticker ? it.raw.ticker : ''; },
                                label: function(ctx) {
                                    var d = ctx.raw; if (!d) return '';
                                    var ret = d.y >= 0 ? '+' + d.y.toFixed(2) + '%' : d.y.toFixed(2) + '%';
                                    return ' Retorno: ' + ret + '  Risco: ' + d.x.toFixed(2);
                                }
                            }
                        }
                    },
                    scales: {
                        x: { title: { display: true, text: 'Risco (Score)', color: '#4dff79', font: { size: 11 } }, grid: { color: '#1a1a1a' }, ticks: { color: '#4dff79', font: { size: 9 } } },
                        y: { title: { display: true, text: 'Retorno Esperado (%)', color: '#4dff79', font: { size: 11 } }, grid: { color: '#1a1a1a' }, ticks: { color: '#4dff79', font: { size: 9 }, callback: function(v) { return v >= 0 ? '+' + v.toFixed(1) + '%' : v.toFixed(1) + '%'; } } }
                    }
                }
            });
        } catch(e) { console.error('Chart error:', e); }
    }

    function ixUpdateAll(stockArray) {
        var dataPoints = [];
        for (var i = 0; i < stockArray.length; i++) {
            var s = stockArray[i];
            if (!s.price || s.price <= 0) continue;
            var retorno = (s.upside !== undefined && s.upside > -100) ? s.upside : (s.expected_return_3m || 0);
            var risco = ixCalcRisk(s);
            dataPoints.push({ ticker: s.ticker, retorno: retorno, risco: risco, category: ixClassify(s.ticker) });
        }

        var indicator = document.getElementById('ix-selection-indicator');
        var label = document.getElementById('ix-selected-label');
        if (ixSelectedTicker && indicator && label) {
            indicator.style.display = 'inline';
            label.textContent = ixSelectedTicker;
        } else if (indicator) {
            indicator.style.display = 'none';
        }

        ixRenderChart(dataPoints);
    }

    window.ixClearSelection = function() {
        ixSelectedTicker = null;
        if (stockData && stockData.length) ixUpdateAll(stockData);
    };

    function ixSetupTableClick() {
        document.getElementById('stock-table-body').addEventListener('click', function(e) {
            var tr = e.target.closest('tr');
            if (!tr) return;
            var tickerCell = tr.querySelector('.ticker-cell');
            if (!tickerCell) return;
            var ticker = tickerCell.textContent.trim();
            ixSelectedTicker = (ixSelectedTicker === ticker) ? null : ticker;
            if (stockData && stockData.length) ixUpdateAll(stockData);
        });
    }

    function formatNumber(num) {
        if (num === null || num === undefined || isNaN(num)) return '-';
        if (num === Infinity) return '∞';
        return num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    function formatCurrency(num) {
        if (num === null || num === undefined || isNaN(num) || num === 0) return '-';
        return 'R$ ' + num.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    let currentFilter = 'all';
    let searchQuery = '';

    function applyFilters() {
        let filtered = stockData;
        
        if (currentFilter !== 'all') {
            filtered = filtered.filter(stock => stock.category === currentFilter);
        }
        
        if (searchQuery) {
            filtered = filtered.filter(stock => stock.ticker.includes(searchQuery));
        }
        
        renderTable(filtered);
        updateStats(filtered);
    }

    // Search functionality
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toUpperCase();
            applyFilters();
        });
    }

    // Filter Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Update active state
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            
            currentFilter = e.target.getAttribute('data-filter');
            applyFilters();
        });
    });

    if (refreshBtn) {
        refreshBtn.addEventListener('click', fetchData);
    }



    // Setup scatter chart interaction
    ixSetupTableClick();

    // Initial fetch
    fetchData();
});
