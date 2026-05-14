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

    async function fetchData() {
        loadingOverlay.classList.remove('hidden');
        try {
            let response;
            try {
                response = await fetch('http://localhost:5000/api/valuation');
            } catch (e) {
                response = await fetch('data.json');
            }

            if (!response.ok) throw new Error('Falha ao buscar dados');
            
            const rawData = await response.json();
            
            // Suporte para o novo formato com metadados
            if (rawData.stocks) {
                stockData = rawData.stocks;
                renderTable(stockData);
                updateStats(stockData);
                renderPredictions(stockData, rawData.model_info);
                
                if (rawData.last_update) {
                    document.getElementById('last-updated').textContent = `[Atualizado: ${rawData.last_update}]`;
                }
            } else {
                // Legado: se vier apenas o array
                stockData = rawData;
                renderTable(stockData);
                updateStats(stockData);
            }
            
        } catch (error) {
            console.error('Erro:', error);
            alert('Erro ao conectar com o servidor. Verifique o console.');
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

        // Pegar top 5 por expected_return
        const top5 = [...data]
            .filter(s => s.expected_return !== undefined)
            .sort((a, b) => b.expected_return - a.expected_return)
            .slice(0, 5);

        container.innerHTML = '';
        top5.forEach((stock, index) => {
            const card = document.createElement('div');
            card.className = 'prediction-card';
            
            card.innerHTML = `
                <div class="rank">#${index + 1}</div>
                <div class="ticker">${stock.ticker}</div>
                <div class="prediction-label">Retorno Esperado (3m)</div>
                <div class="prediction-value">${stock.expected_return.toFixed(2)}%</div>
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
        bestTickerEl.textContent = sortedByUpside[0].ticker;
        
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

    // Search functionality
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toUpperCase();
        const filtered = stockData.filter(stock => stock.ticker.includes(query));
        renderTable(filtered);
    });

    refreshBtn.addEventListener('click', fetchData);

    // Initial fetch
    fetchData();
});
