Web simulation

Bugs
- Simulation with these tickers shows NVDA investments before there were dividends. 
  The chart captions are possibly misleading (probably AVGO labeled chart is NVDA)
  AAPL.US,MSFT.US,LLY.US,JPM.US,AVGO.US,UNH.US,V.US,PG.US,JNJ.US,NVDA

Diagnose missing/limited data
- At top of page, put a table sumarising range of dates for each stock for dividends, earnings, prices
- Rule out any tickers with missing data

Add information on trades missed due to lack of free capital 
(note can sort of see this on free capital the chart)
- In the diagnostics text, report on missed trades (due to not enough pools)
- Allow the number of pools to be specified, so the user can try to optimise time in the market

Advanced capabilities
- Allow reference date selection: Ex div, earnings, 1st of  year, 1st of quarter, 1st of month, 1st of week

Helpful reporting
- Return of each stock over the period (put it on the title of each ticker chart)
