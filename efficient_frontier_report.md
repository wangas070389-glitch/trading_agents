# Strategy Portfolio Efficient Frontier Optimization Report

**Period Evaluated:** 2022-06-21 to 2026-07-01

## 1. Individual Strategy Annualized Metrics
| Strategy Component | Annualized Return | Annualized Volatility | Sharpe Ratio (Rf=9.5%) |
| :--- | :---: | :---: | :---: |
| S1 Alpha Growth | 39.17% | 18.71% | 1.59 |
| S2 MACD Trend | 25.95% | 10.98% | 1.50 |
| S4 US DCS | 26.34% | 17.81% | 0.95 |
| S5 Alternatives | 9.93% | 5.79% | 0.07 |
| S6 High Beta | 11.14% | 8.78% | 0.19 |
| S8 Dividends | 17.07% | 11.55% | 0.65 |

## 2. Correlation Matrix
| | S1 Alpha Growth | S2 MACD Trend | S4 US DCS | S5 Alternatives | S6 High Beta | S8 Dividends |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| S1 Alpha Growth | 1.000 | 0.747 | 0.226 | 0.192 | 0.157 | 0.536 |
| S2 MACD Trend | 0.747 | 1.000 | 0.324 | 0.192 | 0.211 | 0.483 |
| S4 US DCS | 0.226 | 0.324 | 1.000 | 0.041 | 0.555 | 0.178 |
| S5 Alternatives | 0.192 | 0.192 | 0.041 | 1.000 | 0.090 | 0.099 |
| S6 High Beta | 0.157 | 0.211 | 0.555 | 0.090 | 1.000 | 0.094 |
| S8 Dividends | 0.536 | 0.483 | 0.178 | 0.099 | 0.094 | 1.000 |

## 3. Key Optimized Portfolios
| Portfolio | Annualized Return | Annualized Volatility | Sharpe Ratio | Description |
| :--- | :---: | :---: | :---: | :--- |
| **Maximum Sharpe (MSR)** | 31.65% | 12.81% | **1.73** | Portfolio that maximizes return-to-risk |
| **Global Minimum Variance (GMV)** | 11.48% | 4.79% | 0.41 | Portfolio with the absolute lowest risk |
| **Current Target Allocation (S7)** | 23.77% | 9.86% | 1.45 | S4=30%, S1=25%, S8=20%, S6=15%, S5=10% |

## 4. Portfolio Allocation Comparison
| Asset Strategy | Current Target Weight % | Max Sharpe (MSR) % | Min Variance (GMV) % |
| :--- | :---: | :---: | :---: |
| S1 Alpha Growth | 25.0% | 42.5% | 0.0% |
| S2 MACD Trend | 0.0% | 35.4% | 2.8% |
| S4 US DCS | 30.0% | 22.2% | 0.0% |
| S5 Alternatives | 10.0% | 0.0% | 61.8% |
| S6 High Beta | 15.0% | 0.0% | 24.0% |
| S8 Dividends | 20.0% | 0.0% | 11.4% |

## 5. Efficient Frontier Visual Mapping (ASCII Plot)

```text
   Annualized Return
     ^
  43.1% |                                                             
  40.9% |                                                             
  38.7% |                                                    o        
  36.5% |                                             o               
  34.3% |                                       o                     
  32.2% |                                  o                          
  30.0% |                              o*                             
  27.8% |                          o                                  
  25.6% |                       o                                     
  23.4% |                   oX                                        
  21.3% |            o   o                                            
  19.1% |         o                                                   
  16.9% |       o                                                     
  14.7% |     o                                                       
  12.5% |   o                                                         
  10.3% |  #                                                          
        +------------------------------------------------------------
         4.3%                                             20.6%   Annualized Volatility
```

### Legend:
* **`o`** : Efficient Frontier boundary (minimum risk portfolios for any target return)
* **`*`** : **Max Sharpe Ratio (MSR)** Portfolio
* **`#`** : **Global Minimum Variance (GMV)** Portfolio
* **`X`** : **Current Target Allocation (S7)** Portfolio