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



    // Initial fetch
    fetchData();
});
