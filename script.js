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
            const response = await fetch('http://localhost:5000/api/valuation');
            if (!response.ok) throw new Error('Falha ao buscar dados');
            
            stockData = await response.json();
            renderTable(stockData);
            updateStats(stockData);
        } catch (error) {
            console.error('Erro:', error);
            alert('Erro ao conectar com o servidor. Certifique-se de que o server.py está rodando.');
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
                <td class="ticker-cell">${stock.ticker}</td>
                <td>R$ ${formatNumber(stock.price)}</td>
                <td>R$ ${formatNumber(stock.valuation_graham)}</td>
                <td>R$ ${formatNumber(stock.valuation_dcf)}</td>
                <td class="${upsideClass}">${upside.toFixed(2)}% ${upsideIcon}</td>
                <td>${formatNumber(stock.p_e)}</td>
                <td>${formatNumber(stock.p_b)}</td>
                <td>${formatNumber(stock.dividend_yield)}%</td>
                <td><span class="status-badge ${status.class}">${status.label}</span></td>
            `;
            tableBody.appendChild(row);
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
