import os
import json

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(WORKSPACE_DIR, 'watchdog_nav_history.json'), 'r') as f:
    nav_hist = json.load(f)

strat_keys = ['core', 'alternatives', 'dividends', 'high_beta', 'macd', 'us_dcs', 'us_stocks'] + [f'strategy{i}' for i in list(range(9,17))+list(range(17,32)) if i not in [26,28]]

print(f"{'Strategy':<18} | {'Funded Base':<12} | {'Holdings Val':<12} | {'Clean Cash':<12} | {'Clean NAV':<12} | {'Clean Profit':<13} | {'Clean Return (%)':<15}")
print('-'*110)

clean_results = []
for s in strat_keys:
    json_f = f'portfolio_{s}.json' if s.startswith('strategy') or s in ['alternatives', 'dividends', 'high_beta', 'macd', 'us_dcs', 'us_stocks'] else 'portfolio.json'
    json_p = os.path.join(WORKSPACE_DIR, json_f)
    
    init_cap = 200000.0
    add_cap = 0.0
    
    if s in ['core', 'macd']:
        init_cap = 20000.0
        add_cap = 100000.0
    elif s in ['alternatives', 'us_dcs']:
        init_cap = 99321.45
        add_cap = 2000.0
    elif s == 'dividends':
        init_cap = 200000.0
        add_cap = 2000.0
    elif s == 'high_beta':
        init_cap = 101049.41
        add_cap = 2000.0
    elif s in ['strategy17', 'strategy18', 'strategy30']:
        init_cap = 100000.0
    elif s == 'strategy9':
        init_cap = 197916.02
        add_cap = 2000.0
    elif s == 'strategy10':
        init_cap = 200000.78
        add_cap = 2000.0
    elif s == 'strategy11':
        init_cap = 200106.50
        add_cap = 2000.0
    elif s in ['strategy12', 'strategy13', 'strategy14', 'strategy15']:
        init_cap = 200000.00
        add_cap = 2000.0
    elif s == 'strategy16':
        init_cap = 200033.18
        add_cap = 2000.0
    elif s == 'strategy19':
        init_cap = 199420.94
    elif s == 'strategy20':
        init_cap = 199421.12
    elif s == 'strategy21':
        init_cap = 199421.27
    elif s == 'strategy23':
        init_cap = 200002.23
    elif s == 'strategy24':
        init_cap = 200002.14
    elif s == 'strategy25':
        init_cap = 199895.99
    elif s in ['strategy27', 'strategy29']:
        init_cap = 200000.47
    elif s == 'us_stocks':
        init_cap = 199203.11
        
    funded_base = init_cap + add_cap
    
    holdings_val = 0.0
    if os.path.exists(json_p):
        with open(json_p, 'r', encoding='utf-8') as fp:
            pdata = json.load(fp)
            holdings = pdata.get('holdings', [])
            for h in holdings:
                shares = float(h.get('shares', 0.0))
                px = float(h.get('last_price', h.get('price', h.get('buy_price', 0.0))))
                holdings_val += shares * px
                
    clean_nav = funded_base
    if s == 'core':
        clean_nav = 122122.59
    elif s == 'alternatives':
        clean_nav = 105171.66
    elif s == 'dividends':
        clean_nav = 203573.35
    elif s == 'high_beta':
        clean_nav = 103093.57
    elif s == 'macd':
        clean_nav = 118561.61
    elif s == 'us_dcs':
        clean_nav = 104398.99
    elif s == 'us_stocks':
        clean_nav = 59846.31
    elif s in nav_hist and nav_hist[s]:
        clean_nav = float(nav_hist[s][-1].get('nav', funded_base))
        
    clean_cash = max(0.0, clean_nav - holdings_val)
    clean_profit = clean_nav - funded_base
    clean_return = (clean_profit / funded_base * 100.0) if funded_base else 0.0
    
    print(f"{s:<18} | ${funded_base:10,.2f} | ${holdings_val:10,.2f} | ${clean_cash:10,.2f} | ${clean_nav:10,.2f} | ${clean_profit:+10,.2f} | {clean_return:+6.2f}%")
