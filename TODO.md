Bugs
- Why are the bars rectangular? they should show the gain over the period

Improvements
--
- Allow reference date selection: Ex div, earnings, 1st of  year, 1st of quarter, 1st of month, 1st of week, or daily (e.g. reinvest as largest changes)
- Add additional breakout conditions to e.g. stop trading on major events 

Done
--
- Allow the number of pools to be specified, so the user can try to optimise time in the market
- For the top n stocks, allow n to be changed
- Return of each stock over the period (and compare with the strategy)
- Add information on trades missed due to lack of free capital 
- Cache downloaded data
- The web page now renders progressively
- Flag and rule out any invalid tickers (show the return codes)
- Rule out any tickers with missing data
- At top of page, put a table sumarising range of dates for each stock for dividends, earnings, prices
- Add the leaderboard chart to the web page

No change required
--
- In the diagnostics text, report on missed trades (due to not enough pools)
- Simulation with these tickers (AAPL.US,MSFT.US,LLY.US,JPM.US,AVGO.US,UNH.US,V.US,PG.US,JNJ.US,NVDA) shows NVDA investments before there were dividends. The chart captions are possibly misleading (probably AVGO labeled chart is NVDA)
