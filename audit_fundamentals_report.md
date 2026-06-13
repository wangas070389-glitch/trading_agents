# yfinance Fundamentals Coverage Audit

**Universe:** 27 tickers (22 BMV + 5 US)

## Summary

- Fetchable: 27/27
- DCF-usable: 23/27 (85%)
- BMV usable: 18/22 (82%)
- US usable: 5/5 (100%)

A ticker is **DCF-usable** when shares outstanding, EBITDA, net income, debt, and cash are all present and shares are positive. Without these the DCF engine produces meaningless intrinsic values.

## Per-Ticker Detail

| Ticker | Usable | Shares | Mkt Cap | NetInc TTM | EBITDA | Debt | Cash | Beta | Issues |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| AMXB.MX | OK | 60.07B | 1432.13B | 87.52B | 375.66B | 745.43B | 92.90B | 0.23 | — |
| FEMSAUBD.MX | OK | 2.02B | 913.40B | 29.37B | 105.55B | 257.76B | 106.90B | 0.17 | — |
| WALMEX.MX | OK | 17.29B | 895.91B | 50.07B | 97.48B | 81.27B | 28.09B | 0.03 | — |
| GFNORTEO.MX | PARTIAL | 2.77B | 507.06B | 61.32B | — | 670.46B | 110.44B | 0.16 | missing ttm_ebitda |
| GMEXICOB.MX | OK | 7.79B | 1608.54B | 5.66B | 10.98B | 10.67B | 9.99B | 1.05 | — |
| CEMEXCPO.MX | OK | 0.00 | 324.82B | 502.60M | 3.03B | 6.24B | 686.97M | 0.83 | shares_outstanding not positive (0) |
| BIMBOA.MX | OK | 4.30B | 250.66B | 11.71B | 59.20B | 193.80B | 19.57B | 0.28 | — |
| GAPB.MX | OK | 519.23M | 236.19B | 10.00B | 21.66B | 63.83B | 23.19B | 0.25 | — |
| ASURB.MX | OK | 277.05M | 147.04B | 9.79B | 20.00B | 35.35B | 13.81B | 0.18 | — |
| OMAB.MX | OK | 336.40M | 82.41B | 5.29B | 9.77B | 13.58B | 3.66B | 0.36 | — |
| GRUMAB.MX | OK | 341.24M | 100.15B | 493.99M | 1.11B | 1.84B | 419.12M | -0.00 | — |
| ALFAA.MX | PARTIAL | — | — | — | — | — | — | — | missing shares_outstanding; missing market_cap; missing ttm_net_income |
| KIMBERA.MX | OK | 1.56B | 109.62B | 7.77B | 14.07B | 31.31B | 20.36B | 0.25 | — |
| AC.MX | OK | 1.70B | 356.18B | 19.23B | 48.65B | 67.17B | 36.06B | 0.06 | — |
| ORBIA.MX | OK | 1.93B | 42.42B | -441.00M | 962.00M | 5.69B | 884.00M | 0.71 | missing trailing_pe |
| PE&OLES.MX | OK | 397.48M | 320.91B | 1.85B | 4.23B | 3.99B | 3.81B | 1.06 | — |
| PINFRA.MX | OK | 325.41M | 102.77B | 15.23B | 24.15B | 10.94B | 39.57B | 0.39 | — |
| BBAJIOO.MX | PARTIAL | 1.19B | 62.76B | 8.63B | — | 63.08B | 65.65B | — | missing ttm_ebitda; missing beta |
| GENTERA.MX | PARTIAL | 1.58B | 59.82B | 8.54B | — | 48.79B | 10.03B | 0.04 | missing ttm_ebitda |
| CUERVO.MX | OK | 3.59B | 51.25B | 7.87B | 9.53B | 20.73B | 11.47B | 0.26 | — |
| GCC.MX | OK | 326.16M | 64.88B | 306.33M | 493.21M | 660.86M | 857.32M | 0.45 | — |
| VESTA.MX | OK | 920.14M | 53.95B | 328.00M | 223.31M | 1.18B | 206.10M | 0.26 | — |
| NVDA | OK | 24.22B | 4962.16B | 159.61B | 165.51B | 12.81B | 53.17B | 2.20 | — |
| AAPL | OK | 14.69B | 4342.02B | 122.58B | 159.98B | 84.71B | 68.51B | 1.09 | — |
| MSFT | OK | 7.43B | 2899.62B | 125.22B | 184.46B | 125.43B | 78.23B | 1.10 | — |
| AMZN | OK | 10.76B | 2597.95B | 90.80B | 155.86B | 235.54B | 143.09B | 1.44 | missing dividend_rate |
| GOOGL | OK | 5.86B | 4362.98B | 160.21B | 161.32B | 95.88B | 126.84B | 1.24 | — |
