<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Multi-Chain Crypto Dashboard</title>
    <style>
        body { font-family: sans-serif; background-color: #1a1a1a; color: #f0f0f0; margin: 0; padding: 20px; }
        h1 { text-align: center; color: #4d94ff; margin-bottom: 40px;}
        .chain-section { margin-bottom: 40px; }
        .chain-title { font-size: 2em; color: #f0f0f0; text-transform: capitalize; border-bottom: 2px solid #4d94ff; padding-bottom: 10px; margin-bottom: 20px; }
        .card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .card { background-color: #2c2c2c; border-radius: 8px; padding: 15px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); transition: transform 0.2s ease, box-shadow 0.2s ease; display: flex; flex-direction: column; justify-content: space-between; height: 100%; box-sizing: border-box; }
        .card:hover { transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.3); }
        .card h2 { margin: 0 0 10px; font-size: 1.2em; color: #ffcc00; word-break: break-all; }
        .card p { margin: 5px 0; font-size: 0.9em; }
        .card span { font-weight: bold; color: #ffffff; }
        #last-updated { text-align: center; margin-top: 20px; color: #aaa; }
        .message { text-align: center; font-size: 1.2em; padding: 20px; margin: 20px; border-radius: 8px; }
        .loading { color: #aaa; background-color: #2c2c2c; }
        .error { color: #ffffff; background-color: #d32f2f; font-family: monospace; }
        a { color: inherit; text-decoration: none; }
        .gmgn-button { display: inline-block; margin-top: 15px; padding: 8px 12px; background-color: #3d3d3d; color: #4d94ff; text-align: center; border-radius: 5px; font-weight: bold; font-size: 0.8em; transition: background-color 0.2s ease; }
        .gmgn-button:hover { background-color: #555; }
        .positive { color: #4caf50; }
        .negative { color: #f44336; }
    </style>
</head>
<body>

    <h1>Multi-Chain Dex Screener</h1>
    <div id="data-container">
        <p class="message loading">Loading data for all chains, please wait...</p>
    </div>
    <p id="last-updated"></p>

    <script>
        const dataContainer = document.getElementById('data-container');
        const lastUpdatedElem = document.getElementById('last-updated');

        async function fetchData() {
            try {
                const response = await fetch('/api/data');
                const result = await response.json();

                if (result.error) {
                    dataContainer.innerHTML = `<div class="message error"><strong>Error:</strong><br>${result.error}</div>`;
                    return;
                }

                const chainsDataArray = result.data;
                dataContainer.innerHTML = ''; 

                // *** تغییر اصلی: حالا به جای آبجکت، روی یک لیست (آرایه) حلقه می‌زنیم ***
                chainsDataArray.forEach(chainObject => {
                    const chainName = chainObject.chain;
                    const pairs = chainObject.pairs;

                    const section = document.createElement('div');
                    section.className = 'chain-section';
                    const title = document.createElement('h2');
                    title.className = 'chain-title';
                    title.textContent = chainName;
                    section.appendChild(title);
                    const cardGrid = document.createElement('div');
                    cardGrid.className = 'card-grid';

                    if (pairs.length === 0) {
                        cardGrid.innerHTML = `<p class="message loading">No pairs found for ${chainName} matching the criteria...</p>`;
                    } else {
                        pairs.forEach(pair => {
                            // ... (بقیه این بخش بدون تغییر است)
                            if (!pair || !pair.baseToken || !pair.quoteToken) return;
                            const card = document.createElement('div');
                            card.className = 'card';
                            const getSafeSymbol = (token) => token && token.symbol ? token.symbol : 'N/A';
                            const getSafeNumber = (num) => num ? parseInt(num).toLocaleString() : 'N/A';
                            const getSafePrice = (price) => price ? parseFloat(price).toFixed(6) : 'N/A';
                            const getPriceChange = (priceChange) => {
                                if (priceChange === undefined || priceChange === null) return 'N/A';
                                const value = parseFloat(priceChange);
                                const className = value >= 0 ? 'positive' : 'negative';
                                const sign = value >= 0 ? '+' : '';
                                return `<span class="${className}">${sign}${value.toFixed(2)}%</span>`;
                            };
                            const baseSymbol = getSafeSymbol(pair.baseToken);
                            const quoteSymbol = getSafeSymbol(pair.quoteToken);
                            const priceUsd = getSafePrice(pair.priceUsd);
                            const liquidity = getSafeNumber(pair.liquidity ? pair.liquidity.usd : null);
                            const marketCap = getSafeNumber(pair.fdv);
                            const volume24h = getSafeNumber(pair.volume ? pair.volume.h24 : null);
                            const change6h = getPriceChange(pair.priceChange ? pair.priceChange.h6 : null);
                            const change24h = getPriceChange(pair.priceChange ? pair.priceChange.h24 : null);
                            const gmgnUrl = `https://gmgn.ai/${pair.chainId}/token/${pair.baseToken.address}`;
                            const dexscreenerUrl = `https://dexscreener.com/${pair.chainId}/${pair.pairAddress}`;
                            card.innerHTML = `
                                <div>
                                    <a href="${dexscreenerUrl}" target="_blank" rel="noopener noreferrer"><h2>${baseSymbol} / ${quoteSymbol}</h2></a>
                                    <p>Price (USD): <span>$${priceUsd}</span></p>
                                    <p>Liquidity: <span>$${liquidity}</span></p>
                                    <p>Market Cap: <span>$${marketCap}</span></p>
                                    <p>Volume (24h): <span>$${volume24h}</span></p>
                                    <p>Change (6h): ${change6h}</p>
                                    <p>Change (24h): ${change24h}</p>
                                </div>
                                <div>
                                    <a href="${gmgnUrl}" target="_blank" rel="noopener noreferrer" class="gmgn-button">Check Security on GMGN</a>
                                </div>
                            `;
                            cardGrid.appendChild(card);
                        });
                    }
                    section.appendChild(cardGrid);
                    dataContainer.appendChild(section);
                });
                
                lastUpdatedElem.textContent = `Last Updated: ${new Date().toLocaleTimeString()}`;

            } catch (error) {
                console.error('Error in fetchData function:', error);
                dataContainer.innerHTML = `<div class="message error">A critical error occurred: ${error.message}. Please check the console.</div>`;
            }
        }

        fetchData();
        setInterval(fetchData, 60000);
    </script>

</body>
</html>
